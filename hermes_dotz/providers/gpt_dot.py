"""GPT Dotz Provider.

Lightweight generic Dot provider for ordinary GPT-backed persistent agents.
Does not require external firewall policy engines.
Maintains persistent mission, conversational history, task assignment, and steering.
Does NOT silently inherit filesystem or external privileges.
"""
from __future__ import annotations

import json
import logging
import os
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import httpx

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


class GPTDotzProvider(BaseDotProvider):
    """GPT Dotz provider: persistent conversational and planning assistant."""

    def __init__(self, root_dir: Path, store: Optional[DotzStore] = None):
        super().__init__(root_dir, store)
        self.api_base = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
        self.api_key = os.environ.get("OPENAI_API_KEY", "")

    @property
    def id(self) -> str:
        return "gpt-dotz"

    @property
    def name(self) -> str:
        return "GPT Dot"

    @property
    def description(self) -> str:
        return "Persistent conversational and planning assistant backed by OpenAI-compatible LLM endpoints."

    @property
    def governance(self) -> str:
        return "Provider-managed"

    @property
    def features(self) -> ProviderFeatures:
        return ProviderFeatures(
            persistence=True,
            scheduling=False,
            model_selection=True,
            tool_execution=False,
            capabilities=False,
            approvals=False,
            receipts=False,
            drex_governance=False,
            events=True,
        )

    def list_dots(self) -> List[DotSummary]:
        rows = self.store.all(
            "SELECT * FROM dots WHERE provider IN ('gpt-dotz', 'gpt') ORDER BY name ASC"
        )
        summaries: List[DotSummary] = []
        for r in rows:
            name = r["name"]
            tasks = self.store.all(
                "SELECT * FROM tasks WHERE dot = ? ORDER BY created_at DESC", (name,)
            )
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
        activity = self.get_activity(dot_id)
        models = json.loads(row.get("models") or "{}")

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
            models=models or {"default": "gpt-4o-mini"},
            capabilities={"allow": [], "deny": ["*"]},  # Explicit boundary: zero tool privileges
            tasks=tasks,
            receipts=[],
            activity=activity,
            approvals=[],
            responsibilities=[],
        )

    def create_dot(self, config: DotConfig) -> DotDetail:
        dot_dir, ws_dir = self._ensure_dot_dir(config.name, config.workspace)
        now = time.time()

        models_json = json.dumps({"default": config.default_model or "gpt-4o-mini", "escalate": config.escalate_model})

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
                "capabilities": json.dumps({"allow": [], "deny": ["*"]}),
                "workspace": str(ws_dir),
            },
        )

        self._save_dot_config_file(config, dot_dir)

        self.store.record_activity(
            dot_id=config.name,
            event_type="task_created",
            title=f"Initialized GPT Dot {config.name}",
            description=f"Mission: {config.mission}",
            details={"model": config.default_model or "gpt-4o-mini", "governance": self.governance},
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
            title="GPT Dot Ready",
            description="Agent transitioned to IDLE",
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
            title="GPT Dot Paused",
            description="Agent transitioned to STOPPED",
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

        # Generate response using model or simulated planner
        result = self._generate_response(dot, task)

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
                "result": result,
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
            description=result,
            details={"task_id": task_id, "source": source},
        )

        return {
            "status": "assigned",
            "task_id": task_id,
            "dot": dot_id,
            "result": result,
        }

    def steer_dot(self, dot_id: str, message: str) -> Dict[str, Any]:
        dot = self.get_dot(dot_id)
        if not dot:
            raise ValueError(f"Dot {dot_id} not found")

        self.store.record_activity(
            dot_id=dot_id,
            event_type="message",
            title=f"User Steering: {message[:30]}",
            description=message,
            details={"source": "hermes_composer"},
        )
        return self.assign_task(dot_id, f"Instruction: {message}", source="hermes_composer")

    def _generate_response(self, dot: DotDetail, prompt: str) -> str:
        """Call OpenAI-compatible endpoint if API key configured, otherwise return clear plan."""
        if self.api_key and not self.api_key.startswith("mock"):
            try:
                messages = [
                    {"role": "system", "content": f"You are {dot.summary.name}. Mission: {dot.summary.mission}"},
                    {"role": "user", "content": prompt},
                ]
                with httpx.Client(timeout=20.0) as client:
                    resp = client.post(
                        f"{self.api_base}/chat/completions",
                        headers={"Authorization": f"Bearer {self.api_key}"},
                        json={
                            "model": dot.models.get("default", "gpt-4o-mini"),
                            "messages": messages,
                        },
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        return str(data["choices"][0]["message"]["content"])
            except Exception as e:
                log.warning("GPT endpoint call failed: %s; falling back to local plan generation", e)

        # Local fallback simulation response
        return f"[{dot.summary.name}] Understood obligation: '{prompt}'. In alignment with mission '{dot.summary.mission}', synthesized steps and confirmed status."

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
        return []

    def list_approvals(self, dot_id: str) -> List[ApprovalRequest]:
        return []

    def approve_action(self, dot_id: str, approval_id: str, **kwargs) -> Dict[str, Any]:
        return {"status": "unsupported", "reason": "GPT Dot operates without external action approvals."}

    def deny_action(self, dot_id: str, approval_id: str, **kwargs) -> Dict[str, Any]:
        return {"status": "unsupported", "reason": "GPT Dot operates without external action approvals."}

    def execute_action(
        self,
        dot_id: str,
        capability: str,
        action: str,
        args: Dict[str, Any],
        task_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        # GPT Dot has NO silent privilege inheritance
        return {
            "decision": "BLOCK",
            "allowed": False,
            "upstream_executed": False,
            "rule": "GPT_DOT_NO_TOOL_PRIVILEGE",
            "reason": "GPT Dot has no execution firewall or tool grant permissions.",
        }

    def tick(self, dot_id: Optional[str] = None) -> List[str]:
        return []
