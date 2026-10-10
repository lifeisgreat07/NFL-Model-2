"""Every job runs on ubuntu-24.04 until the Ubuntu 26 rollout is seen green (Stage 68 item 4).

GitHub moves `ubuntu-latest` from 24.04 to 26.04 between 2026-10-19 and
2026-11-19 (changelog, 2026-09-17), with tools updated and some removed:
the day before the NBA's opening night. Every job here is pinned to the
image every published number and every green run so far was made on.

Unpinning is a deliberate change of this file, not a drift: run the suite
and one of each writer on `ubuntu-26.04` first (a dispatched run is
enough), then move WANT and every workflow together.

Run with: pytest tests/test_runner_image.py -v
"""
import re
from pathlib import Path

WF = Path(__file__).resolve().parents[1] / '.github' / 'workflows'
WANT = 'ubuntu-24.04'
RUNS_ON = re.compile(r'^\s*runs-on:\s*(\S+)\s*$', re.M)


def images():
    return [(p.name, m) for p in sorted(WF.glob('*.yml'))
            for m in RUNS_ON.findall(p.read_text(encoding='utf-8'))]


def test_every_job_names_its_runner():
    files = {p.name for p in WF.glob('*.yml')}
    assert {f for f, _ in images()} == files, 'a workflow with no runs-on line this scan can read'


def test_every_job_is_pinned_to_the_one_image():
    bad = [(f, i) for f, i in images() if i != WANT]
    assert not bad, f'not on {WANT}: {bad}'
