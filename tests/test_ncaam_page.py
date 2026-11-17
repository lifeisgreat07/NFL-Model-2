"""The March Madness bracket page (Stage 103 item 4), from the 2025 dry run made into a lock.

Run with: pytest tests/test_ncaam_page.py -v
"""
import json
import re
from datetime import date
from itertools import combinations
from pathlib import Path

import pytest

from src.sports.ncaam import bracket, page

ROOT = Path(__file__).resolve().parents[1]
DRY = ROOT / 'data' / 'ncaam' / 'bracket' / 'dryrun_2025.json'


@pytest.fixture(scope='module')
def lock_doc():
    """The dry run as the lock would have saved it: every pair's forecast, when it was locked."""
    d = json.loads(DRY.read_text(encoding='utf-8'))
    p = bracket.pair_forecast(d['ratings'], d['curve'])
    pairs = {f'{a}|{b}': p(a, b) for a, b in combinations(sorted(d['ratings']), 2)}
    return dict(d, locked_utc='2025-03-17T22:00:00Z', games_through='2025-03-16', pairs=pairs)


@pytest.fixture(scope='module')
def conf():
    return json.loads(page.CONFIRMATION.read_text(encoding='utf-8'))


def body(doc, graded, conf):
    return page.Page(doc, graded).body(conf)


@pytest.mark.parametrize('day, want', [('2027-02-28', False), ('2027-03-01', True), ('2027-03-31', True),
                                       ('2027-04-15', True), ('2027-04-16', False), ('2027-11-17', False)])
def test_the_page_is_published_from_the_first_of_march_to_the_middle_of_april(day, want):
    assert page.shown(date.fromisoformat(day)) is want


@pytest.mark.parametrize('x, want', [(0.0001, '<1%'), (0.004, '<1%'), (0.006, '1%'), (0.499, '50%'),
                                     (0.994, '99%'), (0.996, '>99%')])
def test_a_chance_is_never_printed_as_none_or_certain(x, want):
    assert page.pct(x) == want


def test_no_lock_or_the_wrong_month_writes_no_page(tmp_path, monkeypatch):
    monkeypatch.setattr(bracket, 'OUT', tmp_path)
    out = tmp_path / 'site' / 'march' / 'index.html'
    assert page.main(['--out', str(out), '--today', '2027-03-20']) == 0
    assert not out.exists()
    (tmp_path / 'lock_2027.json').write_text('{}', encoding='utf-8')
    assert page.main(['--out', str(out), '--today', '2027-06-01']) == 0
    assert not out.exists()


def test_the_page_is_written_from_the_year_s_lock_in_its_weeks(tmp_path, monkeypatch, lock_doc):
    doc = dict(lock_doc, tournament=2027)
    (tmp_path / 'lock_2027.json').write_text(json.dumps(doc), encoding='utf-8')
    monkeypatch.setattr(bracket, 'OUT', tmp_path)
    monkeypatch.setattr(bracket, 'graded', lambda d: [])
    out = tmp_path / 'site' / 'march' / 'index.html'
    assert page.main(['--out', str(out), '--today', '2027-03-18']) == 0
    html = out.read_text(encoding='utf-8')
    assert 'March Madness 2027: the bracket' in html
    assert '__' not in re.sub(r'<script.*?</script>|<style.*?</style>', '', html, flags=re.S)


def test_the_verdicts_are_the_confirmation_s(lock_doc, conf):
    text = body(lock_doc, [], conf)
    q = conf['questions']
    assert f"({q['H1']['games']} games)" in text
    assert f"\"the higher seed wins\" by a margin too small to call: {q['H1']['label']}" in text
    assert f"Against the betting market: {q['H2']['label']}" in text
    assert 'the betting market beat the seeds' in text  # M1's interval is wholly below zero
    assert f"Model A {page.pct(q['M2']['model_a'])}" in text


def test_the_glance_names_the_filled_champion_and_its_title_odds(lock_doc, conf):
    text = body(lock_doc, [], conf)
    final = [g for g in lock_doc['filled'] if g['round'] == 'final'][0]
    champ = final['winner']
    glance = text.split('The filled bracket at a glance')[1].split('<h2>')[0]
    first = glance.split('ncaam-row')[1]
    assert lock_doc['names'][champ] in first and 'Champion, over' in first
    assert f"{page.pct(lock_doc['odds'][champ]['champion'])} title" in first
    assert glance.count('Into the final, over') == 2


def test_every_club_has_a_row_of_odds_best_title_odds_first(lock_doc, conf):
    text = body(lock_doc, [], conf)
    table = text.split("Every club's chance of reaching each round")[1].split('</tbody>')[0]
    rows = table.split('<tr>')[2:]
    assert len(rows) == 68
    best = max(lock_doc['odds'], key=lambda c: lock_doc['odds'][c]['champion'])
    assert lock_doc['names'][best] in rows[0]


def test_every_region_shows_its_four_rounds_and_the_final_four_its_three_games(lock_doc, conf):
    text = body(lock_doc, [], conf)
    bracket_part = text.split('<h2>The filled bracket</h2>')[1].split('<h2>')[0]
    assert bracket_part.count('class="ncaam-region"') == 5
    assert bracket_part.count('class="ncaam-game"') == 63  # the First Four's games are not drawn
    for name in lock_doc['field']['regions']:
        assert f'<h3>{name}</h3>' in bracket_part


def test_before_any_game_the_page_says_so_and_lists_no_games(lock_doc, conf):
    text = body(lock_doc, [], conf)
    assert 'No game has been played yet.' in text
    assert 'Games played' not in text
    assert 'ncaam-out' not in text


def test_a_played_game_is_graded_and_its_loser_struck_through(lock_doc, conf):
    graded = sorted(lock_doc['graded'], key=lambda g: g['day'])[:10]
    text = body(lock_doc, graded, conf)
    right = sum(g['favourite_won'] for g in graded)
    assert f'So far: 10 of 67 games played; the side the lock gave the better chance won {right} of them.' in text
    table = text.split('<h2>Games played</h2>')[1]
    assert table.count('>Correct<') == right and table.count('>Missed<') == 10 - right
    loser = graded[0]['home'] if graded[0]['winner'] == graded[0]['away'] else graded[0]['away']
    assert f'<span class="ncaam-out">{lock_doc["names"][loser]}</span>' in text


def test_the_winner_s_saved_chance_is_the_lock_s_pair(lock_doc, conf):
    g = sorted(lock_doc['graded'], key=lambda g: g['day'])[0]
    p = bracket.saved_forecast(lock_doc)
    loser = g['home'] if g['winner'] == g['away'] else g['away']
    text = body(lock_doc, [g], conf)
    row = text.split('<h2>Games played</h2>')[1]
    assert f'<td class="ncaam-num">{page.pct(p(g["winner"], loser))}</td>' in row


def test_club_names_are_escaped(lock_doc, conf):
    doc = dict(lock_doc, names=dict(lock_doc['names']))
    some = next(iter(doc['names']))
    doc['names'][some] = '<b>X&Y</b>'
    text = body(doc, [], conf)
    assert '<b>X&Y</b>' not in text and '&lt;b&gt;X&amp;Y&lt;/b&gt;' in text
