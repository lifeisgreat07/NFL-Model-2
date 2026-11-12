"""Stage 102: the leagues' own marks, hot-linked, with our icon behind them and a line saying whose they are.

Mark reversed the 2026-10-09 decline on 2026-11-11 (docs/history/12-mlb-and-more-2026-11-11.md) and chose
option B of the rendered placements: the marks on the home page's cards and in the sport switcher. They are
used as the team logos are: read from ESPN's image server, never committed to this public repository; a
mark that fails to load leaves our own icon on a card and the bare name in a switcher; and the home page's
footer says the site is not affiliated with or endorsed by the leagues.

Run with: pytest tests/test_league_marks.py -v
"""
import json
import re
import subprocess
from pathlib import Path

from tests.optional import require_tool

ROOT = Path(__file__).resolve().parents[1]
HOME = ROOT / 'src' / 'site' / 'home'
PAGE = (HOME / 'page.html').read_text(encoding='utf-8')
JS = (HOME / 'home.js').read_text(encoding='utf-8')
CSS = (HOME / 'home.css').read_text(encoding='utf-8')
SHARED_CSS = (ROOT / 'src' / 'dashboard' / 'styles.css').read_text(encoding='utf-8')
BODIES = {'nfl': ROOT / 'src' / 'dashboard' / 'body.html', 'nhl': ROOT / 'src' / 'sports' / 'nhl' / 'pages' / 'body.html',
          'nba': ROOT / 'src' / 'sports' / 'nba' / 'pages' / 'body.html'}
CDN = 'https://a.espncdn.com/combiner/i?img=/i/teamlogos/leagues/'
SPORTS = ('nfl', 'nhl', 'nba')


def run_mark(sport):
    """leagueMark(sport) as the card calls it, run under node with the page's own icon parts."""
    node = require_tool('node')
    parts = re.search(r'const ICON_PARTS = \{.*?\n\};', JS, re.S).group(0)
    icon = re.search(r'function icon\(sport\)\{.*?\n\}', JS, re.S).group(0)
    const = re.search(r"const LEAGUE_MARKS = '[^']*';", JS).group(0)
    mark = re.search(r'function leagueMark\(sport\)\{.*?\n\}', JS, re.S).group(0)
    src = '\n'.join([parts, icon, const, mark, f'process.stdout.write(JSON.stringify(leagueMark({json.dumps(sport)})));'])
    out = subprocess.run([node, '-e', src], capture_output=True, text=True, encoding='utf-8', check=True).stdout
    return json.loads(out)


def test_each_card_mark_is_hot_linked_in_both_themes_with_our_icon_behind_it():
    for sport in SPORTS:
        html = run_mark(sport)
        srcs = re.findall(r'<img class="(lgm-[ld])" src="([^"]+)"', html)
        assert srcs == [('lgm-l', f'{CDN}500/{sport}.png&amp;w=56&amp;h=56'),
                        ('lgm-d', f'{CDN}500-dark/{sport}.png&amp;w=56&amp;h=56')], sport
        assert '<span class="lgm-own"><svg class="home-icon"' in html, f'{sport}: no icon to fall back on'
        assert html.startswith('<span class="lgm" aria-hidden="true">'), 'the name beside it is read; the mark is not'
    assert run_mark('mlb') == '', 'a sport with no page has no mark'


def test_the_switcher_on_the_home_page_carries_each_leagues_mark_before_its_name():
    nav = re.search(r'<nav class="sport-switch home-switch" aria-label="Sports">(.*?)</nav>', PAGE, re.S).group(1)
    for sport in SPORTS:
        pill = re.search(rf'<a href="{sport}/">(.*?)</a>', nav, re.S).group(1)
        assert pill.startswith('<span class="lgm lgm-sm" aria-hidden="true">'), sport
        assert f'src="{CDN}500/{sport}.png&amp;w=36&amp;h=36"' in pill and f'src="{CDN}500-dark/{sport}.png' in pill
        assert pill.endswith(f'</span>{sport.upper()}'), f'{sport}: the name must stay, after the mark'


def rules(css):
    return {re.sub(r'\s+', ' ', sel.split('*/')[-1]).strip(): body.strip()
            for sel, body in re.findall(r'([^{}]+)\{([^{}]*)\}', css)}


def test_a_mark_that_fails_falls_back_and_the_theme_shows_one_version():
    listener = re.search(r"document\.addEventListener\('error', e => \{.*?\}, true\);", JS, re.S)
    assert listener and "closest('.lgm')" in listener.group(0) and "classList.add('lgm-failed')" in listener.group(0)
    shared, home = rules(SHARED_CSS), rules(CSS)
    assert shared['.lgm .lgm-l'] == 'display:none;', 'dark is the default; the light mark waits'
    assert shared['[data-theme="light"] .lgm .lgm-l'] == 'display:block;'
    assert shared['[data-theme="light"] .lgm .lgm-d'] == 'display:none;'
    assert shared['.lgm-sm:has(img[style*="none"])'] == 'display:none;', 'a sport page pill whose mark failed keeps its name'
    assert home['.lgm .lgm-own'] == 'display:none;'
    assert home['.lgm.lgm-failed img'] == 'display:none;'
    assert home['.lgm.lgm-failed .lgm-own'] == 'display:inline-flex;', 'a card whose mark failed shows our icon'
    assert home['.lgm-sm.lgm-failed'] == 'display:none;', 'a home pill whose mark failed shows its name only'


def test_every_sport_pages_switchers_carry_the_marks_and_hide_a_failed_one():
    for page, path in BODIES.items():
        t = path.read_text(encoding='utf-8')
        navs = re.findall(r'<nav class="sport-switch(?: sport-strip)?" aria-label="Sports">(.*?)</nav>', t, re.S)
        assert len(navs) == 2, page
        for nav in navs:
            for sport in SPORTS:
                pill = re.search(rf'<a href="\.\./{sport}/"(?: aria-current="page")?>(.*?)</a>', nav, re.S).group(1)
                imgs = re.findall(r'<img class="(lgm-[ld])" src="([^"]+)"[^>]*?( data-hide-on-error)?>', pill)
                assert [(c, s) for c, s, _ in imgs] == [('lgm-l', f'{CDN}500/{sport}.png&amp;w=36&amp;h=36'),
                                                        ('lgm-d', f'{CDN}500-dark/{sport}.png&amp;w=36&amp;h=36')], (page, sport)
                assert all(h for _, _, h in imgs), f'{page} {sport}: a failed mark would leave a broken image'
                assert pill.endswith(f'</span>{sport.upper()}'), (page, sport)


def test_the_sidebar_pills_tighten_so_four_fit():
    """Option 2 of the rendered fits (Mark, 2026-11-11: "the slider needs to fit with the logos"): beside the name,
    smaller, with less padding, in the sidebar only. Whether it really fits is a browser check's question
    (tests/browser/check_switcher_fit.py)."""
    assert '  .sidebar .sport-switch a{gap:var(--s1); padding:0 var(--s1); font-size:var(--fs-11);}\n' in SHARED_CSS
    assert rules(SHARED_CSS)['.sidebar .lgm-sm'] == 'width:14px; height:14px; margin-right:0;'
    wf = (ROOT / '.github' / 'workflows' / 'browser-checks.yml').read_text(encoding='utf-8')
    assert 'python tests/browser/check_switcher_fit.py --self-test --tmp' in wf, 'the fit check is never proven able to fail'
    assert re.search(r'python tests/browser/check_switcher_fit\.py index\.html "\$RUNNER_TEMP/states/nhl\.html" '
                     r'"\$RUNNER_TEMP/states/nba\.html"', wf), 'the fit check does not open all three sport pages'


def test_the_page_may_load_them_and_the_repository_holds_none():
    csp = re.search(r'Content-Security-Policy" content="([^"]*)"', PAGE).group(1)
    assert 'https://a.espncdn.com' in re.search(r'img-src ([^;]*)', csp).group(1)
    committed = subprocess.run(['git', 'ls-files'], cwd=ROOT, capture_output=True, text=True, encoding='utf-8').stdout
    leagues = [f for f in committed.splitlines() if re.search(r'(^|/)(nfl|nhl|nba|mlb)\.(png|svg|jpe?g|webp)$', f)]
    assert leagues == [], f'a league mark committed to the public repository: {leagues}'


def test_the_footer_says_the_site_is_not_affiliated():
    foot = re.search(r'<footer class="home-links">(.*?)</footer>', PAGE, re.S).group(1)
    line = re.search(r'<p class="home-legal">([^<]*)</p>', foot)
    assert line, 'no not-affiliated line in the footer'
    for name in ('not affiliated with or endorsed by', 'the NFL', 'the NHL', 'the NBA', 'MLB', 'belong to their owners'):
        assert name in line.group(1), name
