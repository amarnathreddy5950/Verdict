"""A deterministic, offline provider so verdict runs with zero API keys.

Different ``variant`` values produce different output styles, which makes the
example report interesting (and lets tests assert deterministic behaviour).
"""

from __future__ import annotations

import json
import re

from verdict.providers.base import Completion, Provider

_FILLER = (
    " In summary, this captures the main idea while remaining faithful to the source text."
)


def _sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p for p in parts if p]


class MockProvider(Provider):
    """Deterministic provider.

    variants:
        - "concise":  first sentence of the input (after any 'Summarize:' prefix)
        - "verbose":  first two sentences plus a filler clause
        - "echo":     the input, truncated
    """

    def __init__(self, name: str = "mock", variant: str = "concise") -> None:
        self.name = name
        self.variant = variant

    def _payload(self, prompt: str) -> str:
        # Strip a leading instruction like "Summarize the following:\n..."
        body = prompt
        if ":" in prompt:
            body = prompt.split(":", 1)[1].strip() or prompt
        return body

    def complete(
        self, prompt: str, *, system: str | None = None, temperature: float = 0.0
    ) -> Completion:
        if self.variant == "judge":
            return self._judge(prompt)
        body = self._payload(prompt)
        sents = _sentences(body)
        if self.variant == "verbose":
            text = " ".join(sents[:2]) + _FILLER
        elif self.variant == "echo":
            text = body[:200]
        else:  # concise
            text = sents[0] if sents else body[:120]
        # Deterministic, free, but report a plausible latency/token estimate.
        tokens = max(1, len(text.split()))
        return Completion(text=text.strip(), latency_ms=12.0, cost_usd=0.0, tokens=tokens)

    def _judge(self, prompt: str) -> Completion:
        """Deterministic rubric scorer: rewards mid-length, faithful-looking summaries."""
        candidate = prompt
        if "Candidate answer:" in prompt:
            candidate = prompt.split("Candidate answer:", 1)[1]
        candidate = candidate.replace("Return JSON only.", "")
        words = len(candidate.split())
        if words == 0:
            score = 1
        elif words <= 3:
            score = 2
        elif words <= 15:
            score = 5
        elif words <= 30:
            score = 4
        else:
            score = 3
        text = json.dumps({"score": score, "rationale": f"{words} words"})
        return Completion(text=text, latency_ms=10.0, cost_usd=0.0, tokens=len(text.split()))
