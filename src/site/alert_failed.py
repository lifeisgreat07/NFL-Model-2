"""Open or comment on one issue per sport whose page did not build (Stage 53).

Reads the report `src.site.build` wrote. A sport that built says nothing; a
sport that failed gets an issue titled for it, "NHL: page build failed", so
one sport's broken build never reads as another's and never hides inside a
red deploy run. Uses the core's one-issue-per-problem alerts.

Run by the deploy:  python -m src.site.alert_failed site-report.json --run-url <url>
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from src.core import alerts


def failed(report: dict[str, Any]) -> list[dict[str, Any]]:
    return [s for s in report.get('sports', []) if not s.get('built')]


def title(sport: str) -> str:
    return f'{sport.upper()}: page build failed'


def body(entry: dict[str, Any], run_url: str) -> str:
    kept = ('The page that was live before this deploy was published again unchanged.'
            if entry.get('kept_live') else
            'There was no live page to keep, so this sport has no page on the site until it builds.')
    log = '\n'.join(entry.get('log') or []) or '(no step ran)'
    return (f"The {entry['sport'].upper()} page did not build in this deploy: {run_url}\n\n"
            f"Error: {entry.get('error') or 'unknown'}\n\n{kept}\n\n"
            f"Steps:\n```\n{log}\n```\n\n"
            'The other sports published as usual. Close this issue once the build is fixed.')


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('report')
    ap.add_argument('--run-url', required=True)
    args = ap.parse_args(argv)
    data = json.loads(Path(args.report).read_text(encoding='utf-8'))
    for entry in failed(data):
        action, ref = alerts.open_or_comment(title(entry['sport']), body(entry, args.run_url))
        print(f"{entry['sport']}: {action} {ref}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
