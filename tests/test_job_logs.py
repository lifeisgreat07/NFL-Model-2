"""
Line Judge's diagnosis reads the run's logs (src/core/job_logs.py, #517).

Line Judge's first real finding was diagnosed from two empty files: `gh api`
refused to write the logs because they hold colour codes, and the step's
`|| true` let the refusal pass. What is held here:

  - the colour codes are stripped and the text kept;
  - a log that cannot be fetched, or comes back empty, is a `LOGS UNAVAILABLE`
    note that says why, never an empty file; one bad log does not hide the
    others; a job still running is not read;
  - a fetch that got no log at all exits 1 and says so; a partial one warns;
  - the token goes to the API and not to the signed URL a log redirects to,
    and neither the token nor that URL is printed;
  - nothing shells out to `gh`, so no release of it can refuse again, and the
    module needs nothing installed.

Run with: pytest tests/test_job_logs.py -v
"""
import ast
import json
import sys
from pathlib import Path

import pytest

from src.core import job_logs as jl

ESC = '\x1b'
COLOURED = f'{ESC}[36;1mRun python -m x{ESC}[0m\n{ESC}[31;1merror{ESC}[0m: boom\n'
PLAIN = 'Run python -m x\nerror: boom\n'
REPO = 'owner/repo'


def jobs_doc(*jobs):
    return json.dumps({'jobs': [{'id': i, 'name': n, 'status': s} for i, n, s in jobs]})


class FakeApi:
    """api(path) -> text: the run's job list, then each job's log. Records the paths asked."""

    def __init__(self, jobs, logs):
        self.jobs, self.logs, self.asked = jobs, logs, []

    def __call__(self, path):
        self.asked.append(path)
        if '/jobs?' in path:
            if isinstance(self.jobs, Exception):
                raise self.jobs
            return self.jobs if isinstance(self.jobs, str) else jobs_doc(*self.jobs)
        out = self.logs[int(path.rsplit('/jobs/', 1)[1].split('/')[0])]
        if isinstance(out, Exception):
            raise out
        return out


TWO = [(1, 'daily', 'completed'), (2, 'line-judge', 'completed')]


@pytest.mark.parametrize('raw, want', [
    (COLOURED, PLAIN),
    (f'{ESC}[2K{ESC}[1Gdone{ESC}[0m', 'done'),
    (f'{ESC}[?25lhidden cursor{ESC}[?25h', 'hidden cursor'),
    ('no codes at all', 'no codes at all'),
    ('a [bracket] and 100% stay', 'a [bracket] and 100% stay'),
], ids=['colour', 'erase-and-column', 'cursor', 'plain', 'brackets'])
def test_the_colour_codes_are_stripped_and_the_text_kept(raw, want):
    assert jl.strip_ansi(raw) == want


def test_a_fetched_log_is_written_without_codes(tmp_path):
    assert jl.fetch(REPO, '9', tmp_path, FakeApi(TWO, {1: COLOURED, 2: COLOURED})) == 2
    for name in ('daily.log', 'line-judge.log'):
        text = (tmp_path / name).read_text(encoding='utf-8')
        assert text == PLAIN and ESC not in text


def test_a_refused_fetch_leaves_a_note_not_an_empty_file(tmp_path):
    refused = jl.LogError('the response contains terminal escape sequences')
    assert jl.fetch(REPO, '9', tmp_path, FakeApi(TWO, {1: refused, 2: COLOURED})) == 1
    note = (tmp_path / 'daily.log').read_text(encoding='utf-8')
    assert note.startswith(jl.UNAVAILABLE) and 'escape sequences' in note and "'daily'" in note
    assert (tmp_path / 'line-judge.log').read_text(encoding='utf-8') == PLAIN
    assert all(f.stat().st_size > 0 for f in tmp_path.iterdir()), 'an empty file is what #517 handed the agent'


def test_an_empty_body_is_a_note_not_an_empty_file(tmp_path):
    assert jl.fetch(REPO, '9', tmp_path, FakeApi(TWO, {1: '', 2: f'{ESC}[0m  \n'})) == 0
    for name in ('daily.log', 'line-judge.log'):
        text = (tmp_path / name).read_text(encoding='utf-8')
        assert text.startswith(jl.UNAVAILABLE) and 'empty body' in text


def test_a_fetch_that_got_nothing_exits_1_and_says_so(tmp_path, capsys):
    api = FakeApi(TWO, {1: jl.LogError('nope'), 2: jl.LogError('nope')})
    assert jl.main(['--repo', REPO, '--run', '9', '--out', str(tmp_path)], api=api) == 1
    out = capsys.readouterr().out
    assert '::error::' in out and 'daily.log' in out
    assert (tmp_path / 'daily.log').read_text(encoding='utf-8').startswith(jl.UNAVAILABLE)


def test_a_partial_fetch_exits_0_with_a_warning(tmp_path, capsys):
    api = FakeApi(TWO, {1: jl.LogError('nope'), 2: COLOURED})
    assert jl.main(['--repo', REPO, '--run', '9', '--out', str(tmp_path)], api=api) == 0
    out = capsys.readouterr().out
    assert '::warning::1 job log(s) could not be fetched' in out and '::error::' not in out


def test_a_whole_fetch_exits_0_and_lists_the_sizes(tmp_path, capsys):
    assert jl.main(['--repo', REPO, '--run', '9', '--out', str(tmp_path)], api=FakeApi(TWO, {1: COLOURED, 2: COLOURED})) == 0
    out = capsys.readouterr().out
    assert f'daily.log: {len(PLAIN)} bytes' in out and '::' not in out


@pytest.mark.parametrize('jobs, why', [
    (jl.LogError('GitHub answered 403 for the jobs'), 'GitHub answered 403'),
    ('this is not json', 'Expecting value'),
    ('{"jobs": [{"name": "no id", "status": "completed"}]}', "'id'"),
], ids=['refused', 'not-json', 'job-without-an-id'])
def test_a_job_list_that_cannot_be_read_is_a_note(tmp_path, jobs, why):
    assert jl.fetch(REPO, '9', tmp_path, FakeApi(jobs, {})) == 0
    note = (tmp_path / '_jobs.log').read_text(encoding='utf-8')
    assert note.startswith(jl.UNAVAILABLE) and why in note


def test_no_finished_job_is_a_note(tmp_path):
    assert jl.fetch(REPO, '9', tmp_path, FakeApi([(3, 'diagnose / diagnose', 'in_progress')], {})) == 0
    assert 'no finished job' in (tmp_path / '_jobs.log').read_text(encoding='utf-8')


def test_a_job_still_running_is_not_read(tmp_path):
    api = FakeApi(TWO + [(3, 'diagnose / diagnose', 'in_progress')], {1: COLOURED, 2: COLOURED})
    assert jl.fetch(REPO, '9', tmp_path, api) == 2
    assert not any('/jobs/3/' in p for p in api.asked)
    assert sorted(f.name for f in tmp_path.iterdir()) == ['daily.log', 'line-judge.log']


def test_file_names_and_a_clash_between_two_jobs(tmp_path):
    assert jl.file_name('line-judge') == 'line-judge.log'
    assert jl.file_name('diagnose / diagnose') == 'diagnose___diagnose.log'
    api = FakeApi([(1, 'a b', 'completed'), (2, 'a_b', 'completed')], {1: 'one\n', 2: 'two\n'})
    assert jl.fetch(REPO, '9', tmp_path, api) == 2
    assert sorted(f.read_text(encoding='utf-8') for f in tmp_path.iterdir()) == ['one\n', 'two\n']


class FakeTransport:
    def __init__(self, *replies):
        self.replies, self.calls = list(replies), []

    def __call__(self, url, headers):
        self.calls.append((url, headers))
        return self.replies.pop(0) if len(self.replies) > 1 else self.replies[0]


SIGNED = 'https://blob.example/logs?sig=SECRET'


def test_the_token_goes_to_the_api_and_not_to_the_signed_url():
    t = FakeTransport((302, {'Location': SIGNED}, b''), (200, {}, b'the log'))
    assert jl.make_api('TOKEN', t)('repos/o/r/actions/jobs/1/logs') == 'the log'
    (url0, h0), (url1, h1) = t.calls
    assert url0 == jl.API + 'repos/o/r/actions/jobs/1/logs' and h0['Authorization'] == 'Bearer TOKEN'
    assert url1 == SIGNED and not any(k.lower() == 'authorization' for k in h1)


def test_a_redirect_is_followed_whatever_the_case_of_its_header():
    t = FakeTransport((302, {'location': SIGNED}, b''), (200, {}, b'ok'))
    assert jl.make_api('T', t)('x') == 'ok'


def test_an_error_says_what_github_said_and_never_the_signed_url():
    t = FakeTransport((302, {'Location': SIGNED}, b''), (404, {}, b'{"message": "Not Found"}'))
    with pytest.raises(jl.LogError) as caught:
        jl.make_api('TOKEN', t)('repos/o/r/actions/jobs/1/logs')
    msg = str(caught.value)
    assert '404' in msg and 'Not Found' in msg and 'SECRET' not in msg and 'blob.example' not in msg and 'TOKEN' not in msg


def test_a_refusal_from_the_api_is_an_error_with_its_reason():
    t = FakeTransport((403, {}, b'{"message": "Resource not accessible by integration"}'))
    with pytest.raises(jl.LogError, match='403.*Resource not accessible'):
        jl.make_api('T', t)('x')


def test_a_redirect_loop_ends():
    t = FakeTransport((302, {'Location': SIGNED}, b''))
    with pytest.raises(jl.LogError, match='302'):
        jl.make_api('T', t)('x')
    assert len(t.calls) == 4, 'the first call and three hops'


def test_a_byte_order_mark_is_dropped():
    assert jl.make_api('T', FakeTransport((200, {}, '﻿line one\n'.encode())))('x') == 'line one\n'


def test_without_a_token_it_says_so_and_exits_1(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv('GH_TOKEN', raising=False)
    monkeypatch.delenv('GITHUB_TOKEN', raising=False)
    assert jl.main(['--repo', REPO, '--run', '9', '--out', str(tmp_path)]) == 1
    assert '::error::no GH_TOKEN' in capsys.readouterr().out


def test_the_token_is_used_and_never_printed(tmp_path, monkeypatch, capsys):
    seen = []
    monkeypatch.setenv('GH_TOKEN', 'ghs_SECRET')
    monkeypatch.setattr(jl, 'make_api', lambda token: seen.append(token) or FakeApi(TWO, {1: COLOURED, 2: COLOURED}))
    assert jl.main(['--repo', REPO, '--run', '9', '--out', str(tmp_path)]) == 0
    assert seen == ['ghs_SECRET']
    assert 'ghs_SECRET' not in capsys.readouterr().out


SOURCE = Path(jl.__file__).read_text(encoding='utf-8')


def test_the_module_never_shells_out_to_gh():
    # `gh api` is what refused on 2026-10-16; with none, no release of it can.
    assert 'subprocess' not in SOURCE and "'gh'" not in SOURCE and 'gh api' not in SOURCE.split('"""', 2)[2]


def test_the_module_needs_nothing_installed():
    # The diagnosis job runs it on the runner's own Python, before any install.
    tree = ast.parse(SOURCE)
    imported = {a.name.split('.')[0] for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    imported |= {n.module.split('.')[0] for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module}
    assert imported <= set(sys.stdlib_module_names), sorted(imported - set(sys.stdlib_module_names))
