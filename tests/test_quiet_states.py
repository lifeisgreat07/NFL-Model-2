"""Goalie pills and "Locked" stop spending the accent, and the amber is retired (Stage 78 item 38, the 2026-10-13 UI/UX audit's X10).

On the NHL board for 2026-10-13, 22 texts at 390 px and 44 at 1440 px wore
the accent, most of them "Locked" and CONFIRMED (measured 2026-10-14), and
a "Likely" goalie pill wore an amber of its own (--nhl-likely), a fifth
colour job. A goalie's status is now a shared .tag in the tones Mark chose
on 2026-10-14: Confirmed filled, Likely, No report yet and Last start
outlined, each with its word. "Locked" is --text-2 on both day boards; a
game under way (Live) keeps the accent.

Run with: pytest tests/test_quiet_states.py -v
"""
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
NHL_CSS = (ROOT / 'src' / 'sports' / 'nhl' / 'pages' / 'nhl.css').read_text(encoding='utf-8')
NHL_JS = (ROOT / 'src' / 'sports' / 'nhl' / 'pages' / 'nhl.js').read_text(encoding='utf-8')


def test_the_amber_is_retired():
    assert '--nhl-likely' not in NHL_CSS and '--nhl-likely' not in NHL_JS


def test_goalie_pills_are_shared_tags_with_their_word():
    pills = NHL_JS[NHL_JS.index('function goalieText(team, gl){'):]
    pills = pills[:pills.index('\n}\n')]
    assert "'<span class=\"tag tag-fill nhl-goalie confirmed\">Confirmed</span>'" in pills
    assert "'<span class=\"tag tag-outline nhl-goalie likely\">Likely</span>'" in pills
    assert "'<span class=\"tag tag-outline nhl-goalie unreported\">No report yet</span>'" in pills
    assert "'<span class=\"tag tag-outline nhl-goalie unreported\">Last start</span>'" in pills
    assert 'accent' not in NHL_CSS[NHL_CSS.index('.nhl-goalie{'):].split('}')[0]


@pytest.mark.parametrize('sport', ['nhl', 'nba'])
def test_locked_is_quiet_and_live_keeps_the_accent(sport):
    css = (ROOT / 'src' / 'sports' / sport / 'pages' / f'{sport}.css').read_text(encoding='utf-8')
    assert f'.{sport}-row-result.locked{{color:var(--text-2);}}' in css
    assert f'.{sport}-row-result.live{{color:var(--accent);}}' in css
