import pytest
from engine_helpers import chart_from, mini_chart, mini_raw

from jev_mechanic import scoring


def test_initial_scores_use_prior_and_system():
    chart = mini_chart()
    scores = scoring.initial_scores(chart, {"no_start": 0.8, "brakes": 0.2, "none": 0.0})
    raw = {"flat_battery": 0.3 * 0.8, "starter_motor": 0.2 * 0.8, "worn_pads": 0.3 * 0.2, "warped_discs": 0.2 * 0.2}
    total = sum(raw.values())
    for did, value in raw.items():
        assert scores[did] == pytest.approx(value / total)


def test_initial_scores_ignore_none_then_normalize():
    chart = mini_chart()
    scores = scoring.initial_scores(chart, {"no_start": 0.3, "brakes": 0.0, "none": 0.7})
    assert sum(scores.values()) == pytest.approx(1.0)
    assert scores["flat_battery"] == pytest.approx(0.6)
    assert scores["starter_motor"] == pytest.approx(0.4)
    assert scores["worn_pads"] == 0.0


def test_diagnosis_in_two_systems_starts_from_the_sum():
    raw = mini_raw()
    raw["diagnoses"]["flat_battery"]["systems"] = ["no_start", "brakes"]
    chart = chart_from(raw)
    scores = scoring.initial_scores(chart, {"no_start": 0.5, "brakes": 0.5})
    # flat 0.3 × 1.0, starter 0.2 × 0.5, pads 0.3 × 0.5, discs 0.2 × 0.5
    total = 0.3 + 0.1 + 0.15 + 0.1
    assert scores["flat_battery"] == pytest.approx(0.3 / total)
    assert scores["worn_pads"] == pytest.approx(0.15 / total)


def test_initial_scores_fall_back_to_priors():
    scores = scoring.initial_scores(mini_chart(), {"none": 1.0})
    assert scores["flat_battery"] == pytest.approx(0.3)


def test_update_is_the_soft_evidence_sum():
    chart = mini_chart()
    start = {"flat_battery": 0.6, "starter_motor": 0.4, "worn_pads": 0.0, "warped_discs": 0.0}
    q = {"click_only": 0.7, "slow_crank": 0.2, "unclear": 0.1}
    scores = scoring.update(chart, start, "q_key_turn", q)
    flat = 0.6 * (0.7 * 0.5 + 0.2 * 0.9 + 0.1)
    starter = 0.4 * (0.7 * 0.8 + 0.2 * 0.1 + 0.1)
    assert scores["flat_battery"] == pytest.approx(flat / (flat + starter))
    assert scores["starter_motor"] == pytest.approx(starter / (flat + starter))


def test_default_likelihood_for_unnamed_diagnosis():
    chart = mini_chart()
    start = {"flat_battery": 0.25, "starter_motor": 0.25, "worn_pads": 0.25, "warped_discs": 0.25}
    scores = scoring.update(chart, start, "q_key_turn", {"slow_crank": 1.0})
    # worn_pads gets the default 0.1 against 0.9 and 0.1
    assert scores["worn_pads"] == pytest.approx(0.1 / (0.9 + 0.1 + 0.1 + 0.1))


@pytest.mark.parametrize("neutral", ["unclear", "not_stated", "not_sure"])
def test_neutral_answer_does_not_change_scores(neutral):
    chart = mini_chart()
    start = {"flat_battery": 0.5, "starter_motor": 0.3, "worn_pads": 0.15, "warped_discs": 0.05}
    scores = scoring.update(chart, start, "q_key_turn", {neutral: 1.0})
    assert scores == pytest.approx(start)


def test_top_sorts_and_cuts():
    assert scoring.top({"a": 0.1, "b": 0.6, "c": 0.3}, 2) == [("b", 0.6), ("c", 0.3)]


def test_flag_threshold():
    assert scoring.FLAG_THRESHOLD == 0.9
