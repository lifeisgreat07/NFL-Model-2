"""A slice of the mutation corpus runs every night (Stage 27 item 2).

The runner picks the slice from a seed (`--sample N --seed S`), the nightly
workflow passes the UTC date as the seed and appends the counts to the run
summary (`--summary`). These tests hold the choice to being reproducible and
the workflow to running it.

Run with: pytest tests/test_nightly_mutation.py -v
"""
import random
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tests' / 'mutation'))
import runner

WORKFLOW = ROOT / '.github' / 'workflows' / 'nightly-mutation.yml'
CASES = [{'id': f'case-{i:03d}'} for i in range(200)]


def ids(cases):
    return [c['id'] for c in cases]


def test_the_same_seed_picks_the_same_slice():
    assert ids(runner.sample_cases(CASES, 30, 20260929)) == ids(runner.sample_cases(CASES, 30, 20260929))


def test_the_slice_does_not_depend_on_the_order_the_files_loaded_in():
    shuffled = CASES[:]
    random.Random(1).shuffle(shuffled)
    assert set(ids(runner.sample_cases(shuffled, 30, 20260929))) == set(ids(runner.sample_cases(CASES, 30, 20260929)))


def test_another_night_picks_another_slice():
    assert set(ids(runner.sample_cases(CASES, 30, 20260929))) != set(ids(runner.sample_cases(CASES, 30, 20260930)))


def test_the_slice_is_the_size_asked_with_no_repeats():
    got = ids(runner.sample_cases(CASES, 30, 7))
    assert len(got) == 30 == len(set(got))
    assert len(runner.sample_cases(CASES[:5], 30, 7)) == 5


def test_a_sample_without_a_seed_is_refused():
    with pytest.raises(SystemExit):
        runner.main(['--sample', '3'])


def test_the_summary_counts_every_status():
    results = [({'id': 'a'}, {'status': runner.CAUGHT}),
               ({'id': 'b'}, {'status': runner.CAUGHT}),
               ({'id': 'c'}, {'status': runner.SURVIVED})]
    md = runner.summary_markdown(results, '--sample 3 --seed 1')
    assert '| CAUGHT | 2 |' in md and '| SURVIVED | 1 |' in md and '| WRONG-GUARD | 0 |' in md
    assert '`c`: SURVIVED' in md
    assert '--seed 1' in md


def test_the_workflow_runs_nightly_with_the_date_as_the_seed():
    wf = WORKFLOW.read_text(encoding='utf-8')
    assert re.search(r"schedule:\s*\n\s*- cron: '\d+ \d+ \* \* \*'", wf), 'no nightly schedule'
    assert 'seed="$(date -u +%Y%m%d)"' in wf
    assert re.search(r'runner\.py --sample \d+ --rotate --seed "\$seed" --summary "\$GITHUB_STEP_SUMMARY"', wf)


def test_the_workflow_cannot_write_to_the_repository():
    """It may open an issue (Stage 30 item 7) and nothing else."""
    wf = WORKFLOW.read_text(encoding='utf-8')
    block = re.search(r'\npermissions:\n((?:  .*\n)+)', wf)
    assert block and set(block.group(1).split('\n')) - {''} == {'  contents: read', '  issues: write', '  actions: read'}
    assert 'git push' not in wf and 'auto-commit' not in wf


def test_a_failed_night_opens_its_own_issue():
    """Stage 30 item 7: its own title, so a bad night is not filed under the
    canary's issue, and a replay line with the night's seed."""
    wf = WORKFLOW.read_text(encoding='utf-8')
    assert 'python -m src.core.alerts --title "Nightly mutation slice failing"' in wf
    assert '--sample 30 --rotate --seed %s' in wf, 'the issue does not say how to replay the night'


def test_the_workflow_installs_node_for_the_guards_that_need_it():
    assert 'actions/setup-node@' in WORKFLOW.read_text(encoding='utf-8')


# --- Stage 96 item 50: the rotation through src/core and src/sports ------------------

ROTATING = ([{'id': f'core-{i:03d}', 'target': 'src/core/x.py'} for i in range(60)]
            + [{'id': f'nhl-{i:03d}', 'target': 'src/sports/nhl/y.py'} for i in range(45)]
            + [{'id': f'page-{i:03d}', 'target': 'src/sports/nhl/pages/nhl.js'} for i in range(10)]
            + [{'id': f'wf-{i:03d}', 'target': '.github/workflows/z.yml'} for i in range(10)])


def nights(start, n):
    import datetime
    day = datetime.date(*start)
    return [int((day + datetime.timedelta(days=k)).strftime('%Y%m%d')) for k in range(n)]


@pytest.mark.parametrize('start', [(2026, 11, 20), (2027, 1, 10), (2028, 2, 15)], ids=['nov', 'jan', 'leap-feb'])
def test_every_core_and_sport_python_case_comes_up_in_thirty_nights(start):
    """The guard audit 7 asked for: over 30 nights in a row, from any date,
    across month ends, every Python case under src/core and src/sports runs."""
    seen = set()
    for seed in nights(start, 30):
        seen |= set(ids(runner.rotation_cases(ROTATING, seed)))
    assert seen == {c['id'] for c in ROTATING if c['target'].endswith('.py')}


def test_a_night_runs_about_a_28th_of_them_and_nothing_else():
    for seed in nights((2026, 11, 1), 28):
        got = runner.rotation_cases(ROTATING, seed)
        assert 3 <= len(got) <= 4
        assert all(c['target'].endswith('.py') and c['target'].startswith(('src/core/', 'src/sports/')) for c in got)


def test_the_real_corpus_rotates_every_core_and_sport_case_in_28_nights():
    corpus = runner.load_corpus()
    want = {c['id'] for c in corpus if c['target'].endswith('.py') and c['target'].startswith(('src/core/', 'src/sports/'))}
    seen = set()
    for seed in nights((2026, 11, 5), runner.ROTATION_DAYS):
        seen |= set(ids(runner.rotation_cases(corpus, seed)))
    assert want and seen == want


def test_a_rotation_without_a_seed_is_refused():
    with pytest.raises(SystemExit):
        runner.main(['--rotate', '--list'])
