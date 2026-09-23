"""
Every number experiments/stage5/README.md prints must exist in the file it
came from. Prose drifts; this is the pattern tests/test_published_bootstrap_numbers.py
set for the rest of the repository.

The results table is parsed row by row: its label must be the result file's
decision, and each difference must be that file's figure rounded to four
places. The narrative figures (262 games, 0.696, 0.664, rho 0.45 ...) are
checked against residuals.json and kalman_fit.json.

Run with: pytest tests/test_stage5_published_numbers.py -v
"""
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent / 'experiments' / 'stage5'
README = ROOT / 'README.md'


def load(name):
    return json.loads((ROOT / name).read_text(encoding='utf-8'))


def table_rows():
    rows = []
    for line in README.read_text(encoding='utf-8').splitlines():
        m = re.match(r'^\| (Q0|H\d+) \|(.*)\|\s*$', line)
        if m:
            rows.append((m.group(1), [c.strip() for c in m.group(2).split('|')]))
    return rows


def signed(x):
    return f'{x:+.4f}'.replace('+', '+').replace('-', '−')


def test_the_table_is_there():
    ids = [r[0] for r in table_rows()]
    assert len(ids) >= 10, ids


@pytest.mark.parametrize('hid, cells', table_rows())
def test_each_row_matches_its_result_file(hid, cells):
    path = ROOT / 'results' / f'{hid}.json'
    if not path.exists():
        assert cells[1] in ('DEFERRED', 'not run: nothing was accepted'), (hid, cells)
        return
    r = json.loads(path.read_text(encoding='utf-8'))
    assert cells[1] == r['decision'], (hid, cells[1], r['decision'])
    if hid == 'Q0':
        a = r['model_a']
        lo, hi = a['log_loss_ci']
        assert cells[3] == f"Model A {signed(a['log_loss_diff'])} [{signed(lo)}, {signed(hi)}]"
        return
    assert cells[2] == signed(r['validation']['log_loss_diff']), (hid, cells[2])
    if r['confirmation'] is None:
        assert cells[3] == '—'
    else:
        c = r['confirmation']
        lo, hi = c['log_loss_ci']
        assert cells[3] == f"{signed(c['log_loss_diff'])} [{signed(lo)}, {signed(hi)}]", (hid, cells[3])


def test_the_slot_count_is_the_files():
    text = README.read_text(encoding='utf-8')
    spent = sorted(p.stem for p in (ROOT / 'results').glob('*.json')
                   if json.loads(p.read_text(encoding='utf-8')).get('reached_confirmation'))
    words = {1: 'One', 2: 'Two', 3: 'Three', 4: 'Four', 5: 'Five', 6: 'Six'}
    assert f"{words[len(spent)]} of the ten confirmatory slots are spent" in text, spent


def test_the_narrative_figures_come_from_the_residuals_and_the_kalman_fit():
    text = README.read_text(encoding='utf-8')
    s = load('residuals.json')['slices']
    miss = s['lagged QB differs from announced starter (either side)']
    match = s['lagged QB matches announced starter (both sides)']
    allg = s['all games']
    assert f"In {miss['n_games']} of the {allg['n_games']:,} games" in text
    assert f"{miss['log_loss_lagged']:.3f}, against {miss['log_loss_sched']:.3f}" in text
    assert f"On the other {match['n_games']}" in text
    assert f"are {match['log_loss_lagged']:.3f} and {match['log_loss_sched']:.3f}" in text
    assert f"its log loss is {allg['log_loss_lagged']:.3f}, not {allg['log_loss_oracle']:.3f}" in text
    assert f"is {load('kalman_fit.json')['rho']:.2f}," in text
