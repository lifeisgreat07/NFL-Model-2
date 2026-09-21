"""Which meaning-carrying colour tokens are actually painted on each page.

`tests/test_dashboard_charts.py` measures how far apart two tokens are. It
cannot measure whether a reader ever sees them at once, and six entries in its
ACCEPTED_CLOSE list said "Not traced" for exactly that reason. This answers
that question by rendering the built page and reading the DOM, and it prints a
token -> pages map rather than pair verdicts, so a verdict about any pair is
read off one table instead of being re-derived by hand per pair.

    python src/verify_token_cooccurrence.py [path/to/index.html]

NEEDS A BROWSER. Playwright is not installed on the Windows dev machine and no
CI job here has one, so this is a standalone verifier like
`src/verify_matchup_cvd.py` -- run where a browser exists, quote the output.
What the suite CAN check without a browser is the premise underneath the two
"cannot meet" verdicts: see
`test_the_cannot_meet_verdicts_rest_on_a_premise_that_still_holds`.

Two things this script does that a naive version gets wrong, both of which
produced confident wrong answers while it was being written:

1. THE FOUR-SERIES CHART DOES NOT DRAW IN AN ORDINARY VISIT. The Season
   Accuracy trend chart short-circuits below two graded weeks, and the My
   Picks series is computed from localStorage, which is empty in a fresh
   profile. Swept as-is in September it reports that --series-d appears
   nowhere -- a fact about the fixture that reads exactly like a fact about
   the page. So the sweep seeds picks and a second graded week, and REFUSES
   TO REPORT unless the chart then actually drew.
2. AN ELEMENT CAN BE "VISIBLE" AND OFF SCREEN. The skip link is painted
   --accent and parked at y=-40 until focused. checkVisibility() says yes.
   Anything whose box lies entirely outside the document is dropped.
"""
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
PAGES = ['ratings', 'board', 'picks', 'accuracy', 'teamdive',
         'modellab', 'method', 'changelog', 'reliability']

# Seed enough state that every branch of the chart layer is reachable. The
# second week is a copy of the first: the sweep asks WHICH COLOURS REACH THE
# SCREEN, and for that a duplicated week is as good as a real one. It is not
# data anybody should read numbers off, which is why it is never printed.
SEED_PICKS = r"""
() => {
  const key = Object.keys(weeks)[0];
  const picks = {};
  let seeded = 0;
  for (const g of (weeks[key].games || [])) {
    if (g.graded && g.actual_home_win !== null) {
      picks[key + '|' + g.home + '|' + g.away] = g.home;
      seeded++;
    }
  }
  localStorage.setItem(PICKS_STORAGE_KEY, JSON.stringify(picks));
  return {seeded};
}
"""

# The picks go into localStorage and the page then RELOADS, because every page
# that reads them renders once at init: seeding in place leaves My Picks Log
# showing the empty state it was built with, and two runs of this script
# disagreed about that page until the reload went in. The extra week is
# applied after the reload, where it does need an explicit re-render.
SEED_WEEK = r"""
() => {
  const w0 = accuracy.weeks[0];
  accuracy.weeks = [w0, Object.assign({}, w0, {week: w0.week + 1})];
  renderAccuracy();
  return {weeks: accuracy.weeks.length};
}
"""

# Vacuity guard. Every "never together" verdict below is void if this is false,
# so it is checked rather than assumed -- the repo's own rule for any
# assertion over a list some scan produces.
CHART_DREW = r"""
() => {
  const s = document.getElementById('page-accuracy');
  return {svgs: s.querySelectorAll('svg').length,
          trend: /Cumulative Accuracy Trend/.test(s.textContent)};
}
"""

PROBE = r"""
(hexByToken) => {
  const PROPS = ['color','backgroundColor','backgroundImage','borderTopColor',
    'borderRightColor','borderBottomColor','borderLeftColor','outlineColor',
    'fill','stroke','boxShadow','textDecorationColor','caretColor'];
  const toHex = (r,g,b) => '#' + [r,g,b].map(n=>Number(n).toString(16)
      .padStart(2,'0')).join('').toUpperCase();
  const lookup = {};
  for (const [tok, hex] of Object.entries(hexByToken)) {
    (lookup[hex] = lookup[hex] || []).push(tok);
  }
  const onScreen = (el) => {
    if (!el.checkVisibility({checkOpacity:true, checkVisibilityCSS:true})) return false;
    const r = el.getBoundingClientRect();
    if (r.width <= 0 || r.height <= 0) return false;
    // Parked off the document, like the skip link at y=-40.
    return (r.bottom + window.scrollY) > 0 && (r.right + window.scrollX) > 0;
  };
  const hits = {};
  const scan = (el, pseudo) => {
    const cs = getComputedStyle(el, pseudo);
    if (pseudo && (cs.content === 'none' || cs.display === 'none'
        || cs.visibility === 'hidden')) return;
    for (const prop of PROPS) {
      const raw = cs[prop];
      if (!raw || raw === 'none') continue;
      for (const g of raw.matchAll(/rgba?\(\s*(\d+)[,\s]+(\d+)[,\s]+(\d+)/g)) {
        const toks = lookup[toHex(g[1], g[2], g[3])];
        if (!toks) continue;
        const r = el.getBoundingClientRect();
        for (const t of toks) {
          const rec = hits[t] = hits[t] || [];
          rec.push({
            tag: el.tagName.toLowerCase(),
            cls: (el.getAttribute('class') || '').slice(0, 48),
            prop: pseudo ? prop + pseudo : prop,
            chrome: !el.closest('section.page'),
            text: (el.textContent || '').trim().slice(0, 34),
          });
        }
      }
    }
  };
  for (const el of document.querySelectorAll('body *')) {
    if (!onScreen(el)) continue;
    scan(el, null); scan(el, '::before'); scan(el, '::after');
  }
  return hits;
}
"""


def meaning_tokens(src, theme):
    """The same derivation tests/test_dashboard_charts.py uses.

    Copied rather than imported for the reason that file gives about its own
    colour maths: a verifier that shares a helper with the thing it verifies
    agrees with it by construction.
    """
    marker = ':root{' if theme == 'dark' else '[data-theme="light"]{'
    start = src.index(marker)
    block = src[start:src.index('}', start)]
    return {name: value.upper() for name, value in
            re.findall(r'(--[a-z0-9-]+)\s*:\s*(#[0-9A-Fa-f]{6})\b', block)
            if not re.fullmatch(r'--n\d+', name)}


def sweep(built_page):
    from playwright.sync_api import sync_playwright

    src = (REPO_ROOT / 'src' / 'dashboard_template.html').read_text(
        encoding='utf-8')
    out = {}
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={'width': 1440, 'height': 900})
        page.goto(built_page.as_uri())
        page.wait_for_timeout(1000)
        seeded = page.evaluate(SEED_PICKS)
        page.reload()
        page.wait_for_timeout(1200)
        page.evaluate(SEED_WEEK)
        page.wait_for_timeout(500)

        drew = page.evaluate(CHART_DREW)
        if not seeded['seeded'] or not drew['trend'] or not drew['svgs']:
            browser.close()
            sys.exit('the seed did not take -- picks stored: '
                     f'{seeded["seeded"]}, chart drawn: {drew}. Every verdict '
                     'this would print would be a fact about the seed rather '
                     'than about the page.')

        for theme in ('dark', 'light'):
            tokens = meaning_tokens(src, theme)
            page.evaluate(
                "(t) => { if (t === 'light') "
                "document.documentElement.setAttribute('data-theme','light'); "
                "else document.documentElement.removeAttribute('data-theme'); }",
                theme)
            out[theme] = {}
            for name in PAGES:
                page.locator(f'.nav-btn[data-page="{name}"]').click()
                page.wait_for_timeout(420)
                out[theme][name] = page.evaluate(PROBE, tokens)
        browser.close()
    return out


def main():
    built = Path(sys.argv[1]) if len(sys.argv) > 1 else REPO_ROOT / 'index.html'
    if not built.exists():
        sys.exit(f'{built} does not exist -- run '
                 'python src/generate_dashboard.py first')
    out = sweep(built)

    every = sorted({t for theme in out for p in out[theme]
                    for t in out[theme][p]})
    for theme in ('dark', 'light'):
        print(f'\n{theme}: which pages paint each token on screen')
        print('-' * 66)
        for tok in every:
            pages = [p for p in PAGES if tok in out[theme][p]]
            print(f'  {tok:<17} {", ".join(pages) if pages else "(nowhere)"}')

    print('\nwhere each token lands, first instance per page')
    print('-' * 66)
    for theme in ('dark', 'light'):
        for p in PAGES:
            for tok, hs in sorted(out[theme][p].items()):
                h = hs[0]
                where = 'chrome' if h['chrome'] else 'body'
                print(f'  {theme:<5} {p:<11} {tok:<17} <{h["tag"]} '
                      f'class="{h["cls"]}"> {h["prop"]} ({where}) '
                      f'{h["text"]!r}')

    dest = REPO_ROOT / 'dist' / 'token_cooccurrence.json'
    dest.parent.mkdir(exist_ok=True)
    dest.write_text(json.dumps(out, indent=1))
    print(f'\nfull hit list written to {dest}')


if __name__ == '__main__':
    main()
