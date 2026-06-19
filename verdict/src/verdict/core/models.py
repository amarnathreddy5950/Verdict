"""Core data models for verdict."""

from __future__ import annotations

import json
from pathlib import Path
from statistics import mean
from typing import Any

import yaml
from pydantic import BaseModel, Field


class Case(BaseModel):
    """A single evaluation case."""

    id: str
    input: str
    reference: str | None = None  # gold / expected answer, if any
    metadata: dict[str, Any] = Field(default_factory=dict)


class Dataset(BaseModel):
    """A named collection of cases."""

    name: str = "dataset"
    cases: list[Case] = Field(default_factory=list)

    def __len__(self) -> int:
        return len(self.cases)

    def __iter__(self):
        return iter(self.cases)

    @classmethod
    def from_file(cls, path: str | Path) -> Dataset:
        """Load a dataset from YAML or JSON.

        Accepts either a list of cases or a mapping with ``name`` and ``cases``.
        """
        p = Path(path)
        raw = p.read_text(encoding="utf-8")
        data = yaml.safe_load(raw) if p.suffix in {".yaml", ".yml"} else json.loads(raw)
        if isinstance(data, list):
            return cls(name=p.stem, cases=[Case(**c) for c in data])
        return cls(name=data.get("name", p.stem), cases=[Case(**c) for c in data["cases"]])


class Score(BaseModel):
    """The result of one evaluator applied to one output."""

    name: str
    value: float
    passed: bool
    rationale: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class CaseResult(BaseModel):
    """The output and scores for a single case."""

    case_id: str
    output: str = ""
    scores: list[Score] = Field(default_factory=list)
    latency_ms: float | None = None
    cost_usd: float | None = None
    tokens: int | None = None
    error: str | None = None

    def score(self, name: str) -> Score | None:
        return next((s for s in self.scores if s.name == name), None)


class RunResult(BaseModel):
    """All results for one target over a dataset, plus aggregates."""

    target: str
    dataset: str
    case_results: list[CaseResult] = Field(default_factory=list)

    # ---- aggregates -------------------------------------------------------
    @property
    def n(self) -> int:
        return len(self.case_results)

    def pass_rate(self, evaluator: str | None = None) -> float:
        """Fraction of (case, evaluator) scores that passed."""
        flags = [
            s.passed
            for r in self.case_results
            for s in r.scores
            if evaluator is None or s.name == evaluator
        ]
        return round(sum(flags) / len(flags), 4) if flags else 0.0

    def mean_score(self, evaluator: str) -> float | None:
        vals = [s.value for r in self.case_results for s in r.scores if s.name == evaluator]
        return round(mean(vals), 4) if vals else None

    def evaluator_names(self) -> list[str]:
        seen: list[str] = []
        for r in self.case_results:
            for s in r.scores:
                if s.name not in seen:
                    seen.append(s.name)
        return seen

    def mean_latency_ms(self) -> float | None:
        vals = [r.latency_ms for r in self.case_results if r.latency_ms is not None]
        return round(mean(vals), 2) if vals else None

    def total_cost_usd(self) -> float:
        return round(sum(r.cost_usd or 0.0 for r in self.case_results), 6)

    def summary(self) -> dict[str, Any]:
        return {
            "target": self.target,
            "dataset": self.dataset,
            "n": self.n,
            "pass_rate": self.pass_rate(),
            "by_evaluator": {
                name: {
                    "pass_rate": self.pass_rate(name),
                    "mean_score": self.mean_score(name),
                }
                for name in self.evaluator_names()
            },
            "mean_latency_ms": self.mean_latency_ms(),
            "total_cost_usd": self.total_cost_usd(),
        }
