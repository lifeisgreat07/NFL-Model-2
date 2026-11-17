"""The March Madness page in the site build (Stage 103 item 4): built in its own process, only when it writes a
page; a day with no page is not a failure; its card on the home page only when the page was built.

Run with: pytest tests/test_march_build.py -v
"""
import json
from datetime import date
from itertools import combinations
from pathlib import Path

from src.site import build, home
from src.sports.ncaam import bracket

ROOT = Path(__file__).resolve().parents[1]
PAGE = '<!DOCTYPE html><html><head></head><body><main>{what}</main></body></html>'


class Runner:
    """Each builder writes its page, the March page as `march` says: 'page', 'none' (another month) or 'fail'."""

    def __init__(self, march='page'):
        self.march, self.calls = march, []

    def __call__(self, cmd):
        self.calls.append(cmd)
        if cmd[3] == 'src.sports.ncaam.page' and self.march != 'page':
            return 1 if self.march == 'fail' else 0
        out = Path(cmd[cmd.index('--out') + 1])
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(PAGE.format(what=cmd[3]), encoding='utf-8')
        return 0


def test_the_march_page_is_built_from_the_year_s_lock_for_the_day(tmp_path):
    run = Runner()
    res, lock = build.build_march(tmp_path, run, date(2027, 3, 20))
    assert res.built and not res.error
    assert lock == build.MARCH_LOCKS / 'lock_2027.json'
    cmd = run.calls[0]
    assert cmd[cmd.index('--today') + 1] == '2027-03-20' and cmd[cmd.index('--lock') + 1] == str(lock)
    assert (tmp_path / 'march' / 'index.html').exists()


def test_a_day_with_no_march_page_is_neither_built_nor_a_failure(tmp_path):
    res, lock = build.build_march(tmp_path, Runner('none'), date(2027, 6, 1))
    assert not res.built and not res.error and lock is None


def test_a_failed_march_build_is_reported_and_leaves_no_page(tmp_path):
    res, lock = build.build_march(tmp_path, Runner('fail'), date(2027, 3, 20))
    assert not res.built and 'exited 1' in res.error and lock is None
    assert not (tmp_path / 'march').exists()


def test_the_home_page_hears_of_the_lock_only_when_the_march_page_was_built(tmp_path):
    run = Runner()
    build.build_home(tmp_path, run, (), build.MARCH_LOCKS / 'lock_2027.json')
    assert run.calls[-1][-2:] == ['--march', str(build.MARCH_LOCKS / 'lock_2027.json')]
    run = Runner()
    build.build_home(tmp_path, run, ())
    assert '--march' not in run.calls[-1]


def test_the_build_reports_the_march_page_only_when_it_was_built_or_failed(tmp_path, monkeypatch):
    monkeypatch.setattr(build, 'build_sport', lambda s, out, *a, **k: build.SportResult(s, built=True))
    monkeypatch.setattr(build, 'assemble_shared', lambda out: None)
    for name in ('add_strip', 'add_search'):
        monkeypatch.setattr(build, name, lambda out, results: [])
    for name in ('add_sheet', 'add_scores', 'add_share', 'add_expand', 'add_csp', 'add_offline'):
        monkeypatch.setattr(build, name, lambda out: [])
    for march, want in (('page', ['march']), ('none', []), ('fail', ['march'])):
        results = build.build_site(tmp_path / march, None, runner=Runner(march))
        assert [r.sport for r in results if r.sport == 'march'] == want


def test_the_home_card_s_facts_come_from_the_lock(tmp_path, monkeypatch):
    d = json.loads((ROOT / 'data' / 'ncaam' / 'bracket' / 'dryrun_2025.json').read_text(encoding='utf-8'))
    p = bracket.pair_forecast(d['ratings'], d['curve'])
    d['pairs'] = {f'{a}|{b}': p(a, b) for a, b in combinations(sorted(d['ratings']), 2)}
    lock = tmp_path / 'lock_2025.json'
    lock.write_text(json.dumps(d), encoding='utf-8')
    monkeypatch.setattr(bracket, 'graded', lambda doc: d['graded'][:5])
    f = home.march_facts(lock)
    champ = [g for g in d['filled'] if g['round'] == 'final'][0]['winner']
    assert f['built'] and f['tournament'] == 2025 and f['champion'] == d['names'][champ]
    assert f['games'] == 67 and f['played'] == 5
    assert f['right'] == sum(1 for g in d['graded'][:5] if g['favourite_won'])


def test_the_home_page_draws_the_march_card_only_when_handed_one():
    js = (ROOT / 'src' / 'site' / 'home' / 'home.js').read_text(encoding='utf-8')
    assert "function marchCard(m){\n  if(!m || !m.built) return '';" in js
    assert '+ marchCard(HOME.march);' in js
