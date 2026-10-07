"""Hermes Dashboard REST API routes mounted at /api/plugins/dotz/."""
from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request, status as http_status
from pydantic import BaseModel, Field

from hermes_dotz.protocol import DotConfig
from hermes_dotz.registry import get_registry

router = APIRouter()
log = logging.getLogger(__name__)

_loaded_at = time.time()
_source_path = Path(__file__).resolve()
_source_hash = hashlib.sha256(_source_path.read_bytes()).hexdigest()


class CreateDotRequest(BaseModel):
    name: str
    mission: str
    provider: str = "open-dotz"
    workspace: Optional[str] = None
    default_model: str = "cheap"
    escalate_model: Optional[str] = None
    capabilities_allow: List[str] = Field(default_factory=lambda: ["files.read", "repo.read"])
    capabilities_deny: List[str] = Field(default_factory=lambda: ["secrets.read", "filesystem.unrestricted"])
    schedule: Optional[str] = None
    drex_pack: str = "safe-local-coding"
    nova_delegation: Optional[bool] = None


class AssignTaskRequest(BaseModel):
    task: str
    expected_output: Optional[str] = None
    source: str = "hermes"


class SteerRequest(BaseModel):
    input: str


class ActionRequest(BaseModel):
    capability: str
    action: str
    args: Dict[str, Any] = Field(default_factory=dict)
    task_id: Optional[str] = None
    session_id: Optional[str] = None


class ApproveGrantRequest(BaseModel):
    task_id: Optional[str] = None
    session_id: Optional[str] = None
    approval_id: Optional[str] = None
    capability: Optional[str] = None
    resources: List[str] = Field(default_factory=list)
    ttl_seconds: float = 300.0
    max_uses: int = 10


class DenyRequest(BaseModel):
    approval_id: Optional[str] = None
    task_id: Optional[str] = None
    session_id: Optional[str] = None
    capability: Optional[str] = None
    action: Optional[str] = None
    target: Optional[str] = None


@router.get("/runtime")
def runtime_identity() -> Dict[str, Any]:
    import hermes_dotz
    return {
        "plugin_name": "dotz",
        "plugin_loaded_at": _loaded_at,
        "plugin_source_path": str(_source_path),
        "plugin_hash": _source_hash,
        "bridge_version": hermes_dotz.__version__,
    }


@router.get("/providers")
def list_providers() -> Dict[str, Any]:
    """Return available Dot providers with their declared capability matrix."""
    registry = get_registry()
    return {"providers": registry.list_descriptors()}


@router.get("/dots")
def list_dots() -> Dict[str, Any]:
    """List all persistent dots across registered providers."""
    registry = get_registry()
    dots = [d.to_dict() for d in registry.list_all_dots()]
    return {"dots": dots}


@router.get("/dots/{dot_name}")
def get_dot(dot_name: str) -> Dict[str, Any]:
    """Get full details for a dot."""
    registry = get_registry()
    dot = registry.get_dot(dot_name)
    if not dot:
        raise HTTPException(status_code=404, detail=f"Dot '{dot_name}' not found")
    return dot.to_dict()


@router.post("/dots")
def create_dot(req: CreateDotRequest) -> Dict[str, Any]:
    """Create a new Dot with the requested provider."""
    registry = get_registry()
    # Normalize provider if legacy nova_delegation was set
    provider_id = req.provider
    if req.nova_delegation and provider_id == "open-dotz":
        # If nova delegation was explicitly requested, route to drex or external provider
        provider_id = "drex-dotz"

    cfg = DotConfig(
        name=req.name.strip(),
        provider=provider_id,
        mission=req.mission.strip(),
        default_model=req.default_model,
        escalate_model=req.escalate_model,
        workspace=req.workspace,
        capabilities_allow=req.capabilities_allow,
        capabilities_deny=req.capabilities_deny,
        schedule=req.schedule,
        drex_pack=req.drex_pack,
    )
    detail = registry.create_dot(cfg)
    return {
        "status": "created",
        "name": detail.summary.name,
        "state": detail.summary.state,
        "provider": detail.summary.provider,
        "workspace": detail.summary.workspace,
    }


@router.post("/dots/{dot_name}/start")
def start_dot(dot_name: str) -> Dict[str, Any]:
    registry = get_registry()
    provider = registry.resolve_for_dot(dot_name)
    try:
        detail = provider.start_dot(dot_name)
        return {"status": "started", "name": dot_name, "state": detail.summary.state}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/dots/{dot_name}/stop")
def stop_dot(dot_name: str) -> Dict[str, Any]:
    registry = get_registry()
    provider = registry.resolve_for_dot(dot_name)
    try:
        detail = provider.stop_dot(dot_name)
        return {"status": "stopped", "name": dot_name, "state": detail.summary.state}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/dots/{dot_name}/assign")
def assign_task(dot_name: str, req: AssignTaskRequest) -> Dict[str, Any]:
    registry = get_registry()
    provider = registry.resolve_for_dot(dot_name)
    try:
        res = provider.assign_task(
            dot_id=dot_name,
            task=req.task,
            expected_output=req.expected_output,
            source=req.source,
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/dots/{dot_name}/steer")
def steer_dot(dot_name: str, req: SteerRequest) -> Dict[str, Any]:
    registry = get_registry()
    provider = registry.resolve_for_dot(dot_name)
    try:
        res = provider.steer_dot(dot_id=dot_name, message=req.input)
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/dots/{dot_name}/activity")
def get_activity(dot_name: str) -> Dict[str, Any]:
    registry = get_registry()
    provider = registry.resolve_for_dot(dot_name)
    events = [e.to_dict() for e in provider.get_activity(dot_name)]
    return {"dot": dot_name, "activity": events}


@router.get("/dots/{dot_name}/receipts")
def get_receipts(dot_name: str) -> Dict[str, Any]:
    registry = get_registry()
    provider = registry.resolve_for_dot(dot_name)
    receipts = provider.get_receipts(dot_name)
    return {"dot": dot_name, "receipts": receipts}


@router.get("/dots/{dot_name}/approvals")
def list_approvals(dot_name: str) -> Dict[str, Any]:
    registry = get_registry()
    provider = registry.resolve_for_dot(dot_name)
    approvals = [a.to_dict() for a in provider.list_approvals(dot_name)]
    return {"dot": dot_name, "approvals": approvals}


@router.post("/dots/{dot_name}/approvals/{approval_id}/approve")
def approve_action(dot_name: str, approval_id: str, req: ApproveGrantRequest) -> Dict[str, Any]:
    registry = get_registry()
    provider = registry.resolve_for_dot(dot_name)
    try:
        return provider.approve_action(
            dot_id=dot_name,
            approval_id=approval_id,
            ttl_seconds=req.ttl_seconds,
            max_uses=req.max_uses,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/dots/{dot_name}/approvals/{approval_id}/deny")
def deny_action(dot_name: str, approval_id: str, req: DenyRequest) -> Dict[str, Any]:
    registry = get_registry()
    provider = registry.resolve_for_dot(dot_name)
    try:
        return provider.deny_action(dot_id=dot_name, approval_id=approval_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/dots/{dot_name}/action")
def execute_action(dot_name: str, req: ActionRequest) -> Dict[str, Any]:
    """Execute action through provider's governance boundary."""
    registry = get_registry()
    provider = registry.resolve_for_dot(dot_name)
    try:
        res = provider.execute_action(
            dot_id=dot_name,
            capability=req.capability,
            action=req.action,
            args=req.args,
            task_id=req.task_id,
            session_id=req.session_id,
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/dots/{dot_name}/grants/approve")
def approve_grant_legacy(dot_name: str, req: ApproveGrantRequest) -> Dict[str, Any]:
    """Backward-compatible Drex grant approval endpoint."""
    registry = get_registry()
    provider = registry.resolve_for_dot(dot_name)
    try:
        # If approval_id is given or lookup by task/session/capability
        approval_id = req.approval_id
        if not approval_id and req.task_id:
            approvals = provider.list_approvals(dot_name)
            for a in approvals:
                if a.task_id == req.task_id:
                    approval_id = a.approval_id
                    break
        if not approval_id:
            # Create transient approval to authorize
            appr = provider.store.one(
                "SELECT approval_id FROM approvals WHERE dot_id = ? AND task_id = ? AND status = 'pending'",
                (dot_name, req.task_id),
            )
            if appr:
                approval_id = appr["approval_id"]
            else:
                # Direct grant issue for test/legacy clients
                import uuid
                grant_id = f"grant_{uuid.uuid4().hex[:10]}"
                now = time.time()
                provider.store.insert(
                    "grants",
                    {
                        "grant_id": grant_id,
                        "dot": dot_name,
                        "task_id": req.task_id or f"task_{uuid.uuid4().hex[:6]}",
                        "session_id": req.session_id or f"sess_{uuid.uuid4().hex[:6]}",
                        "workspace": str(Path.home() / "workspace" / dot_name),
                        "capability": req.capability or "repo.modify",
                        "resources": json.dumps(req.resources),
                        "issued_at": now,
                        "expires_at": now + req.ttl_seconds,
                        "max_uses": req.max_uses,
                        "uses": 0,
                        "approved_by": "hermes_user",
                        "revoked": 0,
                    },
                )
                return {
                    "status": "approved",
                    "grant_id": grant_id,
                    "capability": req.capability,
                    "expires_at": now + req.ttl_seconds,
                    "max_uses": req.max_uses,
                    "dot_id": dot_name,
                    "task_id": req.task_id,
                    "session_id": req.session_id,
                    "resources": req.resources,
                }
        return provider.approve_action(
            dot_id=dot_name,
            approval_id=approval_id,
            ttl_seconds=req.ttl_seconds,
            max_uses=req.max_uses,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/dots/{dot_name}/requests/deny")
def deny_request_legacy(dot_name: str, req: DenyRequest) -> Dict[str, Any]:
    """Backward-compatible Drex denial endpoint."""
    registry = get_registry()
    provider = registry.resolve_for_dot(dot_name)
    try:
        approval_id = req.approval_id
        if not approval_id and req.task_id:
            approvals = provider.list_approvals(dot_name)
            for a in approvals:
                if a.task_id == req.task_id:
                    approval_id = a.approval_id
                    break
        if not approval_id:
            return {"decision": "BLOCK", "receipt_id": "rcpt_denied", "upstream_executed": False}
        return provider.deny_action(dot_id=dot_name, approval_id=approval_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/tick")
def trigger_tick() -> Dict[str, Any]:
    """Trigger scheduler tick across active providers."""
    registry = get_registry()
    triggered = []
    for pid in ["open-dotz", "drex-dotz"]:
        provider = registry.get(pid)
        if provider.features.scheduling:
            triggered.extend(provider.tick())
    return {"status": "ok", "triggered_tasks": triggered}
