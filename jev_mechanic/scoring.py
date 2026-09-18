"""Diagnosis scores: a naive Bayes update with soft evidence from the Jev distributions."""

from __future__ import annotations

from .flowchart import Flowchart

FLAG_THRESHOLD = 0.9


def _normalize(scores: dict[str, float]) -> dict[str, float]:
    total = sum(scores.values())
    if total <= 0:
        return {d: 1.0 / len(scores) for d in scores}
    return {d: s / total for d, s in scores.items()}


def initial_scores(chart: Flowchart, system_probs: dict[str, float]) -> dict[str, float]:
    """Return P(d) ∝ prior(d) × the sum of the triage probabilities of the systems of d.

    Keys that are not systems, such as `none`, have no effect. When the systems get no
    probability, the scores are the normalized priors.
    """
    scores = {
        did: d.prior * sum(system_probs.get(s, 0.0) for s in d.systems)
        for did, d in chart.diagnoses.items()
    }
    if sum(scores.values()) <= 0:
        scores = {did: d.prior for did, d in chart.diagnoses.items()}
    return _normalize(scores)


def update(
    chart: Flowchart, scores: dict[str, float], node_id: str, option_probs: dict[str, float]
) -> dict[str, float]:
    """Return P(d) × Σ_a q(a) × L(a | d), normalized, for the answer distribution q."""
    node = chart.nodes[node_id]
    updated = {
        did: score * sum(q * node.likelihood(a, did) for a, q in option_probs.items())
        for did, score in scores.items()
    }
    if sum(updated.values()) <= 0:
        return dict(scores)
    return _normalize(updated)


def top(scores: dict[str, float], n: int) -> list[tuple[str, float]]:
    """Return the `n` highest scores, highest first."""
    return sorted(scores.items(), key=lambda item: item[1], reverse=True)[:n]
