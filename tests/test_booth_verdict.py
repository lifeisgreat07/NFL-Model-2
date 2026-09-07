"""
Tests for src/booth_verdict.py -- the parser for Booth's machine-readable block.

The regression suite this parser exists for will rest entirely on it, so the
cases here are mostly about the ways it could quietly say the wrong thing:
a missing block reading as a clean audit, a malformed block degrading into a
missing one, or a block that disagrees with the prose above it passing anyway.

Run with: pytest tests/test_booth_verdict.py -v
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

import booth_verdict as bv  # noqa: E402


def _report(block, checked=2, confirmed=1, discrepancies=1, unverifiable=0,
            overall='NEEDS HUMAN REVIEW'):
    """A minimal report shaped like a real one, for cross_check tests."""
    return f"""## Booth Audit: PR #31

Head commit audited: `abc1234`
Description read at: 2026-09-07T16:00:00Z

Claims checked: {checked}
Confirmed: {confirmed}
Discrepancies: {discrepancies}
Unverifiable: {unverifiable}

### Claim-by-claim
...

### Overall verdict
{overall}

```booth-verdict
{block}
```
"""


GOOD_BLOCK = """{
  "pr": 31,
  "head": "abc1234",
  "claims": [
    {"id": 1, "verdict": "CONFIRMED", "implicates": []},
    {"id": 2, "verdict": "DISCREPANCY", "implicates": ["src/thing.py"]}
  ],
  "overall": "NEEDS HUMAN REVIEW"
}"""


def test_extracts_a_well_formed_block():
    data = bv.extract(_report(GOOD_BLOCK))
    assert data['pr'] == 31
    assert [c['id'] for c in data['claims']] == [1, 2]
    assert data['claims'][1]['implicates'] == ['src/thing.py']


def test_missing_block_returns_none_rather_than_raising():
    """Absence must be distinguishable from a clean audit, not an error.

    Reports written before this protocol change have no block. They are old,
    not broken -- but a caller must never read None as 'nothing wrong'.
    """
    assert bv.extract("## Booth Audit: PR #1\n\nno block here") is None


def test_malformed_json_raises_rather_than_reading_as_missing():
    """The failure this parser most needs to avoid.

    If a broken block degraded to None, a garbled report would be
    indistinguishable from a pre-protocol one and would sail through.
    """
    with pytest.raises(bv.VerdictError, match="not valid JSON"):
        bv.extract(_report('{"pr": 31, "claims": ['))


def test_two_blocks_is_an_error():
    text = _report(GOOD_BLOCK) + "\n```booth-verdict\n" + GOOD_BLOCK + "\n```\n"
    with pytest.raises(bv.VerdictError, match="expected 1"):
        bv.extract(text)


def test_unknown_verdict_is_rejected():
    block = GOOD_BLOCK.replace('"DISCREPANCY"', '"PROBABLY FINE"')
    with pytest.raises(bv.VerdictError, match="is not one of"):
        bv.extract(_report(block))


def test_duplicate_claim_ids_are_rejected():
    block = GOOD_BLOCK.replace('"id": 2', '"id": 1')
    with pytest.raises(bv.VerdictError, match="appears twice"):
        bv.extract(_report(block))


def test_missing_required_key_is_rejected():
    block = GOOD_BLOCK.replace('"head": "abc1234",', '')
    with pytest.raises(bv.VerdictError, match="missing required key"):
        bv.extract(_report(block))


def test_unknown_overall_is_rejected():
    block = GOOD_BLOCK.replace('"NEEDS HUMAN REVIEW"\n}', '"LOOKS GOOD"\n}')
    with pytest.raises(bv.VerdictError, match="overall verdict"):
        bv.extract(_report(block))


def test_empty_claims_list_is_rejected():
    block = '{"pr": 1, "head": "a", "claims": [], "overall": "SAFE TO MERGE"}'
    with pytest.raises(bv.VerdictError, match="non-empty"):
        bv.extract(_report(block))


def test_indented_block_still_parses():
    """The protocol shows the block indented; a report may quote it that way."""
    text = _report(GOOD_BLOCK).replace('```booth-verdict', '   ```booth-verdict')
    text = text.replace('\n```\n', '\n   ```\n')
    assert bv.extract(text) is not None


# --- cross_check: the half that can catch Booth disagreeing with itself ---

def test_cross_check_passes_on_a_consistent_report():
    assert bv.cross_check(_report(GOOD_BLOCK)) == []


def test_cross_check_catches_a_count_mismatch():
    """The block as second opinion rather than restatement.

    A report whose summary says zero discrepancies while its block lists one
    was written from two different conclusions, and which half is right is
    less important than the fact that they disagree.
    """
    problems = bv.cross_check(_report(GOOD_BLOCK, confirmed=2, discrepancies=0))
    assert any('Confirmed' in p for p in problems)
    assert any('Discrepancies' in p for p in problems)


def test_cross_check_catches_discrepancies_under_safe_to_merge():
    block = GOOD_BLOCK.replace('"NEEDS HUMAN REVIEW"\n}', '"SAFE TO MERGE"\n}')
    problems = bv.cross_check(
        _report(block, overall='SAFE TO MERGE')
    )
    assert any('SAFE TO MERGE' in p for p in problems)


def test_cross_check_reports_a_missing_block_as_a_problem():
    assert bv.cross_check("no block at all") == ["no booth-verdict block found"]


# --- the question the regression suite will actually ask ---

def test_implicated_paths_finds_the_seeded_file():
    data = bv.extract(_report(GOOD_BLOCK))
    assert bv.implicated_paths(data) == {'src/thing.py'}


def test_implicated_paths_ignores_confirmed_claims():
    """A CONFIRMED claim naming a file is not Booth catching a defect there."""
    block = GOOD_BLOCK.replace(
        '{"id": 1, "verdict": "CONFIRMED", "implicates": []}',
        '{"id": 1, "verdict": "CONFIRMED", "implicates": ["src/fine.py"]}',
    )
    data = bv.extract(_report(block))
    assert 'src/fine.py' not in bv.implicated_paths(data)
    assert bv.implicated_paths(data) == {'src/thing.py'}
