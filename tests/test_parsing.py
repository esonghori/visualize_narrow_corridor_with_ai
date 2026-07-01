"""No-network tests for parsing, fallback, and JSON round-tripping."""

from narrow_corridor.llm import _parse, _regex_fallback
from narrow_corridor.models import NarrowCorridorPath, PeriodScore


def test_parse_plain_json():
    raw = (
        '{"society_power": 3.2, "state_power": 5.1, "society_change": 0.0, '
        '"state_change": 0.0, "key_event": "Constitutional Revolution", '
        '"reasoning": "Civic mobilization rose."}'
    )
    score = _parse(raw, 0.0, 0.0)
    assert score is not None
    assert score.society_power == 3.2
    assert score.state_power == 5.1
    assert score.key_event == "Constitutional Revolution"


def test_parse_fenced_json():
    raw = '```json\n{"society_power": 4, "state_power": 6, "key_event": "x", "reasoning": "y"}\n```'
    score = _parse(raw, 0.0, 0.0)
    assert score is not None
    assert score.society_power == 4
    assert score.state_power == 6


def test_parse_json_with_surrounding_prose():
    raw = 'Here is my analysis. {"society_power": 2, "state_power": 8, "key_event": "coup", "reasoning": "z"} Done.'
    score = _parse(raw, 0.0, 0.0)
    assert score is not None
    assert score.state_power == 8


def test_regex_fallback_four_tuple():
    score = _regex_fallback("changes <0.5, -1.0, 4.5, 6.0>", prev_society=4.0, prev_state=7.0)
    assert score is not None
    assert (score.society_power, score.state_power) == (4.5, 6.0)
    assert (score.society_change, score.state_change) == (0.5, -1.0)


def test_regex_fallback_two_tuple_derives_change():
    score = _regex_fallback("<6.0, 8.0>", prev_society=4.0, prev_state=5.0)
    assert score is not None
    assert score.society_change == 2.0
    assert score.state_change == 3.0


def test_parse_returns_none_on_garbage():
    assert _parse("no numbers here", 0.0, 0.0) is None


def test_path_json_roundtrip():
    path = NarrowCorridorPath(country="Testland", model="gemini/gemini-2.0-flash")
    p1, p2 = (1900, 1904), (1905, 1909)
    for p, soc, st, ev in [(p1, 3.0, 5.0, "founding"), (p2, 4.0, 6.0, "reform")]:
        path.periods.append(p)
        path.society_power[p] = soc
        path.state_power[p] = st
        path.key_event[p] = ev
        path.reasoning[p] = "because"
        path.score_prompt[p] = "prompt"
        path.score_response[p] = "resp"

    restored = NarrowCorridorPath.from_dict(path.to_dict())
    assert restored.periods == [p1, p2]
    assert restored.society_power[p2] == 4.0
    assert restored.key_event[p1] == "founding"
    assert restored.country == "Testland"


def test_period_score_defaults_changes_to_zero():
    score = PeriodScore(society_power=1.0, state_power=2.0, key_event="e", reasoning="r")
    assert score.society_change == 0.0
    assert score.state_change == 0.0
