import json
from pathlib import Path

import pytest

from practicepreach.quote_matching import quote_needles

FIXTURES_PATH = Path(__file__).resolve().parents[2] / "fixtures" / "quote-matching.json"
CASES = json.loads(FIXTURES_PATH.read_text(encoding="utf-8"))


def _case_id(case: dict) -> str:
    return case["name"]


@pytest.mark.parametrize(
    "case",
    [
        pytest.param(
            case,
            marks=pytest.mark.xfail(reason=case["reason"], strict=True)
            if case.get("knownGap")
            else (),
        )
        for case in CASES
    ],
    ids=_case_id,
)
def test_quote_needles_matches_fixture(case: dict) -> None:
    assert quote_needles(case["quote"]) == case["needles"]
