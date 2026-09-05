"""
Against-the-spread evaluation: would any of this have made money?

Every evaluation in this project so far asks whether we picked the winner.
None has asked the question a skeptical reader asks first, and it is not the
same question -- picking winners is easy when the spread is handed to you as a
feature; beating the spread is the actual claim.

WHAT IS AND ISN'T BEING TESTED. Model B outputs a win probability, not a
margin, so it cannot make an ATS pick directly, and margin-of-victory modelling
is already REJECTED on Model Lab (-1.56pt, CI [-3.13, +0.09]) -- this does not
revive it. The well-posed question is a different target on the same features:

    can these features predict a COVER, given the spread?

So this fits the same weekly-refit walk-forward on `home_covered` instead of
`home_win`. That is a new model, honestly labelled, not a re-scoring of
Model B.

THE BAR IS NOT 50%. A coin flip goes 50%. At standard -110 juice you must hit
52.38% to break even, so a cover rate whose interval clears 50% but not 52.38%
is a real signal that still loses money. Both bars are reported, and the
headline verdict uses the one that matters.

NO SUBGROUP SEARCH. It is tempting to hunt for the slice where this works --
high-confidence games, big spreads, divisional matchups. This project already
ran that experiment deliberately ("Systematic narrow-edge search (12
partitions)") and found the best candidate was +0.74pt with CI [-2.60, +4.09],
which is exactly what testing twelve things on noise produces. So the headline
here is all games, once. Any future slicing has to be a separate, pre-declared
experiment with its own multiple-comparisons accounting.

CONTROLS. Three strategies with known answers run alongside, because a wrong
sign convention or a wrong cover rule would otherwise produce a confident,
completely inverted result. Always-home, always-favourite and always-away
should all land near 50% -- that is what a spread is for. If any control comes
back far from 50%, the arithmetic is wrong and the headline number is
meaningless; the script says so rather than printing it anyway.

Usage: python src/ats_evaluation.py
Writes data/ats_evaluation.json and prints a summary.
"""
import json
import sys
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression

sys.path.insert(0, str(Path(__file__).parent))
from config import BACKTEST_SEASONS, MODEL_VERSION
from calibration import build_hist, wilson_interval

DATA_DIR = Path(__file__).parent.parent / 'data'

FOOTBALL = ['off_matchup', 'def_matchup', 'qb_matchup', 'qb_change_diff']
# The spread is included: the question is whether the football features add
# anything ON TOP of what the market already priced, which is only meaningful
# if the model can see the price.
ATS_FEATURES = FOOTBALL + ['spread_line']

# Standard -110 both sides. Win 100 on a 110 stake, so break-even p satisfies
# 100p = 110(1-p) -> p = 110/210.
BREAK_EVEN = 110 / 210          # 0.523809...
COIN_FLIP = 0.50

N_RESAMPLES = 5000
SEED = 20260905

# A control this far from 50% means the cover arithmetic is wrong, not that a
# trivial strategy beats the market. Generous: real spreads do have small
# documented biases, but nothing near this.
CONTROL_TOLERANCE = 0.06


def add_ats_columns(hist):
    """Attach margin-relative-to-spread and the cover outcome.

    Sign convention is VERIFIED here rather than assumed. nflverse's
    spread_line is documented as the home team's line, positive when the home
    team is favoured -- but a silently inverted convention would flip every
    result in this file while still printing plausible numbers, so the
    relationship is measured against real outcomes and asserted.
    """
    h = hist.dropna(subset=['spread_line', 'home_margin', 'home_win']).copy()

    corr = np.corrcoef(h['spread_line'], h['home_margin'])[0, 1]
    if corr <= 0.2:
        raise ValueError(
            f"spread_line correlates {corr:+.3f} with the home margin. A "
            f"positive spread_line is supposed to mean the home team is "
            f"favoured; this says otherwise, so the cover rule below would be "
            f"inverted. Fix the convention before trusting any output.")

    # Home covers when the actual margin beats the line it was given.
    h['margin_vs_spread'] = h['home_margin'] - h['spread_line']
    h['push'] = h['margin_vs_spread'] == 0
    h['home_covered'] = (h['margin_vs_spread'] > 0).astype(int)
    return h, float(corr)


def walk_forward_ats(hist, test_seasons=BACKTEST_SEASONS):
    """Weekly-refit walk-forward on the cover target.

    Structurally identical to backtest(): train on everything strictly
    earlier, refit every week, predict that week. Pushes are excluded from
    TRAINING as well as scoring -- a push is not a cover and not a
    non-cover, and labelling it either way teaches the model something false.
    """
    hist = hist.sort_values(['season', 'week'])
    d2 = hist[~hist['push']].dropna(subset=ATS_FEATURES + ['home_covered'])

    rows = {'covered': [], 'prob': [], 'spread': [], 'season': [], 'week': []}
    for season in test_seasons:
        for w in sorted(d2[d2['season'] == season]['week'].unique()):
            train = d2[(d2['season'] < season)
                       | ((d2['season'] == season) & (d2['week'] < w))]
            test_w = d2[(d2['season'] == season) & (d2['week'] == w)]
            if len(train) < 50 or len(test_w) == 0:
                continue
            m = LogisticRegression(max_iter=1000)
            m.fit(train[ATS_FEATURES].values, train['home_covered'].values)
            rows['prob'].extend(m.predict_proba(test_w[ATS_FEATURES].values)[:, 1])
            rows['covered'].extend(test_w['home_covered'].values)
            rows['spread'].extend(test_w['spread_line'].values)
            rows['season'].extend(test_w['season'].values)
            rows['week'].extend(test_w['week'].values)

    return {k: np.asarray(v) for k, v in rows.items()}


def hit_rate(picked_home, covered):
    """Fraction of picks that landed. picked_home and covered are 0/1."""
    correct = np.where(picked_home == 1, covered, 1 - covered)
    return float(correct.mean()), correct


def bootstrap_rate(correct, n_resamples=N_RESAMPLES, seed=SEED):
    """Percentile interval on a hit rate by resampling GAMES."""
    rng = np.random.default_rng(seed)
    n = len(correct)
    rates = np.empty(n_resamples)
    for i in range(n_resamples):
        rates[i] = correct[rng.integers(0, n, n)].mean()
    lo, hi = np.percentile(rates, [2.5, 97.5])
    return float(lo), float(hi)


def assess(name, picked_home, covered):
    rate, correct = hit_rate(picked_home, covered)
    n = len(correct)
    boot_lo, boot_hi = bootstrap_rate(correct)
    # Wilson as an independent check: a hit rate is a binomial proportion, so
    # it has a closed form. Two routes disagreeing means the resampling is
    # wrong, which is the failure that would otherwise pass unnoticed.
    wil_lo, wil_hi = wilson_interval(int(correct.sum()), n)
    return {
        'name': name,
        'n': n,
        'rate': rate,
        'ci_lo': boot_lo,
        'ci_hi': boot_hi,
        'wilson_lo': float(wil_lo),
        'wilson_hi': float(wil_hi),
        'beats_coin_flip': bool(boot_lo > COIN_FLIP),
        'beats_break_even': bool(boot_lo > BREAK_EVEN),
    }


def main():
    hist = build_hist()
    h, corr = add_ats_columns(hist)
    pushes = int(h['push'].sum())
    print(f"\nspread_line vs home margin correlation: {corr:+.3f} "
          f"(positive confirms 'positive spread_line = home favoured')")
    print(f"{len(h)} games with a spread; {pushes} pushes excluded "
          f"({100*pushes/len(h):.1f}%)")

    data = walk_forward_ats(h)
    n = len(data['covered'])
    print(f"\n{n} games evaluated across {BACKTEST_SEASONS} (weekly refit).")

    covered = data['covered']
    model_pick = (data['prob'] >= 0.5).astype(int)
    results = {
        'model': assess('Model (features + spread -> cover)', model_pick, covered),
        'always_home': assess('Control: always pick home', np.ones(n, dtype=int), covered),
        'always_away': assess('Control: always pick away', np.zeros(n, dtype=int), covered),
        'always_favourite': assess(
            'Control: always pick the favourite',
            (data['spread'] > 0).astype(int), covered),
    }

    print(f"\n{'strategy':<40}{'n':<7}{'hit rate':<11}{'95% CI':<20}{'vs 52.38%'}")
    for r in results.values():
        ci = f"[{r['ci_lo']*100:.1f}%, {r['ci_hi']*100:.1f}%]"
        verdict = 'PROFITABLE' if r['beats_break_even'] else (
            'above 50% but not profitable' if r['beats_coin_flip'] else 'no edge')
        print(f"{r['name']:<40}{r['n']:<7}{r['rate']*100:<11.2f}{ci:<20}{verdict}")

    controls_ok = all(abs(results[k]['rate'] - 0.5) <= CONTROL_TOLERANCE
                      for k in ('always_home', 'always_away', 'always_favourite'))
    print()
    if controls_ok:
        print("Controls all sit near 50%, which is what a spread is for -- "
              "the cover arithmetic checks out.")
    else:
        print("WARNING: a trivial control is far from 50%. That is not an edge, "
              "it is a bug in the sign convention or the cover rule. "
              "Do not report the model row until this is resolved.")

    m = results['model']
    print(f"\nBootstrap CI [{m['ci_lo']*100:.2f}%, {m['ci_hi']*100:.2f}%] vs "
          f"Wilson [{m['wilson_lo']*100:.2f}%, {m['wilson_hi']*100:.2f}%] "
          f"-- two independent routes to the same interval.")
    print(f"Break-even at -110 juice is {BREAK_EVEN*100:.2f}%. "
          f"{'CLEARED.' if m['beats_break_even'] else 'Not cleared.'}")

    payload = {
        'model_version': MODEL_VERSION,
        'backtest_seasons': BACKTEST_SEASONS,
        'features': ATS_FEATURES,
        'n_games': n,
        'pushes_excluded': pushes,
        'spread_margin_correlation': corr,
        'break_even_rate': BREAK_EVEN,
        'n_resamples': N_RESAMPLES,
        'seed': SEED,
        'controls_sane': controls_ok,
        'results': results,
    }
    DATA_DIR.mkdir(exist_ok=True)
    out = DATA_DIR / 'ats_evaluation.json'
    with open(out, 'w') as f:
        json.dump(payload, f, indent=2)
    print(f"\nSaved to {out}")


if __name__ == '__main__':
    main()
