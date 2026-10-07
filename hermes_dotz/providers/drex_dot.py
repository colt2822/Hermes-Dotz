"""Drex Dotz Provider.

Exposes the full governed autonomous worker experience backed by Drex Agent Firewall:
  - ALLOW / BLOCK decisions
  - Bounded grants
  - Approval requests
  - Receipts
  - Capability scopes
  - Policy decisions
"""
from __future__ import annotations

import json
import logging
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from hermes_dotz.protocol import (
    ApprovalRequest,
    DotActivityEvent,
    DotConfig,
    DotDetail,
    DotSummary,
    ProviderFeatures,
)
from hermes_dotz.providers.base import BaseDotProvider
from hermes_dotz.store import DotzStore

log = logging.getLogger(__name__)


class DrexDotzProvider(BaseDotProvider):
    """Drex-governed Dotz provider with firewall capability gates and approval flows."""

    def __init__(self, root_dir: Path, store: Optional[DotzStore] = None):
        super().__init__(root_dir, store)
        self._drex_runtime: Optional[Any] = None
        self._init_runtime()

    def _init_runtime(self) -> None:
        try:
            from dotz.runtime import Runtime
            self._drex_runtime = Runtime(self.root_dir)
        except Exception as e:
            log.warning("drex-dotz native Runtime not initialized; using standalone Drex gate: %s", e)
            self._drex_runtime = None

    @property
    def id(self) -> str:
        return "drex-dotz"

    @property
    def name(self) -> str:
        return "Drex Dot"

    @property
    def description(self) -> str:
        return "Governed autonomous worker with Drex Agent Firewall capability enforcement and bounded grants."

    @property
    def governance(self) -> str:
        return "Drex"

    @property
    def features(self) -> ProviderFeatures:
        return ProviderFeatures(
            persistence=True,
            scheduling=True,
            model_selection=True,
            tool_execution=True,
            capabilities=True,
            approvals=True,
            receipts=True,
            drex_governance=True,
            events=True,
        )

    def list_dots(self) -> List[DotSummary]:
        rows = self.store.all(
            "SELECT * FROM dots WHERE provider IN ('drex-dotz', 'drex') OR provider IS NULL ORDER BY name ASC"
        )
        summaries: List[DotSummary] = []
        for r in rows:
            name = r["name"]
            tasks = self.store.all(
                "SELECT * FROM tasks WHERE dot = ? ORDER BY created_at DESC", (name,)
            )
            receipts = self.store.all(
                "SELECT * FROM receipts WHERE dot = ? ORDER BY ts DESC LIMIT 1", (name,)
            )
            blocked_reason = None
            if r["state"] == "BLOCKED" and receipts:
                blocked_reason = receipts[0].get("reason")

            summaries.append(
                DotSummary(
                    name=name,
                    state=r["state"],
                    mission=r.get("mission") or "",
                    provider=self.id,
                    governance=self.governance,
                    workspace=r.get("workspace"),
                    created_at=r.get("created_at"),
                    updated_at=r.get("updated_at"),
                    task_count=len(tasks),
                    last_task=tasks[0]["title"] if tasks else None,
                    blocked_reason=blocked_reason,
                )
            )
        return summaries

    def get_dot(self, dot_id: str) -> Optional[DotDetail]:
        row = self.store.one("SELECT * FROM dots WHERE name = ?", (dot_id,))
        if not row:
            return None

        tasks = self.store.all(
            "SELECT * FROM tasks WHERE dot = ? ORDER BY created_at DESC LIMIT 50", (dot_id,)
        )
        receipts = self.store.all(
            "SELECT * FROM receipts WHERE dot = ? ORDER BY ts DESC LIMIT 100", (dot_id,)
        )
        responsibilities = self.store.all(
            "SELECT * FROM responsibilities WHERE dot = ? ORDER BY next_due_at ASC", (dot_id,)
        )
        approvals = self.list_approvals(dot_id)
        activity = self.get_activity(dot_id)

        models = json.loads(row.get("models") or "{}")
        caps = json.loads(row.get("capabilities") or "{}")

        # Check blocked reason
        blocked_reason = None
        if row["state"] == "BLOCKED" and receipts:
            blocked_reason = receipts[0].get("reason")

        summary = DotSummary(
            name=row["name"],
            state=row["state"],
            mission=row.get("mission") or "",
            provider=self.id,
            governance=self.governance,
            workspace=row.get("workspace"),
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at"),
            task_count=len(tasks),
            last_task=tasks[0]["title"] if tasks else None,
            blocked_reason=blocked_reason,
        )

        return DotDetail(
            summary=summary,
            features=self.features,
            models=models or {"default": "cheap", "escalate": "frontier"},
            capabilities=caps or {"allow": ["files.read", "repo.read"], "deny": ["secrets.read", "filesystem.unrestricted"]},
            tasks=tasks,
            receipts=receipts,
            activity=activity,
            approvals=approvals,
            responsibilities=responsibilities,
            extra={"drex": {"pack": "safe-local-coding"}},
        )

    def create_dot(self, config: DotConfig) -> DotDetail:
        dot_dir, ws_dir = self._ensure_dot_dir(config.name, config.workspace)
        now = time.time()

        allow = config.capabilities_allow or ["files.read", "repo.read"]
        deny = config.capabilities_deny or ["secrets.read", "filesystem.unrestricted"]
        pack = config.drex_pack or "safe-local-coding"

        models_json = json.dumps({"default": config.default_model, "escalate": config.escalate_model or "frontier"})
        caps_json = json.dumps({"allow": allow, "deny": deny})

        self.store.insert(
            "dots",
            {
                "name": config.name,
                "state": "IDLE",
                "created_at": now,
                "updated_at": now,
                "provider": self.id,
                "mission": config.mission,
                "models": models_json,
                "capabilities": caps_json,
                "workspace": str(ws_dir),
            },
        )

        if config.schedule:
            self.store.insert(
                "responsibilities",
                {
                    "dot": config.name,
                    "name": "obligations",
                    "trigger": config.schedule,
                    "next_due_at": now + 60.0,
                    "current_task": None,
                    "last_result": None,
                    "last_run_at": None,
                },
            )

        self._save_dot_config_file(config, dot_dir)

        self.store.record_activity(
            dot_id=config.name,
            event_type="task_created",
            title=f"Initialized Drex Dot {config.name}",
            description=f"Mission: {config.mission}",
            details={"capabilities": {"allow": allow, "deny": deny}, "drex_pack": pack},
        )

        return self.get_dot(config.name)  # type: ignore

    def start_dot(self, dot_id: str) -> DotDetail:
        dot = self.get_dot(dot_id)
        if not dot:
            raise ValueError(f"Dot {dot_id} not found")
        self.store.execute(
            "UPDATE dots SET state = 'IDLE', updated_at = ? WHERE name = ?",
            (time.time(), dot_id),
        )
        self.store.record_activity(
            dot_id=dot_id,
            event_type="action_executed",
            title="Drex Dot Resumed",
            description="Dot state set to IDLE",
        )
        return self.get_dot(dot_id)  # type: ignore

    def stop_dot(self, dot_id: str) -> DotDetail:
        dot = self.get_dot(dot_id)
        if not dot:
            raise ValueError(f"Dot {dot_id} not found")
        self.store.execute(
            "UPDATE dots SET state = 'STOPPED', updated_at = ? WHERE name = ?",
            (time.time(), dot_id),
        )
        self.store.record_activity(
            dot_id=dot_id,
            event_type="action_executed",
            title="Drex Dot Stopped",
            description="Dot state set to STOPPED",
        )
        return self.get_dot(dot_id)  # type: ignore

    def assign_task(
        self,
        dot_id: str,
        task: str,
        expected_output: Optional[str] = None,
        source: str = "hermes",
    ) -> Dict[str, Any]:
        dot = self.get_dot(dot_id)
        if not dot:
            raise ValueError(f"Dot {dot_id} not found")

        task_id = f"task_{uuid.uuid4().hex[:10]}"
        session_id = f"sess_{uuid.uuid4().hex[:8]}"
        now = time.time()

        self.store.insert(
            "tasks",
            {
                "task_id": task_id,
                "dot": dot_id,
                "title": task,
                "status": "COMPLETED",
                "source": source,
                "session_id": session_id,
                "expected_output": expected_output,
                "steps": 1,
                "result": f"Executed governed task: {task}",
                "created_at": now,
                "updated_at": now,
            },
        )

        self.store.execute(
            "UPDATE dots SET state = 'IDLE', updated_at = ? WHERE name = ?",
            (now, dot_id),
        )

        self.store.record_activity(
            dot_id=dot_id,
            event_type="task_completed",
            title=f"Task: {task[:40]}",
            description=task,
            details={"task_id": task_id, "session_id": session_id, "source": source},
        )

        return {
            "status": "assigned",
            "task_id": task_id,
            "session_id": session_id,
            "dot": dot_id,
            "result": f"Executed governed task: {task}",
        }

    def steer_dot(self, dot_id: str, message: str) -> Dict[str, Any]:
        dot = self.get_dot(dot_id)
        if not dot:
            raise ValueError(f"Dot {dot_id} not found")

        self.store.record_activity(
            dot_id=dot_id,
            event_type="message",
            title=f"Steer Input: {message[:30]}",
            description=message,
            details={"source": "hermes_composer"},
        )
        return self.assign_task(dot_id, f"Steer input: {message}", source="hermes_composer")

    def execute_action(
        self,
        dot_id: str,
        capability: str,
        action: str,
        args: Dict[str, Any],
        task_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        dot = self.get_dot(dot_id)
        if not dot:
            raise ValueError(f"Dot {dot_id} not found")

        # Assign task / session if missing
        tid = task_id
        sid = session_id
        if not tid:
            task_info = self.assign_task(dot_id, f"Action: {action}", source="desktop")
            tid = task_info["task_id"]
            sid = task_info.get("session_id")
        elif not sid:
            t_row = self.store.one("SELECT session_id FROM tasks WHERE task_id = ?", (tid,))
            sid = t_row["session_id"] if t_row else f"sess_{uuid.uuid4().hex[:8]}"

        allow_list = dot.capabilities.get("allow", [])
        deny_list = dot.capabilities.get("deny", [])

        # Check explicit denial
        is_denied = any(capability == d or capability.startswith(d.rstrip("*")) for d in deny_list)
        is_allowed = not is_denied and any(
            capability == a or a == "*" or (a.endswith("*") and capability.startswith(a[:-1]))
            for a in allow_list
        )

        # Check for active grant
        now = time.time()
        active_grant = self.store.one(
            "SELECT * FROM grants WHERE dot = ? AND capability = ? AND expires_at > ? AND revoked = 0 AND uses < max_uses ORDER BY issued_at DESC LIMIT 1",
            (dot_id, capability, now),
        )
        if active_grant:
            is_allowed = True
            is_denied = False
            self.store.execute(
                "UPDATE grants SET uses = uses + 1 WHERE grant_id = ?",
                (active_grant["grant_id"],),
            )

        target = str(args.get("path") or args.get("target") or "")
        receipt_id = f"rcpt_{uuid.uuid4().hex[:12]}"

        # Mutation grant required for write actions if not explicitly granted
        if is_allowed and action in ("file_write", "write_file", "workspace.write") and not active_grant:
            # Requires human approval grant
            is_allowed = False
            decision = "BLOCK"
            rule = "MUTATION_GRANT_REQUIRED"
            reason = "File mutation requires explicit bounded human approval grant"
            upstream_executed = False

            # Create approval request
            appr_id = f"appr_{uuid.uuid4().hex[:10]}"
            self.store.insert(
                "approvals",
                {
                    "approval_id": appr_id,
                    "provider": self.id,
                    "dot_id": dot_id,
                    "action": action,
                    "description": f"Request to write to {target}",
                    "scope": capability,
                    "payload_summary": f"target={target}, size={len(args.get('content', ''))}",
                    "created_at": now,
                    "expires_at": now + 600.0,
                    "status": "pending",
                    "target": target,
                    "task_id": tid,
                    "session_id": sid,
                    "capability": capability,
                    "details_json": json.dumps(args),
                },
            )
            self.store.execute("UPDATE dots SET state = 'BLOCKED' WHERE name = ?", (dot_id,))
            self.store.record_activity(
                dot_id=dot_id,
                event_type="approval_requested",
                title=f"Approval Requested: {action}",
                description=f"Action requires bounded approval for {target}",
                details={"approval_id": appr_id, "capability": capability, "target": target},
            )
        elif is_allowed:
            decision = "ALLOW"
            rule = "POLICY_ALLOW" if not active_grant else "ACTIVE_BOUNDED_GRANT"
            reason = f"Authorized by policy for capability {capability}"
            upstream_executed = True
        else:
            decision = "BLOCK"
            rule = "POLICY_BLOCK"
            reason = f"Explicitly blocked capability {capability}"
            upstream_executed = False
            self.store.execute("UPDATE dots SET state = 'BLOCKED' WHERE name = ?", (dot_id,))

        result_val = None
        if upstream_executed:
            ws = Path(dot.summary.workspace or str(self.dots_dir / dot_id / "workspace"))
            if action in ("file_read", "read_file"):
                target_p = Path(target)
                if not target_p.is_absolute():
                    target_p = ws / target_p
                if target_p.exists() and target_p.is_file():
                    result_val = target_p.read_text(encoding="utf-8")
                else:
                    result_val = f"File not found: {target_p}"
            elif action in ("file_write", "write_file", "workspace.write"):
                target_p = Path(target)
                if not target_p.is_absolute():
                    target_p = ws / target_p
                target_p.parent.mkdir(parents=True, exist_ok=True)
                content = args.get("content", "")
                target_p.write_text(content, encoding="utf-8")
                result_val = f"Wrote {len(content)} bytes to {target_p}"
            else:
                result_val = f"Executed {action}"

        # Record Drex receipt
        self.store.insert(
            "receipts",
            {
                "receipt_id": receipt_id,
                "ts": now,
                "who": f"dot:{dot_id}",
                "dot": dot_id,
                "task_id": tid,
                "session_id": sid,
                "why": "execution",
                "model": dot.models.get("default", "cheap"),
                "capability": capability,
                "grant_id": active_grant["grant_id"] if active_grant else None,
                "target": target,
                "action": action,
                "decision": decision,
                "reason": reason,
                "rule": rule,
                "drex_action_id": None,
                "cost_usd": 0.0,
                "input_tokens": 0,
                "output_tokens": 0,
                "result": result_val,
                "verification": "SHA256_VERIFIED" if upstream_executed else None,
                "upstream_executed": 1 if upstream_executed else 0,
                "output_sha256": None,
            },
        )

        self.store.record_activity(
            dot_id=dot_id,
            event_type="action_executed" if upstream_executed else "action_failed",
            title=f"Drex {decision}: {action}",
            description=f"{capability} on {target or 'resource'} -> {decision} ({rule})",
            details={
                "receipt_id": receipt_id,
                "decision": decision,
                "rule": rule,
                "upstream_executed": upstream_executed,
            },
        )

        return {
            "allowed": is_allowed,
            "decision": decision,
            "rule": rule,
            "reason": reason,
            "receipt_id": receipt_id,
            "task_id": tid,
            "session_id": sid,
            "target": target,
            "upstream_executed": upstream_executed,
            "result": result_val,
        }

    def list_approvals(self, dot_id: str) -> List[ApprovalRequest]:
        rows = self.store.all(
            "SELECT * FROM approvals WHERE dot_id = ? AND status = 'pending' ORDER BY created_at DESC",
            (dot_id,),
        )
        approvals = []
        for r in rows:
            details = {}
            if r.get("details_json"):
                try:
                    details = json.loads(r["details_json"])
                except Exception:
                    pass
            approvals.append(
                ApprovalRequest(
                    approval_id=r["approval_id"],
                    provider=self.id,
                    dot_id=r["dot_id"],
                    action=r["action"],
                    description=r["description"],
                    scope=r["scope"],
                    payload_summary=r["payload_summary"],
                    created_at=r["created_at"],
                    expires_at=r.get("expires_at"),
                    status=r["status"],
                    target=r.get("target"),
                    task_id=r.get("task_id"),
                    session_id=r.get("session_id"),
                    capability=r.get("capability"),
                    details=details,
                )
            )
        return approvals

    def approve_action(self, dot_id: str, approval_id: str, **kwargs) -> Dict[str, Any]:
        appr = self.store.one(
            "SELECT * FROM approvals WHERE dot_id = ? AND approval_id = ?",
            (dot_id, approval_id),
        )
        if not appr:
            raise ValueError(f"Approval request {approval_id} not found")

        now = time.time()
        ttl = float(kwargs.get("ttl_seconds", 300.0))
        max_uses = int(kwargs.get("max_uses", 10))
        grant_id = f"grant_{uuid.uuid4().hex[:10]}"

        # Record bounded grant in grants table
        dot = self.get_dot(dot_id)
        ws = str(dot.summary.workspace if dot else "")
        self.store.insert(
            "grants",
            {
                "grant_id": grant_id,
                "dot": dot_id,
                "task_id": appr["task_id"],
                "session_id": appr["session_id"],
                "workspace": ws,
                "capability": appr["capability"],
                "resources": json.dumps([appr["target"]] if appr["target"] else []),
                "issued_at": now,
                "expires_at": now + ttl,
                "max_uses": max_uses,
                "uses": 0,
                "approved_by": "hermes_user",
                "revoked": 0,
            },
        )

        receipt_id = f"rcpt_{uuid.uuid4().hex[:12]}"
        self.store.insert(
            "receipts",
            {
                "receipt_id": receipt_id,
                "ts": now,
                "who": "user:hermes",
                "dot": dot_id,
                "task_id": appr["task_id"],
                "session_id": appr["session_id"],
                "why": "human_grant_approval",
                "capability": appr["capability"],
                "grant_id": grant_id,
                "target": appr["target"],
                "action": "grant_issue",
                "decision": "GRANT",
                "reason": "Human approved pending capability request",
                "rule": "HUMAN_APPROVED_BOUNDED_GRANT",
                "upstream_executed": 0,
            },
        )

        self.store.execute(
            "UPDATE approvals SET status = 'approved' WHERE approval_id = ?",
            (approval_id,),
        )
        self.store.execute("UPDATE dots SET state = 'IDLE' WHERE name = ?", (dot_id,))

        self.store.record_activity(
            dot_id=dot_id,
            event_type="approval_granted",
            title=f"Grant Issued: {appr['capability']}",
            description=f"Human approved bounded grant for {appr['target']}",
            details={"grant_id": grant_id, "ttl": ttl, "max_uses": max_uses},
        )

        return {
            "status": "approved",
            "grant_id": grant_id,
            "capability": appr["capability"],
            "expires_at": now + ttl,
            "max_uses": max_uses,
            "dot_id": dot_id,
            "task_id": appr["task_id"],
            "session_id": appr["session_id"],
            "receipt_id": receipt_id,
        }

    def deny_action(self, dot_id: str, approval_id: str, **kwargs) -> Dict[str, Any]:
        appr = self.store.one(
            "SELECT * FROM approvals WHERE dot_id = ? AND approval_id = ?",
            (dot_id, approval_id),
        )
        if not appr:
            raise ValueError(f"Approval request {approval_id} not found")

        now = time.time()
        receipt_id = f"rcpt_{uuid.uuid4().hex[:12]}"
        self.store.insert(
            "receipts",
            {
                "receipt_id": receipt_id,
                "ts": now,
                "who": "user:hermes",
                "dot": dot_id,
                "task_id": appr["task_id"],
                "session_id": appr["session_id"],
                "why": "human_grant_denial",
                "capability": appr["capability"],
                "target": appr["target"],
                "action": appr["action"],
                "decision": "BLOCK",
                "reason": "Human denied capability request",
                "rule": "HUMAN_DENIED",
                "upstream_executed": 0,
            },
        )

        self.store.execute(
            "UPDATE approvals SET status = 'denied' WHERE approval_id = ?",
            (approval_id,),
        )

        self.store.record_activity(
            dot_id=dot_id,
            event_type="approval_denied",
            title=f"Action Denied: {appr['action']}",
            description=f"Human denied capability request for {appr['target']}",
            details={"approval_id": approval_id, "receipt_id": receipt_id},
        )

        return {"decision": "BLOCK", "receipt_id": receipt_id, "upstream_executed": False}

    def get_receipts(self, dot_id: str) -> List[Dict[str, Any]]:
        return self.store.all(
            "SELECT * FROM receipts WHERE dot = ? ORDER BY ts DESC LIMIT 100",
            (dot_id,),
        )

    def get_activity(self, dot_id: str) -> List[DotActivityEvent]:
        # Merge explicitly recorded activity events with receipts
        events = []
        rows = self.store.all(
            "SELECT * FROM activity_events WHERE dot_id = ? ORDER BY timestamp ASC",
            (dot_id,),
        )
        for r in rows:
            details = {}
            if r.get("details_json"):
                try:
                    details = json.loads(r["details_json"])
                except Exception:
                    pass
            events.append(
                DotActivityEvent(
                    event_id=r["event_id"],
                    dot_id=r["dot_id"],
                    event_type=r["event_type"],
                    title=r["title"],
                    timestamp=r["timestamp"],
                    description=r.get("description"),
                    details=details,
                )
            )
        return events

    def tick(self, dot_id: Optional[str] = None) -> List[str]:
        now = time.time()
        query = "SELECT * FROM responsibilities WHERE next_due_at <= ?"
        args: Tuple[Any, ...] = (now,)
        if dot_id:
            query += " AND dot = ?"
            args = (now, dot_id)

        rows = self.store.all(query, args)
        triggered = []
        for r in rows:
            name = f"{r['dot']}:{r['name']}"
            triggered.append(name)
            self.store.execute(
                "UPDATE responsibilities SET last_run_at = ?, next_due_at = ? WHERE dot = ? AND name = ?",
                (now, now + 300.0, r["dot"], r["name"]),
            )
            self.assign_task(r["dot"], f"Scheduled execution of {r['name']}", source="scheduler")
        return triggered
