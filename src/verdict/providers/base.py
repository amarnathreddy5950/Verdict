"""Model provider interface. Keep this tiny so any backend can implement it."""

from __future__ import annotations

from abc import ABC, abstractmethod

from pydantic import BaseModel


class Completion(BaseModel):
    text: str
    latency_ms: float = 0.0
    cost_usd: float = 0.0
    tokens: int = 0


class Provider(ABC):
    """A minimal text-completion interface."""

    name: str = "provider"

    @abstractmethod
    def complete(
        self, prompt: str, *, system: str | None = None, temperature: float = 0.0
    ) -> Completion:
        """Return a completion for ``prompt``."""
        raise NotImplementedError
