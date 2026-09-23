"""
Run one registered Stage 5 question and record the answer.

    python src/stage5_run.py build        # game table + parity check, cached outside the repo
    python src/stage5_run.py run H1       # one registered question -> experiments/stage5/results/H1.json

A question can only be run if experiments/stage5/registry.json registers it,
and the result file carries the registry entry it was run against, the commit
it was run at, and every number the decision rests on. The label in it is
computed by stage5_eval.decide() -- tests/test_stage5_registry.py recomputes
it from the stored interval and fails if the two disagree.

The cache lives outside the repository (STAGE5_CACHE, default
<repo>/../nfl-cache/stage5) because it is 1,600 rows of derived data that is
cheap to rebuild and would otherwise be a second, drift-prone copy of the
feature pipeline in git.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import stage5_data as sd  # noqa: E402
import stage5_eval as se  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = REPO_ROOT / 'experiments' / 'stage5' / 'results'
CACHE = Path(os.environ.get('STAGE5_CACHE', REPO_ROOT.parent / 'nfl-cache' / 'stage5'))
GAMES = CACHE / 'games.pkl'


def git_head():
    return subprocess.run(['git', '-C', str(REPO_ROOT), 'rev-parse', 'HEAD'],
                          capture_output=True, text=True).stdout.strip()


# ------------------------------------------------------------------ build

def parity_check(games):
    """The oracle spec must BE the production feature table, row for row."""
    from calibration import build_hist
    prod = build_hist()
    cols = ['off_matchup', 'def_matchup', 'qb_matchup', 'qb_change_diff']
    mine = games.rename(columns={'base_off_matchup': 'off_matchup', 'base_def_matchup': 'def_matchup',
                                 'oracle_qb_matchup': 'qb_matchup', 'oracle_qb_change_diff': 'qb_change_diff'})
    mine = mine.dropna(subset=cols)

    def keyset(df):
        return sorted(zip(df['season'].astype(int), df['week'].astype(int), df['home_win'].astype(int),
                          *(np.round(df[c].astype(float), 9) for c in cols)))
    a, b = keyset(prod), keyset(mine)
    same = a == b
    print(f"parity: production {len(a)} rows, stage5 oracle {len(b)} rows, identical: {same}")
    if not same:
        sa, sb = set(a), set(b)
        print(f"  only in production: {len(sa - sb)}   only in stage5: {len(sb - sa)}")
        for row in list(sa - sb)[:3]:
            print("   prod:", row)
        for row in list(sb - sa)[:3]:
            print("   s5:  ", row)
    return same, len(a)


def build():
    from kalman_ratings import fit_and_run
    from ratings_engine import prep_plays
    raw, sched = sd.load_inputs()
    plays, week_keys, _ = prep_plays(raw)
    registry = se.load_registry()
    h7 = next(h for h in registry['hypotheses'] if h['id'] == 'H7')
    kal, info = fit_and_run(plays, week_keys, fit_through_season=h7['parameters']['fit_through_season'])
    print("kalman:", info)
    games = sd.build_games(raw, sched, extra_ratings={'kalman': kal})
    same, n = parity_check(games)
    if not same:
        raise SystemExit("parity check FAILED: the stage5 oracle spec is not the production feature table")
    CACHE.mkdir(parents=True, exist_ok=True)
    games.to_pickle(GAMES)
    (CACHE / 'kalman_info.json').write_text(json.dumps(info, indent=2))
    print(f"saved {len(games)} games to {GAMES}")


# -------------------------------------------------------------------- run

def resolved_results():
    out = {}
    for p in RESULTS_DIR.glob('*.json'):
        r = json.loads(p.read_text(encoding='utf-8'))
        out[r['id']] = r
    return out


def incumbent_qb(results):
    h1 = results.get('H1')
    if h1 is None:
        raise SystemExit("INCUMBENT depends on H1, which has not been run yet")
    return 'sched' if h1['decision'] == 'ACCEPT' else 'lagged'


def incumbent_market(results):
    h2 = results.get('H2')
    return 'ml_logit' if (h2 and h2['decision'] == 'ACCEPT') else 'spread_line'


def features_for(side, model, qb_default, market_default):
    spec = side.get('qb_spec', qb_default)
    if spec == 'INCUMBENT':
        spec = qb_default
    market = side.get('market') if model == 'model_b' else None
    if model == 'model_b' and market is None:
        market = market_default
    return sd.feature_set(spec=spec, ratings=side.get('ratings', 'base'),
                          extra=tuple(side.get('extra', ())), market=market)


def compare_on(games, cand_cols, inc_cols, seasons, level, registry):
    se.guard_seasons(seasons, registry)
    p = registry['protocol']
    ids, y, probs = se.walk_forward(games, {'cand': cand_cols, 'inc': inc_cols}, seasons)
    res = se.compare(y, probs['cand'], probs['inc'], level, p['n_resamples'], p['seed'])
    res['seasons'] = seasons
    res['candidate_features'] = cand_cols
    res['incumbent_features'] = inc_cols
    return res


def slots_used(results):
    return sum(1 for r in results.values() if r.get('reached_confirmation'))


def add_stack_column(games, a_cols, registry):
    """Out-of-sample Model A logit for every game from the first predictable week on."""
    seasons = sorted(s for s in games['season'].unique()
                     if s < registry['protocol']['forward_holdout_season'])
    ids, _, probs = se.walk_forward(games, {'a': a_cols}, seasons)
    p = np.clip(probs['a'], 1e-6, 1 - 1e-6)
    oof = pd.Series(np.log(p / (1 - p)), index=ids)
    games = games.copy()
    games['a_oof_logit'] = games['game_id'].map(oof)
    return games


def run(hid):
    registry = se.load_registry()
    entry = next((h for h in registry['hypotheses'] if h['id'] == hid), None)
    if entry is None:
        raise SystemExit(f"{hid} is not registered; register it before running it")
    if entry['kind'] == 'deferred':
        raise SystemExit(f"{hid} is DEFERRED in the registry")
    if (RESULTS_DIR / f'{hid}.json').exists():
        raise SystemExit(f"{hid} already has a result; a question is answered once")
    games = pd.read_pickle(GAMES)
    results = resolved_results()
    p = registry['protocol']
    level = se.confirmatory_level(registry)
    val, conf = p['validation_seasons'], p['confirmation_seasons']
    out = {'id': hid, 'registry_entry': entry, 'code_commit': git_head(), 'ci_level_confirmatory': level}

    if hid == 'Q0':
        for model in ('model_a', 'model_b'):
            c = features_for(entry['candidate'], model, 'oracle', 'spread_line')
            i = features_for(entry['incumbent'], model, 'sched', 'spread_line')
            out[model] = compare_on(games, c, i, entry['seasons'], level, registry)
        out['decision'] = 'CONFIRMED FINDING' if out['model_a']['log_loss_ci'][1] < 0 else 'NO MEASURABLE GAP'
        out['reached_confirmation'] = False
        return save(out)

    qb_inc = 'lagged' if hid == 'H1' else incumbent_qb(results)
    market = incumbent_market(results) if hid != 'H2' else 'spread_line'
    out['incumbent_qb_spec'] = qb_inc
    out['incumbent_market'] = market
    model = entry['decision_model']

    if hid == 'H10':
        a_cols = sd.feature_set(spec=qb_inc)
        games = add_stack_column(games, a_cols, registry)
        cand = ['a_oof_logit', market]
        inc = sd.feature_set(spec=qb_inc, market=market)
    elif hid == 'H11':
        accepted = [h for h in ('H3', 'H4', 'H5', 'H6', 'H7', 'H8')
                    if results.get(h, {}).get('decision') == 'ACCEPT']
        if len(accepted) < 2:
            raise SystemExit(f"H11 runs only with two or more accepted changes; accepted: {accepted}")
        cand = combined_features(accepted, registry, qb_inc)
        inc = sd.feature_set(spec=qb_inc)
        out['combined_from'] = accepted
    else:
        cand = features_for(entry['candidate'], model, qb_inc, market)
        inc = features_for(entry['incumbent'], model, qb_inc, market)

    out['validation'] = compare_on(games, cand, inc, val, 0.95, registry)
    advanced = out['validation']['log_loss_diff'] < 0
    if advanced:
        if slots_used(results) >= p['budget_m']:
            raise SystemExit("the family's confirmatory budget is spent; register a larger budget first")
        out['confirmation'] = compare_on(games, cand, inc, conf, level, registry)
    else:
        out['confirmation'] = None
    out['reached_confirmation'] = advanced
    out['decision'] = se.decide(out['validation'], out['confirmation'])

    for extra_model in entry.get('also_report', []):
        c = features_for(entry['candidate'], extra_model, qb_inc, market)
        i = features_for(entry['incumbent'], extra_model, qb_inc, market)
        out[f'report_{extra_model}'] = compare_on(games, c, i, val + conf, level, registry)
    return save(out)


def combined_features(accepted, registry, qb_inc):
    by_id = {h['id']: h for h in registry['hypotheses']}
    ratings = 'base'
    extra = []
    for hid in accepted:
        c = by_id[hid]['candidate']
        if c.get('ratings', 'base') != 'base':
            if ratings != 'base':
                raise SystemExit(f"two accepted rating replacements ({ratings}, {c['ratings']}); "
                                 "H11 as registered cannot combine them")
            ratings = c['ratings']
        extra.extend(c.get('extra', []))
    return sd.feature_set(spec=qb_inc, ratings=ratings, extra=tuple(extra))


def save(out):
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    path = RESULTS_DIR / f"{out['id']}.json"
    path.write_text(json.dumps(out, indent=2, default=float) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in out.items() if k != 'registry_entry'}, indent=1, default=float))
    print(f"\n{out['id']}: {out['decision']}  -> {path}")
    return out


if __name__ == '__main__':
    if len(sys.argv) >= 2 and sys.argv[1] == 'build':
        build()
    elif len(sys.argv) == 3 and sys.argv[1] == 'run':
        run(sys.argv[2])
    else:
        print(__doc__)
        sys.exit(2)
