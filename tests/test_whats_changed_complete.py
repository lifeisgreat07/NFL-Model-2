"""Each sport's What's Changed page names every amendment to its forward test (audit 9, finding D17).

The NHL's page said "Every change to how the NHL's picks are made" and stopped at 2026-10-06, while its
registration had been amended on 2026-11-03, 11-04, 11-05 and 11-11; the NBA's page left out three of its
amendments. Each entry in `src/sports/<sport>/pages/changes.json` now lists the amendments it covers, as
"<date> <entry>", and these tests hold the lists to the registration both ways.

Run with: pytest tests/test_whats_changed_complete.py -v
"""
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
#: Each sport's forward-test registration, and the backtest registration it rests on.
REGISTRIES = {'nhl': ['experiments/nhl/stage58/registry.json', 'experiments/nhl/stage56/registry.json'],
              'nba': ['experiments/nba/stage65/registry.json', 'experiments/nba/stage61/registry.json'],
              # MLB's forward test is registered with Stage 101; until then its page covers the backtest's.
              'mlb': ['experiments/mlb/stage98/registry.json']}


def changes(sport):
    return json.loads((ROOT / 'src' / 'sports' / sport / 'pages' / 'changes.json').read_text(encoding='utf-8'))


def amendments(sport):
    out = set()
    for path in REGISTRIES[sport]:
        reg = json.loads((ROOT / path).read_text(encoding='utf-8'))
        out |= {f"{a['date']} {a['entry']}" for a in reg.get('amendments', [])}
    return out


@pytest.mark.parametrize('sport', sorted(REGISTRIES))
def test_every_amendment_is_on_the_page_and_the_page_names_no_other(sport):
    named = [a for c in changes(sport) for a in c['amendments']]
    assert len(named) == len(set(named)), 'an amendment named by two entries'
    assert set(named) == amendments(sport), {'missing': sorted(amendments(sport) - set(named)),
                                             'unknown': sorted(set(named) - amendments(sport))}


@pytest.mark.parametrize('sport', sorted(REGISTRIES))
def test_an_entry_is_dated_on_the_day_of_the_amendments_it_names(sport):
    for c in changes(sport):
        assert all(a.split(' ')[0] == c['date'] for a in c['amendments']), c['title']


@pytest.mark.parametrize('sport', sorted(REGISTRIES))
def test_every_entry_says_which_amendments_it_covers(sport):
    assert all(isinstance(c.get('amendments'), list) for c in changes(sport))
    assert any(c['amendments'] for c in changes(sport)), 'a vacuous pass: no entry names an amendment'
