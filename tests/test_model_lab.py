"""The Model Lab's records, held to where they came from (Stage 18).

src/model_lab.py builds one list from two sources: the 46 rows the page
carried before Stage 18, moved into experiments/legacy/rows.json once and
verbatim, and every pre-registered answer in experiments/*/results/. These
tests check the move lost nothing, that every entry carries one of the
project's five decisions, and that every figure a result entry carries is
the one in its file.

Run with: pytest tests/test_model_lab.py -v
"""
import hashlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

import model_lab as ml  # noqa: E402

FIVE = {'ACCEPT', 'REJECT', 'INCONCLUSIVE', 'DEFERRED', 'CONFIRMED FINDING'}


@pytest.fixture(scope='module')
def entries():
    return ml.entries()


#: sha256 of the moved rows' experiment, result and label, as moved in on
#: 2026-09-27 (PR #141, checked then against the template they came from).
#: They were moved once and are not edited: a change here is a change to the
#: published record, and has to be made on purpose, with this figure.
MOVED_ROWS_SHA256 = 'b910e3cdb3411c9d824671387d2452ff87ef1156be5abcc79acd3c3cb91664e4'


def test_the_moved_rows_are_as_they_were_moved():
    rows = json.loads(ml.LEGACY.read_text(encoding='utf-8'))['rows']
    blob = json.dumps([[r['experiment'], r['result'], r['label']] for r in rows], ensure_ascii=False)
    assert len(rows) == 46
    assert hashlib.sha256(blob.encode('utf-8')).hexdigest() == MOVED_ROWS_SHA256, (
        'a moved Model Lab row has been edited. They were moved in verbatim once; if the '
        'edit is deliberate, say why in the commit and update MOVED_ROWS_SHA256')


def test_every_entry_carries_one_of_the_five_decisions(entries):
    assert {e['decision'] for e in entries} <= FIVE
    assert all(e['label'] for e in entries), 'the first label is kept beside the decision'


# The mapping is a judgement, so it is written out here where a change to it
# shows up in review, rather than trusted.
LEGACY_MAPPING = {
    'REMOVED (was live)': 'REJECT',
    'LEAKAGE -- INVALIDATED': 'DEFERRED',
    'DIAGNOSED': 'INCONCLUSIVE',
    'NO PATTERN': 'INCONCLUSIVE',
    'NOT A NEW FINDING': 'INCONCLUSIVE',
    'REJECT &mdash; NO ATS EDGE': 'REJECT',
}


def test_each_moved_label_maps_to_its_decision():
    for r in json.loads(ml.LEGACY.read_text(encoding='utf-8'))['rows']:
        expected = r['label'] if r['label'] in FIVE else LEGACY_MAPPING[r['label']]
        assert r['decision'] == expected, (r['id'], r['label'], r['decision'])


def test_leakage_is_a_flag_on_exactly_the_invalidated_row():
    rows = json.loads(ml.LEGACY.read_text(encoding='utf-8'))['rows']
    assert [r['id'] for r in rows if r['leakage']] == [r['id'] for r in rows if 'LEAKAGE' in r['label']]
    assert sum(r['leakage'] for r in rows) == 1


def test_a_registered_label_maps_as_the_rule_says():
    assert ml.RESULT_DECISION['NOT ADVANCED'] == 'REJECT'
    assert ml.RESULT_DECISION['FAIL'] == 'REJECT'
    assert ml.RESULT_DECISION['NO MEASURABLE GAP'] == 'INCONCLUSIVE', (
        'an interval containing zero is not a confirmed finding under the project rule')


def test_every_result_file_is_an_entry_once_and_nothing_unasked_is(entries):
    files = sorted(p.relative_to(ROOT).as_posix() for p in ROOT.glob('experiments/stage*/results/*.json'))
    sourced = sorted(e['source'] for e in entries if e['source'].split('/')[-2] == 'results')
    assert sourced == files
    ids = {e['id'] for e in entries if e['stage']}
    for not_asked in ('H11', 'N2', 'N3', 'A1', 'R2', 'A2'):
        assert not_asked not in ids, f'{not_asked} was never run; it has no decision to show'


def test_every_deferred_registry_entry_is_shown_with_its_reason(entries):
    for registry in ROOT.glob('experiments/stage*/registry.json'):
        for h in json.loads(registry.read_text(encoding='utf-8'))['hypotheses']:
            if h.get('status') == 'DEFERRED':
                e = next(x for x in entries if x['id'] == h['id'])
                assert e['decision'] == 'DEFERRED' and e['reason'] == h['reason']


def test_every_headline_figure_is_the_one_in_its_file(entries):
    checked = 0
    for e in entries:
        h = e['headline']
        if not h:
            continue
        r = json.loads((ROOT / e['source']).read_text(encoding='utf-8'))
        if h['step'] == 'screen' and 'persistence' in r:
            block = r['persistence']
            assert (h['diff'], h['ci'], h['ci_level'], h['n']) == (
                block['weighted_corr'], block['corr_ci_95'], 0.95, block['n_referees'])
        elif h['step'] == 'screen':
            block = r['candidate_minus_control']
            assert (h['diff'], h['ci'], h['ci_level']) == (block['mse_diff'], block['mse_ci_95'], 0.95)
        elif h['step'] == 'measurement':
            block = r['model_a']
            assert (h['diff'], h['ci'], h['ci_level']) == (block['log_loss_diff'], block['log_loss_ci'],
                                                           block['ci_level'])
        else:
            assert h['step'] == ('confirmation' if r.get('confirmation') else 'validation')
            block = r[h['step']]
            assert (h['diff'], h['ci'], h['ci_level'], h['n']) == (
                block['log_loss_diff'], block['log_loss_ci'], block['ci_level'], block['n_games'])
        checked += 1
    assert checked >= 11, 'the check ran over fewer result files than exist'


def test_a_question_that_reached_confirmation_is_reported_from_confirmation(entries):
    h1 = next(e for e in entries if e['id'] == 'H1')['headline']
    assert h1['step'] == 'confirmation' and h1['ci_level'] == 0.995
    h2 = next(e for e in entries if e['id'] == 'H2')['headline']
    assert h2['step'] == 'validation' and h2['ci_level'] == 0.95


def test_an_unmapped_label_is_an_error_not_a_guess(tmp_path):
    stage = tmp_path / 'stage9'
    (stage / 'results').mkdir(parents=True)
    (stage / 'registry.json').write_text(json.dumps({'hypotheses': [{'id': 'Z1', 'title': 'z'}]}))
    (stage / 'results' / 'Z1.json').write_text(json.dumps({'decision': 'PROMISING', 'validation': {}}))
    with pytest.raises(ValueError, match='PROMISING'):
        ml.result_entries(tmp_path)


def test_newest_stage_first_then_the_moved_rows_in_page_order(entries):
    stages = [e['stage'] for e in entries]
    first_legacy = stages.index(None)
    assert all(s is None for s in stages[first_legacy:])
    numbered = [int(s.split()[-1]) for s in stages[:first_legacy]]
    assert numbered == sorted(numbered, reverse=True)
    assert [e['id'] for e in entries[first_legacy:]] == [f'L{i:02d}' for i in range(1, 47)]
