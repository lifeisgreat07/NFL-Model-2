"""Tuesday's preview of next week's picks (Mark, 2026-09-29).

Since 2026-09-22 a week locks on Thursday, so for two days after Tuesday's
grading the page had nothing for the coming week. Mark asked for "an update
both on Tuesday and Thursday": a run that HOLDS a week now saves what the
models would pick today to predictions/preview/, and the page shows it,
labelled, until the Thursday lock replaces it.

What must never happen is a preview being taken for a lock: graded, counted
in the season record, used to move determine_next_week on, reported as
"Locked" in the run summary, or shown beside the locked picks for its week.
These tests hold each of those, and the page's label.

Run with: pytest tests/test_tuesday_preview.py -v
"""
import inspect
import json
import re
import shutil
import subprocess
from pathlib import Path

import pandas as pd
import pytest

from src.pipeline.template_parts import JOINED_TEMPLATE

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = JOINED_TEMPLATE

from src.pipeline import generate_dashboard as gd  # noqa: E402
from src.pipeline import weekly_summary as ws  # noqa: E402
from src.pipeline import weekly_update as wu  # noqa: E402


def _main_source():
    """main() and the steps it calls, which follow it in the file (Stage 32
    item 16 split main into load_inputs, fit_models, refresh_current_state,
    plan_week, predict_week and save_week)."""
    src = (Path(__file__).resolve().parents[1] / 'src' / 'pipeline' / 'weekly_update.py').read_text(encoding='utf-8')
    return src[src.index('def main(season'):src.index("if __name__ == '__main__':")]

NODE = shutil.which('node')
NOW = pd.Timestamp('2026-09-29 16:41', tz='UTC')
PICKS = [{'season': 2026, 'week': 4, 'home': 'KC', 'away': 'LV',
          'model_a_home_win_prob': 0.7, 'model_b_home_win_prob': 0.72}]


# --- saving -----------------------------------------------------------------

def test_a_preview_is_saved_marked_and_stamped(tmp_path):
    path = wu.save_preview(PICKS, 2026, 4, NOW, preview_dir=tmp_path)
    assert path == tmp_path / '2026_week4.json'
    rows = json.loads(path.read_text(encoding='utf-8'))
    assert rows[0]['preview'] is True, (
        "a preview pick does not say it is one; anything reading the file on "
        "its own could take it for a locked pick")
    assert rows[0]['previewed_utc'] == '2026-09-29T16:41:00+00:00'
    assert 'preview' not in PICKS[0], "save_preview changed the caller's picks"


def test_a_later_holding_run_replaces_the_preview(tmp_path):
    """A lock is write-once; a preview is only as good as its latest run."""
    wu.save_preview(PICKS, 2026, 4, NOW, preview_dir=tmp_path)
    later = [dict(PICKS[0], model_a_home_win_prob=0.55)]
    wu.save_preview(later, 2026, 4, NOW + pd.Timedelta(days=1), preview_dir=tmp_path)
    rows = json.loads((tmp_path / '2026_week4.json').read_text(encoding='utf-8'))
    assert rows[0]['model_a_home_win_prob'] == 0.55
    assert rows[0]['previewed_utc'].startswith('2026-09-30')


def test_an_empty_preview_saves_nothing_and_does_not_fail(tmp_path):
    assert wu.save_preview([], 2026, 4, NOW, preview_dir=tmp_path) is None
    assert not list(tmp_path.iterdir())


def test_previews_live_below_the_folder_every_reader_globs():
    assert wu.PREVIEW_DIR == wu.PRED_DIR / 'preview'


def test_a_preview_does_not_move_the_next_week_on(tmp_path):
    """determine_next_week counts saved and skipped weeks. A preview counted
    as saved would make Thursday lock week 5 and leave week 4 unlocked."""
    pred = tmp_path / 'predictions'
    (pred / 'preview').mkdir(parents=True)
    (pred / '2026_week3.json').write_text('[]', encoding='utf-8')
    (pred / 'preview' / '2026_week4.json').write_text('[]', encoding='utf-8')
    assert wu.determine_next_week(2026, pred_dir=pred,
                                  skipped_dir=pred / 'skipped') == 4


# --- the run: holding saves a preview, locking never does --------------------

def main_source():
    return _main_source()


def test_a_holding_run_saves_a_preview_instead_of_returning_early():
    src = main_source()
    assert re.search(r'preview = not decision\.lock', src), (
        "main() no longer derives the preview from the lock decision")
    assert 'Nothing saved.' not in src, (
        "the holding branch returns before any pick is built again, so "
        "Tuesday saves nothing and the page has no coming week until Thursday")
    i_prev = src.find('save_preview(predictions')
    i_lock = src.find("out_path = PRED_DIR / f'{season}_week{week}.json'")
    assert -1 < i_prev < i_lock, (
        "the preview save must come before the locked save and return, so "
        "a holding run can never reach the write-once file")
    between = src[i_prev:i_lock]
    assert re.search(r'\n\s+return\n', between), (
        "a holding run falls through from its preview into the locked save")


def test_the_starter_warning_still_fires_only_at_lock_time():
    """#186 moved it to lock time because it fired falsely on every Tuesday
    hold. The hold no longer returns early, so it must now be skipped by
    name."""
    assert re.search(r'None if preview else starter_warning\(', main_source())


# --- the run summary -----------------------------------------------------------

def test_the_summary_says_previewed_not_locked():
    text = ws.summarise(2026, ['predictions/preview/2026_week4.json'], '', '',
                        lambda p: PICKS)
    assert '- No week was locked on this run' in text
    assert '- Previewed 2026 week 4: 1 games' in text
    assert 'Locked 2026 week 4' not in text


# --- the page ------------------------------------------------------------------

def test_the_page_ignores_a_preview_once_its_week_is_locked(tmp_path):
    (tmp_path / '2026_week3.json').write_text(json.dumps(PICKS), encoding='utf-8')
    (tmp_path / '2026_week4.json').write_text(json.dumps(PICKS), encoding='utf-8')
    got = gd.load_previews(preview_dir=tmp_path, locked={(2026, 3)})
    assert set(got) == {(2026, 4)}, (
        "a preview was loaded for a week that is already locked; the page "
        "could show Tuesday's picks in place of, or beside, the real ones")


def test_the_build_marks_a_preview_week_and_leaves_it_ungraded():
    src = inspect.getsource(gd.main)
    assert re.search(r"load_previews\(locked=set\(all_preds\) \| skipped_weeks\(\)\)", src)
    assert re.search(r"'preview': True,", src)
    assert re.search(r"build_games_js\(preds, \{\}\)", src), (
        "a preview week is built with a graded lookup; it must never be graded")


def function_source(src, name):
    m = re.search(r'function ' + name + r'\(.*?\n\}\n', src, re.S)
    assert m, f'{name} is not findable -- re-anchor this guard'
    return m.group(0)


@pytest.fixture(scope='module')
def labels():
    if not NODE:
        pytest.skip('node not available')
    t = TEMPLATE.read_text(encoding='utf-8')
    js = ('const weeks = {"2026_week3": {season: 2026, week: 3},'
          ' "2026_week4": {season: 2026, week: 4, preview: true}};'
          + function_source(t, 'weekLabel') + function_source(t, 'previewWhen')
          + 'process.stdout.write(JSON.stringify({locked: weekLabel("2026_week3"),'
            ' preview: weekLabel("2026_week4"),'
            ' when: previewWhen("2026-09-29T16:41:00+00:00"),'
            ' missing: previewWhen(null)}));')
    r = subprocess.run([NODE, '-e', js], capture_output=True, encoding='utf-8')
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def test_a_preview_week_is_labelled_in_the_week_stepper(labels):
    assert labels['locked'] == '2026 · Week 3'
    assert labels['preview'] == '2026 · Week 4 (preview)'


def test_the_preview_note_says_when(labels):
    assert labels['when'] == 'Tue Sep 29, 16:41 UTC'
    assert labels['missing'] == 'the last run'


def test_the_board_shows_the_preview_note_only_for_a_preview_week():
    t = TEMPLATE.read_text(encoding='utf-8')
    assert re.search(r'<p class="board-note board-preview-note" id="board-preview-note" role="note" hidden>', t)
    body = function_source(t, 'renderGames')
    assert re.search(r'previewNote\.hidden = !isPreview;', body)
    # The note's wording is executed in tests/test_preview_after_kickoff.py.
    assert 'previewNoteText(weekData, Date.now())' in body
