"""Optional real-model provider backed by litellm (OpenAI, Anthropic, Bedrock, ...).

``litellm`` is imported lazily so the package works fully offline without it.
"""

from __future__ import annotations

import time

from verdict.providers.base import Completion, Provider
from verdict.providers.cache import SqliteCache


class LiteLLMProvider(Provider):
    def __init__(
        self,
        model: str,
        name: str | None = None,
        cache: SqliteCache | None = None,
    ) -> None:
        self.model = model
        self.name = name or model
        self.cache = cache

    def complete(
        self, prompt: str, *, system: str | None = None, temperature: float = 0.0
    ) -> Completion:
        key = None
        if self.cache is not None:
            key = SqliteCache.make_key("litellm", self.model, system, temperature, prompt)
            hit = self.cache.get(key)
            if hit is not None:
                return Completion(text=hit, latency_ms=0.0, tokens=len(hit.split()))

        try:
            import litellm
        except ImportError as exc:  # pragma: no cover - exercised only without the extra
            raise RuntimeError(
                "litellm is not installed. Install real-model support with:\n"
                "    pip install 'verdict-evals[providers]'"
            ) from exc

        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        start = time.perf_counter()
        resp = litellm.completion(model=self.model, messages=messages, temperature=temperature)
        latency_ms = (time.perf_counter() - start) * 1000.0

        text = resp.choices[0].message.content or ""
        try:
            cost = float(litellm.completion_cost(completion_response=resp) or 0.0)
        except Exception:  # noqa: BLE001 - cost is best-effort
            cost = 0.0
        try:
            tokens = int(resp.usage.total_tokens)
        except Exception:  # noqa: BLE001 - usage is best-effort
            tokens = len(text.split())

        if self.cache is not None and key is not None:
            self.cache.set(key, text)
        return Completion(text=text, latency_ms=latency_ms, cost_usd=cost, tokens=tokens)
