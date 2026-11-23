"""MLB's Model Lab and Methodology pages (Stage 100 item 2), read from the registration
(experiments/mlb/stage98/registry.json), its tuning, the confirmation once it has run, and the history's coverage.

Before the confirmation (it waits for Retrosheet's 2026 game log) each question is DEFERRED with what it was expected
to show when registered; the tuning's ten best settings are listed with the one kept; a tuned value at an end of
the registered grid is said so. On a phone both pages sit in the More sheet.

Run with: pytest tests/test_mlb_lab_page.py -v
"""
import csv
import json
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from src.sports.mlb import backtest, history, site
from tests.js_source import function_source
from tests.optional import require_tool

ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / 'src' / 'sports' / 'mlb' / 'pages' / 'mlb.js').read_text(encoding='utf-8').replace('\r\n', '\n')
DAY_BOARD = (ROOT / 'src' / 'core' / 'day_board.js').read_text(encoding='utf-8').replace('\r\n', '\n')
ESCAPE = (ROOT / 'src' / 'core' / 'escape.js').read_text(encoding='utf-8').replace('\r\n', '\n') + '\n'
BODY = (ROOT / 'src' / 'sports' / 'mlb' / 'pages' / 'body.html').read_text(encoding='utf-8')


def test_the_questions_are_the_registrations_and_unanswered_until_the_confirmation_runs():
    lab = site.lab()
    reg = backtest.registry()
    assert [q['id'] for q in lab['questions']] == [h['id'] for h in reg['hypotheses']]
    assert lab['confirmation'] == (json.loads((backtest.RESULTS / 'confirmation.json').read_text(encoding='utf-8'))
                                   if (backtest.RESULTS / 'confirmation.json').exists() else None)


def test_the_tuning_lists_the_best_settings_first_and_the_kept_one_is_the_best():
    t = site.lab()['tuning']
    tuning = json.loads((backtest.RESULTS / 'tuning.json').read_text(encoding='utf-8'))
    assert t['searched'] == len(tuning['grid']) and len(t['best']) == min(site.TUNING_SHOWN, len(tuning['grid']))
    assert [g['log_loss'] for g in t['best']] == sorted(g['log_loss'] for g in tuning['grid'])[:len(t['best'])]
    assert {k: t['best'][0][k] for k in ('H_days', 'lambda', 'K_outs')} == t['chosen']


def test_the_coverage_counts_the_history_files_and_the_prices_the_backtest_keeps():
    cov = {r['season']: r for r in site.lab()['coverage']}
    folder = history.HISTORY
    kept = set(backtest.load_market(min(cov), max(cov), folder)['game_id'].astype(str))
    for season, row in cov.items():
        with (folder / f'games_{season}.csv').open(encoding='utf-8', newline='') as f:
            ids = [r['game_id'] for r in csv.DictReader(f)]
        assert (row['games'], row['priced']) == (len(ids), sum(i in kept for i in ids)), season


def test_a_season_not_checked_against_retrosheet_says_not_yet(monkeypatch):
    monkeypatch.setattr(backtest, 'checked_seasons', lambda folder=None: {2010})
    cov = {r['season']: r['checked'] for r in site.coverage()}
    assert cov[2010] is True and cov[2011] is False


def test_the_page_data_carries_the_lab(monkeypatch):
    monkeypatch.setattr(site, 'board', lambda season: {'season': season})
    assert site.payload(datetime(2027, 2, 15, tzinfo=UTC))['lab']['registered'] == backtest.registry()['registered']


def test_both_pages_have_their_buttons_and_sit_in_the_more_sheet():
    for page in ('modellab', 'method'):
        assert BODY.count(f'data-page="{page}"') == 2 and f'id="page-{page}"' in BODY
    sheet = re.search(r'<div id="bnav-more-sheet".*?\n</div>\n', BODY, re.S).group(0)
    in_sheet = re.findall(r'class="bnav-more-item" data-page="([a-z]+)"', sheet)
    overflow = json.loads(re.search(r"const OVERFLOW_PAGES = (\[.*?\]);", JS).group(1).replace("'", '"'))
    assert in_sheet == overflow == ['modellab', 'method']


def run_node(names, body, shared=()):
    node = require_tool('node')
    src = (ESCAPE + ''.join(function_source(DAY_BOARD, n, at_line_start=True) for n in shared)
           + ''.join(function_source(JS, n, at_line_start=True) for n in names) + body)
    r = subprocess.run([node, '-e', src], capture_output=True, encoding='utf-8')
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def test_a_tuned_value_at_an_end_of_the_grid_is_found():
    out = run_node(['gridEdges'], """
const grid = {H_days: [60, 120, 240], lambda: [1, 10, 100], K_outs: [150, 300]};
console.log(JSON.stringify([gridEdges(grid, {H_days: 120, lambda: 10, K_outs: 150}),
  gridEdges(grid, {H_days: 240, lambda: 10, K_outs: 300})]));""")
    assert out == [[{'key': 'K_outs', 'value': 150, 'end': 'smallest'}],
                   [{'key': 'H_days', 'value': 240, 'end': 'largest'}, {'key': 'K_outs', 'value': 300, 'end': 'largest'}]]


def test_an_unanswered_question_is_deferred_and_says_what_was_expected():
    out = run_node(['signed4', 'questionRow'], """
const h = {id: 'H1', kind: 'hypothesis', title: 'A <b>', question: 'Q?', expected: 'ACCEPT'};
const m = {id: 'M1', kind: 'measurement', title: 'T', question: 'Q?', expected: null};
console.log(JSON.stringify([questionRow(h, undefined), questionRow(m, undefined)]));""")
    assert 'DEFERRED' in out[0] and 'Expected when registered: ACCEPT' in out[0] and 'A &lt;b&gt;' in out[0]
    assert 'a measurement' in out[1] and 'DEFERRED' not in out[1]


def test_an_answered_question_shows_its_difference_interval_and_label():
    out = run_node(['signed4', 'questionRow'], """
const h = {id: 'H3', kind: 'hypothesis', title: 'T', question: 'Q?', expected: 'INCONCLUSIVE'};
console.log(JSON.stringify(questionRow(h, {diff: -0.0012, low: -0.003, high: 0.0007, label: 'INCONCLUSIVE'})));""",
                   shared=['plainSigned', 'intervalGlyph'])
    assert '-0.0012' in out and '[-0.0030, +0.0007]' in out and 'INCONCLUSIVE' in out and 'Expected' not in out
