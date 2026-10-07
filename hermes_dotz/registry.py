"""Public provider registry for Hermes Dotz bridge.

Enables dynamic registration and feature detection for Dot providers:
  - Open Dotz
  - Drex Dotz
  - GPT Dotz
  - External extensions (e.g. private NOVA adapters)
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Type, Union

from hermes_dotz.protocol import DotConfig, DotDetail, DotProvider, DotSummary
from hermes_dotz.providers.drex_dot import DrexDotzProvider
from hermes_dotz.providers.gpt_dot import GPTDotzProvider
from hermes_dotz.providers.open_dot import OpenDotzProvider
from hermes_dotz.store import DotzStore

log = logging.getLogger(__name__)


class ProviderRegistry:
    """Registry managing available Dot providers and routing operations to them."""

    def __init__(self, root_dir: Path, store: Optional[DotzStore] = None):
        self.root_dir = Path(root_dir).resolve()
        self.root_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.store = store or DotzStore(self.root_dir / "dotz.db")
        self._providers: Dict[str, DotProvider] = {}
        self._default_provider_id = "open-dotz"

        # Register standard built-in providers
        self.register(OpenDotzProvider(self.root_dir, self.store))
        self.register(DrexDotzProvider(self.root_dir, self.store))
        self.register(GPTDotzProvider(self.root_dir, self.store))

    def register(self, provider: Union[DotProvider, Type[DotProvider]]) -> None:
        """Register a provider instance or provider class."""
        if isinstance(provider, type):
            instance = provider(self.root_dir, self.store)
        else:
            instance = provider
        self._providers[instance.id] = instance
        # Support aliases
        if instance.id == "open-dotz":
            self._providers["open"] = instance
        elif instance.id == "drex-dotz":
            self._providers["drex"] = instance
        elif instance.id == "gpt-dotz":
            self._providers["gpt"] = instance

        log.info("Registered Dot provider: %s (%s)", instance.id, instance.name)

    def get(self, provider_id: Optional[str]) -> DotProvider:
        """Get provider by id with fallback to default."""
        if not provider_id:
            return self._providers[self._default_provider_id]
        clean_id = provider_id.strip().lower()
        if clean_id in self._providers:
            return self._providers[clean_id]
        # Fallback to default if unknown
        log.warning("Unknown provider '%s'; falling back to '%s'", provider_id, self._default_provider_id)
        return self._providers[self._default_provider_id]

    def list_descriptors(self) -> List[Dict[str, Any]]:
        """List provider descriptions and feature matrices for API/UI discovery."""
        descriptors = []
        seen = set()
        for p in self._providers.values():
            if p.id in seen:
                continue
            seen.add(p.id)
            descriptors.append({
                "id": p.id,
                "name": p.name,
                "description": p.description,
                "features": p.features.to_dict(),
                "governance": p.governance,
            })
        return descriptors

    def resolve_for_dot(self, dot_name: str) -> DotProvider:
        """Resolve which provider owns a specific dot."""
        row = self.store.one("SELECT provider FROM dots WHERE name = ?", (dot_name,))
        if row and row.get("provider"):
            return self.get(row["provider"])
        return self.get(self._default_provider_id)

    def list_all_dots(self) -> List[DotSummary]:
        """Aggregate dot summaries across all registered providers."""
        all_dots: List[DotSummary] = []
        seen_names = set()
        for p in [self.get("open-dotz"), self.get("drex-dotz"), self.get("gpt-dotz")]:
            for d in p.list_dots():
                if d.name not in seen_names:
                    seen_names.add(d.name)
                    all_dots.append(d)
        # Any other custom registered providers
        for pid, p in self._providers.items():
            if pid in ("open", "drex", "gpt", "open-dotz", "drex-dotz", "gpt-dotz"):
                continue
            for d in p.list_dots():
                if d.name not in seen_names:
                    seen_names.add(d.name)
                    all_dots.append(d)
        return all_dots

    def get_dot(self, dot_name: str) -> Optional[DotDetail]:
        """Get dot details using its resolved provider."""
        provider = self.resolve_for_dot(dot_name)
        return provider.get_dot(dot_name)

    def create_dot(self, config: DotConfig) -> DotDetail:
        """Create dot using the provider specified in config."""
        provider = self.get(config.provider)
        return provider.create_dot(config)


_default_registry: Optional[ProviderRegistry] = None


def get_registry(root_dir: Optional[Path] = None) -> ProviderRegistry:
    """Singleton getter for default provider registry."""
    global _default_registry
    if _default_registry is None:
        import os
        base = Path(os.environ.get("DOTZ_RUNTIME_DIR", Path.home() / "dotz_runtime"))
        _default_registry = ProviderRegistry(root_dir or base)
    return _default_registry


def register_provider(provider: Union[DotProvider, Type[DotProvider]]) -> None:
    """Convenience helper to register custom or external provider."""
    get_registry().register(provider)
