"""The last 30 runs of the jobs that run with nobody watching, for Checking
the AI's work (Stage 41 item 4, from the 2026-10-04 fourth audit).

The page already counts what Booth found on every pull request. It said
nothing about the scheduled jobs: whether Tuesday's run graded the week,
whether Thursday's locked it, whether the nightly checks passed. A reader
had to open the Actions tab to find out, and most readers never will.

Read from GitHub's public Actions API when the site is built, by
.github/workflows/deploy-pages.yml, into data/recent_runs.json -- which is
gitignored, not committed. A file every workflow committed would be a new
writer in every workflow and a commit per run; the build reads the record
GitHub already keeps.

    python -m src.pipeline.recent_runs --repo OWNER/NAME --out data/recent_runs.json

GITHUB_TOKEN is used when set (the deploy job's token can read Actions);
without one the anonymous limit is 60 calls an hour, and this
makes one call per workflow.

A failure to read is not a failure to build: it prints why, writes nothing,
and exits 0, and the page says the history was not read for this build. The
site is not held back because GitHub's API was slow.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

#: The unattended jobs, by workflow file, with the name the page shows.
WATCHED = {
    'weekly-update.yml': 'Weekly update',
    'weekend-refresh.yml': 'Weekend refresh',
    'nightly-canary.yml': 'Nightly data check',
    'nightly-mutation.yml': 'Nightly test of the tests',
    'nightly-random-order.yml': 'Nightly shuffled tests',
}
SHOWN = 30
API = 'https://api.github.com'


def _get(url, token=None, opener=urllib.request.urlopen):
    req = urllib.request.Request(url, headers={'Accept': 'application/vnd.github+json',
                                               'User-Agent': 'nfl-model-2-recent-runs'})
    if token:
        req.add_header('Authorization', f'Bearer {token}')
    with opener(req, timeout=20) as resp:
        return json.load(resp)


def _time(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00')).astimezone(UTC) if value else None


def row(run, shown_name):
    """One run as the page reads it. Duration only once the run has finished."""
    started = _time(run.get('run_started_at') or run.get('created_at'))
    ended = _time(run.get('updated_at')) if run.get('status') == 'completed' else None
    return {
        'workflow': shown_name,
        'event': run.get('event'),
        'conclusion': run.get('conclusion') if run.get('status') == 'completed' else None,
        'started_utc': started.strftime('%Y-%m-%dT%H:%M:%SZ') if started else None,
        'minutes': round((ended - started).total_seconds() / 60, 1) if started and ended else None,
        'url': run.get('html_url'),
    }


def fetch(repo, token=None, get=_get, shown=SHOWN):
    """The `shown` most recent runs across WATCHED, newest first."""
    rows = []
    for file, name in WATCHED.items():
        data = get(f'{API}/repos/{repo}/actions/workflows/{file}/runs?per_page={shown}', token)
        rows.extend(row(r, name) for r in data.get('workflow_runs', []))
    rows.sort(key=lambda r: r['started_utc'] or '', reverse=True)
    return rows[:shown]


def main(argv=None, get=_get, now=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--repo', required=True)
    ap.add_argument('--out', required=True)
    args = ap.parse_args(argv)
    token = os.environ.get('GITHUB_TOKEN')
    try:
        runs = fetch(args.repo, token, get)
    except Exception as exc:  # any failure to read: the build goes on without it
        print(f'recent runs not read ({type(exc).__name__}: {exc}); the page will say so')
        return 0
    now = now or datetime.now(UTC)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({'read_utc': now.strftime('%Y-%m-%dT%H:%M:%SZ'), 'runs': runs},
                              indent=2) + '\n', encoding='utf-8')
    print(f'{len(runs)} recent runs written to {out}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
