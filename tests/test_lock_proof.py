"""Proof of lock (Stage 46 item 5, src/pipeline/lock_proof.py and the Week
Board's lock line).

Held here: every commit that changed a locked week's picks, oldest first,
following renames; previews are not locked weeks; a shallow clone is refused
rather than read (its oldest commit looks as if it added every file); a
failure never fails the build; the page names the last change before the
first kickoff and every change after it; and the wiring from the site build
through the page.

Run with: pytest tests/test_lock_proof.py -v
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from src.pipeline import generate_dashboard as gd
from src.pipeline import lock_proof as lp
from src.pipeline.template_parts import JOINED_TEMPLATE
from src.site import build

ROOT = Path(__file__).resolve().parents[1]
NODE = shutil.which('node')


class FakeGit:
    def __init__(self, logs, shallow='false'):
        self.logs, self.shallow, self.calls = logs, shallow, []

    def __call__(self, args, cwd):
        self.calls.append(args)
        if args[:2] == ['rev-parse', '--is-shallow-repository']:
            return self.shallow + '\n'
        return self.logs.get(args[-1], '')


def week_dir(tmp_path):
    pred = tmp_path / 'predictions'
    (pred / 'preview').mkdir(parents=True)
    for name in ('2026_week4.json', '2026_week5.json', 'preview/2026_week6.json'):
        (pred / name).write_text('[]', encoding='utf-8')
    return pred


LOG4 = ('c80cb28aaaaaaa\t2026-10-01T17:20:56+00:00\tWeekly update: predictions and grading\n'
        '2450baabbbbbbb\t2026-09-29T14:59:32-04:00\tWeekly update: predictions and grading\n')


def test_every_commit_oldest_first_in_utc_and_previews_left_out(tmp_path):
    pred = week_dir(tmp_path)
    git = FakeGit({'predictions/2026_week4.json': LOG4})
    out = lp.proof(pred, tmp_path, 'o/r', git)
    assert list(out) == ['2026_week4'], 'a week git cannot place is left out; a preview is never asked about'
    assert [c['short'] for c in out['2026_week4']] == ['2450baa', 'c80cb28']
    assert out['2026_week4'][0]['committed_utc'] == '2026-09-29T18:59:32Z'
    assert out['2026_week4'][1]['url'] == 'https://github.com/o/r/commit/c80cb28aaaaaaa'
    asked = [c[-1] for c in git.calls if c[0] == 'log']
    assert asked == ['predictions/2026_week4.json', 'predictions/2026_week5.json']


def test_history_follows_renames():
    """Stage 52 moves the NFL's folders; without --follow the move would be
    the oldest commit, and the page would date the lock to the move."""
    src = Path(lp.__file__).read_text(encoding='utf-8')
    assert "['log', '--follow'," in src


def test_a_shallow_clone_is_refused_and_writes_nothing(tmp_path, capsys):
    git = FakeGit({}, shallow='true')
    with pytest.raises(lp.ShallowClone):
        lp.proof(week_dir(tmp_path), tmp_path, 'o/r', git)
    out = tmp_path / 'lock_proof.json'
    assert lp.main(['--out', str(out)], git=git) == 0
    assert not out.exists() and 'no lock line' in capsys.readouterr().out


def test_the_real_history_dates_week_4_before_its_kickoff():
    """Against this repository's own history: week 4's picks file was first
    committed before week 4's Thursday game."""
    try:
        if subprocess.run(['git', 'rev-parse', '--is-shallow-repository'], cwd=ROOT, capture_output=True,
                          text=True).stdout.strip() == 'true':
            pytest.skip('shallow clone: no history to read')
    except FileNotFoundError:
        pytest.skip('git not available')
    weeks = lp.proof()
    assert '2026_week4' in weeks
    assert weeks['2026_week4'][0]['committed_utc'] < '2026-10-02T00:15:00Z'


# --- the page -----------------------------------------------------------------

def function_source(src, name):
    m = re.search(r'function ' + name + r'\(.*?\n\}\n', src, re.S)
    assert m, f'{name} is not findable -- re-anchor this guard'
    return m.group(0)


def page_line(commits, games):
    if not NODE:
        pytest.skip('node not available')
    src = JOINED_TEMPLATE.read_text(encoding='utf-8').replace('\r\n', '\n')
    js = ''.join(function_source(src, n) for n in ('easternOffsetHours', 'kickoffInstant', 'escapeHtml',
                                                   'lockUtc', 'lockCommitLink', 'lockProofHtml'))
    js += f'process.stdout.write(JSON.stringify(lockProofHtml({json.dumps(commits)}, {json.dumps(games)})));'
    r = subprocess.run([NODE, '-e', js], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def commit(short, when, subject='Weekly update'):
    return {'sha': short * 2, 'short': short, 'committed_utc': when, 'subject': subject,
            'url': f'https://github.com/o/r/commit/{short}'}


GAMES = [{'gameday': '2026-10-01', 'gametime_et': '20:15'}, {'gameday': '2026-10-04', 'gametime_et': '13:00'}]


def test_the_line_names_the_last_change_before_kickoff_and_the_first_save():
    line = page_line([commit('2450baa', '2026-09-29T18:59:32Z'), commit('c80cb28', '2026-10-01T17:20:56Z')], GAMES)
    assert 'last changed in commit <a href="https://github.com/o/r/commit/c80cb28"' in line
    assert 'Thu, Oct 1, 17:20 UTC, 6 hours before' in line, line
    assert 'First saved in <a href="https://github.com/o/r/commit/2450baa"' in line
    assert 'after kickoff' not in line


def test_a_change_after_kickoff_is_named_with_its_reason():
    line = page_line([commit('a6ba9f1', '2026-09-02T16:38:14Z'),
                      commit('f599666', '2026-10-02T18:22:12Z', 'Backfill the schedule dates')], GAMES)
    assert 'Changed after kickoff: <a href="https://github.com/o/r/commit/f599666"' in line
    assert '(Backfill the schedule dates)' in line
    assert 'last changed in commit <a href="https://github.com/o/r/commit/a6ba9f1"' in line


def test_no_commits_say_nothing():
    assert page_line([], GAMES) == ''


def test_a_subject_cannot_inject_markup():
    line = page_line([commit('a', '2026-09-02T16:38:14Z'), commit('b', '2026-10-05T00:00:00Z', '<img src=x>')], GAMES)
    assert '<img' not in line and '&lt;img' in line


# --- wiring -------------------------------------------------------------------

def test_the_site_build_reads_the_history_before_it_builds_the_board():
    cmds = [c[3] for c in build.build_commands('nfl', Path('_site'))]
    assert cmds.index('src.pipeline.lock_proof') < cmds.index('src.pipeline.generate_dashboard')


def test_the_deploy_checks_out_the_whole_history():
    text = (ROOT / '.github' / 'workflows' / 'deploy-pages.yml').read_text(encoding='utf-8')
    assert re.search(r'uses: actions/checkout@\S+ # v\S+\n\s+with:\n(?:\s+#.*\n)*\s+fetch-depth: 0\n', text)


def test_the_board_shows_it_for_locked_weeks_and_the_file_is_not_committed(tmp_path):
    src = JOINED_TEMPLATE.read_text(encoding='utf-8')
    assert 'const lockProof = __LOCK_PROOF_JSON__;' in src
    assert 'renderLockProof(currentBoardWeek, weekData);' in function_source(src.replace('\r\n', '\n'), 'renderGames')
    assert "(weekData && !weekData.preview) ? lockProofHtml(" in src
    assert 'id="board-lock-note" hidden' in src
    assert gd.load_lock_proof(tmp_path / 'none.json') is None
    assert 'data/lock_proof.json' in (ROOT / '.gitignore').read_text(encoding='utf-8').splitlines()
