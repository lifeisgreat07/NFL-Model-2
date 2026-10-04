"""Release notes come from VERSION_HISTORY, and the Releases workflow only
ever adds a release that is missing (Stage 41 item 3).

Run with: pytest tests/test_release_notes.py -v
"""
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


def test_the_workflow_skips_a_version_already_released_and_runs_only_by_hand():
    wf = WORKFLOW.read_text(encoding='utf-8')
    assert 'gh release view "v$v"' in wf and 'continue' in wf
    assert '--verify-tag' in wf, 'a release must never create a tag the history did not'
    assert 'schedule:' not in wf and 'push:' not in wf
