"""Stage 85 item 4: the live models are fitted on games strictly before the
pick's slate day, and the picks that were not are disclosed.

Until 2026-11-03 each daily run fitted Model A and Model B once, on every
final game it knew, and used that fit for today's and tomorrow's picks. A
run after the day's first games had finished fitted on them before picking
the same day's later games. experiments/nba/stage65/registry.json says "to
the day before", and the backtests' walk-forward fits on earlier days only.
Each pick records the last day its models saw (`training_through`), so the
files show which picks it touched; both registrations list them.

Run with: pytest tests/test_fit_before_the_day.py -v
"""
import json
from pathlib import Path

import pandas as pd
import pytest

from src.sports.nba import daily as nba_daily
from src.sports.nhl import daily as nhl_daily

ROOT = Path(__file__).resolve().parents[1]
REGISTRIES = {'nba': ROOT / 'experiments' / 'nba' / 'stage65' / 'registry.json',
              'nhl': ROOT / 'experiments' / 'nhl' / 'stage58' / 'registry.json'}


def table():
    days = pd.to_datetime(['2026-10-29', '2026-10-30', '2026-10-31', '2026-10-31', '2026-11-01'])
    return pd.DataFrame({'game_id': list('abcde'), 'day': days, 'home_prob': [0.5] * 5, 'home_win': [1, 0, 1, 0, 1]})


@pytest.mark.parametrize('sport', ['nba', 'nhl'])
def test_the_fit_sees_only_games_before_the_slate_day(sport, monkeypatch):
    seen = []
    if sport == 'nba':
        monkeypatch.setattr(nba_daily, 'fit_models', lambda t: seen.append(t) or {})
        _, trained = nba_daily.fit_before(table(), pd.Timestamp('2026-10-31'), 2015)
    else:
        monkeypatch.setattr(nhl_daily, 'fit_models', lambda t, k: seen.append(t) or (None, None))
        _, _, trained = nhl_daily.fit_before(table(), pd.Timestamp('2026-10-31'), 1.0, 2015)
    (fit_on,) = seen
    assert list(fit_on['game_id']) == ['a', 'b'], 'the two games of the slate day itself are not fitted on'
    assert trained['training_through'] == '2026-10-30'
    assert trained['data_provenance']['training_games'] == 2


@pytest.mark.parametrize('sport', ['nba', 'nhl'])
def test_the_run_fits_once_per_slate_day_and_never_on_the_whole_table(sport):
    src = (ROOT / 'src' / 'sports' / sport / 'daily.py').read_text(encoding='utf-8')
    main = src[src.index('def main('):]
    assert 'fit_before(table, day,' in main and 'if day not in fitted:' in main
    assert 'fit_models(table' not in main and 'training(table, first)' not in main


def saved(sport):
    return [json.loads(p.read_text(encoding='utf-8')) for p in sorted((ROOT / 'predictions' / sport / '2026').glob('*.json'))]


def disclosed(sport):
    reg = json.loads(REGISTRIES[sport].read_text(encoding='utf-8'))
    (dev,) = [a for a in reg['amendments'] if a['entry'] == 'deviation']
    return dev


@pytest.mark.parametrize('sport', ['nba', 'nhl'])
def test_every_saved_pick_was_fitted_before_its_day_or_is_disclosed(sport):
    """A postcondition over the committed picks: the list in the registration
    is exactly the picks whose models saw their own slate day, so a new one
    fails here rather than going unnoticed."""
    leaked = sorted(p['game_id'] for p in saved(sport)
                    if p.get('training_through') and p['training_through'] >= p['slate'])
    assert leaked == disclosed(sport)['picks']


@pytest.mark.parametrize('sport', ['nba', 'nhl'])
def test_the_disclosure_is_dated_and_changes_no_rule(sport):
    dev = disclosed(sport)
    assert dev['date'] == '2026-11-03' and dev['before_any_result'] is False
    assert dev['change'].startswith('No rule changes.') and 'never rewritten' in dev['change']
    assert f"{len(dev['picks'])} of " in dev['seen']
