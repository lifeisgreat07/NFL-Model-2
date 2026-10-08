"""
src/pipeline/canary.py and .github/workflows/nightly-canary.yml.

The steps are injected, so the error paths run with no network. What is
checked: one broken step does not hide the others, a crash is a finding,
the exit code follows the errors, and the workflow alerts on failure and
writes nothing to the repository.

Run with: pytest tests/test_canary.py -v
"""
import re
from datetime import UTC, datetime
from pathlib import Path

REPO = Path(__file__).parent.parent

from src.pipeline import canary
from src.pipeline.data_quality import Report

WORKFLOW = REPO / '.github' / 'workflows' / 'nightly-canary.yml'


def _boom(state):
    raise ConnectionError('nflverse said 404')


def _warn(state):
    r = Report()
    r.warnings.append('a warning')
    return r


def _error(state):
    r = Report()
    r.errors.append('a real error')
    return r


def test_a_crashing_step_is_an_error_and_the_rest_still_run():
    ran = []
    steps = [('load', _boom), ('after', lambda s: ran.append('after') or 'fine')]
    report, notes = canary.run(2026, steps)
    assert any('load raised ConnectionError: nflverse said 404' in e for e in report.errors)
    assert ran == ['after'], 'one broken step hid the steps after it'
    assert notes[0].startswith('load: FAILED')


def test_findings_from_every_step_are_collected():
    report, _ = canary.run(2026, [('a', _warn), ('b', _error)])
    assert report.warnings == ['a warning'] and report.errors == ['a real error']


def test_warnings_alone_do_not_fail_the_canary(monkeypatch):
    monkeypatch.setattr(canary, 'default_steps', lambda: [('a', _warn)])
    assert canary.main(['--season', '2026']) == 0


def test_an_error_fails_the_canary_and_the_report_says_so(monkeypatch, tmp_path):
    monkeypatch.setattr(canary, 'default_steps', lambda: [('a', _error)])
    out = tmp_path / 'report.md'
    assert canary.main(['--season', '2026', '--report', str(out)]) == 1
    text = out.read_text(encoding='utf-8')
    assert 'FAILING' in text and 'ERROR: a real error' in text


def test_january_belongs_to_last_season():
    assert canary.current_season(datetime(2027, 1, 20, tzinfo=UTC)) == 2026
    assert canary.current_season(datetime(2026, 9, 24, tzinfo=UTC)) == 2026


def test_the_default_steps_are_the_weekly_data_path():
    names = [name for name, _ in canary.default_steps()]
    assert names == ['load play-by-play', 'load schedule', 'data quality',
                     'schema', 'next week', 'nfl.com schedule', 'sources']


# --- Stage 41 item 5: which source, not only that something broke -----------

def _head_from(answers):
    """A fake HEAD: the first matching fragment's answer, else 200."""
    def head(url):
        for fragment, answer in answers.items():
            if fragment in url:
                return answer
        return 200, None
    return head


def test_every_source_answering_is_quiet():
    r = canary.reachability(2026, 6, head=_head_from({}))
    assert r.errors == [] and r.warnings == []


def test_an_unreachable_source_a_pick_depends_on_is_an_error_naming_it():
    r = canary.reachability(2026, 6, head=_head_from({'play_by_play_2026': (None, 'URLError: timed out')}))
    assert len(r.errors) == 1 and r.errors[0].startswith('nflverse play-by-play: unreachable (URLError')
    assert 'play_by_play_2026.parquet' in r.errors[0]


def test_a_missing_schedule_file_is_an_error():
    r = canary.reachability(2026, 6, head=_head_from({'schedules/games': (404, None)}))
    assert r.errors == [f'nflverse schedules: HTTP 404 -- {canary.NFLVERSE}schedules/games.parquet']


def test_a_context_source_failing_is_only_a_warning():
    """Injuries, depth charts and the TV page feed context; none of them
    ever costs a pick, so none of them fails the canary."""
    r = canary.reachability(2026, 6, head=_head_from({'injuries_2026': (404, None),
                                                      'nfl.com': (403, None)}))
    assert r.errors == []
    assert [w.split(':')[0] for w in r.warnings] == ['nflverse injuries', 'nfl.com schedule']


def test_the_tv_page_is_not_asked_for_a_week_past_the_regular_season():
    asked = []
    canary.reachability(2026, 19, head=lambda url: asked.append(url) or (200, None))
    assert not any('nfl.com' in u for u in asked)


def test_a_redirect_counts_as_answering():
    """nflverse's release assets answer 302 to a storage host."""
    r = canary.reachability(2026, 6, head=_head_from({'nflverse': (302, None)}))
    assert r.errors == []


# --- the workflow ------------------------------------------------------------

def _text():
    return WORKFLOW.read_text(encoding='utf-8')


def test_it_runs_every_night():
    assert re.search(r"cron:\s*'0 6 \* \* \*'", _text())


def test_a_failure_raises_the_alert():
    text = _text()
    alert = text[text.index('- name: Raise an alert'):]
    assert re.search(r'if:\s*failure\(\)', alert)
    assert '--title "Nightly canary failing"' in alert
    assert '--report canary-report.md' in text and '--body-file canary-report.md' in alert


def test_it_can_open_issues_and_cannot_write_the_repository():
    """The canary must never be able to touch a lock, a pick or a grade."""
    text = _text()
    block = re.search(r'^permissions:\s*\n((?:[ \t]+.+\n)+)', text, re.M)
    granted = dict(re.findall(r'(\S+):\s*(\S+)', block.group(1)))
    assert granted == {'contents': 'read', 'issues': 'write'}
    assert 'git-auto-commit' not in text and 'git push' not in text
