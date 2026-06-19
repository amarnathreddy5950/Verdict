"""Provider registry + factory."""

from __future__ import annotations

from typing import Any

from verdict.providers.base import Completion, Provider
from verdict.providers.cache import SqliteCache
from verdict.providers.mock import MockProvider


def build_provider(spec: dict[str, Any], cache: SqliteCache | None = None) -> Provider:
    """Build a provider from a config mapping.

    Examples
    --------
    {"provider": "mock", "variant": "concise"}
    {"provider": "litellm", "model": "gpt-4o-mini"}
    """
    spec = dict(spec)
    ptype = spec.get("provider", "mock")
    name = spec.get("name")

    if ptype == "mock":
        return MockProvider(name=name or "mock", variant=spec.get("variant", "concise"))
    if ptype == "litellm":
        from verdict.providers.litellm_provider import LiteLLMProvider

        if "model" not in spec:
            raise ValueError("litellm provider requires a 'model'")
        return LiteLLMProvider(model=spec["model"], name=name, cache=cache)
    raise ValueError(f"Unknown provider type: {ptype!r}")


__all__ = ["Provider", "Completion", "MockProvider", "SqliteCache", "build_provider"]
