"""
Run one registered Stage 6 question and record the answer.

    python -m src.research.stage6_run build        # inputs + the Stage 5 parity check, cached outside the repo
    python -m src.research.stage6_run run N1       # -> experiments/stage6/results/N1.json

The rules are experiments/stage6/registry.json's, and nothing here restates
them: a question must be registered, must not already have an answer, and
must have its precondition ("requires") met by a stored result. Model
comparisons (N2, N3) go through Stage 5's own walk-forward and bootstrap
(src/research/stage5_eval.py, src/stage5_run.compare_on), against the Stage 6
registry's budget. N1 is a screen and is scored by stage6_data's rule. R1,
the referee screen, loads its own inputs (it needs no build) and is scored by
stage6_referee's rule:

    python -m src.research.stage6_run run R1       # -> experiments/stage6/results/R1.json

The game table is Stage 5's, built by stage5_data.build_games with only the
base ratings, and it must pass Stage 5's parity check against the production
feature table before it is saved. The cache lives outside the repository
(STAGE6_CACHE, default <repo>/../nfl-cache/stage6).
"""
import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from src.research import stage5_data as sd
from src.research import stage5_eval as se
from src.research import stage6_data as s6
from src.research import stage6_referee as rf
from src.research.stage5_run import compare_on, git_head, parity_check

REPO_ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = REPO_ROOT / 'experiments' / 'stage6' / 'registry.json'
RESULTS_DIR = REPO_ROOT / 'experiments' / 'stage6' / 'results'
CACHE = Path(os.environ.get('STAGE6_CACHE', REPO_ROOT.parent / 'nfl-cache' / 'stage6'))

FIT_SEASONS = [2017, 2018, 2019, 2020, 2021]   # registry: N1 "fitted on qb_games in 2017-2021"
LAST_SEASON = 2025                               # never load the forward holdout
MODEL_FROM = 2020                                # config.TRAIN_SEASONS starts here; the game table does too
#: Loaded names that differ from the nflreadr data dictionary's. Empty unless
#: the first load shows a difference; every result records it.
NGS_COLUMN_MAP = {}


def registry():
    return se.load_registry(REGISTRY_PATH)


def stored_results():
    return {p.stem: json.loads(p.read_text(encoding='utf-8')) for p in RESULTS_DIR.glob('*.json')}


# ------------------------------------------------------------------ build

def build():
    from src.pipeline.ratings_engine import (
        build_qb_ratings,
        build_team_ratings,
        prep_plays,
    )
    reg = registry()
    se.guard_seasons(list(range(s6.PBP_FROM, LAST_SEASON + 1)), reg)
    seasons = list(range(s6.PBP_FROM, LAST_SEASON + 1))
    pbp = s6.load_pbp(seasons)
    ngs = s6.load_ngs(seasons, NGS_COLUMN_MAP)
    qb = build_qb_ratings(pbp)
    w2i = qb['week_to_idx']
    n_weeks = len(qb['week_keys'])
    unmatched = s6.unmatched_ngs_weeks(ngs, w2i)
    tables = {'trailing_cpoe': s6.Trailing(s6.weekly_cpoe(pbp, w2i), n_weeks)}
    for c in s6.NGS_COLUMNS:
        tables[f'trailing_{c}'] = s6.Trailing(s6.weekly_ngs(ngs, c, w2i), n_weeks)

    # N1's rows: every qb_game from the first fit season on.
    games = s6.qb_games(qb['plays'])
    games = games[games['season'] >= FIT_SEASONS[0]]
    qbg = s6.predictor_table(games, qb['trailing_rating'], tables)
    ngs_ids = set(ngs['player_gsis_id'].dropna())
    qbg['in_ngs_ever'] = qbg['player'].isin(ngs_ids)

    # N2/N3's rows: Stage 5's game table on the model's own seasons, base ratings only.
    raw = pbp[pbp['season'] >= MODEL_FROM].reset_index(drop=True)
    sched = pd.concat([sd.load_schedule(s) for s in range(MODEL_FROM, LAST_SEASON + 1)], ignore_index=True)
    sched = sched[sched['game_type'] == 'REG'].dropna(subset=['home_score', 'away_score']).reset_index(drop=True)
    plays, week_keys, _ = prep_plays(raw)
    model_games = sd.build_games(raw, sched, variants={'base': build_team_ratings(plays, week_keys)})
    same, n = parity_check(model_games)
    if not same:
        raise SystemExit("parity check FAILED: the game table is not the production feature table")

    # Each game's announced starters, with every N1 input as of that game's cutoff.
    rows = []
    for g in sched.itertuples(index=False):
        cutoff = w2i.get((g.season, g.week))
        for side, pid in (('home', g.home_qb_id), ('away', g.away_qb_id)):
            row = {'game_id': g.game_id, 'side': side, 'player': pid, 'season': g.season, 'week': g.week}
            if cutoff is not None and isinstance(pid, str):
                row['trailing_epa'] = qb['trailing_rating'](pid, cutoff)
                for name, t in tables.items():
                    row[name] = t.value(pid, cutoff)
            rows.append(row)
    starters = pd.DataFrame(rows)

    CACHE.mkdir(parents=True, exist_ok=True)
    qbg.to_pickle(CACHE / 'qb_games.pkl')
    model_games.to_pickle(CACHE / 'games.pkl')
    starters.to_pickle(CACHE / 'starters.pkl')
    info = {'unmatched_ngs_weeks': unmatched, 'ngs_rows_reg_weekly': int(len(ngs)),
            'ngs_seasons': sorted(int(s) for s in ngs['season'].unique()),
            'qb_games': int(len(qbg)), 'model_games': int(len(model_games)), 'parity_rows': n,
            'starter_rows_missing_id': int(starters['player'].isna().sum()),
            'ngs_column_map': NGS_COLUMN_MAP}
    (CACHE / 'build_info.json').write_text(json.dumps(info, indent=2))
    print(json.dumps(info, indent=2))


# -------------------------------------------------------------------- N1

def run_n1(entry, reg):
    p = reg['protocol']
    qbg = pd.read_pickle(CACHE / 'qb_games.pkl')
    val = p['validation_seasons']
    se.guard_seasons(FIT_SEASONS + val, reg)
    fit = qbg[qbg['season'].isin(FIT_SEASONS)]
    test = qbg[qbg['season'].isin(val)]
    betas, preds, mse = {}, {}, {}
    for name, cols in s6.FEATURES.items():
        b = s6.wls(fit[cols].to_numpy(float), fit['target'].to_numpy(float), fit['dropbacks'].to_numpy(float))
        betas[name] = {'intercept': float(b[0]), **{c: float(v) for c, v in zip(cols, b[1:])}}
        preds[name] = s6.predict(b, test[cols].to_numpy(float))
        mse[name] = s6.weighted_mse(test['target'].to_numpy(float), preds[name], test['dropbacks'].to_numpy(float))
    y, w = test['target'].to_numpy(float), test['dropbacks'].to_numpy(float)
    clusters = test['player'].astype(str) + '_' + test['season'].astype(str)

    def diff(a, b):
        bs = s6.cluster_bootstrap_mse_diff(y, preds[a], preds[b], w, clusters, p['n_resamples'], p['seed'])
        return {'mse_diff': mse[a] - mse[b], 'mse_ci_95': list(se.interval(bs, 0.95))}

    out = {
        'fit': {'seasons': FIT_SEASONS, 'n_qb_games': int(len(fit)), 'coefficients': betas},
        'validation': {'seasons': val, 'n_qb_games': int(len(test)), 'n_clusters': int(clusters.nunique()),
                       'mse': mse,
                       'share_of_games_whose_passer_is_never_in_ngs': float((~test['in_ngs_ever']).mean())},
        'candidate_minus_control': diff('candidate', 'control'),
        'control_minus_base': diff('control', 'base'),
    }
    out['decision'] = s6.screen_label(out['candidate_minus_control']['mse_diff'],
                                      out['candidate_minus_control']['mse_ci_95'])
    out['reached_confirmation'] = False
    return out


# -------------------------------------------------------------------- R1

def run_r1(entry, reg):
    """Loads its own inputs (schedule and three play-by-play columns, 2016-2023)."""
    p = reg['protocol']
    se.guard_seasons(rf.R1_SEASONS, reg)
    sched = pd.concat([sd.load_schedule(s) for s in rf.R1_SEASONS], ignore_index=True)
    games = rf.named_referee_games(sched)
    pbp = s6.load_pbp(rf.R1_SEASONS, rf.PBP_COLUMNS)
    games, counts = rf.penalty_differential(pbp, games)
    t = rf.window_means(games)
    x, y, w = t['mean_early'], t['mean_late'], t['weight']
    r = float(rf.weighted_corr(x, y, w))
    bs = rf.bootstrap_corr(x, y, w, p['n_resamples'], p['seed'])
    defined = bs[~np.isnan(bs)]
    ci = list(se.interval(defined, 0.95))
    out = {
        'inputs': {'seasons': rf.R1_SEASONS, 'games_scored': int(len(games)), **counts,
                   'mean_differential': float(games['differential'].mean())},
        'referees': {ref: {'mean_early': float(row.mean_early), 'games_early': int(row.count_early),
                           'mean_late': float(row.mean_late), 'games_late': int(row.count_late),
                           'weight': int(row.weight)}
                     for ref, row in t.iterrows()},
        'persistence': {'n_referees': int(len(t)), 'weighted_corr': r, 'corr_ci_95': ci,
                        'undefined_resamples': int(len(bs) - len(defined))},
    }
    out['decision'] = rf.r1_label(ci)
    out['reached_confirmation'] = False
    return out


# ---------------------------------------------------------------- N2, N3

def add_matchup(games, starters, beta, cols, name):
    """home prediction minus away prediction, from a frozen N1 fit."""
    s = starters.dropna(subset=cols).copy()
    s['pred'] = s6.predict([beta['intercept'], *[beta[c] for c in cols]], s[cols].to_numpy(float))
    wide = s.pivot(index='game_id', columns='side', values='pred')
    games = games.copy()
    games[name] = games['game_id'].map(wide['home'] - wide['away'])
    return games


def run_model(entry, reg, results):
    p = reg['protocol']
    n1 = results['N1']
    games = pd.read_pickle(CACHE / 'games.pkl')
    starters = pd.read_pickle(CACHE / 'starters.pkl')
    coefs = n1['fit']['coefficients']
    games = add_matchup(games, starters, coefs['candidate'], s6.FEATURES['candidate'], 'ngs_qb_matchup')
    games = add_matchup(games, starters, coefs['control'], s6.FEATURES['control'], 'cpoe_qb_matchup')

    def cols(side, model):
        return sd.feature_set(spec=side['qb_spec'], ratings=side['ratings'], extra=tuple(side.get('extra', ())),
                              market='spread_line' if model == 'model_b' else None)

    level = se.confirmatory_level(reg)
    cand, inc = cols(entry['candidate'], 'model_a'), cols(entry['incumbent'], 'model_a')
    out = {'frozen_from': 'N1', 'validation': compare_on(games, cand, inc, p['validation_seasons'], 0.95, reg)}
    advanced = out['validation']['log_loss_diff'] < 0
    if advanced:
        used = sum(1 for r in results.values() if r.get('reached_confirmation'))
        if used >= p['budget_m']:
            raise SystemExit("Stage 6's confirmatory budget is spent")
        out['confirmation'] = compare_on(games, cand, inc, p['confirmation_seasons'], level, reg)
    else:
        out['confirmation'] = None
    out['reached_confirmation'] = advanced
    out['decision'] = se.decide(out['validation'], out['confirmation'])
    if 'model_b' in entry.get('also_report', []):
        out['model_b'] = compare_on(games, cols(entry['candidate'], 'model_b'), cols(entry['incumbent'], 'model_b'),
                                    p['validation_seasons'] + p['confirmation_seasons'], level, reg)
    return out


# -------------------------------------------------------------------- run

def unmet_precondition(entry, results):
    for dep, needed in entry.get('requires', {}).items():
        got = results.get(dep, {}).get('decision')
        if got != needed:
            return f"{entry['id']} requires {dep} = {needed}; {dep} is {got}"
    return None


def run(hid):
    reg = registry()
    entry = next((h for h in reg['hypotheses'] if h['id'] == hid), None)
    if entry is None:
        raise SystemExit(f"{hid} is not registered; register it before running it")
    if entry['kind'] in ('deferred', 'measurement'):
        raise SystemExit(f"{hid} is a {entry['kind']} and is not run by this script")
    if (RESULTS_DIR / f'{hid}.json').exists():
        raise SystemExit(f"{hid} already has a result; a question is answered once")
    results = stored_results()
    why = unmet_precondition(entry, results)
    if why:
        raise SystemExit(why)
    if hid == 'R1':
        ngs = {}
        body = run_r1(entry, reg)
    else:
        info = json.loads((CACHE / 'build_info.json').read_text())
        ngs = {'ngs_column_map': info['ngs_column_map'], 'build': info}
        body = run_n1(entry, reg) if hid == 'N1' else run_model(entry, reg, results)
    out = {'id': hid, 'registry_entry': entry, 'code_commit': git_head(),
           'ci_level_confirmatory': se.confirmatory_level(reg), **ngs, **body}
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    path = RESULTS_DIR / f'{hid}.json'
    path.write_text(json.dumps(out, indent=2, default=float) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in out.items() if k not in ('registry_entry', 'build')}, indent=1, default=float))
    print(f"\n{hid}: {out['decision']}  -> {path}")
    return out


if __name__ == '__main__':
    if len(sys.argv) >= 2 and sys.argv[1] == 'build':
        build()
    elif len(sys.argv) == 3 and sys.argv[1] == 'run':
        run(sys.argv[2])
    else:
        print(__doc__)
        sys.exit(2)
