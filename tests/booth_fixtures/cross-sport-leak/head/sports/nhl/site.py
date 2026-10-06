"""The NHL's page: ratings, then the latest results."""
from pathlib import Path

from core.data import ROOT, load_ratings, load_results


def build():
    rows = [f'<tr><td>{t}</td><td>{r:+.2f}</td></tr>' for t, r in load_ratings('nhl').items()]
    results = load_results()
    games = [f'<li>{g["away"]} {g["away_score"]} at {g["home"]} {g["home_score"]}</li>' for g in results]
    html = '<h1>NHL</h1><table>' + ''.join(rows) + '</table><h2>Latest results</h2><ul>' + ''.join(games) + '</ul>'
    out = ROOT / 'out'
    out.mkdir(exist_ok=True)
    (out / 'nhl.html').write_text(html, encoding='utf-8')
    return html


if __name__ == '__main__':
    build()
