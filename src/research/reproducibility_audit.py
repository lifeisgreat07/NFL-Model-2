"""
Re-run the published backtest from today's code and check it reproduces.

VERIFICATION.md says "this result is reproducible" is not a claim on its
own; a fresh re-run, from the current code, with the actual numbers, is.
Until Stage 4 that re-run was something a person remembered to do. This is
the re-run, written down once, with its pass mark stated in advance.

What it checks, for each published model in data/calibration.json (the
file the dashboard's reliability diagram and Model Lab figures come from):

  1. Determinism. The walk-forward backtest runs twice in one process and
     must return identical outcomes and identical probabilities.
  2. The published figures. Log loss, Brier and AUC must match to four
     decimals; this project's CONFIRMED FINDING is that they agree to four
     decimals across Linux and Windows. Accuracy may differ by up to two
     games out of the sample, for the reason recorded in the same finding.
     The game count must match exactly: a different n means a different set
     of games, and every other comparison is then meaningless.
  (Until Stage 35 a third check compared config.BACKTEST_ACCURACY, the drift
  check's stored baseline. The drift check now reads data/calibration.json,
  which check 2 already covers; see audit().)

It writes what it found, with the commit and the library versions, and exits
1 if anything failed. It needs nflverse and six seasons of play-by-play, so
it runs on markys or from the Run backtest workflow, never in the suite; the
suite tests the comparison rules on synthetic numbers, and holds the
committed record to the published file.

    python -m src.research.reproducibility_audit [--out results/reproducibility_audit.json]
"""
import argparse
import json
import platform
import subprocess
from datetime import UTC, datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PUBLISHED = REPO / 'data' / 'calibration.json'

#: Four decimals, for the metrics that agree across platforms.
PROPER_SCORE_TOL = 5e-5
PROPER_SCORES = ('log_loss', 'brier', 'auc')
#: Accuracy may move by this many games across platforms (CONFIRMED FINDING).
ACCURACY_GAMES = 2


def compare(model, published, reproduced):
    """Rows comparing one model's published metrics with a fresh run."""
    rows = []
    same_n = published.get('n') == reproduced.get('n')
    rows.append({'model': model, 'metric': 'n', 'published': published.get('n'),
                 'reproduced': reproduced.get('n'), 'tolerance': 0, 'ok': same_n})
    for metric in PROPER_SCORES:
        p, r = published.get(metric), reproduced.get(metric)
        ok = p is not None and r is not None and abs(p - r) <= PROPER_SCORE_TOL
        rows.append({'model': model, 'metric': metric, 'published': p, 'reproduced': r,
                     'tolerance': PROPER_SCORE_TOL, 'ok': bool(ok and same_n)})
    n = reproduced.get('n') or 0
    tol = ACCURACY_GAMES / n if n else 0
    p, r = published.get('accuracy'), reproduced.get('accuracy')
    ok = p is not None and r is not None and abs(p - r) <= tol + 1e-12
    rows.append({'model': model, 'metric': 'accuracy', 'published': p, 'reproduced': r,
                 'tolerance': tol, 'ok': bool(ok and same_n)})
    return rows


def audit(published, run_backtest):
    """published: data/calibration.json's `models`. run_backtest(name) ->
    (metrics, y_true, y_prob) for that model; called twice per model.
    Returns (rows, determinism).

    Until Stage 35 this also compared config.BACKTEST_ACCURACY, the drift
    check's own stored baseline, with the reproduced accuracy. The drift
    check now reads its baseline from data/calibration.json, which the
    accuracy row above already compares, so that row would repeat it."""
    rows, determinism = [], {}
    for model, entry in published.items():
        first = run_backtest(model)
        second = run_backtest(model)
        same = (list(first[1]) == list(second[1])) and (list(first[2]) == list(second[2]))
        determinism[model] = bool(same)
        rows += compare(model, entry['metrics'], first[0])
    return rows, determinism


def verdict(rows, determinism):
    return 'REPRODUCED' if all(r['ok'] for r in rows) and all(determinism.values()) else 'NOT REPRODUCED'


def _provenance():
    def ver(pkg):
        try:
            return __import__(pkg).__version__
        except Exception:
            return None
    try:
        commit = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=REPO, capture_output=True,
                                text=True, check=True).stdout.strip()
    except Exception:
        commit = None
    return {'commit': commit, 'platform': platform.platform(), 'cpu': cpu_model(),
            'python': platform.python_version(), 'numpy': ver('numpy'),
            'pandas': ver('pandas'), 'scikit-learn': ver('sklearn')}


def cpu_model(cpuinfo='/proc/cpuinfo'):
    """The machine's CPU, by name.

    On one commit with one set of packages, two GitHub runners disagreed:
    one REPRODUCED, one put Model A's log loss at 0.6499472 against
    0.6498122 (docs/traps.md). Each run's two passes agreed and the local
    Windows machine always reproduces exactly, so the likeliest cause is the
    CPU underneath the float sums, and until now the record did not say
    which CPU it ran on. platform.processor() names it on Windows but says
    only "x86_64" on Linux, where /proc/cpuinfo has the model name."""
    try:
        with open(cpuinfo, encoding='utf-8') as f:
            for line in f:
                if line.lower().startswith('model name'):
                    return line.split(':', 1)[1].strip()
    except OSError:
        pass
    return platform.processor() or platform.machine() or None


def main(argv=None):
    ap = argparse.ArgumentParser(description='Re-run the published backtest and compare.')
    ap.add_argument('--out', default=str(REPO / 'results' / 'reproducibility_audit.json'))
    args = ap.parse_args(argv)

    from src.pipeline.config import BACKTEST_SEASONS
    from src.pipeline.model_specs import MODEL_SPECS
    from src.research.backtest import backtest
    from src.research.calibration import build_hist

    published = json.loads(PUBLISHED.read_text(encoding='utf-8'))
    hist = build_hist()
    # The specs the live pipeline fits (Stage 33 item 21), not a copy of them.
    rows, determinism = audit(
        published['models'],
        lambda name: backtest(hist, MODEL_SPECS[name], BACKTEST_SEASONS, return_raw=True))
    result = {
        'generated_utc': datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'provenance': _provenance(),
        'published_file': 'data/calibration.json',
        'published_generated_at': published.get('generated_at'),
        'published_provenance': published.get('provenance'),
        'determinism': determinism,
        'comparisons': rows,
        'verdict': verdict(rows, determinism),
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')

    for r in rows:
        mark = 'ok  ' if r['ok'] else 'FAIL'
        print(f"{mark} {r['model']:<8} {r['metric']:<24} published {r['published']}  "
              f"reproduced {r['reproduced']}")
    for model, same in determinism.items():
        print(f"{'ok  ' if same else 'FAIL'} {model:<8} two runs identical: {same}")
    print(f"\n{result['verdict']} -- written to {out}")
    return 0 if result['verdict'] == 'REPRODUCED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
