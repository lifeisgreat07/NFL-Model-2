"""The NHL's day-board rows keep a game's score on a phone, as the NBA's do (audit 9, finding D12).

At 375 px the NHL's game cell was narrower than a final game's text and cut it with an ellipsis, losing the home
score. The rendered proof is `tests/browser/check_row_cut.py`, which the Browser checks workflow runs on the NHL's
and the NBA's pages; these hold the rules it rests on.

Run with: pytest tests/test_nhl_row_wrap.py -v
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGES = ROOT / 'src' / 'sports'
WORKFLOW = (ROOT / '.github' / 'workflows' / 'browser-checks.yml').read_text(encoding='utf-8')


def phone_rules(sport):
    css = (PAGES / sport / 'pages' / f'{sport}.css').read_text(encoding='utf-8')
    blocks = re.findall(r'@media \(max-width:600px\)\{(.*?)\n\}', css, re.S)
    return ''.join(b for b in blocks if f'.{sport}-row-game' in b)


def test_a_team_and_its_score_never_split():
    js = (PAGES / 'nhl' / 'pages' / 'nhl.js').read_text(encoding='utf-8')
    assert 'return `<span class="nhl-row-team">${abbr === won ? `<b>${text}</b>` : text}</span>`;' in js
    css = (PAGES / 'nhl' / 'pages' / 'nhl.css').read_text(encoding='utf-8')
    assert '.nhl-row-team{white-space:nowrap;}' in css


def test_on_a_phone_the_game_wraps_and_the_result_column_grows_on_both_sports():
    for sport in ('nhl', 'nba'):
        rules = phone_rules(sport)
        assert f'.{sport}-row-game{{white-space:normal; overflow:visible;}}' in rules, sport
        assert 'minmax(4.4rem, max-content)' in rules, sport


def test_the_browser_checks_run_the_cut_check_on_both_day_boards_and_prove_it_can_fail():
    assert 'python tests/browser/check_row_cut.py --self-test --tmp "$RUNNER_TEMP/rowcut"' in WORKFLOW
    assert ('python tests/browser/check_row_cut.py "$RUNNER_TEMP/states/nhl.html" '
            '"$RUNNER_TEMP/states/nba.html"') in WORKFLOW
