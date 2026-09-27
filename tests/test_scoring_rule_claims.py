"""Methodology's comparisons rest on log loss and Brier, not on accuracy.

Stage 14 (CLAUDE.md). The page's own methodology says accuracy cannot carry
a comparison at this sample size (it moved by a full game between platforms
on identical code), yet Methodology argued "Model B consistently outperforms
Model A (68.2% vs. 62.8% accuracy)" and "On raw predictive accuracy, this
model does not beat the Vegas betting market". Both now lead with log loss
and Brier and give the paired-bootstrap intervals Model Lab already records.

Every figure in those sentences is read here from the two places it comes
from -- the backtest table on the same page, and Model Lab's CONFIRMED
FINDING rows -- so a re-run that moves either cannot leave the prose behind.

Run with: pytest tests/test_scoring_rule_claims.py -v
"""
import html
import re
from pathlib import Path

import pytest
from page_source import page_source  # Model Lab's rows are rendered in at build time

TEMPLATE = Path(__file__).resolve().parents[1] / 'src' / 'dashboard_template.html'


def num(s):
    return float(html.unescape(s).replace('−', '-'))


@pytest.fixture(scope='module')
def src():
    return page_source()


@pytest.fixture(scope='module')
def table(src):
    """Backtest table rows: name -> (accuracy %, log loss, Brier)."""
    rows = {}
    for name, acc, ll, br in re.findall(
            r'<tr><td>([^<]+)</td><td[^>]*>([\d.]+)%</td><td[^>]*>([\d.]+)</td><td[^>]*>([\d.]+)</td>', src):
        rows[name.strip()] = (float(acc), float(ll), float(br))
    need = ('Model A -- live, 4 features, weekly refit', 'Model B -- live, 4 features + market, weekly refit',
            'Vegas market alone', 'Coin flip')
    for n in need:
        assert n in rows, f'the backtest table has no row {n!r} -- re-anchor this guard'
    return {'A': rows[need[0]], 'B': rows[need[1]], 'market': rows[need[2]], 'coin': rows[need[3]]}


def lab_interval(src, row_title, metric):
    row = re.search(rf'<tr><td>{re.escape(row_title)}</td><td>(.*?)</td>', src, re.S)
    assert row, f'Model Lab has no row {row_title!r} -- re-anchor this guard'
    m = re.search(rf'{metric} ((?:&minus;|\+)[\d.]+) CI \[((?:&minus;|\+)[\d.]+), ((?:&minus;|\+)[\d.]+)\]', row.group(1))
    assert m, f'no {metric} interval in {row_title!r}'
    return tuple(round(num(x), 3) for x in m.groups())


def test_b_versus_a_leads_with_log_loss_and_brier_from_the_table(src, table):
    claim = re.search(r'data-claim="b-vs-a"[^>]*>log loss ([\d.]+) against ([\d.]+), and Brier ([\d.]+) against ([\d.]+)</b>', src)
    assert claim, 'the Model B vs Model A sentence no longer leads with log loss and Brier'
    b_ll, a_ll, b_br, a_br = map(float, claim.groups())
    assert (b_ll, a_ll) == (table['B'][1], table['A'][1]), 'the log loss in the sentence is not the table\'s'
    assert (b_br, a_br) == (table['B'][2], table['A'][2]), 'the Brier in the sentence is not the table\'s'


def test_b_versus_a_intervals_are_model_labs(src):
    ll = lab_interval(src, 'Model B beats Model A on proper scoring rules (not just accuracy)', 'log loss')
    br = lab_interval(src, 'Model B beats Model A on proper scoring rules (not just accuracy)', 'Brier')
    text = ('(log loss &minus;%.3f, 95%% interval &minus;%.3f to &minus;%.3f; Brier &minus;%.3f, &minus;%.3f to &minus;%.3f)'
            % (-ll[0], -ll[1], -ll[2], -br[0], -br[1], -br[2]))
    assert text in src, f'the B vs A intervals in Methodology are not Model Lab\'s: expected {text}'


def test_a_versus_the_market_leads_with_log_loss(src, table):
    claim = re.search(r'data-claim="a-vs-market">Model A\'s log loss is ([\d.]+) against the market\'s ([\d.]+)</span>', src)
    assert claim, '"does not beat the market" no longer states the log loss'
    assert (float(claim.group(1)), float(claim.group(2))) == (table['A'][1], table['market'][1])
    ll = lab_interval(src, 'The market genuinely beats Model A (now with intervals)', 'log loss')
    assert f'the gap at +{ll[0]:.3f}, 95% interval +{ll[1]:.3f} to +{ll[2]:.3f}' in src, (
        "the A vs market interval in Methodology is not Model Lab's")


def test_the_standing_table_compares_on_scoring_rules(src, table):
    # "Model A", not "this project": Model B is level with the market (log loss
    # 0.606 against 0.607), so "behind on both" is true only of Model A.
    assert '<tr><td>Model A against the market (log loss, Brier)</td><td>Behind on both.' in src
    assert table['A'][1] > table['market'][1] and table['A'][2] > table['market'][2], (
        'the table no longer has Model A behind the market on both rules, so the row is wrong')
    m = re.search(r'Football-only, no market data</td><td>Reasonable -- log loss ([\d.]+) on held-out games against ([\d.]+) for a coin flip', src)
    assert m, 'the football-only row no longer leads with log loss'
    assert (float(m.group(1)), float(m.group(2))) == (table['A'][1], table['coin'][1])


def test_the_accuracy_led_phrasings_are_gone(src):
    for old in ('consistently outperforms', 'On raw predictive accuracy', 'Raw accuracy vs. market'):
        assert old not in src, f'an accuracy-led claim is back: {old!r}'
