"""Tokens, cost and time of each Jev request, with the Opus 5 cost of the same input tokens."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from .jev import JevResult

JEV_PRICE_PER_MTOK = 0.042
OPUS5_INPUT_PRICE_PER_MTOK = 5.00


@dataclass
class LedgerRow:
    step: int
    lane: str
    kind: str
    input_tokens: int
    output_tokens: int
    model: str
    seconds: float
    jev_cost: float
    opus5_cost: float

    def to_dict(self) -> dict:
        return asdict(self)


class Ledger:
    """One row for each Jev request of a session."""

    def __init__(self) -> None:
        self.rows: list[LedgerRow] = []

    def add(self, step: int, lane: str, kind: str, result: JevResult) -> LedgerRow:
        row = LedgerRow(
            step=step,
            lane=lane,
            kind=kind,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            model=result.model,
            seconds=result.seconds,
            jev_cost=result.input_tokens * JEV_PRICE_PER_MTOK / 1e6,
            opus5_cost=result.input_tokens * OPUS5_INPUT_PRICE_PER_MTOK / 1e6,
        )
        self.rows.append(row)
        return row

    def totals(self) -> dict:
        """Return the sums. `wait_seconds` adds the longest request of each step."""
        longest: dict[int, float] = {}
        for row in self.rows:
            longest[row.step] = max(longest.get(row.step, 0.0), row.seconds)
        return {
            "requests": len(self.rows),
            "input_tokens": sum(r.input_tokens for r in self.rows),
            "output_tokens": sum(r.output_tokens for r in self.rows),
            "jev_cost": sum(r.jev_cost for r in self.rows),
            "opus5_cost": sum(r.opus5_cost for r in self.rows),
            "compute_seconds": sum(r.seconds for r in self.rows),
            "wait_seconds": sum(longest.values()),
        }

    def to_dict(self) -> dict:
        return {"rows": [r.to_dict() for r in self.rows], "totals": self.totals()}
