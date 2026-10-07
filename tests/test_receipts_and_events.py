import pytest
from pathlib import Path
from hermes_dotz.protocol import DotConfig
from hermes_dotz.registry import ProviderRegistry
from hermes_dotz.store import DotzStore


@pytest.fixture
def env(tmp_path):
    root = tmp_path / "runtime"
    store = DotzStore(root / "dotz.db")
    reg = ProviderRegistry(root, store)
    return root, store, reg


def test_normalized_event_timeline(env):
    root, store, reg = env
    cfg = DotConfig(
        name="TimelineWorker",
        provider="open-dotz",
        mission="Test normalized timeline",
        workspace=str(root / "ws_timeline"),
    )
    reg.create_dot(cfg)

    # 1. task_created event from creation
    activity = reg.get("open-dotz").get_activity("TimelineWorker")
    assert any(e.event_type == "task_created" for e in activity)

    # 2. task assignment generates task_completed
    reg.get("open-dotz").assign_task("TimelineWorker", "Run smoke test")
    activity = reg.get("open-dotz").get_activity("TimelineWorker")
    assert any(e.event_type == "task_completed" for e in activity)

    # 3. message steering generates message event
    reg.get("open-dotz").steer_dot("TimelineWorker", "Adjust logging verbosity")
    activity = reg.get("open-dotz").get_activity("TimelineWorker")
    assert any(e.event_type == "message" for e in activity)

    # 4. action execution generates action_executed event
    reg.get("open-dotz").execute_action(
        "TimelineWorker", "files.write", "file_write",
        {"path": "status.txt", "content": "OK"}
    )
    activity = reg.get("open-dotz").get_activity("TimelineWorker")
    assert any(e.event_type == "action_executed" for e in activity)


def test_drex_receipts_rendered_with_details(env):
    root, store, reg = env
    cfg = DotConfig(
        name="ReceiptWorker",
        provider="drex-dotz",
        mission="Test receipt collection",
        capabilities_allow=["files.read"],
        capabilities_deny=["secrets.read"],
    )
    reg.create_dot(cfg)

    # Allow
    reg.get("drex-dotz").execute_action(
        "ReceiptWorker", "files.read", "file_read", {"path": "safe.txt"}
    )
    # Block
    reg.get("drex-dotz").execute_action(
        "ReceiptWorker", "secrets.read", "file_read", {"path": "keys.pem"}
    )

    receipts = reg.get("drex-dotz").get_receipts("ReceiptWorker")
    assert len(receipts) == 2
    # Verify raw Drex attributes preserved
    assert receipts[0]["decision"] in ("ALLOW", "BLOCK")
    assert "receipt_id" in receipts[0]
    assert "upstream_executed" in receipts[0]
