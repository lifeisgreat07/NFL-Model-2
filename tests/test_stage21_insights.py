"""Stage 21: what the board points out, and the trend beside each rating.

Option A of the rendered "Stage 21 Insight Options" (Claude's pick under
Mark's delegation, for Mark to confirm). Three kinds of insight, each with its
threshold in INSIGHT in the page's script, read here rather than retyped:

- a team that moved RANK_MOVE_MIN or more places names itself in Power
  Ratings' movers line; smaller moves no longer do, and a week with none
  hides the line;
- a game where Model B and the market are MARKET_GAP_MIN points or more
  apart. Model B, because Model A never sees the market: measured with
  Model A, eleven of week 5's fifteen games would be flagged;
- a game both models put within COIN_FLIP_WITHIN points of 50%.

The two game kinds sit in a "Worth a look" box above the Week Board's cards.
Power Ratings gains a sparkline of this season's net rating once
TREND_MIN_WEEKS weeks exist.

The functions run in node, over the real template.

Run with: pytest tests/test_stage21_insights.py -v
"""
import json
import re
import shutil
import subprocess

import pytest

from src.pipeline.template_parts import JOINED_TEMPLATE

NODE = shutil.which('node')
SRC = JOINED_TEMPLATE.read_text(encoding='utf-8').replace('\r\n', '\n')


def function_source(name):
    m = re.search(r'function ' + name + r'\(.*?\n\}\n', SRC, re.S)
    assert m, f'{name} is not findable -- re-anchor this guard'
    return m.group(0)


def insight_consts():
    m = re.search(r'const INSIGHT = (\{[^}]*\});', SRC)
    assert m, 'INSIGHT is not findable'
    return m.group(0), json.loads(re.sub(r'(\w+):', r'"\1":', m.group(1)))


CONST_JS, INSIGHT = insight_consts()


def game(away, home, a, b, mkt, kick='2026-10-11T17:00'):
    return {'away': away, 'home': home, 'fbA_home': a, 'mktB_home': b, 'mkt_home': mkt, 'kick': kick}


def run(js_body):
    if not NODE:
        pytest.skip('node not available')
    js = (CONST_JS + '\n' + function_source('moversSentence') + function_source('boardInsights')
          + function_source('seasonTrend') + function_source('trendSvg')
          + 'function ratingScale(){ return 100; }\n' + function_source('fmtRating')
          + 'function byKickoff(a,b){ return a.kick < b.kick ? -1 : a.kick > b.kick ? 1 : 0; }\n'
          + js_body)
    r = subprocess.run([NODE, '-e', js], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def test_the_thresholds_are_the_ones_the_stage_names():
    assert INSIGHT == {'RANK_MOVE_MIN': 3, 'MARKET_GAP_MIN': 10, 'COIN_FLIP_WITHIN': 5, 'TREND_MIN_WEEKS': 4}


# --- the game insights --------------------------------------------------------

WEEK5 = [  # shaped on the week 5 preview, in percent
    game('NYG', 'WAS', 50.2, 54.4, 63.3, '2026-10-11T17:00'),
    game('SF', 'SEA', 25.8, 49.1, 63.3, '2026-10-11T20:25'),
    game('BUF', 'LA', 49.6, 54.2, 61.2, '2026-10-13T00:15'),
    game('PHI', 'JAX', 56.9, 71.3, 76.5, '2026-10-11T17:00'),   # Model A 20 off, Model B 5: not flagged
    game('CIN', 'MIA', 46.2, 24.1, None, '2026-10-11T17:00'),   # no market: no gap to measure
]


def test_week_5_flags_what_option_a_showed():
    out = run(f'const r = boardInsights({json.dumps(WEEK5)});'
              'process.stdout.write(JSON.stringify(r.map(i => [i.kind, i.g.away + "@" + i.g.home, i.text])));')
    assert out == [
        ['flip', 'NYG@WAS', 'Both models put it between 45% and 55%.'],
        ['market', 'SF@SEA', 'Model B gives SEA 49%, the market 63%.'],
        ['flip', 'BUF@LA', 'Both models put it between 45% and 55%.'],
    ]


def test_the_market_gap_is_measured_with_model_b_not_model_a():
    g = [game('PHI', 'JAX', 56.9, 71.3, 76.5)]
    assert run(f'process.stdout.write(JSON.stringify(boardInsights({json.dumps(g)})));') == []


def test_the_edges_of_each_threshold():
    g = [game('A', 'B', 70, 60, 70.0),     # exactly 10 apart: flagged
         game('C', 'D', 70, 60.1, 70.0),   # 9.9: not
         game('E', 'F', 55, 45, 50.0),     # both exactly 5 from 50: a coin flip
         game('G', 'H', 55.1, 50, 50.0)]   # Model A 5.1 out: not
    out = run(f'process.stdout.write(JSON.stringify(boardInsights({json.dumps(g)}).map(i => i.kind + i.g.home)));')
    assert out == ['marketB', 'flipF']


# --- the movers line ----------------------------------------------------------

def t(name, change):
    return {'name': name, 'rank_change': change}


def test_only_moves_of_three_places_or_more_are_named():
    teams = [t('Kansas City Chiefs', 3), t('Green Bay Packers', -3), t('Dallas Cowboys', 2), t('Buffalo Bills', -2)]
    assert run(f'process.stdout.write(JSON.stringify(moversSentence({json.dumps(teams)})));') == (
        'Biggest moves since the last update: Kansas City Chiefs up 3 places; Green Bay Packers down 3 places.')


def test_a_week_of_small_moves_hides_the_line():
    teams = [t('Kansas City Chiefs', 2), t('Green Bay Packers', -2), t('Dallas Cowboys', 0)]
    assert run(f'process.stdout.write(JSON.stringify(moversSentence({json.dumps(teams)})));') == ''


# --- the trend ----------------------------------------------------------------

def history(labels_nets):
    return {'names': {'LA': 'Los Angeles Rams'},
            'timeline': {'LA': [{'label': lab, 'net': n} for lab, n in labels_nets]}}


def test_the_trend_is_this_seasons_weeks_only():
    h = history([('2024', 0.05), ('2025', 0.09), ('2026 Wk1', 0.118), ('2026 Wk2', 0.136),
                 ('2026 Wk3', 0.127), ('2026 Wk4', 0.135)])
    out = run(f'const teamHistory = {json.dumps(h)};process.stdout.write(JSON.stringify(seasonTrend("LA")));')
    assert out == [0.118, 0.136, 0.127, 0.135]


def test_fewer_weeks_than_the_minimum_draw_no_line():
    h = history([('2025', 0.09), ('2026 Wk1', 0.118), ('2026 Wk2', 0.136), ('2026 Wk3', 0.127)])
    out = run(f'const teamHistory = {json.dumps(h)};'
              'const v = seasonTrend("LA");process.stdout.write(JSON.stringify([v, trendSvg(v)]));')
    assert out[0] == []
    assert '<svg' not in out[1] and 'trend-none' in out[1]


def test_the_line_is_drawn_inside_its_box_and_marks_this_week():
    out = run('process.stdout.write(JSON.stringify(trendSvg([0.118, 0.136, 0.127, 0.135])));')
    pts = [tuple(map(float, p.split(','))) for p in re.search(r'points="([^"]+)"', out).group(1).split()]
    assert len(pts) == 4
    assert all(0 <= x <= 84 and 0 <= y <= 24 for x, y in pts)
    assert min(y for _, y in pts) == pytest.approx(3) and max(y for _, y in pts) == pytest.approx(21)
    cx, cy = (float(v) for v in re.search(r'<circle cx="([\d.]+)" cy="([\d.]+)"', out).groups())
    assert (cx, cy) == pytest.approx(pts[-1])
    assert 'aria-label="Net rating each week this season: ' in out


# --- wiring -------------------------------------------------------------------

def test_the_board_and_the_table_use_them():
    assert 'renderBoardInsights(gamesList);' in function_source('renderGames')
    assert '${trendSvg(seasonTrend(t.team))}' in function_source('renderRatings')
    assert 'id="board-insights" hidden' in SRC and 'id="board-insights-list"' in SRC
    assert 'class="trend-head"' in SRC


def test_the_no_match_row_spans_the_new_column():
    heads = re.search(r'<table id="ratings-table">.*?</thead>', SRC, re.S).group(0).count('<th ')
    assert f'colspan="{heads}"' in function_source('ratingsNoMatchRow')
