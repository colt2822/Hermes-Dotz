"""Backend-neutral Dot bridge protocol.

Defines the contract between Hermes and underlying Dot providers:
  - Open Dotz (open / local persistent workers)
  - Drex Dotz (governed autonomous workers with Drex capability firewalls)
  - GPT Dotz (lightweight persistent LLM-backed agents)
  - External extensions (e.g., NovaDotzProvider)
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ProviderCapability(str, Enum):
    PERSISTENCE = "persistence"
    SCHEDULING = "scheduling"
    MODEL_SELECTION = "model_selection"
    TOOL_EXECUTION = "tool_execution"
    CAPABILITIES = "capabilities"
    APPROVALS = "approvals"
    RECEIPTS = "receipts"
    DREX_GOVERNANCE = "drex_governance"
    EVENTS = "events"


@dataclass
class ProviderFeatures:
    """Declared capability matrix for a Dot provider."""
    persistence: bool = True
    scheduling: bool = False
    model_selection: bool = True
    tool_execution: bool = False
    capabilities: bool = False
    approvals: bool = False
    receipts: bool = False
    drex_governance: bool = False
    events: bool = True

    def to_dict(self) -> Dict[str, bool]:
        return {
            "persistence": self.persistence,
            "scheduling": self.scheduling,
            "model_selection": self.model_selection,
            "tool_execution": self.tool_execution,
            "capabilities": self.capabilities,
            "approvals": self.approvals,
            "receipts": self.receipts,
            "drex_governance": self.drex_governance,
            "events": self.events,
        }


@dataclass
class DotSummary:
    name: str
    state: str
    mission: str
    provider: str
    governance: str
    workspace: Optional[str] = None
    created_at: Optional[float] = None
    updated_at: Optional[float] = None
    task_count: int = 0
    last_task: Optional[str] = None
    next_wake: Optional[str] = None
    blocked_reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "state": self.state,
            "mission": self.mission,
            "provider": self.provider,
            "governance": self.governance,
            "workspace": self.workspace,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "task_count": self.task_count,
            "last_task": self.last_task,
            "next_wake": self.next_wake,
            "blocked_reason": self.blocked_reason,
        }


@dataclass
class ApprovalRequest:
    approval_id: str
    provider: str
    dot_id: str
    action: str
    description: str
    scope: str
    payload_summary: str
    created_at: float
    expires_at: Optional[float] = None
    status: str = "pending"  # pending, approved, denied, expired
    target: Optional[str] = None
    task_id: Optional[str] = None
    session_id: Optional[str] = None
    capability: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "approval_id": self.approval_id,
            "provider": self.provider,
            "dot_id": self.dot_id,
            "action": self.action,
            "description": self.description,
            "scope": self.scope,
            "payload_summary": self.payload_summary,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "status": self.status,
            "target": self.target,
            "task_id": self.task_id,
            "session_id": self.session_id,
            "capability": self.capability,
            "details": self.details,
        }


@dataclass
class DotActivityEvent:
    event_id: str
    dot_id: str
    event_type: str  # task_created, task_started, message, tool_request, tool_result, approval_requested, approval_granted, approval_denied, action_executed, action_failed, task_completed
    title: str
    timestamp: float
    description: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "dot_id": self.dot_id,
            "event_type": self.event_type,
            "title": self.title,
            "timestamp": self.timestamp,
            "description": self.description,
            "details": self.details,
        }


@dataclass
class DotDetail:
    summary: DotSummary
    features: ProviderFeatures
    models: Dict[str, str] = field(default_factory=dict)
    capabilities: Dict[str, List[str]] = field(default_factory=lambda: {"allow": [], "deny": []})
    tasks: List[Dict[str, Any]] = field(default_factory=list)
    receipts: List[Dict[str, Any]] = field(default_factory=list)
    activity: List[DotActivityEvent] = field(default_factory=list)
    approvals: List[ApprovalRequest] = field(default_factory=list)
    responsibilities: List[Dict[str, Any]] = field(default_factory=list)
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        base = self.summary.to_dict()
        base.update({
            "features": self.features.to_dict(),
            "models": self.models,
            "capabilities": self.capabilities,
            "tasks": self.tasks,
            "receipts": self.receipts,
            "activity": [e.to_dict() for e in self.activity],
            "approvals": [a.to_dict() for a in self.approvals],
            "responsibilities": self.responsibilities,
            **self.extra,
        })
        return base


@dataclass
class DotConfig:
    name: str
    provider: str = "open-dotz"
    mission: str = ""
    default_model: str = "cheap"
    escalate_model: Optional[str] = None
    workspace: Optional[str] = None
    capabilities_allow: List[str] = field(default_factory=list)
    capabilities_deny: List[str] = field(default_factory=list)
    schedule: Optional[str] = None
    drex_pack: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> DotConfig:
        return cls(
            name=str(data.get("name", "")).strip(),
            provider=str(data.get("provider", "open-dotz")).strip(),
            mission=str(data.get("mission", "")).strip(),
            default_model=str(data.get("default_model", data.get("models", {}).get("default", "cheap"))),
            escalate_model=data.get("escalate_model") or data.get("models", {}).get("escalate"),
            workspace=data.get("workspace") if isinstance(data.get("workspace"), str) else (data.get("workspace", {}).get("path") if isinstance(data.get("workspace"), dict) else None),
            capabilities_allow=list(data.get("capabilities_allow", data.get("capabilities", {}).get("allow", []))),
            capabilities_deny=list(data.get("capabilities_deny", data.get("capabilities", {}).get("deny", []))),
            schedule=data.get("schedule") if isinstance(data.get("schedule"), str) else (data.get("schedule", [{}])[0].get("every") if isinstance(data.get("schedule"), list) and data.get("schedule") else None),
            drex_pack=data.get("drex_pack") or (data.get("drex", {}).get("pack") if isinstance(data.get("drex"), dict) else None),
            extra=data.get("extra", {}),
        )


class DotProvider(ABC):
    """Abstract interface defining the contract for any Dot backend."""

    @property
    @abstractmethod
    def id(self) -> str:
        """Provider identifier (e.g. 'open-dotz', 'drex-dotz', 'gpt-dotz')."""
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable provider name."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """Brief provider description."""
        ...

    @property
    @abstractmethod
    def features(self) -> ProviderFeatures:
        """Declared features and capabilities for this provider."""
        ...

    @property
    @abstractmethod
    def governance(self) -> str:
        """Governance label (e.g. 'Drex', 'Provider-managed', 'Unrestricted')."""
        ...

    @abstractmethod
    def list_dots(self) -> List[DotSummary]:
        """List all active dots managed by this provider."""
        ...

    @abstractmethod
    def get_dot(self, dot_id: str) -> Optional[DotDetail]:
        """Retrieve full details for a dot."""
        ...

    @abstractmethod
    def create_dot(self, config: DotConfig) -> DotDetail:
        """Create and initialize a new dot."""
        ...

    @abstractmethod
    def start_dot(self, dot_id: str) -> DotDetail:
        """Start or unpause a dot."""
        ...

    @abstractmethod
    def stop_dot(self, dot_id: str) -> DotDetail:
        """Stop a dot and halt its operations."""
        ...

    @abstractmethod
    def assign_task(
        self,
        dot_id: str,
        task: str,
        expected_output: Optional[str] = None,
        source: str = "hermes",
    ) -> Dict[str, Any]:
        """Assign a task obligation to the dot."""
        ...

    @abstractmethod
    def steer_dot(self, dot_id: str, message: str) -> Dict[str, Any]:
        """Directly steer or prompt the dot."""
        ...

    @abstractmethod
    def get_activity(self, dot_id: str) -> List[DotActivityEvent]:
        """Retrieve chronological normalized activity timeline."""
        ...

    @abstractmethod
    def get_receipts(self, dot_id: str) -> List[Dict[str, Any]]:
        """Retrieve execution receipts (if provider supports receipts)."""
        ...

    @abstractmethod
    def list_approvals(self, dot_id: str) -> List[ApprovalRequest]:
        """List pending approvals (if provider supports approvals)."""
        ...

    @abstractmethod
    def approve_action(self, dot_id: str, approval_id: str, **kwargs) -> Dict[str, Any]:
        """Authorize a pending action or issue a bounded grant."""
        ...

    @abstractmethod
    def deny_action(self, dot_id: str, approval_id: str, **kwargs) -> Dict[str, Any]:
        """Deny a pending action."""
        ...

    @abstractmethod
    def execute_action(
        self,
        dot_id: str,
        capability: str,
        action: str,
        args: Dict[str, Any],
        task_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute a guarded action through the provider."""
        ...

    @abstractmethod
    def tick(self, dot_id: Optional[str] = None) -> List[str]:
        """Trigger scheduler tick for due obligations."""
        ...
