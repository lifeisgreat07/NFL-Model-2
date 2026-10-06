"""The NFL's page: ratings, then the week's results."""
from pathlib import Path

from core.data import ROOT, load_ratings, load_results


def build():
    rows = [f'<tr><td>{t}</td><td>{r:+.1f}</td></tr>' for t, r in load_ratings('nfl').items()]
    played = load_results()
    games = [f'<li>{g["away"]} {g["away_score"]} at {g["home"]} {g["home_score"]}</li>' for g in played]
    html = '<h1>NFL</h1><table>' + ''.join(rows) + '</table><ul>' + ''.join(games) + '</ul>'
    out = ROOT / 'out'
    out.mkdir(exist_ok=True)
    (out / 'nfl.html').write_text(html, encoding='utf-8')
    return html


if __name__ == '__main__':
    build()
