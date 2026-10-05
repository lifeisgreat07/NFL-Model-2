"""Release notes come from VERSION_HISTORY, and the Releases workflow only
ever adds a release that is missing (Stage 41 item 3).

Run with: pytest tests/test_release_notes.py -v
"""
import re
from pathlib import Path

import pytest

from src.agents import release_notes as rn
from src.pipeline.config import MODEL_VERSION, VERSION_HISTORY

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / '.github' / 'workflows' / 'releases.yml'


def test_every_tagged_version_from_2_2_to_the_current_one_is_listed():
    versions = rn.released_versions()
    assert versions[0] == '2.2' and versions[-1] == MODEL_VERSION, versions
    assert '2.0' not in versions and '2.1' not in versions


def test_the_notes_are_the_history_entry_word_for_word():
    for v in rn.released_versions():
        e = next(h for h in VERSION_HISTORY if h['version'] == v)
        assert e['detail'] in rn.notes(v) and e['date'] in rn.notes(v)
        assert rn.title(v) == f"v{v}: {e['headline']}"


def test_a_version_with_two_entries_is_an_error_not_a_guess():
    with pytest.raises(ValueError):
        rn.entry('2.5', history=[{'version': '2.5'}, {'version': '2.5'}])


def _workflow():
    return WORKFLOW.read_text(encoding='utf-8').replace('\r\n', '\n')


def test_the_workflow_skips_a_version_already_released():
    wf = _workflow()
    assert 'gh release view "v$v"' in wf and 'continue' in wf
    assert '--verify-tag' in wf, 'a release must never create a tag the history did not'


def test_the_workflow_runs_by_hand_or_on_a_version_tag_never_a_branch():
    """Stage 49 item 25: a pushed `v*` tag releases itself. A branch push
    must not start it, and nor may a schedule: releases follow versions."""
    wf = _workflow()
    on = wf.split('\non:\n', 1)[1].split('\npermissions:', 1)[0]
    assert 'workflow_dispatch:' in on
    assert re.search(r"^  push:\n    tags: \['v\*'\]\n", on, re.M), on
    assert 'branches' not in on and 'schedule:' not in on, on


def test_a_pushed_tag_outside_the_history_fails_the_run():
    """A tag nobody wrote a history entry for would otherwise release
    nothing and go green."""
    wf = _workflow()
    guard = wf.split('- name: A pushed tag must name a version in the history', 1)[1]
    guard = guard.split('- name:', 1)[0]
    assert "if: github.event_name == 'push'" in guard
    assert 'TAG: ${{ github.ref_name }}' in guard
    assert 'release_notes --list | grep -qx "${TAG#v}"' in guard
    assert 'exit 1' in guard
