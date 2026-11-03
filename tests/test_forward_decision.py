"""Stage 84 item 3: the forward test's season-end decision rule is registered,
as an amendment disclosed as written after the first figures were read.

Run with: pytest tests/test_forward_decision.py -v
"""
import json
import re
from pathlib import Path

import pytest

from src.core import forward_test as ft

ROOT = Path(__file__).resolve().parents[1]
REGISTRIES = {'nhl': ROOT / 'experiments' / 'nhl' / 'stage58' / 'registry.json',
              'nba': ROOT / 'experiments' / 'nba' / 'stage65' / 'registry.json'}
BACKTESTS = {'nhl': ROOT / 'src' / 'sports' / 'nhl' / 'backtest.py',
             'nba': ROOT / 'src' / 'sports' / 'nba' / 'backtest.py'}


def reg(sport):
    return json.loads(REGISTRIES[sport].read_text(encoding='utf-8'))


@pytest.mark.parametrize('sport', ['nhl', 'nba'])
def test_the_rule_is_the_backtests_rule_at_the_backtests_level(sport):
    d = reg(sport)['forward_test']['decision']
    assert '1 - 0.05/3 (98.33%)' in d['rule'] and abs(ft.LEVEL - (1 - 0.05 / 3)) < 1e-12
    assert ('ACCEPT when the whole interval is below zero' in d['rule']
            and 'REJECT when it is above zero' in d['rule'] and 'INCONCLUSIVE otherwise' in d['rule'])
    # The backtest's label() says the same: below zero ACCEPT, above REJECT.
    src = BACKTESTS[sport].read_text(encoding='utf-8')
    assert "if interval['high'] < 0:\n        return 'ACCEPT'" in src
    assert "if interval['low'] > 0:\n        return 'REJECT'" in src


@pytest.mark.parametrize('sport', ['nhl', 'nba'])
def test_it_decides_once_at_the_seasons_end_on_the_file_the_run_writes(sport):
    d = reg(sport)['forward_test']['decision']
    assert f'results/{sport}/forward_2026.json' in d['when']
    assert 'after the 2026 regular season' in d['when'] and 'No earlier look decides anything' in d['when']
    for name in ('Model A minus the base rate', 'Model B minus Model A', 'Model B minus the market'):
        assert name in d['what'], name
    assert d['implemented_by'] == 'src/core/forward_test.py'
    assert {c[0] for c in ft.COMPARISONS} == {'model_a_minus_base_rate', 'model_b_minus_model_a', 'model_b_minus_market'}


@pytest.mark.parametrize('sport', ['nhl', 'nba'])
def test_the_amendment_discloses_what_was_seen_before_it(sport):
    """Written after the figures were read, and says so with the figures: a
    rule written after the data is only honest if the reader can see that."""
    r = reg(sport)
    (a,) = r['amendments']
    assert a['entry'] == 'forward_test.decision' and a['before_any_result'] is False
    assert a['date'] == '2026-11-03'
    seen = a['seen']
    assert re.search(rf'\d+ graded {sport.upper()} picks through 2026-11-\d\d', seen)
    assert seen.count('[') == 3, 'all three comparisons, with their intervals, as they stood'
    assert 'The rule was written knowing these' in seen


def test_the_registration_dates_are_untouched():
    """An amendment adds; it does not move the date a registration was made."""
    assert reg('nhl')['registered'] == '2026-10-05'
    assert reg('nba')['registered'] == '2026-10-09'
