"""The NHL's page: ratings."""
from pathlib import Path

from core.data import ROOT, load_ratings


def build():
    rows = [f'<tr><td>{t}</td><td>{r:+.2f}</td></tr>' for t, r in load_ratings('nhl').items()]
    html = '<h1>NHL</h1><table>' + ''.join(rows) + '</table>'
    out = ROOT / 'out'
    out.mkdir(exist_ok=True)
    (out / 'nhl.html').write_text(html, encoding='utf-8')
    return html


if __name__ == '__main__':
    build()
