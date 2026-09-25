"""
src/weekly_summary.py and the summary and alert steps of the Weekly update
workflow.

The summary is built from synthetic changed-file lists, logs and result
rows, so it runs without a real weekly run or git state.

Run with: pytest tests/test_weekly_summary.py -v
"""
import re
import sys
from pathlib import Path

REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO / 'src'))

import weekly_summary as ws  # noqa: E402

WEEKLY = REPO / '.github' / 'workflows' / 'weekly-update.yml'


def game(result, a=1, b=1, m=0):
    if result is None:
        return {'actual_home_win': None, 'model_a_correct': None,
                'model_b_correct': None, 'market_correct': None}
    return {'actual_home_win': result, 'model_a_correct': a,
            'model_b_correct': b, 'market_correct': m}


FILES = {
    'predictions/2026_week4.json': [{}] * 16,
    'results/2026_week3_graded.json': [game(1), game(0, a=0), game(1, b=0)] + [game(None)] * 13,
}

LOG = """Checking data quality...
  data quality WARNING: 2026 week 3 is complete in the schedule but has no play-by-play yet.
WARNING: NYJ@NE has already kicked off and gets NO pick.
Saved 16 predictions to predictions/2026_week4.json
"""

DRIFT = "Model A:\n  No significant drift detected.\n\n=== DRIFT CHECK: OK ===\n"


def summary(changed=tuple(FILES), log=LOG, drift=DRIFT):
    return ws.summarise(2026, list(changed), log, drift, lambda p: FILES[p])


def test_a_locked_week_is_named_with_its_game_count():
    assert '- Locked 2026 week 4: 16 games' in summary()


def test_no_new_predictions_file_means_nothing_locked():
    assert '- No week was locked on this run' in summary(changed=['results/2026_week3_graded.json'])


def test_grading_counts_only_games_with_a_result():
    """An ungraded game is null, not wrong. Counting it would put 'Model A
    2/16' on a week where 3 games have been played."""
    text = summary()
    assert '3 of 16 games graded. Model A 2/3, Model B 2/3, Market 0/3' in text


def test_a_week_with_nothing_graded_says_so():
    line = ws.graded_line(2026, 5, [game(None)] * 16)
    assert line == '- 2026 week 5: none of 16 games graded yet'


def test_data_quality_findings_and_run_warnings_are_listed():
    text = summary()
    assert '- WARNING: 2026 week 3 is complete in the schedule' in text
    assert '- WARNING: NYJ@NE has already kicked off and gets NO pick.' in text


def test_a_clean_check_says_no_findings():
    assert '**Data quality**\n- No findings' in summary(log='  data quality: no findings\n')


def test_a_check_that_never_ran_is_not_reported_as_clean():
    """A run that stopped before the checks must not read 'No findings'."""
    text = summary(log='Traceback (most recent call last):\n')
    assert 'The checks did not run' in text and 'No findings' not in text


def test_the_drift_verdict_is_carried_over():
    assert '- DRIFT CHECK: OK' in summary()
    assert '- The drift check did not run' in summary(drift='')


def test_changed_paths_reads_git_status_and_normalises_slashes():
    class Done:
        stdout = '?? predictions/2026_week4.json\n M results\\2026_week3_graded.json\n'

    got = ws.changed_paths(run=lambda *a, **k: Done())
    assert got == ['predictions/2026_week4.json', 'results/2026_week3_graded.json']


def test_the_bare_command_runs_without_a_log_or_a_drift_report(capsys):
    """--log and --drift are optional. The first version crashed on
    Path(None) when either was left off; Booth found it on #105 by running
    the command exactly as the PR body quoted it."""
    assert ws.main(['--season', '2026'], changed=[]) == 0
    out = capsys.readouterr().out
    assert '- No week was locked on this run' in out
    assert 'The checks did not run' in out and 'The drift check did not run' in out


# --- the workflow ------------------------------------------------------------

def _text():
    return WEEKLY.read_text(encoding='utf-8')


def _step(name):
    text = _text()
    start = text.index(f'- name: {name}')
    nxt = text.find('\n      - name:', start + 1)
    return text[start:nxt if nxt != -1 else None]


def test_the_lock_step_keeps_its_exit_code_through_tee():
    """Without an explicit bash shell there is no pipefail, and `| tee`
    would turn the deliberate failure of an unlocked week into a success."""
    step = _step("Generate/lock in this week's predictions")
    assert '| tee weekly-update.log' in step
    assert re.search(r'^\s+shell:\s*bash\s*$', step, re.M)


def test_the_summary_runs_before_the_commit_and_survives_a_failed_lock():
    text = _text()
    assert text.index('- name: Summarise the run') < text.index('- name: Commit and push changes')
    step = _step('Summarise the run')
    assert re.search(r"if:\s*\$\{\{\s*!cancelled\(\)\s*\}\}", step)
    assert '>> "$GITHUB_STEP_SUMMARY"' in step and '--out weekly-summary.md' in step


def test_a_failed_run_raises_the_alert_last():
    text = _text()
    step = _step('Raise an alert')
    assert text.index('- name: Raise an alert') > text.index('- name: Commit and push changes')
    assert re.search(r'if:\s*failure\(\)', step)
    assert '--title "Weekly update failed"' in step and 'weekly-summary.md' in step
