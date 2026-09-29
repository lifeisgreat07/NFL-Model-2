"""A card whose game is over but not graded stops saying "to win"
(Stage 26 item 1, from the 2026-09-28 audit).

Between the final whistle and Tuesday's grading, the Week Board card still
read "Model B GB 68% to win". Now it reads "Model B picked GB 68% · ATL won":
what was picked and who won, in the headline's neutral grey. No right or
wrong -- that is the graded tag's, once grading runs -- and no "graded on
Tuesday", which Mark removed on 2026-09-28. cardProvisional() and
cardProbHtml() are run in node over each state.

Run with: pytest tests/test_final_ungraded_card.py -v
"""
import json

from test_card_v2 import ATL_GB, run, src

FINAL = dict(ATL_GB, status='final', away_score=35, home_score=14, graded=False)


def headline(g):
    html = run(f'cardProbHtml({json.dumps(g)}, "#a00", "#fb1")')
    return html[html.index('<div class="card-hl">'):html.index('</div>')]


def test_the_result_is_named_by_who_won():
    got = run('[' + ', '.join(f'cardProvisional({json.dumps(g)})' for g in (
        FINAL,
        dict(FINAL, away_score=14, home_score=35),
        dict(FINAL, away_score=20, home_score=20),
        dict(FINAL, away_score=0, home_score=3),
    )) + ']')
    assert got == ['ATL won', 'GB won', 'a tie', 'GB won']


def test_only_an_ungraded_final_with_both_scores_is_provisional():
    got = run('[' + ', '.join(f'cardProvisional({json.dumps(g)})' for g in (
        dict(FINAL, graded=True),
        dict(FINAL, status='started'),
        dict(FINAL, status='upcoming'),
        dict(FINAL, home_score=None),
        dict(ATL_GB),
    )) + ']')
    assert got == ['', '', '', '', '']


def test_an_ungraded_final_says_picked_and_the_result_not_to_win():
    h = headline(FINAL)
    assert 'to win' not in h
    assert '<span class="card-hl-label">Model B picked</span> <b>GB 68%</b>' in h
    assert '<span class="card-hl-to">&middot; ATL won</span>' in h


def test_the_result_is_neutral_text_not_a_verdict():
    h = headline(FINAL)
    for word in ('right', 'wrong', 'correct', 'Tuesday', 'graded'):
        assert word not in h, word
    assert 'class="card-hl-to"' in h, 'the result is not in the headline\'s neutral style'


def test_a_game_not_yet_over_still_says_to_win():
    for g in (dict(ATL_GB, graded=False), dict(FINAL, status='started'), dict(FINAL, graded=True)):
        h = headline(g)
        assert '<span class="card-hl-to">to win</span>' in h and 'picked' not in h


def test_too_close_to_call_gets_the_result_too():
    h = headline(dict(FINAL, mktB_home=50.8))
    assert '<b>Too close to call</b> <span class="card-hl-to">&middot; ATL won</span>' in h
    assert 'to win' not in h


def test_the_template_still_does_not_say_graded_on_tuesday():
    assert 'graded on Tuesday' not in src()
