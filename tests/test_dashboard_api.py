import pytest
from pathlib import Path
from fastapi import FastAPI
from fastapi.testclient import TestClient

from hermes_dotz.dashboard_api import router
from hermes_dotz.registry import ProviderRegistry
import hermes_dotz.registry as reg_mod


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DOTZ_RUNTIME_DIR", str(tmp_path / "runtime"))
    reg_mod._default_registry = None
    app = FastAPI()
    app.include_router(router, prefix="/api/plugins/dotz")
    return TestClient(app)


def test_runtime_endpoint(client):
    resp = client.get("/api/plugins/dotz/runtime")
    assert resp.status_code == 200
    data = resp.json()
    assert data["plugin_name"] == "dotz"
    assert "bridge_version" in data


def test_providers_endpoint(client):
    resp = client.get("/api/plugins/dotz/providers")
    assert resp.status_code == 200
    providers = resp.json()["providers"]
    ids = {p["id"] for p in providers}
    assert "open-dotz" in ids
    assert "drex-dotz" in ids
    assert "gpt-dotz" in ids


def test_dots_crud_open_dot(client):
    # 1. Initially empty
    list_resp = client.get("/api/plugins/dotz/dots")
    assert list_resp.status_code == 200
    assert list_resp.json()["dots"] == []

    # 2. Create Open Dot
    create_resp = client.post(
        "/api/plugins/dotz/dots",
        json={
            "name": "Researcher",
            "provider": "open-dotz",
            "mission": "Track AI research papers",
            "default_model": "cheap",
        },
    )
    assert create_resp.status_code == 200
    create_data = create_resp.json()
    assert create_data["name"] == "Researcher"
    assert create_data["provider"] == "open-dotz"

    # 3. Get Detail
    get_resp = client.get("/api/plugins/dotz/dots/Researcher")
    assert get_resp.status_code == 200
    detail = get_resp.json()
    assert detail["name"] == "Researcher"
    assert detail["features"]["drex_governance"] is False
    assert detail["governance"] == "Provider-managed"

    # 4. Assign Task
    assign_resp = client.post(
        "/api/plugins/dotz/dots/Researcher/assign",
        json={"task": "Find latest reasoning models papers"},
    )
    assert assign_resp.status_code == 200
    assert assign_resp.json()["status"] == "assigned"

    # 5. Steer
    steer_resp = client.post(
        "/api/plugins/dotz/dots/Researcher/steer",
        json={"input": "Include benchmark evaluations"},
    )
    assert steer_resp.status_code == 200
    assert steer_resp.json()["status"] == "assigned"

    # 6. Stop and Start
    stop_resp = client.post("/api/plugins/dotz/dots/Researcher/stop")
    assert stop_resp.status_code == 200
    assert stop_resp.json()["state"] == "STOPPED"

    start_resp = client.post("/api/plugins/dotz/dots/Researcher/start")
    assert start_resp.status_code == 200
    assert start_resp.json()["state"] == "IDLE"

    # 7. Activity
    act_resp = client.get("/api/plugins/dotz/dots/Researcher/activity")
    assert act_resp.status_code == 200
    assert len(act_resp.json()["activity"]) >= 2


def test_dots_drex_governance_api(client, tmp_path):
    ws = tmp_path / "ws_drex"
    ws.mkdir(parents=True, exist_ok=True)
    sample_file = ws / "test.txt"
    sample_file.write_text("Drex governed content", encoding="utf-8")

    # Create Drex Dot
    create_resp = client.post(
        "/api/plugins/dotz/dots",
        json={
            "name": "SecOps",
            "provider": "drex-dotz",
            "mission": "Enforce infrastructure guardrails",
            "workspace": str(ws),
            "capabilities_allow": ["files.read"],
            "capabilities_deny": ["secrets.read"],
        },
    )
    assert create_resp.status_code == 200
    assert create_resp.json()["provider"] == "drex-dotz"

    # Action ALLOW
    allow_resp = client.post(
        "/api/plugins/dotz/dots/SecOps/action",
        json={
            "capability": "files.read",
            "action": "file_read",
            "args": {"path": str(sample_file)},
        },
    )
    assert allow_resp.status_code == 200
    allow_data = allow_resp.json()
    assert allow_data["decision"] == "ALLOW"
    assert allow_data["upstream_executed"] is True
    assert allow_data["result"] == "Drex governed content"

    # Action BLOCK
    block_resp = client.post(
        "/api/plugins/dotz/dots/SecOps/action",
        json={
            "capability": "secrets.read",
            "action": "file_read",
            "args": {"path": "~/.ssh/id_ed25519"},
        },
    )
    assert block_resp.status_code == 200
    block_data = block_resp.json()
    assert block_data["decision"] == "BLOCK"
    assert block_data["upstream_executed"] is False

    # Action Mutation requires approval
    write_target = ws / "audit.log"
    write_resp = client.post(
        "/api/plugins/dotz/dots/SecOps/action",
        json={
            "capability": "files.read",
            "action": "file_write",
            "args": {"path": str(write_target), "content": "Log line 1\n"},
        },
    )
    assert write_resp.status_code == 200
    assert write_resp.json()["decision"] == "BLOCK"
    assert write_resp.json()["rule"] == "MUTATION_GRANT_REQUIRED"

    # Check Approvals
    appr_resp = client.get("/api/plugins/dotz/dots/SecOps/approvals")
    assert appr_resp.status_code == 200
    approvals = appr_resp.json()["approvals"]
    assert len(approvals) >= 1
    appr_id = approvals[0]["approval_id"]

    # Approve
    approve_resp = client.post(
        f"/api/plugins/dotz/dots/SecOps/approvals/{appr_id}/approve",
        json={"ttl_seconds": 300, "max_uses": 5},
    )
    assert approve_resp.status_code == 200
    assert approve_resp.json()["status"] == "approved"

    # Check Receipts
    rcpt_resp = client.get("/api/plugins/dotz/dots/SecOps/receipts")
    assert rcpt_resp.status_code == 200
    receipts = rcpt_resp.json()["receipts"]
    assert len(receipts) >= 3
