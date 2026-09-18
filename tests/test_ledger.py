import pytest

from jev_mechanic.jev import JevResult
from jev_mechanic.ledger import JEV_PRICE_PER_MTOK, OPUS5_INPUT_PRICE_PER_MTOK, Ledger


def result(input_tokens: int, seconds: float) -> JevResult:
    return JevResult(answers={}, input_tokens=input_tokens, output_tokens=40, model="jev-1.13.0", seconds=seconds)


def test_row_costs():
    row = Ledger().add(0, "flowchart", "A", result(2000, 0.8))
    assert row.jev_cost == pytest.approx(2000 * 0.042 / 1e6)
    assert row.opus5_cost == pytest.approx(2000 * 5.00 / 1e6)
    assert JEV_PRICE_PER_MTOK == 0.042
    assert OPUS5_INPUT_PRICE_PER_MTOK == 5.00
    assert (row.step, row.lane, row.kind, row.model) == (0, "flowchart", "A", "jev-1.13.0")


def test_totals_and_wait_seconds():
    ledger = Ledger()
    ledger.add(0, "flowchart", "A", result(2000, 0.8))
    ledger.add(0, "independent", "C", result(1000, 0.5))
    ledger.add(1, "flowchart", "B", result(800, 0.3))
    ledger.add(1, "independent", "C", result(1200, 0.6))
    ledger.add(2, "flowchart", "B", result(700, 0.4))
    totals = ledger.totals()
    assert totals["requests"] == 5
    assert totals["input_tokens"] == 5700
    assert totals["output_tokens"] == 200
    assert totals["jev_cost"] == pytest.approx(5700 * 0.042 / 1e6)
    assert totals["opus5_cost"] == pytest.approx(5700 * 5.00 / 1e6)
    assert totals["compute_seconds"] == pytest.approx(2.6)
    assert totals["wait_seconds"] == pytest.approx(0.8 + 0.6 + 0.4)


def test_empty_totals():
    totals = Ledger().totals()
    assert totals["requests"] == 0
    assert totals["wait_seconds"] == 0


def test_to_dict_shape():
    ledger = Ledger()
    ledger.add(0, "flowchart", "A", result(100, 0.1))
    data = ledger.to_dict()
    assert set(data) == {"rows", "totals"}
    assert data["rows"][0]["input_tokens"] == 100
