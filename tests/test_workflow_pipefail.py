"""Every `| tee` in every workflow keeps the exit status of the command it logs.

GitHub runs a step with no `shell:` as `bash -e {0}`: no pipefail, so
`python ... | tee log` exits with tee's status, 0, when Python crashed. The
NHL and NBA daily runs did exactly that until Stage 68 item 1 (the
2026-10-09 audit): a crash would have committed partial state and the
`if: failure()` alert would never have fired. `shell: bash` runs
`bash --noprofile --norc -eo pipefail {0}`; an explicit `set -o pipefail`
before the pipe does the same.

The scan is over every workflow, not a list of the ones somebody remembered,
because the NFL's guards (test_weekly_summary.py, test_weekend_refresh.py)
held the NFL's steps and nothing held the next sport's copy of them.

Run with: pytest tests/test_workflow_pipefail.py -v
"""
import re
from pathlib import Path

WF = Path(__file__).resolve().parents[1] / '.github' / 'workflows'
NAME = re.compile(r'^\s*- name:\s*(.+?)\s*$')
TEE = re.compile(r'\|\s*tee\b')

# A step allowed to lose the piped status, and the reason that makes it safe.
EXEMPT = {
    ('booth-regression.yml', 'Record the baseline'):
        'continue-on-error by design; record.log, re-read by a later step, is the signal',
}


def tee_steps():
    """(file, step name, step text) for every step whose run pipes into tee."""
    out = []
    for f in sorted(WF.glob('*.yml')):
        lines = f.read_text(encoding='utf-8').replace('\r\n', '\n').split('\n')
        starts = [i for i, ln in enumerate(lines) if NAME.match(ln)] + [len(lines)]
        for a, b in zip(starts, starts[1:]):
            block = lines[a:b]
            body = [ln for ln in block if not ln.strip().startswith('#')]
            if any(TEE.search(ln) for ln in body):
                out.append((f.name, NAME.match(lines[a]).group(1).strip("'\""), '\n'.join(body)))
    return out


def keeps_status(step):
    if re.search(r'^\s+shell:\s*bash\s*$', step, re.M):
        return True
    tee_at = TEE.search(step).start()
    return bool(re.search(r'set -[a-z]*o pipefail', step[:tee_at]))


def test_the_scan_sees_the_daily_runs():
    seen = {(f, n) for f, n, _ in tee_steps()}
    assert ('nhl-daily.yml', "Run the NHL's daily run") in seen
    assert ('nba-daily.yml', "Run the NBA's daily run") in seen
    assert ('nfl-weekly-update.yml', "Generate/lock in this week's predictions") in seen


def test_every_tee_keeps_the_exit_status_of_what_it_logs():
    bad = [(f, n) for f, n, s in tee_steps() if (f, n) not in EXEMPT and not keeps_status(s)]
    assert not bad, f'| tee without pipefail (add shell: bash): {bad}'


def test_each_exemption_still_has_its_reason():
    steps = {(f, n): s for f, n, s in tee_steps()}
    for key in EXEMPT:
        assert key in steps, f'exempt step gone; drop it from EXEMPT: {key}'
    rec = steps[('booth-regression.yml', 'Record the baseline')]
    assert 'continue-on-error: true' in rec and '| tee record.log' in rec
    text = (WF / 'booth-regression.yml').read_text(encoding='utf-8')
    assert text.count('record.log') >= 2, 'a later step must re-read record.log'
