"""MLB's pages go through the browser checks before they are published (Stage 100 item 4).

The NBA's page was checked in a real browser from Stage 61, months before it
had picks; MLB's had no check at all. Now browser-checks.yml builds MLB's
pages with the real builder (src/sports/mlb/site.py, committed files only)
and runs check_page.py (overflow, focus, target size, axe, fonts, errors,
sticky headers, sort marks, byte budget) and the cross-sport checks that take
any page: the sport menu's fit, the sidebar's reach and nothing hidden drawn.

The first run found axe's scrollable-region-focusable on two Model Lab tables
and one Methodology table at 390 px: mlb.js had no copy of the rule that puts
a table wider than its box into the Tab order. It has the NBA's now.

Run with: pytest tests/test_mlb_browser_checks.py -v
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / '.github' / 'workflows' / 'browser-checks.yml'
MLB_JS = (ROOT / 'src' / 'sports' / 'mlb' / 'pages' / 'mlb.js').read_text(encoding='utf-8')
PAGE = (ROOT / 'src' / 'sports' / 'mlb' / 'pages' / 'page.html').read_text(encoding='utf-8')
MLB = '"$RUNNER_TEMP/states/mlb.html"'


def steps():
    """Each step's name and its one-line `run`, in order (the steps checked here are all one line)."""
    text = WORKFLOW.read_text(encoding='utf-8').replace('\r\n', '\n')
    out = []
    for chunk in re.split(r'\n      - ', text)[1:]:
        name = re.match(r'name: (.*)', chunk)
        run = re.search(r'^        run: (?!\|)(.*)$', chunk, re.M)
        out.append((name.group(1) if name else '', run.group(1) if run else ''))
    return out


def index(pred):
    hits = [i for i, (name, run) in enumerate(steps()) if pred(name, run)]
    assert len(hits) == 1, hits
    return hits[0]


def test_the_workflow_builds_mlbs_pages_with_the_real_builder_and_checks_them():
    build = index(lambda n, r: r.strip() == f'python -m src.sports.mlb.site --out {MLB}')
    check = index(lambda n, r: r.startswith('python tests/browser/check_page.py ') and MLB in r)
    assert build < check, 'the check runs before the page is built'
    assert '--axe node_modules/axe-core/axe.min.js' in steps()[check][1], 'MLB is checked without axe'


def test_the_cross_sport_checks_open_mlbs_pages_too():
    for script in ('check_switcher_fit.py', 'check_sidebar_reach.py', 'check_hidden.py'):
        run = steps()[index(lambda n, r, s=script: r.startswith(f'python tests/browser/{s} index.html'))][1]
        assert run.rstrip().endswith(MLB), f'{script} does not open MLB\'s pages'


def test_a_table_wider_than_its_box_is_in_the_tab_order():
    """setScrollStop and fitTables (src/core/day_board.js) read FOCUSABLE_INSIDE and scrollStopLabel from the
    sport's own script and run on the sport's own schedule: without these, fitTables never runs on MLB's pages."""
    assert "const FOCUSABLE_INSIDE = 'a[href], button, input, select, textarea, [tabindex]:not([tabindex=\"-1\"])';" in MLB_JS
    assert re.search(r'^function scrollStopLabel\(el\)\{', MLB_JS, re.M)
    block = MLB_JS[MLB_JS.index('/* ---------- tables that scroll'):MLB_JS.index('/* ---------- days and weeks')]
    assert "requestAnimationFrame(() => { queued = false; fitTables(); })" in block
    assert "window.addEventListener('resize', later);" in block and '  later();\n})();' in block.replace('\r\n', '\n')
    assert PAGE.index('{% include "day_board.js" %}') < PAGE.index('{% include "mlb.js" %}'), (
        'mlb.js must follow day_board.js, which defines fitTables')
