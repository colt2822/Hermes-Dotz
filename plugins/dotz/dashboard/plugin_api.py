"""Dotz dashboard API routes mounted at /api/plugins/dotz/."""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure hermes_dotz package is importable
_pkg_root = Path(__file__).resolve().parents[3]
if str(_pkg_root) not in sys.path:
    sys.path.insert(0, str(_pkg_root))

from hermes_dotz.dashboard_api import router

__all__ = ["router"]
