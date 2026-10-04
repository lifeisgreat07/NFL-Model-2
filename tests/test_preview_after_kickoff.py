"""
A preview does not outlive its week.

Stage 30 item 3, from the 2026-09-29 re-audit. A Tuesday run that holds a
week saves predictions/preview/<season>_week<N>.json. Three ways it could
outlive the week, each closed here:

  1. Nothing deleted it when Thursday locked the week. The page ignored it,
     but the file stayed in predictions/ for good. weekly_update now deletes
     it the moment the lock is written (run end to end on the synthetic
     league from tests/synthetic_league.py).
  2. A week recorded as SKIPPED (every game kicked off with nothing locked)
     still showed its preview as if it were coming. generate_dashboard now
     leaves out a skipped week's preview, as it does a locked week's.
  3. A preview still showing after the week's first kickoff promised that
     "the picks lock before the week's first kickoff". The note now says the
     lock run did not happen (previewNoteText, run in node).

Run with: pytest tests/test_preview_after_kickoff.py -v
"""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

from src.pipeline.template_parts import JOINED_TEMPLATE

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = JOINED_TEMPLATE
sys.path.insert(0, str(Path(__file__).parent))

import synthetic_league as league

from src.pipeline import generate_dashboard as gd
from src.pipeline import weekly_update as wu

NODE = shutil.which('node')
H = pd.Timedelta(hours=1)


# --- 1. the lock deletes the preview ------------------------------------------

@pytest.fixture
def run(monkeypatch, tmp_path, capsys):
    for name, path in (('PRED_DIR', tmp_path / 'predictions'),
                       ('SKIPPED_DIR', tmp_path / 'predictions' / 'skipped'),
                       ('PREVIEW_DIR', tmp_path / 'predictions' / 'preview'),
                       ('DATA_DIR', tmp_path / 'data'),
                       ('LINE_HISTORY_DIR', tmp_path / 'data' / 'line_history'),
                       ('QB_OVERRIDE_DIR', tmp_path / 'data' / 'qb_overrides')):
        path.mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr(wu, name, path)
    real = wu.simulate_season
    monkeypatch.setattr(wu, 'simulate_season', lambda *a, n_sim=10000, **k: real(*a, n_sim=200, **k))

    def go(offsets):
        pbp, schedules = league.build(pd.Timestamp.now(tz='UTC'), offsets)
        monkeypatch.setattr(wu, 'load_plays', lambda seasons: pbp[pbp['season'].isin(seasons)])
        monkeypatch.setattr(wu, 'load_schedule',
                            lambda season: schedules.get(season, league.empty_schedule()))
        wu.main(league.TARGET, league.TARGET_WEEK)
        return capsys.readouterr().out
    return go


def test_locking_a_week_deletes_its_preview(run, tmp_path):
    name = f'{league.TARGET}_week{league.TARGET_WEEK}.json'
    six_days = pd.Timedelta(days=6)
    run([six_days, six_days + H, six_days + 2 * H, six_days + 3 * H])
    assert (tmp_path / 'predictions' / 'preview' / name).exists(), 'the holding run saved no preview'
    out = run([H, 2 * H, 3 * H, 4 * H])
    assert (tmp_path / 'predictions' / name).exists(), out
    assert not (tmp_path / 'predictions' / 'preview' / name).exists(), (
        'the lock was written and the preview was left beside it')
    assert f'Removed predictions/preview/{name}' in out


# --- 2. a skipped week's preview is not shown ---------------------------------

def test_a_skipped_weeks_preview_is_not_shown(tmp_path):
    preview, skipped = tmp_path / 'preview', tmp_path / 'skipped'
    preview.mkdir()
    skipped.mkdir()
    for w in (4, 5):
        (preview / f'2026_week{w}.json').write_text(json.dumps([{'home': 'GB'}]), encoding='utf-8')
    (skipped / '2026_week4.json').write_text('{}', encoding='utf-8')
    assert gd.skipped_weeks(skipped) == {(2026, 4)}
    shown = gd.load_previews(preview, locked=gd.skipped_weeks(skipped))
    assert set(shown) == {(2026, 5)}


def test_the_build_leaves_out_skipped_weeks_previews():
    """Wiring: main() has to pass the skipped weeks with the locked ones."""
    src = (ROOT / 'src' / 'pipeline' / 'generate_dashboard.py').read_text(encoding='utf-8')
    assert 'load_previews(locked=set(all_preds) | skipped_weeks())' in src


# --- 3. the note after kickoff ------------------------------------------------

def function_source(src, name):
    m = re.search(r'function ' + name + r'\(.*?\n\}\n', src, re.S)
    assert m, f'{name} is not findable -- re-anchor this guard'
    return m.group(0)


def note(week, now_iso):
    if not NODE:
        pytest.skip('node not available')
    t = TEMPLATE.read_text(encoding='utf-8')
    js = ''.join(function_source(t, f) for f in
                 ('easternOffsetHours', 'kickoffInstant', 'previewWhen', 'previewNoteText'))
    js += (f'\nprocess.stdout.write(JSON.stringify(previewNoteText({json.dumps(week)}, '
           f'Date.parse({json.dumps(now_iso)}))));')
    r = subprocess.run([NODE, '-e', js], capture_output=True, encoding='utf-8')
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


WEEK = {'preview': True, 'previewed_utc': '2026-09-29T16:41:00+00:00',
        'games': [{'gameday': '2026-10-01', 'gametime_et': '20:15'},   # Thu 00:15 UTC Fri
                  {'gameday': '2026-10-04', 'gametime_et': '13:00'}]}


def test_before_the_first_kickoff_the_preview_says_it_will_lock():
    text = note(WEEK, '2026-10-01T12:00:00Z')
    assert text.startswith("Preview: these are the models' picks as of Tue Sep 29, 16:41 UTC.")
    assert 'The picks lock before the week' in text and 'only locked picks are graded' in text


def test_after_the_first_kickoff_the_preview_says_the_lock_did_not_happen():
    """Thursday 20:15 Eastern is 00:15 UTC Friday (EDT, UTC-4)."""
    assert 'lock before' in note(WEEK, '2026-10-02T00:14:00Z')
    text = note(WEEK, '2026-10-02T00:16:00Z')
    assert 'the lock run did not happen' in text
    assert 'lock before' not in text


def test_a_week_that_is_not_a_preview_has_no_note():
    assert note({'preview': False, 'games': []}, '2026-10-01T00:00:00Z') == ''


def test_a_preview_with_no_known_kickoff_keeps_the_promise():
    """No kickoff time means nothing is known to have started."""
    assert 'lock before' in note({'preview': True, 'games': [{}]}, '2030-01-01T00:00:00Z')
