"""
Write a short summary of a Weekly update run, for the run's page and for
the alert when a run fails.

Why: the Weekly update workflow is the one thing in this repository that
runs unattended and changes what the public page says, and until Stage 4
the only record of a run was its raw log. This answers the four questions
anyone opening the run asks, in the order they ask them:

  1. Did a week lock, and how many games does it have?
  2. What got graded, and how did each model do on it?
  3. Did the data-quality checks find anything?
  4. What did the drift check say?

Everything comes from what the run left behind: `git status` for which
prediction and result files it wrote (the summary runs before the commit
step, so they are still uncommitted), the run's own log for the
data-quality lines and warnings, and drift-report.txt. Nothing is
re-derived from the model, so the summary cannot disagree with the run.

    python src/weekly_summary.py --season 2026 --log weekly-update.log \
        --drift drift-report.txt
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PRED_RE = re.compile(r'predictions/(\d+)_week(\d+)\.json$')
GRADED_RE = re.compile(r'results/(\d+)_week(\d+)_graded\.json$')
MODELS = (('Model A', 'model_a_correct'), ('Model B', 'model_b_correct'),
          ('Market', 'market_correct'))


def changed_paths(run=subprocess.run, repo=REPO):
    """Paths under predictions/ and results/ that this run created or
    modified, from `git status --porcelain`."""
    out = run(['git', 'status', '--porcelain', '--untracked-files=all', '--',
               'predictions', 'results'], cwd=repo, capture_output=True,
              text=True, check=True).stdout
    return sorted(line[3:].strip().replace('\\', '/') for line in out.splitlines() if line.strip())


def graded_line(season, week, rows):
    """One line per graded week. A game with no result yet is not graded;
    null stays null rather than counting as wrong."""
    done = [r for r in rows if r.get('actual_home_win') is not None]
    if not done:
        return f'- {season} week {week}: none of {len(rows)} games graded yet'
    parts = []
    for label, key in MODELS:
        scored = [r[key] for r in done if r.get(key) is not None]
        if scored:
            parts.append(f'{label} {sum(scored)}/{len(scored)}')
    return (f'- {season} week {week}: {len(done)} of {len(rows)} games graded. '
            + ', '.join(parts))


def log_findings(log_text):
    """(data-quality lines, other warnings, whether the check ran at all)."""
    dq, warnings, ran = [], [], False
    for raw in log_text.splitlines():
        line = raw.strip()
        if line.startswith('data quality'):
            ran = True
            if 'ERROR' in line or 'WARNING' in line:
                dq.append(line[len('data quality'):].strip())
        elif line.startswith('WARNING'):
            warnings.append(line)
    return dq, warnings, ran


def summarise(season, changed, log_text, drift_text, read_json):
    lines = [f'## Weekly update, {season} season', '']

    locked = [(int(m.group(1)), int(m.group(2)), p) for p in changed
              for m in [PRED_RE.search(p)] if m]
    lines.append('**Picks**')
    if locked:
        for s, w, p in locked:
            lines.append(f'- Locked {s} week {w}: {len(read_json(p))} games')
    else:
        lines.append('- No week was locked on this run')

    graded = [(int(m.group(1)), int(m.group(2)), p) for p in changed
              for m in [GRADED_RE.search(p)] if m]
    lines += ['', '**Grading**']
    if graded:
        lines += [graded_line(s, w, read_json(p)) for s, w, p in graded]
    else:
        lines.append('- No results changed on this run')

    dq, warnings, ran = log_findings(log_text)
    lines += ['', '**Data quality**']
    if not ran:
        lines.append('- The checks did not run: the run stopped before reaching them, '
                     'or there was nothing to predict')
    elif dq:
        lines += [f'- {d}' for d in dq]
    else:
        lines.append('- No findings')
    if warnings:
        lines += ['', '**Warnings from the run**'] + [f'- {w}' for w in warnings]

    verdict = [ln.strip() for ln in drift_text.splitlines() if 'DRIFT CHECK:' in ln]
    lines += ['', '**Drift**',
              f'- {verdict[-1].strip("= ")}' if verdict else '- The drift check did not run']
    return '\n'.join(lines) + '\n'


def _read(path):
    """The file's text, or '' when no path was given or the file is absent.
    The None check comes first: Path(None) raises, and --log and --drift are
    optional (Booth found this on #105, from the bare command)."""
    if not path:
        return ''
    p = Path(path)
    return p.read_text(encoding='utf-8') if p.is_file() else ''


def main(argv=None, changed=None):
    ap = argparse.ArgumentParser(description='Summarise a Weekly update run.')
    ap.add_argument('--season', type=int, required=True)
    ap.add_argument('--log', default=None)
    ap.add_argument('--drift', default=None)
    ap.add_argument('--out', default=None, help='also write the summary here')
    args = ap.parse_args(argv)
    changed = changed_paths() if changed is None else changed
    text = summarise(args.season, changed, _read(args.log), _read(args.drift),
                     lambda p: json.loads((REPO / p).read_text(encoding='utf-8')))
    print(text, end='')
    if args.out:
        Path(args.out).write_text(text, encoding='utf-8')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
