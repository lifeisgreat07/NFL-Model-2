"""
Stage 89 item 1 (the 2026-11-02 review): README's "Results at a glance" is
tied to the files, every cell.

The backtest rows are read from the registered results. The live rows name a
week or a day, and are recomputed here from the saved picks and final scores
up to it, with the registered forward test's own functions, so they hold
however much later the suite runs: a pick is never rewritten and a final
score never changes. A newer table is written by `python -m src.site.glance
--write`; this test does not ask for the newest, only for a true one.

Run with: pytest tests/test_results_glance.py -v
"""
import json
import re
from pathlib import Path

import pytest

from src.site import glance

ROOT = Path(__file__).resolve().parents[1]
README = (ROOT / 'README.md').read_text(encoding='utf-8')
ROW = re.compile(r'^\| (NFL|NHL|NBA) \| ([^|]+) \| ([^|]+) \| ([^|]+) \| ([^|]+) \|$', re.M)


def table():
    assert README.count(glance.START) == 1 and README.count(glance.END) == 1
    body = README[README.index(glance.START):README.index(glance.END)]
    rows = ROW.findall(body)
    assert [(r[0], r[1].split(',')[0]) for r in rows] == [
        ('NFL', 'Backtest'), ('NFL', 'Live 2026'), ('NHL', 'Backtest'), ('NHL', 'Live 2026-27'),
        ('NBA', 'Backtest'), ('NBA', 'Live 2026-27')]
    return {(r[0], r[1].split(',')[0].split(' ')[0]): r for r in rows}


def cells(row):
    return list(row[2:])


def expected(computed):
    return [glance.cell(computed[k]) for k in ('model_b', 'market', 'base_rate')]


def test_the_section_is_near_the_top_and_says_how_to_read_it():
    assert README.index('## Results at a glance') < README.index('## For recruiters -- project overview')
    assert 'Log loss, lower is better' in README and 'recomputed from the saved picks' in README


def test_the_backtest_rows_are_the_registered_results():
    t = table()
    nfl = glance.nfl_backtest()
    assert t[('NFL', 'Backtest')][1] == nfl['label'] and cells(t[('NFL', 'Backtest')]) == expected(nfl)
    for sport in ('nhl', 'nba'):
        b = glance.day_backtest(sport)
        row = t[(sport.upper(), 'Backtest')]
        assert row[1] == b['label'] and cells(row) == expected(b), sport


def test_the_nfl_live_row_is_its_graded_weeks():
    row = table()[('NFL', 'Live')]
    week = int(re.fullmatch(r'Live 2026, weeks 1-(\d+)', row[1]).group(1))
    assert cells(row) == expected(glance.nfl_live(week))


@pytest.mark.parametrize('sport', ['nhl', 'nba'])
def test_each_day_sports_live_row_is_its_forward_test_on_that_day(sport):
    row = table()[(sport.upper(), 'Live')]
    day = re.fullmatch(r'Live 2026-27, through (\d{4}-\d\d-\d\d)', row[1]).group(1)
    assert cells(row) == expected(glance.day_live(sport, day))


@pytest.mark.parametrize('sport', ['nhl', 'nba'])
def test_the_recomputation_is_the_registered_forward_test(sport):
    """At the forward test's own day, the recomputation gives back the file the
    daily run wrote, every figure, so the README's day is scored the same way."""
    day = glance.forward_through(sport)
    live = glance.day_live(sport, day)
    written = json.loads((ROOT / 'results' / sport / 'forward_2026.json').read_text(encoding='utf-8'))['scores']
    for k in ('model_b', 'market', 'base_rate'):
        assert live[k] == written[k], k


def test_a_cell_is_log_loss_with_its_games():
    assert glance.cell({'log_loss': 0.61234, 'games': 1087}) == '0.6123 (1,087)'
    assert glance.cell(None) == 'not published'
