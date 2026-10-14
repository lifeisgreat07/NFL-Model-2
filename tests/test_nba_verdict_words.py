"""The NBA's pre-season note says the backtest's verdict in plain words (Stage 77 item 21, the 2026-10-13 UI/UX audit's copy fix 10).

It read "the backtest's answer to H3 was REJECT: on 2024-25 and 2025-26,
Model B's log loss was higher than the market alone's (+0.0008)". It now
reads "In the two test seasons Model B did not beat the betting market, so
the first live picks are a real test, not a victory lap." The label, the
gap and its sign stay on the Model Lab; the note's direction and the number
of seasons are still read from the results and the registry.

Run with: pytest tests/test_nba_verdict_words.py -v
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / 'src' / 'sports' / 'nba' / 'pages' / 'nba.js').read_text(encoding='utf-8')


def note():
    return JS[JS.index('function preseasonHtml(){'):JS.index('function stateHtml(')]


def test_the_note_says_the_verdict_in_plain_words():
    body = note()
    assert ('` In the ${howMany} test seasons Model B did not beat the betting market, '
            'so the first live picks are a real test, not a victory lap.`') in body
    assert "const howMany = ['no', 'one', 'two', 'three', 'four'][seasons] || String(seasons);" in body
    for jargon in ('answer to H3', 'log loss', '${escapeHtml(h3.label)}', 'signed(h3.diff'):
        assert jargon not in re.sub(r'/\*.*?\*/', '', body, flags=re.S), f'the note still says {jargon!r}'
