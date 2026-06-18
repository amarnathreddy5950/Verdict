"""verdict: a small, model-agnostic LLM evaluation toolkit.

Highlights
----------
- Rule-based and LLM-as-judge evaluators.
- A judge **bias audit** (position / length bias) with swap calibration and
  human-agreement (Cohen's kappa) -- because an un-audited judge is an unreliable judge.
- Runs fully offline with the built-in mock provider; plug in real models via litellm.
"""

from verdict.core.models import Case, CaseResult, Dataset, RunResult, Score

__all__ = ["Case", "Dataset", "Score", "CaseResult", "RunResult"]
__version__ = "0.2.0"
