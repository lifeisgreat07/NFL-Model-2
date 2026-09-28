"""
Every number experiments/stage6/README.md prints must exist in the file it
came from, the pattern tests/test_stage5_published_numbers.py set for
Stage 5.

The results table is parsed row by row: an answered question's cell must be
its result file's decision and figure; an unanswered one must say why, and
the reason must be true of the stored results. The narrative figures are
checked against N1.json.

Run with: pytest tests/test_stage6_published_numbers.py -v
"""
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent / 'experiments' / 'stage6'
README = ROOT / 'README.md'


def result(hid):
    path = ROOT / 'results' / f'{hid}.json'
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else None


def table_rows():
    rows = []
    for line in README.read_text(encoding='utf-8').splitlines():
        m = re.match(r'^\| ([NARP]\d+) \|(.*)\|\s*$', line)
        if m:
            rows.append((m.group(1), [c.strip() for c in m.group(2).split('|')]))
    return rows


def signed(x, places):
    return f'{x:+.{places}f}'.replace('-', '−')


def test_the_table_is_there():
    ids = [r[0] for r in table_rows()]
    assert ids == ['N1', 'N2', 'N3', 'A1', 'N4', 'R1', 'R2', 'A2', 'P1'], ids


@pytest.mark.parametrize('hid, cells', table_rows())
def test_each_row_matches_its_result_file(hid, cells):
    r = result(hid)
    if r is None:
        m = re.match(r'not run: ([NR]\d+) failed', cells[1])
        if m:
            assert result(m.group(1))['decision'] == 'FAIL', cells[1]
        elif cells[1].startswith('not checked: nothing was accepted'):
            guarded = {'A1': ('N2', 'N3'), 'A2': ('R2',)}[hid]
            assert not any((result(h) or {}).get('decision') == 'ACCEPT' for h in guarded)
        else:
            assert cells[1] == 'DEFERRED', (hid, cells)
            kinds = {h['id']: h['kind'] for h in
                     json.loads((ROOT / 'registry.json').read_text(encoding='utf-8'))['hypotheses']}
            assert kinds[hid] == 'deferred', f"{hid} is written up as DEFERRED but the registry asks it"
        return
    assert cells[1] == r['decision'], (hid, cells[1], r['decision'])
    if hid == 'N1':
        d = r['candidate_minus_control']
        lo, hi = d['mse_ci_95']
        assert cells[2] == (f"candidate minus control MSE {signed(d['mse_diff'], 5)} "
                            f"[{signed(lo, 5)}, {signed(hi, 5)}]"), cells[2]
    if hid == 'R1':
        d = r['persistence']
        lo, hi = d['corr_ci_95']
        assert cells[2] == (f"weighted correlation {signed(d['weighted_corr'], 2)} "
                            f"[{signed(lo, 2)}, {signed(hi, 2)}], {d['n_referees']} referees"), cells[2]


def test_the_referee_narrative_comes_from_r1():
    text = README.read_text(encoding='utf-8')
    r = result('R1')
    d = r['persistence']
    lo, hi = d['corr_ci_95']
    assert f"Over {r['inputs']['games_scored']:,}\nregular-season games" in text
    assert f"{d['n_referees']} referees had at least 40 games" in text
    assert f"is {signed(d['weighted_corr'], 2)}, and its 95% interval runs from {signed(lo, 2)} to {signed(hi, 2)}." \
        in text.replace('\n', ' ')
    assert f"flagged for {r['inputs']['mean_differential']:.1f} more penalty yards" in text


def test_the_narrative_figures_come_from_n1():
    text = README.read_text(encoding='utf-8')
    r = result('N1')
    assert f"Fitted on {r['fit']['n_qb_games']:,} quarterback games" in text
    assert f"scored on {r['validation']['n_qb_games']:,} from 2022" in text
    mse = r['validation']['mse']
    assert f"error {mse['candidate']:.5f} against\n{mse['control']:.5f} without them" in text
    assert f"(control minus base {signed(r['control_minus_base']['mse_diff'], 7)})" in text


def test_the_slot_sentence_is_the_files():
    text = README.read_text(encoding='utf-8')
    spent = [p.stem for p in (ROOT / 'results').glob('*.json')
             if json.loads(p.read_text(encoding='utf-8')).get('reached_confirmation')]
    words = {0: 'None', 1: 'One', 2: 'Two', 3: 'Three', 4: 'Four', 5: 'Five'}
    verb = 'were' if len(spent) != 1 else 'was'
    assert f"{words[len(spent)]} of\nStage 6's five slots {verb} spent" in text or \
           f"{words[len(spent)]} of Stage 6's five slots {verb} spent" in text, spent
