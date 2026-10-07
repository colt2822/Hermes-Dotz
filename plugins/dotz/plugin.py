"""Hermes session plugin adapter exposing Dotz management tools to Hermes sessions."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from hermes_dotz.protocol import DotConfig
from hermes_dotz.registry import get_registry


def register(ctx):
    """Hermes session plugin entrypoint."""
    runtime_dir = Path(ctx.get_config("dotz_runtime_dir", Path.home() / "dotz_runtime"))
    registry = get_registry(runtime_dir)

    def dots_list(args, **kwargs):
        dots = [d.to_dict() for d in registry.list_all_dots()]
        return json.dumps({"dots": dots})

    def dots_create(args, **kwargs):
        payload = args.get("payload", {})
        cfg = DotConfig.from_dict(payload)
        detail = registry.create_dot(cfg)
        return json.dumps({
            "status": "created",
            "dot": detail.summary.name,
            "provider": detail.summary.provider,
            "state": detail.summary.state,
        })

    def dots_assign(args, **kwargs):
        dot_name = args.get("dot")
        task = args.get("task", "")
        provider = registry.resolve_for_dot(dot_name)
        res = provider.assign_task(dot_id=dot_name, task=task, source="hermes")
        return json.dumps(res)

    def dots_status(args, **kwargs):
        dot_name = args.get("dot")
        try:
            dot = registry.get_dot(dot_name)
            if not dot:
                return json.dumps({"error": f"Dot {dot_name} not found"})
            return json.dumps(dot.to_dict())
        except Exception as e:
            return json.dumps({"error": str(e)})

    def dots_result(args, **kwargs):
        task_id = args.get("task_id")
        task = registry.store.one("SELECT * FROM tasks WHERE task_id = ?", (task_id,))
        if not task:
            return json.dumps({"error": "Task not found"})
        return json.dumps(task)

    def dots_stop(args, **kwargs):
        dot_name = args.get("dot")
        try:
            provider = registry.resolve_for_dot(dot_name)
            detail = provider.stop_dot(dot_name)
            return json.dumps({"dot": dot_name, "state": detail.summary.state})
        except Exception as e:
            return json.dumps({"error": str(e)})

    def dots_history(args, **kwargs):
        dot_name = args.get("dot")
        provider = registry.resolve_for_dot(dot_name)
        receipts = provider.get_receipts(dot_name)
        return json.dumps({"dot": dot_name, "receipts": receipts})

    tools = [
        ("dots_list", dots_list, "List all active persistent Dot workers across providers"),
        ("dots_create", dots_create, "Create a new Dot worker with configuration"),
        ("dots_assign", dots_assign, "Assign a task obligation to a Dot worker"),
        ("dots_status", dots_status, "Check status and lifecycle state of a Dot worker"),
        ("dots_result", dots_result, "Get result of an assigned Dot task"),
        ("dots_stop", dots_stop, "Stop a Dot worker"),
        ("dots_history", dots_history, "Retrieve Dot capability receipts and audit history"),
    ]

    for name, handler, desc in tools:
        ctx.register_tool(
            name=name,
            toolset="dotz",
            handler=handler,
            description=desc,
            schema={
                "name": name,
                "description": desc,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "dot": {"type": "string"},
                        "task": {"type": "string"},
                        "task_id": {"type": "string"},
                        "payload": {"type": "object"},
                    },
                },
            },
        )
