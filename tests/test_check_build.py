"""
src/check_build.py: the built page carries every payload its pages need.

Checked twice, per this repo's rule for guards whose failing branch today's
data cannot reach: once over the real built page, which must pass, and once
over synthetic pages broken in exactly the way each rule names.

Run with: pytest tests/test_check_build.py -v
"""
import json
import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO / 'src'))

import check_build as cb  # noqa: E402
from data_quality import NFL_TEAMS  # noqa: E402

TEAMS = sorted(NFL_TEAMS)
PAGES = REPO / '.github' / 'workflows' / 'deploy-pages.yml'


def good():
    return {
        'agentLog': {'audits': [{'pr': 1}]},
        'versionHistory': [{'version': '2.5'}],
        'modelVersion': '2.5',
        'teams': [{'team': t} for t in TEAMS],
        'playoffMeta': {'season': 2026},
        'weeks': {'2026_week1': {'games': [{'home': 'KC'}]}},
        'latestWeekKey': '2026_week1',
        'picksPdfs': ['2026_week1'],
        'accuracy': {'weeks': []},
        'teamHistory': {'names': {}, 'timeline': {t: [{'net': 0.1}] for t in TEAMS}},
        'calibration': {'models': {'model_a': {}}},
    }


def page(payloads):
    lines = [f'const {k} = {json.dumps(v, indent=2)};' for k, v in payloads.items()]
    return '<script>\n' + '\n'.join(lines) + '\n</script>'


def errors_for(**changes):
    p = good()
    for k, v in changes.items():
        if v is KeyError:
            del p[k]
        else:
            p[k] = v
    return cb.check(page(p)).errors


def test_the_real_built_page_passes():
    """conftest.py builds index.html once per session."""
    html = (REPO / 'index.html').read_text(encoding='utf-8')
    report = cb.check(html)
    assert report.errors == [], report.errors
    assert set(cb.extract(html)) == set(cb.PAYLOADS), 'the extractor found fewer payloads than the page has'


def test_a_good_synthetic_page_passes():
    assert cb.check(page(good())).lines() == []


@pytest.mark.parametrize('name, value, phrase', [
    ('teamHistory', {'names': {}, 'timeline': {}}, 'Team Deep-Dive would be blank'),
    ('teamHistory', {'names': {}, 'timeline': {**{t: [{'net': 0}] for t in TEAMS}, 'KC': []}},
     'Team Deep-Dive would be blank'),
    ('teams', [{'team': t} for t in TEAMS[:31]], 'does not hold the 32 teams'),
    ('weeks', {}, 'holds no saved weeks'),
    ('weeks', {'2026_week1': {'games': []}}, 'a week with no games'),
    ('latestWeekKey', '2026_week9', 'is not one of the saved weeks'),
    ('latestWeekKey', None, 'is not one of the saved weeks'),
    ('accuracy', {}, 'no weeks list'),
    ('versionHistory', [], "What's Changed would be blank"),
    ('modelVersion', '', 'is empty'),
    ('calibration', None, 'reliability diagram would be omitted'),
    ('agentLog', None, 'no audits were ever recorded'),
])
def test_each_empty_payload_is_an_error(name, value, phrase):
    errs = errors_for(**{name: value})
    assert any(f'`{name}`' in e and phrase in e for e in errs), errs


def test_a_payload_missing_from_the_page_is_an_error():
    assert any('no `calibration` payload' in e for e in errors_for(calibration=KeyError))


def test_a_payload_that_is_not_json_is_an_error():
    html = page(good()).replace('const modelVersion = "2.5"', 'const modelVersion = __oops')
    assert any('`modelVersion` is not valid JSON' in e for e in cb.check(html).errors)


def test_an_unfilled_placeholder_is_an_error():
    html = page(good()) + '<p>__SIDEBAR_FOOT__</p>'
    assert any("['__SIDEBAR_FOOT__']" in e for e in cb.check(html).errors)


def test_no_picks_sheets_is_only_a_warning():
    report = cb.check(page({**good(), 'picksPdfs': []}))
    assert report.errors == [] and report.warnings


def test_an_empty_season_accuracy_is_allowed():
    """Before the first graded week there is nothing to show, honestly."""
    assert errors_for(accuracy={'weeks': []}) == []


def test_main_fails_on_a_missing_file(tmp_path, capsys):
    assert cb.main([str(tmp_path / 'nope.html')]) == 1


# --- wired into the Pages build ----------------------------------------------

def test_pages_checks_the_build_before_uploading_it():
    """A check that runs after the upload, or not at all, publishes the
    broken page anyway."""
    text = PAGES.read_text(encoding='utf-8')
    build = text.index('run: python src/generate_dashboard.py')
    check = text.index('run: python src/check_build.py index.html')
    upload = text.index('uses: actions/upload-pages-artifact')
    assert build < check < upload
