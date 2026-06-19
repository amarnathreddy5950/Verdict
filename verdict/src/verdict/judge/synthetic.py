"""A synthetic judge with *injectable* biases.

This exists so the bias probes/auditor can be demonstrated and unit-tested fully
offline: we inject a known bias (position, length, style, authority, sentiment) and
confirm the probe detects it. The same probes run unchanged against a real LLM judge.

Each bias is a probability that the judge ignores content and instead prefers the
answer carrying that feature (e.g., the one with Markdown, or a citation).
"""

from __future__ import annotations

import hashlib
import random
import re

from verdict.judge.base import PairwiseJudge, Verdict

_MARKDOWN = re.compile(r"(\*\*|__|^#{1,6}\s|`|^\s*[-*+]\s)", re.MULTILINE)
_CITATION = re.compile(r"(\[\d+\]|https?://|et al\.|\(\d{4}\))")
_POLITE = re.compile(r"\b(please|thank|thanks|happy|glad|kindly|appreciate)\b", re.IGNORECASE)


def _stable_hash(text: str) -> int:
    return int(hashlib.sha256(text.encode("utf-8")).hexdigest(), 16)


def _has_markdown(text: str) -> bool:
    return _MARKDOWN.search(text) is not None


def _has_citation(text: str) -> bool:
    return _CITATION.search(text) is not None


def _politeness(text: str) -> int:
    return len(_POLITE.findall(text))


class SyntheticBiasedJudge(PairwiseJudge):
    """A judge that mixes a stable content preference with injected biases.

    Parameters (each in [0, 1] -- the probability of applying that bias)
    --------------------------------------------------------------------
    position_bias  : blindly prefer whichever answer is shown first.
    length_bias    : prefer the longer answer.
    style_bias     : prefer the answer that contains Markdown formatting.
    authority_bias : prefer the answer that contains a citation/reference.
    sentiment_bias : prefer the more polite / positive-toned answer.
    noise          : decide at random.
    """

    def __init__(
        self,
        position_bias: float = 0.0,
        length_bias: float = 0.0,
        style_bias: float = 0.0,
        authority_bias: float = 0.0,
        sentiment_bias: float = 0.0,
        noise: float = 0.0,
        seed: int = 0,
        name: str = "synthetic",
    ) -> None:
        self.position_bias = position_bias
        self.length_bias = length_bias
        self.style_bias = style_bias
        self.authority_bias = authority_bias
        self.sentiment_bias = sentiment_bias
        self.noise = noise
        self.seed = seed
        self.name = name

    def _rng(self, question: str, answer_a: str, answer_b: str) -> random.Random:
        return random.Random(_stable_hash(f"{question}|{answer_a}|{answer_b}|{self.seed}"))

    @staticmethod
    def _content_pref(answer_a: str, answer_b: str) -> Verdict:
        # Stable, position-independent "true" preference; identical answers -> tie.
        ha, hb = _stable_hash(answer_a), _stable_hash(answer_b)
        if ha == hb:
            return "tie"
        return "A" if ha > hb else "B"

    def compare(self, question: str, answer_a: str, answer_b: str) -> Verdict:
        rng = self._rng(question, answer_a, answer_b)

        if rng.random() < self.position_bias:
            return "A"
        if rng.random() < self.style_bias:
            ma, mb = _has_markdown(answer_a), _has_markdown(answer_b)
            if ma != mb:
                return "A" if ma else "B"
        if rng.random() < self.authority_bias:
            ca, cb = _has_citation(answer_a), _has_citation(answer_b)
            if ca != cb:
                return "A" if ca else "B"
        if rng.random() < self.sentiment_bias:
            pa, pb = _politeness(answer_a), _politeness(answer_b)
            if pa != pb:
                return "A" if pa > pb else "B"
        if rng.random() < self.length_bias and len(answer_a) != len(answer_b):
            return "A" if len(answer_a) > len(answer_b) else "B"
        if rng.random() < self.noise:
            return rng.choice(["A", "B"])
        return self._content_pref(answer_a, answer_b)
