"""The March Madness bracket page (Stage 103 item 4), at `march/`.

Built only from the year's lock (`data/ncaam/bracket/lock_<year>.json`, written once by `bracket.py lock`), and
only from 1 March to 15 April of that year: the tournament's weeks, its final early in April. Any other day, or
with no lock, nothing is written and the site has no `march/` page and no home card for it.

The page, top to bottom (Mark's layout options of 2026-11-17, docs/bracket_options): how far to trust it (the
confirmation's verdicts, #760); how the lock has done so far, every played game graded on its saved forecast;
the filled bracket's champion and Final Four; the filled bracket region by region, rounds as columns; every
club's odds of reaching each round; the games played, each with the saved forecast.

Run by hand: python -m src.sports.ncaam.page --out _site/march/index.html [--today 2027-03-20] [--lock FILE]
"""
from __future__ import annotations

import argparse
import html
import json
from datetime import date
from pathlib import Path
from typing import Any

from src.core import page_render
from src.core.page_fill import font_faces_css
from src.sports.ncaam import bracket

ROOT = Path(__file__).resolve().parents[3]
TEMPLATE = Path(__file__).resolve().parent / 'pages'
SHARED_STYLES = ROOT / 'src' / 'dashboard' / 'styles.css'
CONFIRMATION = ROOT / 'experiments' / 'ncaam' / 'stage103' / 'results' / 'confirmation.json'
REGISTRY_URL = ('https://github.com/lifeisgreat07/NFL-Model-2/blob/main/'
                'experiments/ncaam/stage103/registry.json')

#: The rounds a club can reach, as the page names them (bracket.ROUNDS).
ROUND_NAMES = {'round_of_64': 'First round', 'round_of_32': 'Second round', 'sweet_16': 'Sweet 16',
               'elite_8': 'Elite 8', 'final_four': 'Final Four', 'final': 'Final', 'champion': 'Champion'}
#: The games of a region, as columns, by the round they are played in (bracket.PLAYED).
REGION_ROUNDS = (('round_of_64', 'First round'), ('round_of_32', 'Second round'), ('sweet_16', 'Sweet 16'),
                 ('elite_8', 'Elite 8'))
MONTHS = ('Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec')


def shown(today: date) -> bool:
    """Whether the page is published on `today`: 1 March to 15 April."""
    return (today.month == 3) or (today.month == 4 and today.day <= 15)


def pct(x: float) -> str:
    """A chance in whole percent; under half a percent is "<1%", and over 99.5% is ">99%", never 0% or 100%."""
    if x < 0.005:
        return '<1%'
    if x > 0.995:
        return '>99%'
    return f'{round(x * 100)}%'


def day_text(iso: str) -> str:
    d = date.fromisoformat(iso[:10])
    return f'{MONTHS[d.month - 1]} {d.day}, {d.year}'


class Page:
    """What every part of the page needs: the lock, the clubs' seeds and regions, who is out."""

    def __init__(self, doc: dict[str, Any], graded: list[dict[str, Any]]):
        self.doc, self.graded = doc, graded
        self.names: dict[str, str] = doc['names']
        self.seed = {c: int(s) for r in doc['field']['regions'].values() for s, slot in r.items() for c in slot}
        self.region = {c: name for name, r in doc['field']['regions'].items() for slot in r.values() for c in slot}
        self.out = {g['home'] if g['winner'] == g['away'] else g['away'] for g in graded}

    def club(self, c: str) -> str:
        name = html.escape(self.names.get(c, c))
        cls = ' class="mm-out"' if c in self.out else ''
        return f'<span class="mm-seed">{self.seed.get(c, "")}</span> <span{cls}>{name}</span>'

    def trust(self, conf: dict[str, Any]) -> str:
        q = conf['questions']
        h1, h2, m1, m2 = q['H1'], q['H2'], q['M1'], q['M2']
        span = f"{min(conf['tournaments'])} to {max(conf['tournaments'])}"
        words = {'INCONCLUSIVE': 'by a margin too small to call', 'ACCEPT': 'clearly', 'REJECT': 'not at all'}
        market = ('the betting market beat the seeds' if m1['high'] < 0 else
                  'the betting market did no better than the seeds' if m1['low'] > 0 else
                  'the betting market and the seeds came out level')
        return (
            '<section class="mm-trust" aria-labelledby="mm-trust-h"><p><strong id="mm-trust-h">How far to trust it.</strong> '
            f"On the {span} tournaments ({h1['games']} games), Model A's forecasts beat \"the higher seed wins\" "
            f"{words.get(h1['label'], '')}: {h1['label']}. Against the betting market: {h2['label']}. "
            f'Measured beside them, not a test: {market}.</p>'
            f"<p>Picked the winner of the {m2['games']} games between different seeds: Model A {pct(m2['model_a'])}, "
            f"the higher seed {pct(m2['higher_seed'])}, the market {pct(m2['market'])}. "
            f'<a href="{REGISTRY_URL}">The registration</a> fixed every rule before any result.</p></section>')

    def so_far(self) -> str:
        n = len(self.graded)
        if not n:
            return '<p class="mm-lede" id="mm-so-far">No game has been played yet.</p>'
        right = sum(1 for g in self.graded if g['favourite_won'])
        loss = sum(g['log_loss'] for g in self.graded) / n
        return (f'<p class="mm-lede" id="mm-so-far">So far: {n} of {len(self.doc["filled"])} games played; the side the lock gave the '
                f'better chance won {right} of them. Average log loss {loss:.3f} (lower is better; a coin flip '
                'scores 0.693).</p>')

    def glance(self) -> str:
        filled = self.doc['filled']
        rows = []
        for g in [x for x in filled if x['round'] == 'final'] + [x for x in filled if x['round'] == 'final_four']:
            w = g['winner']
            loser = g['clubs'][1] if g['clubs'][0] == w else g['clubs'][0]
            what = 'Champion, over' if g['round'] == 'final' else 'Into the final, over'
            rows.append(f'<div class="mm-row"><span>{self.club(w)} <span class="mm-what">{what} '
                        f'{html.escape(self.names.get(loser, loser))}: {pct(g["forecast"])} to win that game</span>'
                        f'</span><span class="mm-chip">{pct(self.doc["odds"][w]["champion"])} title</span></div>')
        return '<h2>The filled bracket at a glance</h2><div class="mm-glance">' + ''.join(rows) + '</div>'

    def game(self, g: dict[str, Any]) -> str:
        cells = []
        for c in g['clubs']:
            mine = c == g['winner']
            p = g['forecast'] if mine else 1 - g['forecast']
            cells.append(f'<div class="{"mm-pick" if mine else "mm-not"}"><span>{self.club(c)}</span>'
                         f'<span class="mm-num">{pct(p)}</span></div>')
        return '<div class="mm-game">' + ''.join(cells) + '</div>'

    def regions(self) -> str:
        parts = ['<h2>The filled bracket</h2><p class="mm-note">Each game shows the two clubs the bracket puts '
                 'there and the lock\'s chance for each; the bold one is picked. A club that has lost is struck '
                 'through.</p>']
        filled = self.doc['filled']
        for name in self.doc['field']['regions']:
            mine = [g for g in filled if all(self.region.get(c) == name for c in g['clubs'])]
            cols = []
            for rnd, label in REGION_ROUNDS:
                games = ''.join(self.game(g) for g in mine if g['round'] == rnd)
                cols.append(f'<div class="mm-col"><h4>{label}</h4><div class="mm-games">{games}</div></div>')
            parts.append(f'<section class="mm-region"><h3>{html.escape(name)}</h3><div class="mm-scroll">'
                         f'<div class="mm-cols">{"".join(cols)}</div></div></section>')
        last = [g for g in filled if g['round'] in ('final_four', 'final')]
        cols = [f'<div class="mm-col"><h4>{label}</h4><div class="mm-games">'
                f'{"".join(self.game(g) for g in last if g["round"] == rnd)}</div></div>'
                for rnd, label in (('final_four', 'Final Four'), ('final', 'Final'))]
        semis = ' and '.join(f'{a} v {b}' for a, b in self.doc['field']['semifinals'])
        parts.append(f'<section class="mm-region"><h3>Final Four: {html.escape(semis)}</h3><div class="mm-scroll">'
                     f'<div class="mm-cols" style="--mm-cols:2">{"".join(cols)}</div></div></section>')
        return ''.join(parts)

    def odds_table(self) -> str:
        odds = self.doc['odds']
        rounds = bracket.ROUNDS[1:]
        # A phone keeps the later rounds; the second round and the Sweet 16 are on wider screens.
        hide = {r: (' mm-hide-phone' if r in ('round_of_32', 'sweet_16') else '') for r in rounds}
        head = ''.join(f'<th scope="col" class="mm-num{hide[r]}">{ROUND_NAMES[r]}</th>' for r in rounds)
        rows = []
        for c in sorted(odds, key=lambda c: (-odds[c]['champion'], self.seed.get(c, 99), self.names.get(c, c))):
            cells = ''.join(f'<td class="mm-num{hide[r]}">{pct(odds[c][r])}</td>' for r in rounds)
            rows.append(f'<tr><td>{self.club(c)} <span class="mm-region-name">{html.escape(self.region[c])}</span>'
                        f'</td>{cells}</tr>')
        return ('<h2>Every club\'s chance of reaching each round</h2><div class="table-wrap"><table class="mm-table">'
                f'<thead><tr><th scope="col">Club</th>{head}</tr></thead><tbody>{"".join(rows)}</tbody></table></div>'
                '<p class="mm-note">From the lock: the chance of winning each game ahead, over every club that could '
                'be met there. Worked out exactly, not by simulating.</p>')

    def played(self) -> str:
        if not self.graded:
            return ''
        rows = []
        for g in sorted(self.graded, key=lambda g: (g['day'], g['game_id']), reverse=True):
            winner, loser = g['winner'], g['away'] if g['winner'] == g['home'] else g['home']
            p = g['home_forecast'] if winner == g['home'] else 1 - g['home_forecast']
            mark = ('<span class="mm-right">Correct</span>' if g['favourite_won']
                    else '<span class="mm-wrong">Missed</span>')
            day = day_text(g['day']).rsplit(',', 1)[0]  # the year is in the page's title
            rows.append(f'<tr><td class="mm-nowrap">{html.escape(self.names.get(winner, winner))} beat '
                        f'{html.escape(self.names.get(loser, loser))}</td><td class="mm-nowrap mm-hide-phone">{day}</td>'
                        f'<td class="mm-num">{pct(p)}</td><td>{mark}</td></tr>')
        return ('<h2>Games played</h2><div class="table-wrap"><table class="mm-table"><thead><tr>'
                '<th scope="col">Game</th><th scope="col" class="mm-hide-phone">Day</th>'
                '<th scope="col" class="mm-num">Winner\'s saved chance</th>'
                f'<th scope="col">The lock\'s side</th></tr></thead><tbody>{"".join(rows)}</tbody></table></div>')

    def body(self, conf: dict[str, Any]) -> str:
        year = self.doc['tournament']
        return ('<nav class="mm-top" aria-label="Site"><a href="../">Sportalytics home</a></nav>'
                f'<h1>March Madness {year}: the bracket</h1>'
                '<p class="mm-lede">Model A\'s forecast for every game of the men\'s tournament, saved once on '
                f'{day_text(self.doc["locked_utc"])} before the First Four, from every game through '
                f'{day_text(self.doc["games_through"])}, and never changed. Each club\'s chance of reaching each '
                'round, and one filled-in bracket that starts from the likeliest champion and works down.</p>'
                + self.trust(conf) + self.so_far() + self.glance() + self.regions() + self.odds_table()
                + self.played())


def render(doc: dict[str, Any], graded: list[dict[str, Any]], conf: dict[str, Any], font_faces: str = '') -> str:
    """The page, by the renderer every page shares (src/core/page_render.py)."""
    return page_render.finish(page_render.assemble(TEMPLATE, {'styles.css': SHARED_STYLES}),
                              {'__FONT_FACES__': font_faces, '__MARCH_BODY__': Page(doc, graded).body(conf)})


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description='Build the March Madness bracket page, in its weeks only')
    ap.add_argument('--out', default='_site/march/index.html')
    ap.add_argument('--today', default=None, help='the day to build for (default: today)')
    ap.add_argument('--lock', default=None, help="a lock file to use instead of the year's")
    args = ap.parse_args(argv)
    today = date.fromisoformat(args.today) if args.today else date.today()
    path = Path(args.lock) if args.lock else bracket.OUT / f'lock_{today.year}.json'
    if not shown(today) or not path.exists():
        print(f'no March page: {"no lock at " + path.name if shown(today) else "not March or early April"}')
        return 0
    doc = json.loads(path.read_text(encoding='utf-8'))
    graded = bracket.graded(doc)
    conf = json.loads(CONFIRMATION.read_text(encoding='utf-8'))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render(doc, graded, conf, font_faces_css()), encoding='utf-8')
    print(f'wrote {out} ({out.stat().st_size} bytes)')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
