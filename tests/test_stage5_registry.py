"""
Stage 5's pre-registration, held to itself.

A pre-registration is only worth anything if three things are mechanically
true, and each has a test here:

  1. A question is written down BEFORE it is answered. The commit that first
     adds experiments/stage5/results/<id>.json must have a parent in which
     registry.json already registers <id>, with the same wording. Editing the
     question after seeing the answer -- or registering and answering in one
     commit -- fails.
  2. The label is computed, not typed. Every stored decision is recomputed
     from the stored interval with stage5_eval's own rules.
  3. The budget holds. No more candidates reach confirmation than budget_m,
     and every confirmatory interval is at the level that budget implies.

The rest is the evaluation machinery itself, checked over synthetic inputs:
walk-forward never trains on the week it predicts, the forward holdout is
refused, the paired bootstrap points the right way, the moneyline conversion
is symmetric, the three quarterback specs mean what stage5_data says, and the
Kalman ratings for a week do not see that week's games.

Run with: pytest tests/test_stage5_registry.py -v
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / 'src'))

import stage5_eval as se  # noqa: E402
import stage5_data as sd  # noqa: E402
from kalman_ratings import KalmanRatings  # noqa: E402

REGISTRY = REPO_ROOT / 'experiments' / 'stage5' / 'registry.json'
RESULTS = REPO_ROOT / 'experiments' / 'stage5' / 'results'


def registry():
    return json.loads(REGISTRY.read_text(encoding='utf-8'))


def results():
    return {p.stem: json.loads(p.read_text(encoding='utf-8')) for p in sorted(RESULTS.glob('*.json'))}


def git(*args):
    return subprocess.run(['git', '-C', str(REPO_ROOT), *args], capture_output=True, text=True)


# ------------------------------------------------------------ the registry

def test_the_registry_is_there_and_has_questions():
    r = registry()
    assert r['family'] == 'stage5'
    assert len(r['hypotheses']) >= 5, "vacuity: a registry with no questions passes every rule below"


def test_ids_are_unique_and_kinds_known():
    ids = [h['id'] for h in registry()['hypotheses']]
    assert len(ids) == len(set(ids)), ids
    for h in registry()['hypotheses']:
        assert h['kind'] in ('measurement', 'hypothesis', 'deferred'), h['id']
        if h['kind'] == 'deferred':
            assert h.get('reason'), f"{h['id']} is deferred without saying why"


def test_the_seasons_do_not_overlap_and_the_holdout_is_last():
    p = registry()['protocol']
    val, conf = set(p['validation_seasons']), set(p['confirmation_seasons'])
    assert not val & conf
    assert p['forward_holdout_season'] > max(val | conf)


def test_the_budget_covers_every_question_that_could_spend_a_slot():
    r = registry()
    could_spend = [h['id'] for h in r['hypotheses']
                   if h['kind'] == 'hypothesis' and h.get('spends_slot') is not False]
    assert len(could_spend) <= r['protocol']['budget_m'], (
        f"{len(could_spend)} questions could reach confirmation against a budget of "
        f"{r['protocol']['budget_m']}: {could_spend}"
    )


def test_the_confirmatory_level_is_bonferroni_over_the_budget():
    r = registry()
    assert se.confirmatory_level(r) == pytest.approx(1 - 0.05 / 10)


# --------------------------------------------------------------- results

def test_every_result_answers_a_registered_question_as_worded_now():
    reg = {h['id']: h for h in registry()['hypotheses']}
    for hid, res in results().items():
        assert hid in reg, f"result {hid} answers a question the registry does not ask"
        assert res['registry_entry'] == reg[hid], (
            f"{hid}: the registry entry changed after the result was recorded. A question "
            "is not edited once answered; register a new one."
        )


def recompute(res):
    if res['id'] == 'Q0':
        return 'CONFIRMED FINDING' if res['model_a']['log_loss_ci'][1] < 0 else 'NO MEASURABLE GAP'
    return se.decide(res['validation'], res['confirmation'])


def test_every_stored_decision_is_the_one_its_numbers_give():
    for hid, res in results().items():
        assert res['decision'] == recompute(res), f"{hid}: stored {res['decision']!r}"


def test_the_budget_is_not_overspent_and_intervals_use_its_level():
    r = registry()
    level = se.confirmatory_level(r)
    spent = [hid for hid, res in results().items() if res.get('reached_confirmation')]
    assert len(spent) <= r['protocol']['budget_m'], spent
    for hid in spent:
        assert results()[hid]['confirmation']['ci_level'] == pytest.approx(level), hid
        assert results()[hid]['confirmation']['seasons'] == r['protocol']['confirmation_seasons']


def test_no_result_touches_the_forward_holdout():
    holdout = registry()['protocol']['forward_holdout_season']
    for hid, res in results().items():
        for part in ('validation', 'confirmation', 'model_a', 'model_b'):
            block = res.get(part)
            if block:
                assert max(block['seasons']) < holdout, (hid, part)


def _shallow():
    return git('rev-parse', '--is-shallow-repository').stdout.strip() == 'true'


@pytest.mark.skipif(_shallow(), reason="needs full history to see when a result was first committed")
def test_every_committed_result_was_registered_in_an_earlier_commit():
    for path in sorted(RESULTS.glob('*.json')):
        rel = path.relative_to(REPO_ROOT).as_posix()
        added = git('log', '--diff-filter=A', '--format=%H', '--', rel).stdout.split()
        if not added:
            continue  # not committed yet; the check applies from the first commit
        first = added[-1]
        parent_registry = git('show', f'{first}^:experiments/stage5/registry.json')
        assert parent_registry.returncode == 0, (
            f"{rel} was committed in {first[:7]}, whose parent has no registry at all"
        )
        entries = {h['id']: h for h in json.loads(parent_registry.stdout)['hypotheses']}
        hid = path.stem
        assert hid in entries, f"{hid} was answered in {first[:7]} without being registered before it"
        stored = json.loads(path.read_text(encoding='utf-8'))['registry_entry']
        assert entries[hid] == stored, f"{hid}'s wording changed between registration and answer"


# ------------------------------------------------------------ evaluation

def test_the_forward_holdout_is_refused():
    with pytest.raises(se.ForwardHoldoutError):
        se.guard_seasons([2025, 2026], registry())
    se.guard_seasons([2024, 2025], registry())


@pytest.mark.parametrize('lo, hi, label', [
    (-0.02, -0.001, 'ACCEPT'), (0.001, 0.02, 'REJECT'), (-0.01, 0.01, 'INCONCLUSIVE'),
    (-0.01, 0.0, 'INCONCLUSIVE'),
])
def test_labels(lo, hi, label):
    assert se.label_from_interval(lo, hi) == label


def test_a_candidate_that_fails_the_screen_is_not_advanced():
    assert se.decide({'log_loss_diff': 0.001}, None) == 'NOT ADVANCED'
    assert se.decide({'log_loss_diff': 0.0}, None) == 'NOT ADVANCED'
    with pytest.raises(ValueError):
        se.decide({'log_loss_diff': -0.001}, None)
    assert se.decide({'log_loss_diff': -0.001}, {'log_loss_ci': [-0.01, -0.002]}) == 'ACCEPT'


def synthetic_games(n_seasons=4, weeks=6, per_week=8, seed=0):
    rng = np.random.default_rng(seed)
    rows = []
    for s in range(2020, 2020 + n_seasons):
        for w in range(1, weeks + 1):
            for k in range(per_week):
                x = rng.normal()
                rows.append({'game_id': f'{s}_{w}_{k}', 'season': s, 'week': w, 'x': x,
                             'noise': rng.normal(), 'home_win': int(rng.random() < 1 / (1 + np.exp(-2 * x)))})
    return pd.DataFrame(rows)


def test_walk_forward_never_trains_on_the_week_it_predicts(monkeypatch):
    games = synthetic_games()
    seen = []
    real_fit = se.LogisticRegression.fit

    def spy(self, X, y, *a, **k):
        seen.append(len(y))
        return real_fit(self, X, y, *a, **k)

    monkeypatch.setattr(se.LogisticRegression, 'fit', spy)
    se.walk_forward(games, {'a': ['x']}, [2022])
    before = [len(games[(games.season < 2022) | ((games.season == 2022) & (games.week < w))])
              for w in range(1, 7)]
    assert seen == before


def test_walk_forward_scores_both_sides_on_the_same_games():
    games = synthetic_games()
    games.loc[games.index[::7], 'noise'] = np.nan
    ids, y, probs = se.walk_forward(games, {'a': ['x'], 'b': ['noise']}, [2022, 2023])
    assert len(ids) == len(set(ids)) == len(y) == len(probs['a']) == len(probs['b'])
    assert not games.set_index('game_id').loc[ids, 'noise'].isna().any()


def test_the_bootstrap_points_the_right_way():
    games = synthetic_games(seed=1)
    ids, y, probs = se.walk_forward(games, {'good': ['x'], 'bad': ['noise']}, [2022, 2023])
    res = se.compare(y, probs['good'], probs['bad'], 0.995, 2000, 7)
    assert res['log_loss_diff'] < 0
    assert se.label_from_interval(*res['log_loss_ci']) == 'ACCEPT'
    lo, hi = res['log_loss_ci_analytic_95']
    blo, bhi = res['log_loss_ci_95']
    assert abs(lo - blo) < 0.01 and abs(hi - bhi) < 0.01, "bootstrap and closed form disagree"
    same = se.compare(y, probs['good'], probs['good'], 0.995, 500, 7)
    assert same['log_loss_ci'] == [0.0, 0.0]


@pytest.mark.parametrize('home, away, sign', [(-110, -110, 0), (-200, 170, 1), (170, -200, -1)])
def test_moneyline_logit(home, away, sign):
    v = sd.moneyline_logit(np.array([home]), np.array([away]))[0]
    assert np.sign(round(v, 9)) == sign
    mirror = sd.moneyline_logit(np.array([away]), np.array([home]))[0]
    assert v == pytest.approx(-mirror)


def test_moneyline_devig_by_hand():
    """-200 / +170: implied 2/3 and 100/270; normalised, the favourite is 0.6429.

    Symmetry alone cannot catch a conversion that is wrong the same way on
    both sides -- a first version of this file had only the symmetry test,
    and a mutation that broke the underdog formula survived it.
    """
    ph, pa = sd.implied(np.array([-200.0, 170.0]))
    assert ph == pytest.approx(2 / 3) and pa == pytest.approx(100 / 270)
    p = (2 / 3) / (2 / 3 + 100 / 270)
    v = sd.moneyline_logit(np.array([-200.0]), np.array([170.0]))[0]
    assert v == pytest.approx(np.log(p / (1 - p)))


class FakeQB(dict):
    """identify_starters for a hand-written season: team T's starters by week."""

    def __init__(self, starters):
        rows = [{'season': s, 'week': w, 'posteam': t, 'passer_player_id': pid, 'passer_player_name': pid, 'n': 30}
                for (s, w, t), pid in starters.items()]
        df = pd.DataFrame(rows)
        super().__init__(identify_starters=lambda season, week=None: (
            df[(df.season == season) & ((df.week == week) if week is not None else True)].copy()))


def test_the_three_quarterback_specs_mean_what_they_say():
    # Team T: A starts weeks 1-2, B finishes week 2 with the most dropbacks
    # (A hurt early), B starts week 3. The schedule records A as week 2's starter.
    sched = pd.DataFrame([
        {'game_id': f'g{w}', 'season': 2021, 'week': w, 'home_team': 'T', 'away_team': f'O{w}',
         'home_qb_id': qb, 'away_qb_id': f'o{w}'}
        for w, qb in [(1, 'A'), (2, 'A'), (3, 'B'), (4, 'B')]
    ])
    most = {(2021, 1, 'T'): 'A', (2021, 2, 'T'): 'B', (2021, 3, 'T'): 'B', (2021, 4, 'T'): 'B'}
    most.update({(2021, w, f'O{w}'): f'o{w}' for w in range(1, 5)})
    st = sd.starter_table(FakeQB(most), sched)
    t = st[st.team == 'T'].set_index('week')
    assert list(t['oracle_qb']) == ['A', 'B', 'B', 'B']
    assert list(t['oracle_changed']) == [0, 1, 0, 0]      # "new starter THIS game", knowing the box score
    assert list(t['sched_changed']) == [0, 0, 1, 0]       # the announced starter changed in week 3
    assert list(t['lagged_qb'].fillna('-')) == ['-', 'A', 'B', 'B']
    assert list(t['lagged_changed']) == [0, 0, 1, 0]      # live flags week 2's change in week 3


def test_kalman_ratings_for_a_week_do_not_see_that_week():
    teams = ['A', 'B']
    obs = pd.DataFrame([
        {'gwidx': 0, 'posteam': 'A', 'defteam': 'B', 'mean': 0.3, 'count': 60},
        {'gwidx': 0, 'posteam': 'B', 'defteam': 'A', 'mean': -0.2, 'count': 60},
        {'gwidx': 1, 'posteam': 'A', 'defteam': 'B', 'mean': 0.3, 'count': 60},
        {'gwidx': 1, 'posteam': 'B', 'defteam': 'A', 'mean': -0.2, 'count': 60},
    ])
    week_keys = [(2020, 1), (2020, 2), (2020, 3)]
    params = (1e-3, 1e-3, 0.5, 0.05)
    kr = KalmanRatings(teams, sigma2=1.9)
    _, before = kr.run(obs, week_keys, params)
    changed = obs.copy()
    changed.loc[changed.gwidx == 1, 'mean'] = [5.0, -5.0]
    _, after = kr.run(changed, week_keys, params)
    assert before[(2020, 2)] == after[(2020, 2)], "week 2's rating moved when week 2's games changed"
    assert before[(2020, 3)] != after[(2020, 3)]
    assert before[(2020, 2)]['A'][0] > before[(2020, 2)]['B'][0], "the better offence should rate higher"


def test_fit_ratings_is_the_production_fit_when_nothing_is_changed():
    from ratings_engine import build_team_ratings
    rng = np.random.default_rng(3)
    teams = ['A', 'B', 'C', 'D']
    rows = []
    for gw in range(6):
        for _ in range(120):
            o, d = rng.choice(teams, 2, replace=False)
            rows.append({'posteam': o, 'defteam': d, 'gwidx': gw, 'epa': rng.normal(0.1 * teams.index(o), 1)})
    plays = pd.DataFrame(rows)
    week_keys = [(2020, w) for w in range(1, 7)]
    prod = build_team_ratings(plays, week_keys)
    mine = sd.fit_ratings(plays, week_keys, plays['epa'].values)
    assert prod.keys() == mine.keys() and len(prod) >= 3
    for k in prod:
        for t in teams:
            assert prod[k][t] == pytest.approx(mine[k][t], abs=1e-12)
