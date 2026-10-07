import pytest
from pathlib import Path
from hermes_dotz.protocol import DotConfig, ApprovalRequest
from hermes_dotz.registry import ProviderRegistry
from hermes_dotz.store import DotzStore


@pytest.fixture
def env(tmp_path):
    root = tmp_path / "runtime"
    store = DotzStore(root / "dotz.db")
    reg = ProviderRegistry(root, store)
    return root, store, reg


def test_generic_approval_contract(env):
    root, store, reg = env
    cfg = DotConfig(
        name="ReviewBot",
        provider="drex-dotz",
        mission="Test generic approval contract",
        capabilities_allow=["workspace.write"],
        capabilities_deny=["secrets.read"],
    )
    reg.create_dot(cfg)

    # Trigger action requiring approval
    res = reg.get("drex-dotz").execute_action(
        "ReviewBot", "workspace.write", "file_write",
        {"path": "config.json", "content": "{}"}
    )
    assert res["decision"] == "BLOCK"
    assert res["rule"] == "MUTATION_GRANT_REQUIRED"

    approvals = reg.get("drex-dotz").list_approvals("ReviewBot")
    assert len(approvals) == 1
    appr: ApprovalRequest = approvals[0]

    # Verify generic approval fields
    assert appr.dot_id == "ReviewBot"
    assert appr.provider == "drex-dotz"
    assert appr.action == "file_write"
    assert appr.status == "pending"
    assert appr.target == "config.json"
    assert appr.scope == "workspace.write"
    assert appr.created_at > 0

    # Test Approve
    grant = reg.get("drex-dotz").approve_action(
        "ReviewBot", appr.approval_id, ttl_seconds=600.0, max_uses=3
    )
    assert grant["status"] == "approved"
    assert grant["max_uses"] == 3

    # Approval is no longer pending
    pending_after = reg.get("drex-dotz").list_approvals("ReviewBot")
    assert len(pending_after) == 0


def test_generic_approval_denial(env):
    root, store, reg = env
    cfg = DotConfig(
        name="DenialBot",
        provider="drex-dotz",
        mission="Test denial flow",
        capabilities_allow=["workspace.write"],
    )
    reg.create_dot(cfg)

    reg.get("drex-dotz").execute_action(
        "DenialBot", "workspace.write", "file_write",
        {"path": "dangerous.sh", "content": "rm -rf /"}
    )
    approvals = reg.get("drex-dotz").list_approvals("DenialBot")
    assert len(approvals) == 1

    denial_res = reg.get("drex-dotz").deny_action("DenialBot", approvals[0].approval_id)
    assert denial_res["decision"] == "BLOCK"
    assert denial_res["upstream_executed"] is False

    pending_after = reg.get("drex-dotz").list_approvals("DenialBot")
    assert len(pending_after) == 0
