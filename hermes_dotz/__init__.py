"""Hermes Dotz Bridge.

Generic, pluggable bridge connecting Hermes to persistent autonomous Dot workers:
  - Open Dotz
  - Drex-governed Dotz
  - GPT-backed Dotz
"""
from hermes_dotz.protocol import (
    ApprovalRequest,
    DotActivityEvent,
    DotConfig,
    DotDetail,
    DotProvider,
    DotSummary,
    ProviderCapability,
    ProviderFeatures,
)
from hermes_dotz.registry import (
    ProviderRegistry,
    get_registry,
    register_provider,
)
from hermes_dotz.providers import (
    BaseDotProvider,
    DrexDotzProvider,
    GPTDotzProvider,
    OpenDotzProvider,
)
from hermes_dotz.store import DotzStore

__version__ = "0.1.0"

__all__ = [
    "ApprovalRequest",
    "BaseDotProvider",
    "DotActivityEvent",
    "DotConfig",
    "DotDetail",
    "DotProvider",
    "DotSummary",
    "DotzStore",
    "DrexDotzProvider",
    "GPTDotzProvider",
    "OpenDotzProvider",
    "ProviderCapability",
    "ProviderFeatures",
    "ProviderRegistry",
    "get_registry",
    "register_provider",
]
