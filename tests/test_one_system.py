"""One component for each thing the sports share (Stage 78 item 37, the 2026-10-13 UI/UX audit's X10 and H3).

The audit counted two sport switches (the home's 48 px tall, the others' 50),
two copies of the day chip's eleven declarations, three game rows (only two
of whose chevrons turned smoothly) and two disclosure markers (the home's
questions and a Model Lab table drew the browser's triangle, every other
<details> drew + and −). Each is one component in the shared stylesheet
now; a sport keeps only what is its own (its columns, its row height, a
class its script selects by). The result words are one vocabulary since
Stage 77 item 26 (tests/test_result_words.py).

Run with: pytest tests/test_one_system.py -v
"""
import re
from pathlib import Path

from src.core.template_parts import every_stylesheet

ROOT = Path(__file__).resolve().parents[1]
SHEETS = dict(every_stylesheet())
SHARED = SHEETS['the NFL template']
SPORT = {k: v for k, v in SHEETS.items() if k != 'the NFL template'}
JS = {sp: (ROOT / 'src' / 'sports' / sp / 'pages' / f'{sp}.js').read_text(encoding='utf-8') for sp in ('nhl', 'nba')}
APP = (ROOT / 'src' / 'dashboard' / 'app.js').read_text(encoding='utf-8')
HOME = (ROOT / 'src' / 'site' / 'home' / 'page.html').read_text(encoding='utf-8')
BODY = (ROOT / 'src' / 'dashboard' / 'body.html').read_text(encoding='utf-8')


def rules(css, selector):
    body = re.sub(r'/\*.*?\*/', '', css, flags=re.S)
    return [b for s, b in re.findall(r'([^{}]+)\{([^{}]*)\}', body) if selector in {x.strip() for x in s.split(',')}]


def test_one_sport_switch():
    assert '<nav class="sport-switch home-switch" aria-label="Sports">' in HOME
    home = SPORT['src/site/home/home.css']
    assert not rules(home, '.home-switch a') and not rules(home, '.home-switch a[aria-current="page"]')
    # Only where it sits: no margin in the bar, its own row on a phone.
    assert rules(home, '.home-switch') == [' margin-top:0; ', ' grid-column:1 / -1; justify-self:start; ']


def test_one_day_chip():
    assert rules(SHARED, '.day-chip') and rules(SHARED, '.day-strip')
    for sp, js in JS.items():
        assert not [n for n, css in SPORT.items() if f'.{sp}-day-chip' in css], f'{sp} keeps its own chip styles'
        assert f'<button type="button" class="day-chip {sp}-day-chip" data-day=' in js
        body = (ROOT / 'src' / 'sports' / sp / 'pages' / 'body.html').read_text(encoding='utf-8')
        assert f'<nav class="day-strip {sp}-day-strip" id="{sp}-day-strip"' in body


def test_one_game_row_and_one_chevron_turn():
    assert rules(SHARED, '.game-row')
    assert rules(SHARED, '.game-row-chev') == ['color:var(--text-3); transition:transform var(--dur-base) var(--ease);']
    assert rules(SHARED, '.game-row[aria-expanded="true"] .game-row-chev') == ['transform:rotate(180deg);']
    turns = [n for n, css in SHEETS.items() for b in re.findall(r'row-chev[^{]*\{([^}]*)\}', css) if 'transition' in b or 'rotate' in b]
    assert turns == ['the NFL template'] * 2, f'a chevron turns by a rule of its own: {turns}'
    for sp, js in JS.items():
        assert f'<button type="button" class="game-row {sp}-row" aria-expanded' in js
        assert f'<svg class="game-row-chev {sp}-row-chev"' in js
    assert 'class="game-row nfl-row" aria-expanded' in APP and '<svg class="game-row-chev nfl-row-chev"' in APP


def test_one_disclosure():
    markers = [n for n, css in SHEETS.items() for _ in re.finditer(r'summary::before\s*\{', re.sub(r'/\*.*?\*/', '', css, flags=re.S))]
    assert markers == ['the NFL template'] * 2, f'a disclosure draws its own marker: {markers}'
    assert rules(SHARED, '.disclosure > summary::-webkit-details-marker') == ['display:none;']
    details = re.findall(r'<details\b[^>]*>', HOME + BODY + APP)
    assert details and all('class="disclosure' in d for d in details), [d for d in details if 'disclosure' not in d]


TAGS = ('.tag', '.graded-tag', '.conf-tag', '.insight-chip', '.tv-pill')


def test_one_tag_shape_and_three_tones():
    shape = [s for s, b in re.findall(r'([^{}]+)\{([^{}]*)\}', re.sub(r'/\*.*?\*/', '', SHARED, flags=re.S))
             if 'min-height:20px' in b and 'text-transform:uppercase' in b]
    assert [{x.strip() for x in s.split(',')} for s in shape] == [set(TAGS)], 'every tag shares one shape'
    assert rules(SHARED, '.tag-fill') == ['background:var(--surface-2); color:var(--text-2);']
    assert rules(SHARED, '.tag-outline') == ['border-color:var(--border-strong); color:var(--text-2);']
    assert rules(SHARED, '.tag-accent') == ['background:var(--accent-soft); color:var(--accent);']
    # No tag class sets its own size, case, radius or padding anywhere else.
    for name, css in SHEETS.items():
        body = re.sub(r'/\*.*?\*/', '', css, flags=re.S)
        for sel, b in re.findall(r'([^{}]+)\{([^{}]*)\}', body):
            own = {x.strip() for x in sel.split(',')}
            if own & set(TAGS) and own != set(TAGS):
                assert not re.search(r'font-size|text-transform|border-radius|padding', b), f'{name}: {sel.strip()} {b}'
    for sp, js in JS.items():
        assert f'<span class="graded-tag tag-fill {sp}-locked">Locked' in js
