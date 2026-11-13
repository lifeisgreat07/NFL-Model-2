"""
Stage 85 item 2 (the 2026-11-02 review): like-for-like baselines.

An NBA pick made without the injury report ran Model A without the
availability term, so the drift check holds it to that model's backtest
(`drift.amended_2026_11_05` in experiments/nba/stage65/registry.json). Every
NHL pick carries both goalies (a projected starter, or the last starter when
none is projected), so the NHL's one baseline is already like for like. The
NFL's live log loss is printed by model version beside the backtest each
version is like, for information; Stage 33 R4's flag is unchanged.

Run with: pytest tests/test_like_for_like.py -v
"""
import json
import shutil
from pathlib import Path

import pandas as pd
import pytest

from src.sports.nba import daily as nba_daily
from src.sports.nba import drift
from src.sports.nfl import check_drift
from tests.optional import in_ci
from tests.test_drift_looks import function_source, page, run

ROOT = Path(__file__).resolve().parents[1]
NODE = shutil.which('node')
REGISTRY = ROOT / 'experiments' / 'nba' / 'stage65' / 'registry.json'


def spec():
    return drift.baseline()


# --- the NBA's baselines ---------------------------------------------------------

def test_the_no_availability_baseline_is_stage61s_model_without_availability():
    conf = json.loads((ROOT / 'experiments/nba/stage61/results/confirmation.json').read_text(encoding='utf-8'))
    s = spec()
    assert s['baseline']['value'] == conf['scores']['model_a']['log_loss']
    assert s['baseline_no_availability']['value'] == conf['scores']['model_a_no_availability']['log_loss']
    assert conf['scores']['model_a_no_availability']['games'] == 2643
    assert '(2643 games)' in s['baseline_no_availability']['source']


def test_the_amendment_is_registered_and_disclosed_as_written_after_results():
    reg = json.loads(REGISTRY.read_text(encoding='utf-8'))
    text = reg['drift']['amended_2026_11_05']
    assert 'availability.read false' in text and '0.6103' in text and '0.5983' in text
    # Found by what it is, not by being last: a later amendment (Stage 94's disclosures) follows it.
    entry = next(a for a in reg['amendments'] if a['entry'] == 'drift' and a['date'] == '2026-11-05')
    assert entry['before_any_result'] is False
    assert '15 of them without the injury report' in entry['seen']


def test_each_pick_is_held_to_the_backtest_of_the_model_it_ran():
    s = spec()
    assert drift.pick_baselines([True, False, True], s) == [
        s['baseline']['value'], s['baseline_no_availability']['value'], s['baseline']['value']]


def test_a_look_is_held_to_the_mean_of_its_own_picks_baselines():
    s = spec()
    bases = drift.pick_baselines([False] * 20 + [True] * 180, s)
    # Stage 95 item 31: each pick's model's figure over a season's first 100 games.
    with_it, without = s['baseline_by_look']['100'], s['baseline_no_availability_by_look']['100']
    assert drift.look_baseline(s, bases, 100) == pytest.approx((20 * without + 80 * with_it) / 100)
    assert drift.look_baseline(s, None, 100) == with_it
    looks = drift.looks([0.6] * 200, s, bases)
    assert [look['baseline'] for look in looks] == [drift.look_baseline(s, bases, 100),
                                                     drift.look_baseline(s, bases, 200)]


def test_picks_without_the_report_at_their_own_backtest_do_not_flag():
    """At the no-availability backtest's log loss, held to Model A's with
    availability, the check flags on the missing report rather than on
    drift; held to their own baseline it does not."""
    s = spec()
    # Stage 95 item 31: one look, at 100 picks, at the no-availability backtest's figure for a
    # season's first 100 games, which sits above Model A's with availability.
    with_it, without = s['baseline_by_look']['100'], s['baseline_no_availability_by_look']['100']
    losses = [without - 0.02, without + 0.02] * 50
    bound = drift.lower_bound(losses, s['rule'], s['rule']['per_look_level'])
    assert with_it < bound < without, 'the premise: the bound falls between the two models\' figures'
    bases = drift.pick_baselines([False] * 100, s)
    assert drift.flags(losses, s) is True
    assert drift.flags(losses, s, bases) is False
    # And picks made with the report are held where they were.
    assert drift.flags(losses, s, drift.pick_baselines([True] * 100, s)) is True


def test_a_game_without_a_result_takes_its_baseline_with_it():
    s = spec()
    rows = [(0.7, 1, False), (None, 1, True), (0.4, None, True), (0.6, 0, True)]
    losses, bases = drift.per_game(rows, s)
    assert len(losses) == len(bases) == 2
    assert bases == drift.pick_baselines([False, True], s)


def test_the_daily_reads_whether_each_pick_had_the_report(tmp_path):
    picks = (('1', '2026-10-12T23:00:00Z', 0.7, {'read': False, 'note': 'injury report not read'}),
             ('2', '2026-10-10T23:00:00Z', 0.4, {'availability_matchup': 0.1}),
             ('3', '2026-10-11T23:00:00Z', 0.6, None))
    for gid, start, p, avail in picks:
        (tmp_path / f'{gid}.json').write_text(json.dumps({'game_id': gid, 'pick': 'X', 'model_a': p,
                                                          'start_utc': start, 'availability': avail}))
    sched = pd.DataFrame([{'game_id': g, 'status': 'final', 'home_win': w} for g, w in (('1', 1), ('2', 0), ('3', 1))])
    assert nba_daily.drift_picks(tmp_path, sched) == [(0.4, 0, True), (0.6, 1, True), (0.7, 1, False)]
    assert nba_daily.drift_rows(tmp_path, sched) == [(0.4, 0), (0.6, 1), (0.7, 1)]


def test_the_daily_run_writes_its_own_baselines():
    src = (ROOT / 'src' / 'sports' / 'nba' / 'daily.py').read_text(encoding='utf-8')
    assert 'picks = drift_picks(folder, sched)\n        losses, bases = drift.per_game(picks, spec)' in src.replace('\r\n', '\n')
    # Stage 95 item 32: with each pick's day, for the bootstrap.
    assert 'flagged = drift.flags(losses, spec, bases, days)' in src
    assert "'looks': drift.looks(losses, spec, bases, days)" in src


# --- on the pages ----------------------------------------------------------------

@pytest.mark.skipif(NODE is None and not in_ci(), reason='node not installed')
def test_the_nba_page_names_both_baselines_and_how_many_picks_are_held_to_the_second():
    rule = spec()
    looks = run('nba', f'driftLooks({json.dumps(rule)})')
    # Stage 95 item 31: both models' figures, look by look.
    a, na = rule['baseline_by_look'], rule['baseline_no_availability_by_look']
    assert f"pooled (100, {a['100']:.4f}; 200, {a['200']:.4f};" in looks
    assert f"against the model without it: 100, {na['100']:.4f}; 200, {na['200']:.4f};" in looks
    d = {'games': 107, 'mean_log_loss': 0.6251, 'baseline': 0.6000, 'without_availability': 15,
         'flagged': False, 'looks': [{'games': 100, 'lower_bound': 0.5502, 'flagged': False}], 'next_look': 200}
    out = run('nba', f'driftStatus({json.dumps(d)}, {json.dumps(rule)})')
    assert ('against 0.6000 in the backtest for the same picks, 15 of which were made without the injury '
            'report and are held to the backtest without it.') in out


@pytest.mark.skipif(NODE is None and not in_ci(), reason='node not installed')
def test_the_nhl_page_keeps_its_one_baseline():
    rule = json.loads((ROOT / 'data' / 'nhl' / 'drift_baseline.json').read_text(encoding='utf-8'))
    assert 'baseline_no_availability' not in rule
    looks = run('nhl', f'driftLooks({json.dumps(rule)})')
    # Stage 95 item 31: one model, its figure look by look.
    assert "above the backtest&#39;s log loss over a season&#39;s first that many games" in looks
    assert f"(100, {rule['baseline_by_look']['100']:.4f}; 200, {rule['baseline_by_look']['200']:.4f};" in looks
    assert 'without the injury report' not in looks
    d = {'games': 194, 'mean_log_loss': 0.6561, 'baseline': 0.6753, 'flagged': False, 'looks': [], 'next_look': 200}
    assert 'against 0.6753 in the backtest.' in run('nhl', f'driftStatus({json.dumps(d)}, {json.dumps(rule)})')


def test_both_pages_still_carry_the_same_functions():
    for name in ('driftStatus', 'driftLooks'):
        assert function_source(page('nhl'), name) == function_source(page('nba'), name), name


# --- the NHL ---------------------------------------------------------------------

def test_every_saved_nhl_pick_carries_both_goalies():
    """The NHL has no pick made without its goalie term, so no second baseline."""
    folder = ROOT / 'predictions' / 'nhl'
    paths = sorted(folder.glob('*/*.json'))
    assert paths
    for path in paths:
        goalies = json.loads(path.read_text(encoding='utf-8'))['goalies']
        assert set(goalies) == {'home', 'away'}, path.name
        assert all(goalies[side]['basis'] in ('projected', 'last_start') for side in goalies), path.name


# --- the NFL, by model version ----------------------------------------------------

def nfl_spec():
    return check_drift.log_loss_baseline()


def rec(version, p, y):
    return {'model_version': version, 'model_a_home_win_prob': p, 'actual_home_win': y}


def test_each_nfl_version_is_beside_the_backtest_it_is_like():
    s = nfl_spec()
    records = [rec('2.4', 0.6, 1), rec('2.4', 0.6, 0), rec('2.5', 0.7, 1), rec('2.6', 0.8, 1), rec('2.10', 0.5, 1)]
    out = check_drift.by_version(records, s)
    assert list(out) == ['2.4', '2.5', '2.6', '2.10']
    assert out['2.4']['baseline'] == s['printed_beside']['value']
    assert out['2.5']['baseline'] == out['2.6']['baseline'] == out['2.10']['baseline'] == s['baseline']['value']
    assert out['2.4']['games'] == 2
    assert out['2.4']['log_loss'] == pytest.approx(sum(check_drift.per_game_log_loss(records[:2])) / 2)


def test_a_pick_with_no_version_is_listed_without_a_baseline():
    out = check_drift.by_version([rec(None, 0.6, 1), rec('2.6', 0.6, 1), rec('2.6', 0.6, None)], nfl_spec())
    assert list(out) == ['2.6', 'None'] and out['None']['baseline'] is None and out['2.6']['games'] == 1


def test_the_split_is_printed_and_the_flag_is_unchanged(caplog, monkeypatch):
    s = nfl_spec()
    records = [rec('2.4', 0.6, 1)] * 40
    monkeypatch.setattr(check_drift, 'load_live_results', lambda: records)
    caplog.set_level('INFO')
    assert check_drift.main() == (1 if check_drift.check_log_loss(records, s) else 0)
    text = caplog.text
    assert "log loss by model version" in text and 'v2.4: 0.5108 over 40 games, against 0.6643' in text
