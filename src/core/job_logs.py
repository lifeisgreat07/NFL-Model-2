"""
A run's finished job logs, one file per job, for Line Judge's diagnosing agent.

The diagnosis job runs inside the run it diagnoses, so `gh run view --log`
refuses (the run is not finished); each finished job's log is read on its own
through the API instead. Two things went wrong with the shell this replaces
(#517, Line Judge's first real finding):

  - `gh api` refused to write the logs to a file: a job log is full of colour
    codes, and the runner's `gh` stops at "the response contains terminal
    escape sequences" unless given a flag that only newer releases have (the
    one in the cloud sandbox does not know it). Both logs were refused;
  - the loop ended in `|| true`, so the refusals left two empty files under a
    green step, and the agent diagnosed a finding from nothing and said so.

Now the API is called directly, so there is no `gh` to refuse and no version
of it to depend on; the colour codes are stripped from what is kept; a log
that cannot be fetched, or comes back empty, is written as a `LOGS UNAVAILABLE`
note that says why, never as an empty file; and the module exits 1 when no log
at all was fetched, so the step shows red.

A log is served as a redirect to a signed URL, which takes no token: the token
goes to the API only, and the redirect is followed by hand. Neither the token
nor the signed URL is ever printed.

Stdlib only: the diagnosis job runs it on the runner's own Python, with no
install step. GH_TOKEN (the job's read-only token) authenticates the call.

    python3 -m src.core.job_logs --repo OWNER/REPO --run 123 --out DIR
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from collections.abc import Callable, Sequence
from http.client import HTTPMessage
from pathlib import Path
from typing import IO

API = 'https://api.github.com/'
USER_AGENT = 'nfl-model-2-line-judge'
REDIRECTS = (301, 302, 303, 307, 308)
UNAVAILABLE = 'LOGS UNAVAILABLE'
# Control sequences (colour, cursor) and nothing else: a log line keeps its text.
ANSI = re.compile(r'\x1b\[[0-9;?]*[ -/]*[@-~]')

#: One request, no redirects followed: (url, headers) -> (status, headers, body).
Transport = Callable[[str, dict[str, str]], tuple[int, dict[str, str], bytes]]
Api = Callable[[str], str]


class LogError(RuntimeError):
    """A log, or the list of jobs, could not be read; the message says why."""


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req: urllib.request.Request, fp: IO[bytes], code: int, msg: str,
                         headers: HTTPMessage, newurl: str) -> urllib.request.Request | None:
        return None


def urllib_transport(url: str, headers: dict[str, str]) -> tuple[int, dict[str, str], bytes]:
    opener = urllib.request.build_opener(_NoRedirect)
    try:
        with opener.open(urllib.request.Request(url, headers=headers), timeout=60) as r:
            return int(r.status), dict(r.headers), bytes(r.read())
    except urllib.error.HTTPError as exc:
        return exc.code, dict(exc.headers), exc.read()
    except (urllib.error.URLError, OSError) as exc:
        raise LogError(f'could not reach GitHub: {exc}') from exc


def make_api(token: str, transport: Transport = urllib_transport) -> Api:
    """GET one API path. The token goes to the API; the signed URL a log
    redirects to is fetched without it."""
    def api(path: str) -> str:
        status, headers, body = transport(API + path, {
            'Authorization': f'Bearer {token}', 'Accept': 'application/vnd.github+json',
            'X-GitHub-Api-Version': '2022-11-28', 'User-Agent': USER_AGENT})
        for _ in range(3):
            where = {k.lower(): v for k, v in headers.items()}.get('location')
            if status not in REDIRECTS or not where:
                break
            status, headers, body = transport(where, {'User-Agent': USER_AGENT})
        if status != 200:
            raise LogError(f'GitHub answered {status} for {path}: {body.decode("utf-8", "replace")[:200].strip()}')
        return body.decode('utf-8', 'replace').lstrip('﻿')
    return api


def strip_ansi(text: str) -> str:
    return ANSI.sub('', text)


def file_name(job: str) -> str:
    """A job's log file: its name with anything but letters, digits, `_` and `-` as `_`."""
    return re.sub(r'[^A-Za-z0-9_-]', '_', job) + '.log'


def _write(path: Path, text: str) -> None:
    """The text as UTF-8 bytes, so a log reads the same on every platform (no newline translation)."""
    path.write_bytes(text.encode('utf-8'))


def finished_jobs(repo: str, run_id: str, api: Api) -> list[tuple[int, str]]:
    """(id, name) of every job of the run that has finished, in the API's order."""
    doc = json.loads(api(f'repos/{repo}/actions/runs/{run_id}/jobs?per_page=100') or '{}')
    return [(int(j['id']), str(j['name'])) for j in doc.get('jobs', []) if j.get('status') == 'completed']


def fetch(repo: str, run_id: str, out: Path, api: Api) -> int:
    """Write one file per finished job into `out`. Returns how many held a real log."""
    out.mkdir(parents=True, exist_ok=True)
    try:
        jobs = finished_jobs(repo, run_id, api)
    except (LogError, ValueError, KeyError, TypeError) as exc:
        _write(out / '_jobs.log', f"{UNAVAILABLE}: the run's list of jobs could not be read: {exc}\n")
        return 0
    if not jobs:
        _write(out / '_jobs.log', f'{UNAVAILABLE}: the run has no finished job yet.\n')
        return 0
    fetched = 0
    for job_id, name in jobs:
        path = out / file_name(name)
        if path.exists():
            path = out / f'{path.stem}-{job_id}.log'
        try:
            text = strip_ansi(api(f'repos/{repo}/actions/jobs/{job_id}/logs'))
            if not text.strip():
                raise LogError('the API returned an empty body')
        except LogError as exc:
            _write(path, f'{UNAVAILABLE} for job {name!r} (id {job_id}): {exc}\n')
            continue
        _write(path, text)
        fetched += 1
    return fetched


def main(argv: Sequence[str] | None = None, api: Api | None = None) -> int:
    p = argparse.ArgumentParser(description="Write the run's finished job logs, one file per job.")
    p.add_argument('--repo', required=True, help='OWNER/REPO')
    p.add_argument('--run', required=True, help="the run's id")
    p.add_argument('--out', required=True, type=Path, help='the folder to write into')
    a = p.parse_args(argv)
    if api is None:
        token = os.environ.get('GH_TOKEN') or os.environ.get('GITHUB_TOKEN')
        if not token:
            print('::error::no GH_TOKEN, so no job log can be fetched')
            return 1
        api = make_api(token)
    fetched = fetch(a.repo, a.run, a.out, api)
    notes = 0
    for f in sorted(a.out.iterdir()):
        print(f'{f.name}: {f.stat().st_size} bytes')
        notes += f.read_text(encoding='utf-8').startswith(UNAVAILABLE)
    if not fetched:
        print('::error::no job log could be fetched, so the diagnosis has none to read '
              f'(see the {UNAVAILABLE} notes above)')
        return 1
    if notes:
        print(f'::warning::{notes} job log(s) could not be fetched ({UNAVAILABLE} notes were written instead)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
