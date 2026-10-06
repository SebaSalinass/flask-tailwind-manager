"""Immutable Tailwind ecosystem declarations; no lifecycle hooks."""

from types import MappingProxyType

from flask_node import ConfigurationError

from .daisyui import DAISYUI
from .flowbite import FLOWBITE
from .models import Integration
from .preline import PRELINE

REGISTRY = MappingProxyType({item.name: item for item in (PRELINE, FLOWBITE, DAISYUI)})


def select_integrations(names) -> tuple[Integration, ...]:
    if not isinstance(names, (list, tuple)) or not all(
        isinstance(n, str) for n in names
    ):
        raise ConfigurationError(
            "TAILWIND_INTEGRATIONS must be a list of integration names."
        )
    unknown = set(names) - REGISTRY.keys()
    if unknown:
        raise ConfigurationError(
            f"Unknown Tailwind integrations: {', '.join(sorted(unknown))}. "
            f"Available: {', '.join(sorted(REGISTRY))}."
        )
    return tuple(REGISTRY[name] for name in sorted(set(names)))
