import pytest
from pathlib import Path
from hermes_dotz.protocol import DotConfig
from hermes_dotz.registry import ProviderRegistry
from hermes_dotz.store import DotzStore


@pytest.fixture
def test_env(tmp_path):
    root = tmp_path / "runtime"
    store = DotzStore(root / "dotz.db")
    reg = ProviderRegistry(root, store)
    return root, store, reg


def test_registry_registers_three_built_in_providers(test_env):
    root, store, reg = test_env
    descriptors = reg.list_descriptors()
    ids = {d["id"] for d in descriptors}
    assert "open-dotz" in ids
    assert "drex-dotz" in ids
    assert "gpt-dotz" in ids

    # Check feature matrices
    open_desc = next(d for d in descriptors if d["id"] == "open-dotz")
    assert open_desc["features"]["tool_execution"] is True
    assert open_desc["features"]["drex_governance"] is False
    assert open_desc["features"]["receipts"] is False
    assert open_desc["governance"] == "Provider-managed"

    drex_desc = next(d for d in descriptors if d["id"] == "drex-dotz")
    assert drex_desc["features"]["drex_governance"] is True
    assert drex_desc["features"]["receipts"] is True
    assert drex_desc["features"]["approvals"] is True
    assert drex_desc["governance"] == "Drex"

    gpt_desc = next(d for d in descriptors if d["id"] == "gpt-dotz")
    assert gpt_desc["features"]["tool_execution"] is False
    assert gpt_desc["features"]["drex_governance"] is False
    assert gpt_desc["features"]["receipts"] is False
    assert gpt_desc["governance"] == "Provider-managed"


def test_open_dot_lifecycle(test_env):
    root, store, reg = test_env
    cfg = DotConfig(
        name="ResearchWorker",
        provider="open-dotz",
        mission="Continuous literature survey",
        workspace=str(root / "ws_research"),
    )
    detail = reg.create_dot(cfg)
    assert detail.summary.name == "ResearchWorker"
    assert detail.summary.state == "IDLE"
    assert detail.summary.provider == "open-dotz"

    # Assign task
    assign_res = reg.get("open-dotz").assign_task("ResearchWorker", "Scan arXiv for new agents")
    assert assign_res["status"] == "assigned"
    assert "Scan arXiv" in assign_res["result"]

    # Steer
    steer_res = reg.get("open-dotz").steer_dot("ResearchWorker", "Focus on memory benchmarks")
    assert steer_res["status"] == "assigned"

    # Stop and start
    stopped = reg.get("open-dotz").stop_dot("ResearchWorker")
    assert stopped.summary.state == "STOPPED"
    started = reg.get("open-dotz").start_dot("ResearchWorker")
    assert started.summary.state == "IDLE"

    # Activity events recorded
    activity = reg.get("open-dotz").get_activity("ResearchWorker")
    assert len(activity) >= 3
    event_types = [e.event_type for e in activity]
    assert "task_created" in event_types
    assert "task_completed" in event_types


def test_gpt_dot_lifecycle_and_boundaries(test_env):
    root, store, reg = test_env
    cfg = DotConfig(
        name="PlanningAssistant",
        provider="gpt-dotz",
        mission="Maintain high-level milestone plans",
        default_model="gpt-4o",
    )
    detail = reg.create_dot(cfg)
    assert detail.summary.name == "PlanningAssistant"
    assert detail.summary.provider == "gpt-dotz"
    assert detail.features.tool_execution is False

    # Task assignment
    task_res = reg.get("gpt-dotz").assign_task("PlanningAssistant", "Draft release checklist")
    assert task_res["status"] == "assigned"
    assert "Draft release checklist" in task_res["result"]

    # Security boundary check: executing action without permissions fails safely
    action_res = reg.get("gpt-dotz").execute_action(
        "PlanningAssistant", "files.read", "file_read", {"path": "/etc/passwd"}
    )
    assert action_res["decision"] == "BLOCK"
    assert action_res["upstream_executed"] is False
    assert action_res["rule"] == "GPT_DOT_NO_TOOL_PRIVILEGE"


def test_drex_dot_governance_and_receipts(test_env):
    root, store, reg = test_env
    ws = root / "ws_dev"
    ws.mkdir(parents=True, exist_ok=True)
    readme = ws / "README.md"
    readme.write_text("Drex governed project", encoding="utf-8")

    cfg = DotConfig(
        name="DevWorker",
        provider="drex-dotz",
        mission="Write and test bounded software changes",
        workspace=str(ws),
        capabilities_allow=["files.read", "repo.read"],
        capabilities_deny=["secrets.read", "filesystem.unrestricted"],
    )
    detail = reg.create_dot(cfg)
    assert detail.summary.provider == "drex-dotz"
    assert detail.features.drex_governance is True

    # 1. ALLOW action
    allow_res = reg.get("drex-dotz").execute_action(
        "DevWorker", "files.read", "file_read", {"path": str(readme)}
    )
    assert allow_res["decision"] == "ALLOW"
    assert allow_res["upstream_executed"] is True
    assert allow_res["result"] == "Drex governed project"

    # 2. BLOCK action
    block_res = reg.get("drex-dotz").execute_action(
        "DevWorker", "secrets.read", "file_read", {"path": "~/.ssh/id_rsa"}
    )
    assert block_res["decision"] == "BLOCK"
    assert block_res["upstream_executed"] is False

    # 3. Mutation requires grant
    target_write = ws / "output.txt"
    mutation_res = reg.get("drex-dotz").execute_action(
        "DevWorker", "files.read", "file_write", {"path": str(target_write), "content": "Canary"}
    )
    assert mutation_res["decision"] == "BLOCK"
    assert mutation_res["rule"] == "MUTATION_GRANT_REQUIRED"

    # Approvals listed
    approvals = reg.get("drex-dotz").list_approvals("DevWorker")
    assert len(approvals) >= 1
    appr = approvals[0]
    assert appr.action == "file_write"

    # Approve grant
    grant_res = reg.get("drex-dotz").approve_action(
        "DevWorker", appr.approval_id, ttl_seconds=300.0, max_uses=5
    )
    assert grant_res["status"] == "approved"
    assert "grant_id" in grant_res

    # Receipts recorded
    receipts = reg.get("drex-dotz").get_receipts("DevWorker")
    decisions = [r["decision"] for r in receipts]
    assert "ALLOW" in decisions
    assert "BLOCK" in decisions
    assert "GRANT" in decisions


def test_external_nova_provider_registration(test_env):
    """Phase 10 & 17: prove private NOVA provider can register externally without modifying bridge."""
    root, store, reg = test_env

    # Define mock external private NOVA extension
    from hermes_dotz.providers.drex_dot import DrexDotzProvider
    from hermes_dotz.protocol import ProviderFeatures

    class ExternalNovaDotzProvider(DrexDotzProvider):
        @property
        def id(self) -> str:
            return "nova-dotz"

        @property
        def name(self) -> str:
            return "NOVA Dot"

        @property
        def description(self) -> str:
            return "Proprietary NOVA Frontier delegated engineering agent."

        @property
        def governance(self) -> str:
            return "NOVA + Drex"

        @property
        def features(self) -> ProviderFeatures:
            f = super().features
            return f

    # Register external extension
    reg.register(ExternalNovaDotzProvider(root, store))

    descriptors = reg.list_descriptors()
    ids = [d["id"] for d in descriptors]
    assert "nova-dotz" in ids

    # Create dot using external provider
    cfg = DotConfig(
        name="NovaEngineer",
        provider="nova-dotz",
        mission="Frontier code synthesis",
    )
    detail = reg.create_dot(cfg)
    assert detail.summary.name == "NovaEngineer"
    assert detail.summary.provider == "nova-dotz"
    assert detail.summary.governance == "NOVA + Drex"
