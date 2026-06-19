"""Load a run from a YAML config file."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from verdict.core.models import Case, Dataset
from verdict.core.runner import Target
from verdict.evaluators import build_rule_evaluator
from verdict.evaluators.base import Evaluator
from verdict.evaluators.judge import JudgeEvaluator
from verdict.providers import SqliteCache, build_provider


@dataclass
class RunSpec:
    target: Target
    dataset: Dataset
    evaluators: list[Evaluator]


def load_run_config(path: str | Path, cache: SqliteCache | None = None) -> RunSpec:
    cfg_path = Path(path)
    data: dict[str, Any] = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    base = cfg_path.parent

    # dataset: a path, or an inline mapping/list
    ds = data["dataset"]
    if isinstance(ds, str):
        dataset = Dataset.from_file(base / ds)
    elif isinstance(ds, list):
        dataset = Dataset(cases=[Case(**c) for c in ds])
    else:
        dataset = Dataset(**ds)

    # target
    tspec = dict(data["target"])
    target = Target(
        name=tspec.get("name", "target"),
        provider=build_provider(tspec, cache=cache),
        prompt_template=tspec.get("prompt", "{input}"),
        system=tspec.get("system"),
    )

    # evaluators
    evaluators: list[Evaluator] = []
    for spec in data.get("evaluators", []):
        spec = dict(spec)
        if spec.get("type") == "judge":
            judge_provider = build_provider(spec.get("judge", {"provider": "mock"}), cache=cache)
            evaluators.append(
                JudgeEvaluator(
                    judge=judge_provider,
                    rubric=spec.get("rubric", "Overall quality."),
                    scale=int(spec.get("scale", 5)),
                    threshold=int(spec.get("threshold", 3)),
                    name=spec.get("name", "judge"),
                )
            )
        else:
            evaluators.append(build_rule_evaluator(spec))

    return RunSpec(target=target, dataset=dataset, evaluators=evaluators)
