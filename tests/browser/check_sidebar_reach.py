"""Every control in the desktop sidebar can be reached in a laptop-sized window (audit 9, finding D1).

The sidebar is as tall as the window and sticks to it. Once it held more than the window is tall, its last
tabs, Settings and the theme button sat below the window's edge with no way to scroll to them: 937 px of sidebar
on the NFL's page in a 657 px window. Its tab list now scrolls and its foot stays pinned.

This opens every page given at 1366x657, 1280x720 and 1440x900, with the network refused. For each tab button,
the Settings button when it is shown and the theme button, it scrolls the control into view inside the sidebar
and fails unless the control then lies inside the window and is the element at its own centre, which is what a
mouse can click. It also fails if the theme button is not inside the window before anything is scrolled: the foot
is meant to stay pinned.

`--self-test` takes the scrolling back out of a copy of the NHL page and fails unless the unreachable controls
are reported.

Usage:
  python tests/browser/check_sidebar_reach.py <page.html> ...
  python tests/browser/check_sidebar_reach.py --self-test --tmp <dir>
"""
import argparse
import asyncio
import subprocess
import sys
from pathlib import Path

from playwright.async_api import async_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))  # tests/browser, when imported from elsewhere
from page_edit import rehash

ROOT = Path(__file__).resolve().parents[2]
SIZES = ((1366, 657), (1280, 720), (1440, 900))
MEASURE = """() => { const bar = document.querySelector('.sidebar');
  if(!bar || getComputedStyle(bar).display === 'none') return null;
  const shown = el => el && !el.hidden && getComputedStyle(el).display !== 'none';
  const inside = r => r.top >= -0.5 && r.bottom <= innerHeight + 0.5 && r.height > 0;
  const theme = bar.querySelector('#theme-toggle');
  const out = {pinned: shown(theme) && inside(theme.getBoundingClientRect()), controls: []};
  const controls = [...bar.querySelectorAll('.side-nav .nav-btn'), bar.querySelector('.side-settings'), theme];
  for(const el of controls.filter(shown)){
    el.scrollIntoView({block: 'nearest'});
    const r = el.getBoundingClientRect();
    const hit = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
    out.controls.push({name: (el.textContent || '').trim().replace(/\\s+/g, ' ') || el.id,
                       inside: inside(r), hit: !!hit && (hit === el || el.contains(hit))});
  }
  return out; }"""


async def check_pages(pages):
    report = []
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        for path in pages:
            uri = Path(path).resolve().as_uri()
            for width, height in SIZES:
                where = f'[{Path(path).name} {width}x{height}]'
                ctx = await browser.new_context(viewport={'width': width, 'height': height})
                page = await ctx.new_page()
                await page.route(lambda u: u.startswith(('http://', 'https://')), lambda route: route.abort())
                await page.goto(uri)
                await page.wait_for_timeout(300)
                m = await page.evaluate(MEASURE)
                await ctx.close()
                if m is None:
                    report.append(f'{where} no sidebar is shown')
                    continue
                if len(m['controls']) < 5:
                    report.append(f'{where} only {len(m["controls"])} sidebar controls found')
                if not m['pinned']:
                    report.append(f'{where} the theme button is not inside the window before any scrolling')
                for c in m['controls']:
                    if not c['inside']:
                        report.append(f'{where} "{c["name"]}" cannot be scrolled into the window')
                    elif not c['hit']:
                        report.append(f'{where} "{c["name"]}" is covered at its own centre')
        await browser.close()
    return report


#: The two rules that let the sidebar scroll, as styles.css writes them, and what stood there before them.
FIXED = ('flex:0 1 auto; min-height:132px; overflow-y:auto; overscroll-behavior:contain;',
         'overflow-y:auto; overscroll-behavior:contain;\n  }')
BROKEN = ('', '\n  }')


def self_test(tmp):
    tmp = Path(tmp)
    tmp.mkdir(parents=True, exist_ok=True)
    nhl = tmp / 'reach-nhl.html'
    subprocess.run([sys.executable, 'tests/browser/build_nhl.py', '--out', str(nhl)], cwd=ROOT, check=True,
                   capture_output=True)
    t = nhl.read_text(encoding='utf-8')
    for rule in FIXED:
        if t.count(rule) != 1:
            return [f'self-test: {t.count(rule)} copies of a sidebar scrolling rule, expected 1: {rule!r}']
    broken = tmp / 'reach-nhl-broken.html'
    broken.write_text(rehash(t.replace(FIXED[0], BROKEN[0]).replace(FIXED[1], BROKEN[1])), encoding='utf-8')
    problems = [f'self-test: the real page should be clean: {r}' for r in asyncio.run(check_pages([nhl]))]
    found = asyncio.run(check_pages([broken]))
    if not any('1366x657' in r and ('cannot be scrolled' in r or 'before any scrolling' in r) for r in found):
        problems.append('self-test: the sidebar without its scrolling was not reported at 1366x657')
    return problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('pages', nargs='*')
    ap.add_argument('--self-test', action='store_true')
    ap.add_argument('--tmp')
    a = ap.parse_args()
    report = self_test(a.tmp) if a.self_test else asyncio.run(check_pages(a.pages))
    for line in report:
        print(line)
    print('OK' if not report else f'{len(report)} problem(s)')
    return 1 if report else 0


if __name__ == '__main__':
    sys.exit(main())
