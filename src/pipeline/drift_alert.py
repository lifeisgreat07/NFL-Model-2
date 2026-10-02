"""
Run the drift check after grading, and open an issue when it flags.

src/pipeline/check_drift.py has existed since before Stage 3 and nothing ran it. It
compares live Model A's log loss with its backtest baseline and exits 1
when the gap is too large to be small-sample noise (a one-sided bootstrap
bound, 30 games minimum; on accuracy and a z-test until Stage 33 R4).
A flag nobody sees is the same as no check, so the Weekly update workflow
runs this after grading and, on a flag, opens the issue "Model drift
detected", or comments on it if it is already open.

An issue, not a pull request: drift has no code change to propose, so a PR
would be empty (decided in Stage 4's notes in CLAUDE.md).

It never fails the weekly run. Drift is a question for a person, and the
run's job is to lock and grade; stopping it would cost picks and answer
nothing. The drift output is also written to --report for the run summary.

A caution the issue carries. Since Stage 33 R4 the flag is on Model A's
LOG LOSS against a committed backtest baseline (data/drift_baseline.json),
not on accuracy, which this project's own methodology says cannot carry a
result at this sample size. A flag is still a reason to look, not a
verdict: a one-sided 95% test re-run every week on a growing sample will
sometimes fire by chance.

    python -m src.pipeline.drift_alert [--report drift-report.txt]
"""
import argparse
import io
from contextlib import redirect_stdout
from pathlib import Path

TITLE = 'Model drift detected'
CAUTION = ("This flag is on Model A's log loss against the 2022-2025 backtest "
           '(Stage 33 R4, experiments/stage33/registry.json); accuracy is printed '
           'above for information only. A one-sided 95% test, re-run every '
           'week on a growing sample, will sometimes flag by chance: read the '
           'per-game losses before acting.')


def run_check(check):
    """(exit code, printed output) of the drift check."""
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = check()
    return code, buf.getvalue()


def main(argv=None, check=None, raise_alert=None):
    ap = argparse.ArgumentParser(description='Run the drift check; alert on a flag.')
    ap.add_argument('--report', default=None, help='also write the drift output here')
    args = ap.parse_args(argv)
    if check is None:
        from src.pipeline.check_drift import main as check
    code, text = run_check(check)
    print(text, end='')
    if args.report:
        Path(args.report).write_text(text, encoding='utf-8')
    if code != 1:
        return 0
    body = f'The drift check flagged after grading.\n\n```\n{text.strip()}\n```\n\n{CAUTION}\n'
    if raise_alert is None:
        from src.pipeline.alerts import open_or_comment as raise_alert
    action, ref = raise_alert(TITLE, body)
    print(f'drift alert {action}: {ref}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
