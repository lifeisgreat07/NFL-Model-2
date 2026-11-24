"""MLB's Season Accuracy and Checking the AI's work pages (Stage 100 item 2), before Opening Day.

Season Accuracy says nothing is graded and when picks start. Checking the AI's work says what was written down before
anything was fitted, and what the tests hold the committed files to; the first of those claims is held here, on the
committed tuning file itself: every registered setting searched once, on the validation seasons only, the lowest kept.

Run with: pytest tests/test_mlb_checking_page.py -v
"""
import itertools
import json
from pathlib import Path

from src.sports.mlb import backtest, site
from tests.js_source import function_source

ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / 'src' / 'sports' / 'mlb' / 'pages' / 'mlb.js').read_text(encoding='utf-8').replace('\r\n', '\n')
BODY = (ROOT / 'src' / 'sports' / 'mlb' / 'pages' / 'body.html').read_text(encoding='utf-8')


def test_the_committed_tuning_searched_every_registered_setting_on_the_validation_seasons_and_kept_the_lowest():
    reg = backtest.registry()
    grid = reg['models']['model_a']['grid']
    tuning = json.loads((backtest.RESULTS / 'tuning.json').read_text(encoding='utf-8'))
    want = sorted(itertools.product(grid['H_days'], grid['lambda'], grid['K_outs']))
    got = sorted((g['H_days'], g['lambda'], g['K_outs']) for g in tuning['grid'])
    assert got == want, 'the tuning file is not the registered grid, each setting once'
    assert tuning['seasons'] == reg['protocol']['validation_seasons']
    lowest = min(tuning['grid'], key=lambda g: g['log_loss'])
    assert {k: lowest[k] for k in ('H_days', 'lambda', 'K_outs')} == tuning['chosen']


def test_checking_says_what_the_tuning_test_holds_and_counts_the_amendments():
    fn = function_source(JS, 'renderReliability', at_line_start=True)
    assert 'the tuning searched every registered setting, on the validation seasons only, and kept the lowest' in fn
    assert site.lab()['amendments'] == len(backtest.registry()['amendments'])
    # The page said Booth "re-runs" the confirmation, which the code refuses to run twice (found before opening).
    assert 'it runs once: the code refuses to run it again' in fn and 're-runs' not in fn
    source = Path(backtest.__file__).read_text(encoding='utf-8')
    assert 'the confirmation is run once and never rewritten' in source, 'the page says a refusal the code lost'


def test_accuracy_says_nothing_is_graded_until_opening_day():
    fn = function_source(JS, 'renderAccuracy', at_line_start=True)
    assert "'Nothing graded yet'" in fn and 'OPENING_DAY' in fn


def test_both_pages_have_their_buttons_and_accuracy_is_a_phone_tab():
    for page in ('accuracy', 'reliability'):
        assert BODY.count(f'data-page="{page}"') == 2 and f'id="page-{page}"' in BODY
    assert '<button class="bnav-btn" data-page="accuracy">' in BODY
