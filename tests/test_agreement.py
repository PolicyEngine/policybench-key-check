"""Properties of the agreement classes (scripts/agreement.py: classify)."""

import importlib.util
import itertools
from pathlib import Path

from hypothesis import given
from hypothesis import strategies as st

spec = importlib.util.spec_from_file_location(
    "agreement", Path(__file__).resolve().parents[1] / "scripts" / "agreement.py"
)
agreement = importlib.util.module_from_spec(spec)
spec.loader.exec_module(agreement)
classify = agreement.classify

amounts = st.floats(min_value=-1e6, max_value=1e6, allow_nan=False, allow_infinity=False)
MODELS = ("policyengine", "taxcalc", "taxsim")


@given(amounts, amounts, amounts)
def test_three_answers_fall_in_exactly_one_class(a, b, c):
    result = classify(dict(zip(MODELS, (a, b, c))), 1.0)
    spread = max(a, b, c) - min(a, b, c)
    pairs_close = [abs(x - y) <= 1.0 for x, y in itertools.combinations((a, b, c), 2)]
    if spread <= 1.0:
        assert result == "all_agree"
    elif not any(pairs_close):
        assert result == "all_differ"
    elif sum(pairs_close) == 1:
        assert result.startswith("two_agree:")
    else:
        assert result == "chain"


@given(amounts, amounts, amounts)
def test_the_odd_model_is_the_one_outside_the_agreeing_pair(a, b, c):
    values = dict(zip(MODELS, (a, b, c)))
    result = classify(values, 1.0)
    if result.startswith("two_agree:"):
        odd = result.split(":", 1)[1]
        rest = [m for m in MODELS if m != odd]
        assert abs(values[rest[0]] - values[rest[1]]) <= 1.0
        assert all(abs(values[odd] - values[m]) > 1.0 for m in rest)


@given(amounts, amounts, amounts, st.permutations(MODELS))
def test_class_does_not_depend_on_model_order(a, b, c, order):
    values = dict(zip(MODELS, (a, b, c)))
    shuffled = {m: values[m] for m in order}
    assert classify(values, 1.0) == classify(shuffled, 1.0)




@given(amounts, amounts)
def test_a_missing_model_leaves_a_pair(a, b):
    result = classify({"policyengine": a, "taxcalc": b, "taxsim": None}, 1.0)
    assert result == ("pair_agree:taxsim" if abs(a - b) <= 1.0 else "pair_differ:taxsim")


def test_one_answer():
    assert classify({"policyengine": 5.0, "taxcalc": None, "taxsim": None}, 1.0) == "one_answer"


def test_examples():
    assert classify({"policyengine": 100.0, "taxcalc": 100.4, "taxsim": 99.6}, 1.0) == "all_agree"
    assert classify({"policyengine": 100.0, "taxcalc": 100.4, "taxsim": 250.0}, 1.0) == "two_agree:taxsim"
    assert classify({"policyengine": 100.0, "taxcalc": 300.0, "taxsim": 100.9}, 1.0) == "two_agree:taxcalc"
    assert classify({"policyengine": 0.0, "taxcalc": 300.0, "taxsim": 100.9}, 1.0) == "all_differ"
    assert classify({"policyengine": 0.0, "taxcalc": 0.9, "taxsim": 1.8}, 1.0) == "chain"
