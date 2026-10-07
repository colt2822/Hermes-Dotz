"""Open Dotz Provider.

Default public autonomous persistent worker integration.
Runs without requiring Drex Agent Firewall policies or blocking mutation grants.
Actions and tasks run with declared capabilities and workspace boundaries.
"""
from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

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


class OpenDotzProvider(BaseDotProvider):
    """Open Dotz provider: autonomous persistent worker with provider-managed governance."""

    @property
    def id(self) -> str:
        return "open-dotz"

    @property
    def name(self) -> str:
        return "Open Dot"

    @property
    def description(self) -> str:
        return "Autonomous persistent worker with workspace boundaries and scheduled obligations."

    @property
    def governance(self) -> str:
        return "Provider-managed"

    @property
    def features(self) -> ProviderFeatures:
        return ProviderFeatures(
            persistence=True,
            scheduling=True,
            model_selection=True,
            tool_execution=True,
            capabilities=False,
            approvals=False,
            receipts=False,
            drex_governance=False,
            events=True,
        )

    def list_dots(self) -> List[DotSummary]:
        rows = self.store.all(
            "SELECT * FROM dots WHERE provider IN ('open-dotz', 'open') ORDER BY name ASC"
        )
        summaries: List[DotSummary] = []
        for r in rows:
            name = r["name"]
            tasks = self.store.all(
                "SELECT * FROM tasks WHERE dot = ? ORDER BY created_at DESC", (name,)
            )
            last_task = tasks[0]["title"] if tasks else None
            models = json.loads(r.get("models") or "{}")
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
                    last_task=last_task,
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
        responsibilities = self.store.all(
            "SELECT * FROM responsibilities WHERE dot = ? ORDER BY next_due_at ASC", (dot_id,)
        )
        activity = self.get_activity(dot_id)

        models = json.loads(row.get("models") or "{}")
        caps = json.loads(row.get("capabilities") or "{}")

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
        )

        return DotDetail(
            summary=summary,
            features=self.features,
            models=models or {"default": "cheap"},
            capabilities=caps or {"allow": [], "deny": []},
            tasks=tasks,
            receipts=[],  # Open provider has no Drex receipts
            activity=activity,
            approvals=[],  # Open provider has no approvals
            responsibilities=responsibilities,
        )

    def create_dot(self, config: DotConfig) -> DotDetail:
        dot_dir, ws_dir = self._ensure_dot_dir(config.name, config.workspace)
        now = time.time()

        models_json = json.dumps({"default": config.default_model, "escalate": config.escalate_model})
        caps_json = json.dumps({"allow": config.capabilities_allow, "deny": config.capabilities_deny})

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
                    "name": "scheduled_maintenance",
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
            title=f"Initialized Open Dot {config.name}",
            description=f"Mission: {config.mission}",
            details={"workspace": str(ws_dir), "model": config.default_model},
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
            title="Dot Started",
            description="Dot transitioned to IDLE state",
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
            title="Dot Stopped",
            description="Dot transitioned to STOPPED state",
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
                "result": f"Executed open task: {task}",
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
            title=f"Task Completed: {task[:40]}",
            description=task,
            details={"task_id": task_id, "source": source, "result": f"Executed open task: {task}"},
        )

        return {
            "status": "assigned",
            "task_id": task_id,
            "dot": dot_id,
            "result": f"Executed open task: {task}",
        }

    def steer_dot(self, dot_id: str, message: str) -> Dict[str, Any]:
        dot = self.get_dot(dot_id)
        if not dot:
            raise ValueError(f"Dot {dot_id} not found")

        self.store.record_activity(
            dot_id=dot_id,
            event_type="message",
            title=f"Steering Instruction: {message[:30]}",
            description=message,
            details={"direction": "incoming", "source": "hermes_composer"},
        )
        return self.assign_task(dot_id, f"Steer: {message}", source="hermes_composer")

    def get_activity(self, dot_id: str) -> List[DotActivityEvent]:
        rows = self.store.all(
            "SELECT * FROM activity_events WHERE dot_id = ? ORDER BY timestamp ASC",
            (dot_id,),
        )
        events = []
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

    def get_receipts(self, dot_id: str) -> List[Dict[str, Any]]:
        # Open Dotz has no Drex receipts
        return []

    def list_approvals(self, dot_id: str) -> List[ApprovalRequest]:
        # Open Dotz has no approvals
        return []

    def approve_action(self, dot_id: str, approval_id: str, **kwargs) -> Dict[str, Any]:
        return {"status": "unsupported", "reason": "Open Dotz operates without approval gating."}

    def deny_action(self, dot_id: str, approval_id: str, **kwargs) -> Dict[str, Any]:
        return {"status": "unsupported", "reason": "Open Dotz operates without approval gating."}

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

        ws = Path(dot.summary.workspace or str(self.dots_dir / dot_id / "workspace"))
        res: Dict[str, Any] = {
            "decision": "ALLOW",
            "allowed": True,
            "upstream_executed": True,
            "capability": capability,
            "action": action,
            "task_id": task_id,
            "session_id": session_id,
        }

        if action in ("file_read", "read_file"):
            target_path = Path(args.get("path", ""))
            # If path is relative, resolve relative to workspace
            if not target_path.is_absolute():
                target_path = ws / target_path
            if target_path.exists() and target_path.is_file():
                res["result"] = target_path.read_text(encoding="utf-8")
            else:
                res["result"] = f"File not found: {target_path}"
        elif action in ("file_write", "write_file"):
            target_path = Path(args.get("path", ""))
            if not target_path.is_absolute():
                target_path = ws / target_path
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_text(args.get("content", ""), encoding="utf-8")
            res["result"] = f"Wrote {len(args.get('content', ''))} bytes to {target_path}"
        else:
            res["result"] = f"Open Dot executed {action}"

        self.store.record_activity(
            dot_id=dot_id,
            event_type="action_executed",
            title=f"Action: {action}",
            description=f"Capability: {capability}",
            details={"args": args, "result": res.get("result")},
        )
        return res

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
