"""
Stage 33's evaluation rules, as code (experiments/nfl/stage33/registry.json).

The registry was committed before anything here ran (8ddbcec); this module
reads its protocol rather than restating it, so the rules cannot drift from
what was registered. What it adds to Stage 5's machinery:

  * Models are ModelSpecs (src/core/model_specs.py), scored by the same
    walk_forward the published backtest and the live fit use. A registry
    entry's candidate and incumbent are turned into specs by spec_from(),
    and the incumbent must BE the published spec, not a copy of it.
  * PAIRED on identical games. Two specs with the same features score the
    same rows; evaluate() refuses to compare if they do not.
  * R3 is not a superiority question. It switches on non-inferiority with a
    margin, and goes to confirmation whatever validation shows. Its labels
    are REJECT (measurably worse: never switches, Mark's 2026-10-02
    amendment), NON-INFERIOR (switch), INCONCLUSIVE.
  * The paired bootstrap, the interval and the superiority labels are Stage
    5's own functions, imported, not copied.

    python -m src.sports.nfl.research.stage33_eval R1     # writes experiments/nfl/stage33/results/R1.json

R4 is a monitoring rule, not a comparison; it is implemented in the drift
check, not here.
"""
import argparse
import json
import platform
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

from src.core.model_specs import MODEL_SPECS, ModelSpec, walk_forward
from src.sports.nfl.research.stage5_eval import (
    ForwardHoldoutError,
    compare,
    label_from_interval,
)
from src.sports.nfl.weekly_update import market_prob

REPO_ROOT = Path(__file__).resolve().parents[4]
REGISTRY_PATH = REPO_ROOT / 'experiments' / 'nfl' / 'stage33' / 'registry.json'
STAGE33_RESULTS = REPO_ROOT / 'experiments' / 'nfl' / 'stage33' / 'results'

#: The comparisons this module runs. R4 is a monitoring rule.
COMPARISONS = ('R1', 'R2', 'R3')

#: Validation intervals are reported at 95%; only the point estimate screens.
VALIDATION_LEVEL = 0.95


def load_registry(path=REGISTRY_PATH):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def entry(registry, hid):
    for h in registry['hypotheses']:
        if h['id'] == hid:
            return h
    raise KeyError(f'{hid} is not registered in Stage 33')


def guard_seasons(seasons, registry):
    forbidden = registry['protocol']['forward_holdout_season']
    touched = [s for s in seasons if s >= forbidden]
    if touched:
        raise ForwardHoldoutError(
            f"season(s) {touched} are the forward holdout (>= {forbidden}). Stage 33 may "
            "not evaluate on them until the season is over and the forward test runs.")


def confirmatory_level(registry):
    p = registry['protocol']
    return 1.0 - p['alpha'] / p['budget_m']


# ------------------------------------------------------------- the models

def spec_from(settings, model=None):
    """A registry entry's candidate or incumbent, as a ModelSpec on the
    features of `model` (default: the settings' own model). penalty null
    means unpenalised, which takes no C."""
    base = MODEL_SPECS[model or settings['model']]
    penalty = settings.get('penalty', 'l2')
    return ModelSpec(base.features, penalty=penalty,
                     C=settings.get('C', 1.0) if penalty is not None else None,
                     scaler=settings.get('scaler'))


def is_market_curve(h):
    return 'market_curve' in h['candidate']


def fixed_curve(spread_line):
    """The live pipeline's market probability, the incumbent in R3: the same
    function the weekly run calls, not a copy of its formula."""
    return market_prob(spread_line)


# -------------------------------------------------------------- the rules

def decide_non_inferiority(confirmation, margin):
    """R3's rule with Mark's 2026-10-02 precedence: measurably worse never
    switches, even inside the margin."""
    lo, hi = confirmation['log_loss_ci']
    if lo > 0:
        return 'REJECT'
    if hi < margin:
        return 'NON-INFERIOR'
    return 'INCONCLUSIVE'


def reaches_confirmation(h, validation):
    """The screen: validation log loss below the incumbent's. R3 goes to
    confirmation whatever validation shows (the registry's exception)."""
    return 'margin' in h or validation['log_loss_diff'] < 0


def decide(h, validation, confirmation):
    """The label, from the numbers. Nothing downstream writes one by hand."""
    if 'margin' in h:
        if confirmation is None:
            raise ValueError(f"{h['id']} always reaches confirmation, and has no confirmation result")
        return decide_non_inferiority(confirmation, h['margin'])
    if validation['log_loss_diff'] >= 0:
        return 'NOT ADVANCED'
    if confirmation is None:
        raise ValueError(f"{h['id']} passed the validation screen but has no confirmation result")
    return label_from_interval(*confirmation['log_loss_ci'])


# ------------------------------------------------------------ the scoring

def score(h, hist, seasons, level, registry, model=None):
    """One paired comparison of h's candidate against its incumbent, on
    `seasons`, for `model` (default: h's decision model)."""
    guard_seasons(seasons, registry)
    p = registry['protocol']
    if is_market_curve(h):
        # The fitted curve is the published "market" model: a logistic
        # regression on spread_line alone, the row the backtest table prints.
        scored, p_cand = walk_forward(MODEL_SPECS['market'], hist, seasons)
        p_inc = fixed_curve(scored['spread_line'].values)
    else:
        model = model or h['decision_model']
        s_c, p_cand = walk_forward(spec_from(h['candidate'], model), hist, seasons)
        scored, p_inc = walk_forward(spec_from(h['incumbent'], model), hist, seasons)
        if not s_c.index.equals(scored.index):
            raise ValueError(f"{h['id']}: candidate and incumbent were scored on different games")
    out = compare(scored['home_win'].values.astype(float), p_cand, p_inc, level,
                  p['n_resamples'], p['seed'])
    out['seasons'] = list(seasons)
    return out


def run(hid, hist, registry):
    """Answer one registered comparison. Returns the result record."""
    h = entry(registry, hid)
    if hid not in COMPARISONS:
        raise ValueError(f'{hid} is not a comparison this module runs')
    p = registry['protocol']
    if not is_market_curve(h):
        published = MODEL_SPECS[h['decision_model']]
        if spec_from(h['incumbent']) != published:
            raise ValueError(f'{hid}: the registered incumbent is not the published {h["decision_model"]} spec')
    level = confirmatory_level(registry)
    val = score(h, hist, p['validation_seasons'], VALIDATION_LEVEL, registry)
    conf = (score(h, hist, p['confirmation_seasons'], level, registry)
            if reaches_confirmation(h, val) else None)
    result = {'id': hid, 'registry_entry': h, 'validation': val, 'confirmation': conf,
              'reached_confirmation': conf is not None, 'decision': decide(h, val, conf)}
    also = {}
    for m in h.get('also_report', []):
        also[m] = {'validation': score(h, hist, p['validation_seasons'], VALIDATION_LEVEL, registry, m),
                   'confirmation': (score(h, hist, p['confirmation_seasons'], level, registry, m)
                                    if conf is not None else None)}
    if also:
        result['also_report'] = also
    return result


def _provenance():
    def ver(pkg):
        try:
            return __import__(pkg).__version__
        except Exception:
            return None
    commit = subprocess.run(['git', '-C', str(REPO_ROOT), 'rev-parse', 'HEAD'],
                            capture_output=True, text=True).stdout.strip()
    return {'commit': commit, 'generated_utc': datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%SZ'),
            'platform': platform.platform(), 'processor': platform.processor(),
            'python': platform.python_version(), 'numpy': ver('numpy'),
            'pandas': ver('pandas'), 'scikit-learn': ver('sklearn')}


def main(argv=None):
    ap = argparse.ArgumentParser(description="Answer one of Stage 33's registered comparisons.")
    ap.add_argument('id', choices=COMPARISONS)
    args = ap.parse_args(argv)
    out = STAGE33_RESULTS / f'{args.id}.json'
    if out.exists():
        print(f'{out} already exists. A registered question is answered once.', file=sys.stderr)
        return 1
    from src.sports.nfl.research.calibration import build_hist
    registry = load_registry()
    result = run(args.id, build_hist(), registry)
    result['provenance'] = _provenance()
    STAGE33_RESULTS.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(f"{args.id}: {result['decision']}  written to {out}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
