"""Stage 91 items 5 and 6 (audit 7, M5 and R16): the day sports' pick writer.

Item 5: a record that could have seen its own result (fitted through its
slate day, saved at or after the start, or priced from a read at or after the
start) is refused before anything is written. Item 6: a pick is written
through src/core/atomic_write.py (fsync, a unique temporary name), byte for
byte as before.

Run with: pytest tests/test_pick_guard.py -v
"""
import json
from pathlib import Path

import pytest

from src.core import pick_guard

ROOT = Path(__file__).resolve().parents[1]

GOOD = {'game_id': '1', 'slate': '2026-11-04', 'start_utc': '2026-11-05T00:00:00Z', 'saved_utc': '2026-11-04T21:01:00Z',
        'training_through': '2026-11-03', 'market': {'read_utc': '2026-11-04T21:01:00Z'}, 'pick': 'SEA'}


def test_a_clean_record_passes():
    assert pick_guard.problems(GOOD) == []


@pytest.mark.parametrize('change, why', [
    ({'training_through': '2026-11-04'}, 'fitted through 2026-11-04, on or after its slate day'),
    ({'training_through': '2026-11-05'}, 'fitted through 2026-11-05'),
    ({'saved_utc': '2026-11-05T00:00:00Z'}, 'saved at 2026-11-05T00:00:00Z, at or after the start'),
    ({'market': {'read_utc': '2026-11-05T00:10:00Z'}}, 'market read at 2026-11-05T00:10:00Z'),
], ids=['fitted-on-the-day', 'fitted-after', 'saved-at-start', 'priced-after-start'])
def test_a_leaked_record_is_refused(change, why):
    bad = GOOD | change
    assert any(why in p for p in pick_guard.problems(bad))
    with pytest.raises(pick_guard.LeakedPick, match="pick 1 not saved"):
        pick_guard.refuse_leak(bad)


def test_a_missing_field_is_not_checked():
    assert pick_guard.problems({'game_id': '2', 'slate': '2026-11-04', 'market': None}) == []


@pytest.mark.parametrize('sport', ['nhl', 'nba'])
def test_the_writer_refuses_a_leak_and_writes_nothing(sport, tmp_path):
    from importlib import import_module
    daily = import_module(f'src.sports.{sport}.daily')
    with pytest.raises(pick_guard.LeakedPick):
        daily.save_once(GOOD | {'training_through': '2026-11-04'}, tmp_path / 'p')
    assert not (tmp_path / 'p').exists() or not any((tmp_path / 'p').iterdir())


@pytest.mark.parametrize('sport', ['nhl', 'nba'])
def test_the_writer_writes_the_same_bytes_atomically(sport, tmp_path):
    from importlib import import_module
    daily = import_module(f'src.sports.{sport}.daily')
    assert daily.save_once(GOOD, tmp_path) is True
    out = tmp_path / '1.json'
    assert [p.name for p in tmp_path.iterdir()] == ['1.json'], 'no temporary file is left'
    # The old writer's bytes, on this platform (both write text mode, so CRLF on Windows).
    old = tmp_path / 'old' / '1.json'
    old.parent.mkdir()
    old.write_text(json.dumps(GOOD, indent=1) + '\n', encoding='utf-8')
    assert out.read_bytes() == old.read_bytes()
    # save_once is the day sports' shared writer (Stage 87 item 2), taken from src/core.
    from src.core import day_picks
    assert daily.save_once is day_picks.save_once
    src = (ROOT / 'src' / 'core' / 'day_picks.py').read_text(encoding='utf-8')
    body = src[src.index('def save_once('):src.index('def missed(')]
    assert 'write_json_atomic(path, record, trailing_newline=True, indent=1)' in body
    assert "with_suffix('.tmp')" not in body


@pytest.mark.parametrize('sport, registry', [('nhl', 'nhl/stage58'), ('nba', 'nba/stage65')])
def test_every_committed_pick_passes_but_the_disclosed_ones(sport, registry):
    """A postcondition over committed data: the guard refuses exactly the
    same-day fits the live registration discloses, and nothing else."""
    reg = json.loads((ROOT / 'experiments' / registry / 'registry.json').read_text(encoding='utf-8'))
    (dev,) = [a for a in reg['amendments'] if a['entry'] == 'deviation']
    refused = set()
    for p in (ROOT / 'predictions' / sport / '2026').glob('*.json'):
        rec = json.loads(p.read_text(encoding='utf-8'))
        if pick_guard.problems(rec):
            refused.add(str(rec['game_id']))
    assert refused == set(dev['picks'])
