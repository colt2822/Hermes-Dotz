"""Base provider helper utilities for Hermes Dotz bridge."""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from hermes_dotz.protocol import (
    ApprovalRequest,
    DotActivityEvent,
    DotConfig,
    DotDetail,
    DotProvider,
    DotSummary,
    ProviderFeatures,
)
from hermes_dotz.store import DotzStore


class BaseDotProvider(DotProvider):
    """Common functionality for Dot providers."""

    def __init__(self, root_dir: Path, store: Optional[DotzStore] = None):
        self.root_dir = Path(root_dir).resolve()
        self.root_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.dots_dir = self.root_dir / "dots"
        self.dots_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.store = store or DotzStore(self.root_dir / "dotz.db")

    def _dot_path(self, dot_name: str) -> Path:
        return self.dots_dir / dot_name

    def _ensure_dot_dir(self, dot_name: str, workspace_override: Optional[str] = None) -> Tuple[Path, Path]:
        d = self._dot_path(dot_name)
        d.mkdir(parents=True, exist_ok=True, mode=0o700)
        ws = Path(workspace_override) if workspace_override else d / "workspace"
        ws.mkdir(parents=True, exist_ok=True, mode=0o700)
        return d, ws

    def _load_dot_config_file(self, dot_name: str) -> Optional[DotConfig]:
        cfg_file = self._dot_path(dot_name) / "config.yaml"
        if not cfg_file.exists():
            return None
        import yaml
        try:
            data = yaml.safe_load(cfg_file.read_text(encoding="utf-8")) or {}
            return DotConfig.from_dict(data)
        except Exception:
            return None

    def _save_dot_config_file(self, config: DotConfig, dot_dir: Path) -> None:
        cfg_file = dot_dir / "config.yaml"
        import yaml
        data = {
            "name": config.name,
            "provider": self.id,
            "mission": config.mission,
            "models": {
                "default": config.default_model,
                "escalate": config.escalate_model,
            },
            "workspace": {"path": config.workspace},
            "capabilities": {
                "allow": config.capabilities_allow,
                "deny": config.capabilities_deny,
            },
            "schedule": config.schedule,
            "extra": config.extra,
        }
        cfg_file.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

        dot_md = dot_dir / "DOT.md"
        if not dot_md.exists():
            dot_md.write_text(
                f"# {config.name}\n\n**Mission:** {config.mission}\n**Provider:** {self.name} ({self.governance})\n",
                encoding="utf-8",
            )
