"""Every stylesheet is under the CSS guards, and no shadow carries a colour literal (Stage 78 item 36, the 2026-10-13 UI/UX audit's X9 and V9).

The motion, token and type-scale guards read only the joined NFL template,
so every violation the audit found sat in home.css, nhl.css and nba.css:
unguarded :hover, a literal .15s, an undeclared --r-2 drawing a 10 px
fallback, 13 literal font sizes on the home, nine spacing literals, and a
rgba(0,0,0,.18) shadow under the raised segment of both sport switches (the
only colour literals in the site's rules). The three guards now read all
four sheets (tests/test_motion_system.py, tests/test_css_tokens_defined.py,
tests/test_type_and_spacing_scale.py); this file holds the list they read
and the shadow rule.

Run with: pytest tests/test_css_sheets_guarded.py -v
"""
import re
from pathlib import Path

from src.core.template_parts import SPORT_SHEETS, every_stylesheet

ROOT = Path(__file__).resolve().parents[1]


def test_the_guards_read_every_sheet_the_site_ships():
    shipped = sorted(p.relative_to(ROOT).as_posix() for p in ROOT.glob('src/**/*.css')
                     if p.name != 'styles.css' and '_site' not in p.parts)
    assert sorted(p.relative_to(ROOT).as_posix() for p in SPORT_SHEETS) == shipped
    names = [n for n, _ in every_stylesheet()]
    assert names[0] == 'the NFL template' and sorted(names[1:]) == shipped, names
    for guard in ('test_motion_system.py', 'test_css_tokens_defined.py', 'test_type_and_spacing_scale.py'):
        assert 'every_stylesheet' in (ROOT / 'tests' / guard).read_text(encoding='utf-8'), guard


def test_no_shadow_carries_a_colour_literal():
    found = []
    for name, css in every_stylesheet():
        body = re.sub(r'/\*.*?\*/', '', css, flags=re.S)
        for m in re.finditer(r'(?<![\w-])box-shadow\s*:\s*([^;}]+)', body):
            if re.search(r'rgba?\(|#[0-9a-fA-F]{3,8}\b', m.group(1)):
                found.append(f'{name}: {m.group(1).strip()}')
    assert not found, 'a shadow written with a colour literal, not a token: ' + '; '.join(found)


def test_the_raised_segment_is_drawn_with_the_strong_border():
    sheets = dict(every_stylesheet())
    assert '.sport-switch a[aria-current="page"]{background:var(--surface); color:var(--text); box-shadow:inset 0 0 0 1px var(--border-strong);}' in sheets['the NFL template']
    assert '.home-switch a[aria-current="page"]{ background:var(--surface); color:var(--text); box-shadow:inset 0 0 0 1px var(--border-strong); }' in sheets['src/site/home/home.css']
