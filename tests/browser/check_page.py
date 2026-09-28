"""Browser checks on the BUILT dashboard (Stage 12).

Drives Chromium with Playwright over every page of index.html at six widths
and fails on what a static read of the template cannot see:

  overflow   the page scrolls sideways (scrollWidth past the viewport)
  focus      a Tab stop is off-screen or invisible when it has focus
  target     a control is under 24 CSS px in either dimension (WCAG 2.5.8),
             except links inside running text, which 2.5.8 exempts
  axe        axe-core reports a serious or critical violation
  font       Plus Jakarta Sans is not the face actually rendering text,
             asserted from MEASURED WIDTHS against a monospace fallback,
             never from document.fonts.check() (CLAUDE.md: that returns
             true when nothing is pending, which proves nothing)
  error      the page throws
  budget     index.html is over its byte budget

Every run is made twice: once with all network blocked -- the site must work
self-contained, and the ESPN logos must fail gracefully -- and once with
network allowed, because a loaded logo changes the layout.

`--self-test` runs each rule against a synthetic page that breaks it and
fails unless the rule reports it. A rule that cannot fail is decoration
(CLAUDE.md, "Before writing a guard, ask what input would make it go red").

Usage:
  python tests/browser/check_page.py index.html --axe node_modules/axe-core/axe.min.js
  python tests/browser/check_page.py --self-test --axe node_modules/axe-core/axe.min.js
"""
import argparse
import asyncio
import sys
from pathlib import Path

from playwright.async_api import async_playwright

WIDTHS = (360, 390, 768, 1024, 1280, 1440)
HEIGHT = 900
MOBILE_BELOW = 768          # the page's own phone layout starts under 1080;
                            # touch emulation for the two phone widths
TARGET_MIN = 24
AXE_WIDTHS = (390, 1280)    # one phone, one desktop: axe is slow and
                            # layout rarely changes what it finds
FAIL_IMPACTS = ('serious', 'critical')
# Measured 2026-09-28 on markys after Stage 26 item 11 (the built page drops
# the template's comments, the agent log's per-audit records and its JSON
# indentation), LF line endings: the page is 437,659 bytes, down from 749,502,
# of which the inlined font block is about 98,000. Each saved week now adds
# 8.5-16KB of compact JSON (weeks 1-3: 8,568 / 8,539 / 16,325; week 3 carries
# context notes). About 19 more weeks through the playoffs at 12KB puts the
# page near 665KB by February, and near 745KB if every week is as heavy as
# week 3. The budget is that plus room for a feature or two: exceeding it
# should mean something grew that nobody meant to grow. Moving it is a
# decision with a reason in the commit, not a reflex. (It was 1,000,000
# before Stage 26, set against the page with comments and indentation.)
BYTE_BUDGET = 800_000
TAB_CAP = 400

PAGE_IDS_JS = "[...document.querySelectorAll('section.page')].map(s => s.id.replace(/^page-/, ''))"

OVERFLOW_JS = """() => {
  const d = document.documentElement;
  return d.scrollWidth > window.innerWidth + 1
    ? `scrollWidth ${d.scrollWidth} > viewport ${window.innerWidth}` : null;
}"""

# The element that has focus: where it is, and whether anyone can see it.
FOCUS_JS = """() => {
  const e = document.activeElement;
  if (!e || e === document.body || e === document.documentElement) return null;
  const r = e.getBoundingClientRect();
  const cs = getComputedStyle(e);
  const name = (e.getAttribute('aria-label') || e.textContent || e.id || e.tagName).trim().slice(0, 40);
  return {name, tag: e.tagName, cls: e.className && e.className.baseVal === undefined ? e.className : '',
          left: r.left, top: r.top, right: r.right, bottom: r.bottom, width: r.width, height: r.height,
          hidden: cs.visibility === 'hidden' || cs.opacity === '0',
          key: e.tagName + '|' + name + '|' + Math.round(r.left) + '|' + Math.round(r.top)};
}"""

# Every visible control, with its size. A link is exempt when it sits in a
# sentence: its parent has more text than the link itself.
TARGETS_JS = """(minPx) => {
  const sel = 'a[href], button, select, input:not([type=hidden]), [role=button], [tabindex]:not([tabindex="-1"])';
  const out = [];
  for (const e of document.querySelectorAll(sel)) {
    if (e.closest('[inert]') || e.disabled) continue;
    const r = e.getBoundingClientRect();
    if (r.width === 0 && r.height === 0) continue;          // not rendered
    const cs = getComputedStyle(e);
    if (cs.visibility === 'hidden') continue;
    // The visually hidden native <select> behind each listbox is 1x1 and
    // clipped on purpose; its visible stand-in is the listbox button.
    if (r.width <= 1 && r.height <= 1) continue;
    if (e.tagName === 'A') {
      const parentText = (e.parentElement && e.parentElement.textContent || '').trim();
      const ownText = (e.textContent || '').trim();
      if (parentText.length > ownText.length + 1) continue;  // inline in a sentence
    }
    if (r.width < minPx - 0.5 || r.height < minPx - 0.5) {
      const name = (e.getAttribute('aria-label') || e.textContent || e.tagName).trim().slice(0, 40);
      out.push(`${e.tagName.toLowerCase()} "${name}" is ${r.width.toFixed(1)}x${r.height.toFixed(1)}`);
    }
  }
  return out;
}"""

FONT_JS = """async () => {
  await document.fonts.ready;
  await document.fonts.load("700 16px 'Plus Jakarta Sans'");
  const loaded = [...document.fonts].some(f => f.family.replace(/["']/g, '') === 'Plus Jakarta Sans' && f.status === 'loaded');
  const c = document.createElement('canvas').getContext('2d');
  const s = 'Most Confident First 0123456789 iiii WWWW';
  c.font = "700 16px 'Plus Jakarta Sans', monospace"; const withFace = c.measureText(s).width;
  c.font = "700 16px monospace"; const fallback = c.measureText(s).width;
  return {loaded, withFace, fallback};
}"""


def rel_diff(a, b):
    return abs(a - b) / max(a, b, 1e-9)


async def tab_walk(page):
    """Tab from the top until focus comes round again; report bad stops."""
    problems, seen = [], set()
    await page.evaluate("() => { document.activeElement && document.activeElement.blur(); window.scrollTo(0, 0); }")
    vw, vh = await page.evaluate("() => [window.innerWidth, window.innerHeight]")
    for _ in range(TAB_CAP):
        await page.keyboard.press('Tab')
        f = await page.evaluate(FOCUS_JS)
        if f is None:
            if seen:
                break          # focus left the document: one full cycle done
            continue
        if f['key'] in seen:
            break
        seen.add(f['key'])
        off = (f['right'] <= 0 or f['bottom'] <= 0 or f['left'] >= vw or f['top'] >= vh)
        tiny = f['width'] < 2 or f['height'] < 2
        if off or tiny or f['hidden']:
            why = 'off-screen' if off else ('invisible' if f['hidden'] else 'zero-size')
            problems.append(f"Tab stop {f['tag'].lower()} \"{f['name']}\" is {why} "
                            f"at ({f['left']:.0f},{f['top']:.0f}) {f['width']:.0f}x{f['height']:.0f}")
    return problems, len(seen)


async def check_one(browser, url, width, network, axe_src, report):
    mobile = width < MOBILE_BELOW
    ctx = await browser.new_context(viewport={'width': width, 'height': HEIGHT},
                                    is_mobile=mobile, has_touch=mobile,
                                    reduced_motion='reduce')
    page = await ctx.new_page()
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    if not network:
        await page.route(lambda u: u.startswith(('http://', 'https://')), lambda r: r.abort())
    await page.goto(url)
    await page.wait_for_timeout(300)
    tag = f"{width}px, network {'on' if network else 'blocked'}"
    ids = await page.evaluate(PAGE_IDS_JS)
    if not ids:
        report.append(f"[{tag}] no section.page found -- the checker is looking at the wrong page")
    stops_total = 0
    for pid in ids:
        await page.evaluate(f"setActivePage({pid!r})")
        await page.wait_for_timeout(120)
        where = f"[{tag}] {pid}"
        o = await page.evaluate(OVERFLOW_JS)
        if o:
            report.append(f"{where}: overflow: {o}")
        for t in await page.evaluate(TARGETS_JS, TARGET_MIN):
            report.append(f"{where}: target: {t}")
        problems, stops = await tab_walk(page)
        stops_total += stops
        report.extend(f"{where}: focus: {p}" for p in problems)
        if axe_src and width in AXE_WIDTHS and not network:
            await page.add_script_tag(content=axe_src)
            res = await page.evaluate("""async () => {
              const r = await axe.run(document, {runOnly: {type: 'tag', values: ['wcag2a','wcag2aa','wcag21a','wcag21aa','wcag22aa']}});
              return r.violations.map(v => ({id: v.id, impact: v.impact, n: v.nodes.length,
                                             where: v.nodes.slice(0, 2).map(n => n.target.join(' '))}));
            }""")
            for v in res:
                if v['impact'] in FAIL_IMPACTS:
                    report.append(f"{where}: axe {v['impact']}: {v['id']} on {v['n']} node(s), e.g. {v['where']}")
    if ids and stops_total == 0:
        report.append(f"[{tag}] the Tab walk reached nothing -- the focus check is looking at nothing")
    if not network:
        font = await page.evaluate(FONT_JS)
        if not font['loaded'] or rel_diff(font['withFace'], font['fallback']) < 0.05:
            report.append(f"[{tag}] font: Plus Jakarta Sans is not rendering "
                          f"(loaded={font['loaded']}, {font['withFace']:.1f}px vs monospace {font['fallback']:.1f}px)")
    report.extend(f"[{tag}] page error: {e}" for e in errors)
    await ctx.close()


async def check_page(path, axe_src=None, widths=WIDTHS, budget=BYTE_BUDGET):
    report = []
    size = Path(path).stat().st_size
    if size > budget:
        report.append(f"budget: {path} is {size:,} bytes, over the {budget:,}-byte budget")
    url = Path(path).resolve().as_uri()
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        for network in (False, True):
            for w in widths:
                await check_one(browser, url, w, network, axe_src, report)
        await browser.close()
    return report


# ---------------------------------------------------------------- self-test
# Each fixture is a minimal page in the dashboard's shape (section.page and a
# setActivePage) that breaks exactly one rule. The rule must report it.
SHELL = """<!doctype html><html lang="en"><head><meta charset="utf-8"><title>t</title>
<style>{css} body{{font-family:'Plus Jakarta Sans',monospace;margin:0}}</style>{head}</head>
<body><main><section class="page active" id="page-one"><h1>One</h1>{body}</section></main>
<script>function setActivePage(){{}} {script}</script></body></html>"""

FIXTURES = {
    'overflow': dict(body='<div style="width:3000px">wide</div>', expect='overflow'),
    # The real defect's shape (#111): a fixed sheet moved below the screen
    # with a transform. Scrolling cannot bring it into view, so focus lands
    # somewhere nobody can see. (An absolutely placed button would not do:
    # the browser scrolls a focused element into view, and then it is fine.)
    'focus': dict(body='<div style="position:fixed;left:0;right:0;bottom:0;transform:translateY(400px)">'
                       '<button style="min-width:40px;min-height:40px">hidden sheet</button></div>',
                  expect='focus'),
    'target': dict(body='<p><button style="font-size:10px;padding:0">tiny</button></p>', expect='target'),
    'axe': dict(body='<img src="data:image/gif;base64,R0lGODlhAQABAAAAACw=">', expect='axe'),
    'font': dict(body='<p>No self-hosted face here.</p>', expect='font'),
    'error': dict(body='<p>ok</p>', script='throw new Error("boom")', expect='page error'),
}


async def self_test(axe_src, tmp):
    failed = []
    for name, fx in FIXTURES.items():
        if name == 'axe' and not axe_src:
            print(f"self-test {name}: SKIPPED (no axe-core given)")
            continue
        page = Path(tmp) / f'fixture_{name}.html'
        page.write_text(SHELL.format(css=fx.get('css', ''), head='', body=fx['body'],
                                     script=fx.get('script', '')), encoding='utf-8')
        report = await check_page(page, axe_src, widths=(390,), budget=10**9)
        hit = [r for r in report if fx['expect'] in r]
        print(f"self-test {name}: {'caught' if hit else 'MISSED'} ({len(report)} finding(s))")
        if not hit:
            failed.append(name)
    # The budget rule: a real page run with a budget it exceeds. No widths,
    # so no browser pass is needed to reach the one line under test.
    big = Path(tmp) / 'fixture_budget.html'
    big.write_text(SHELL.format(css='', head='', body='x' * 2000, script=''), encoding='utf-8')
    report = await check_page(big, None, widths=(), budget=1000)
    hit = [r for r in report if r.startswith('budget:')]
    print(f"self-test budget: {'caught' if hit else 'MISSED'}")
    if not hit:
        failed.append('budget')
    return failed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('page', nargs='?', default='index.html')
    ap.add_argument('--axe', help='path to axe.min.js')
    ap.add_argument('--self-test', action='store_true')
    ap.add_argument('--tmp', default='.')
    a = ap.parse_args()
    axe_src = Path(a.axe).read_text(encoding='utf-8') if a.axe else None
    if a.self_test:
        failed = asyncio.run(self_test(axe_src, a.tmp))
        if failed:
            print(f"SELF-TEST FAILED: these rules did not catch their own fixture: {failed}")
            sys.exit(1)
        print("self-test: every rule caught its fixture")
        return
    report = asyncio.run(check_page(a.page, axe_src))
    for line in report:
        print(line)
    if report:
        print(f"{len(report)} finding(s)")
        sys.exit(1)
    print(f"{a.page}: no findings at {', '.join(map(str, WIDTHS))}px, network blocked and allowed")


if __name__ == '__main__':
    main()
