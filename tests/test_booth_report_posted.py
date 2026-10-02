"""
A Booth run that posts nothing must fail. Two halves, both here.

The RULES live in src/agents/booth_report_posted.py and are checked over synthetic
comment lists, because the interesting branches -- "posted nothing", "posted
for the wrong commit", "a stale report from the previous run" -- are states
no real PR is in when the suite runs. (CLAUDE.md: if a guard's failure can only
be produced by data the repository does not contain, it needs synthetic inputs.)

The WIRING lives in booth-pr-audit.yml and is checked by line position, the
same way tests/test_booth_edited_trigger.py does it, because PyYAML is not
installed where this suite runs. The ordering matters as much as the presence:
the SHA and start time must be recorded before Booth runs, and the check must
run after it.

Booth cannot audit the PR that introduces this -- the Claude Code action skips
when a PR changes its own workflow file -- so this file and its mutation cases
are most of the evidence. The rest is the next PR's run.

Run with: pytest tests/test_booth_report_posted.py -v
"""
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent

from src.agents.booth_report_posted import check, head_matches, load_comments, main  # noqa: E402

WORKFLOW = REPO_ROOT / '.github' / 'workflows' / 'booth-pr-audit.yml'

SHA = 'c901b01c286eda828336e64f19f689132aa9c602'
OTHER = '2668063aaaabbbbccccddddeeeeffff000011112'
STARTED = '2026-09-22T13:32:43Z'


def report(head=SHA[:7], overall='SAFE TO MERGE'):
    block = {
        'pr': 82, 'head': head, 'overall': overall,
        'claims': [{'id': 1, 'verdict': 'CONFIRMED', 'implicates': []}],
    }
    return (
        '## Booth Audit: PR #82\n\n'
        f'Head commit audited: `{head}`\n\n'
        'Claims checked: 1\nConfirmed: 1\nDiscrepancies: 0\nUnverifiable: 0\n\n'
        f'### Overall verdict\n{overall}\n\n'
        '```booth-verdict\n' + json.dumps(block, indent=2) + '\n```\n'
    )


def comment(body, created='2026-09-22T13:41:57Z', kind='Bot', login='claude[bot]', cid=1):
    return {'id': cid, 'html_url': f'https://example/c{cid}', 'created_at': created,
            'user': {'login': login, 'type': kind}, 'body': body}


# --------------------------------------------------------------------- rules

def test_a_report_for_this_commit_passes():
    ok, message = check([comment(report())], SHA, STARTED)
    assert ok, message
    assert 'SAFE TO MERGE' in message


def test_no_comments_at_all_fails():
    """The #80 case: the action succeeded and the thread is silent."""
    ok, message = check([], SHA, STARTED)
    assert not ok
    assert 'NO report' in message


def test_a_report_from_the_previous_run_does_not_count():
    """An `edited` re-audit shares its head SHA with the last one.

    Without the time floor, the first audit on a commit would satisfy every
    later run on it forever -- the exact silent pass this exists to stop.
    """
    old = comment(report(), created='2026-09-22T13:29:37Z')
    ok, message = check([old], SHA, STARTED)
    assert not ok
    assert 'NO report' in message


def test_a_person_quoting_a_report_does_not_count():
    """PR #82 carries a comment under Mark's login written by a Scout session."""
    quoted = comment(report(), kind='User', login='lifeisgreat07')
    ok, _ = check([quoted], SHA, STARTED)
    assert not ok


def test_another_apps_bot_does_not_count():
    """Stage 30 item 5. Any bot used to count; a report-shaped comment from
    some other app's bot during the run would have passed as Booth's."""
    other = comment(report(), kind='Bot', login='dependabot[bot]')
    ok, message = check([other], SHA, STARTED)
    assert not ok and 'NO report' in message


def test_both_of_booths_accounts_count():
    """The Claude app posted every report before Stage 23; the workflow's own
    token posts them since. Both must still be read as Booth."""
    for login in ('claude[bot]', 'github-actions[bot]'):
        ok, message = check([comment(report(), login=login)], SHA, STARTED)
        assert ok, f'{login}: {message}'


def test_a_report_for_a_different_commit_fails_and_says_which():
    ok, message = check([comment(report(head=OTHER[:7]))], SHA, STARTED)
    assert not ok
    assert OTHER[:7] in message and SHA[:7] in message


def test_a_bot_comment_with_no_verdict_block_fails():
    """Readable by a person, invisible to data/agent_log.json."""
    ok, message = check([comment('## Booth Audit\n\nran out of turns')], SHA, STARTED)
    assert not ok
    assert 'no booth-verdict block' in message


def test_a_malformed_verdict_block_fails_rather_than_passing_as_absent():
    body = report().replace('"overall": "SAFE TO MERGE"', '"overall": "LGTM"')
    ok, message = check([comment(body)], SHA, STARTED)
    assert not ok
    assert 'malformed' in message


def test_one_good_report_among_other_bot_chatter_passes():
    chatter = comment('Claude is working on this...', cid=1)
    good = comment(report(), cid=2)
    ok, message = check([chatter, good], SHA, STARTED)
    assert ok, message
    assert 'c2' in message


def test_a_truncated_head_sha_is_refused():
    """The workflow must record a full SHA; a short one could match anything."""
    ok, message = check([comment(report())], SHA[:7], STARTED)
    assert not ok
    assert 'not a full SHA' in message


@pytest.mark.parametrize('block_head, expected', [
    (SHA, True),
    (SHA[:7], True),
    (SHA[:12].upper(), True),
    (SHA[:6], False),      # too short to be evidence
    ('', False),
    (OTHER[:7], False),
    (SHA[1:8], False),     # a substring is not a prefix
])
def test_head_matching(block_head, expected):
    assert head_matches(block_head, SHA) is expected


def test_paginated_output_is_read_across_pages():
    """`gh api --paginate` writes `[...][...]`, one array per page.

    json.loads rejects that, and only on a PR long enough to need a second
    page -- the long-running PRs where a missed report is likeliest.
    """
    page1 = json.dumps([comment('first', cid=1)])
    page2 = json.dumps([comment(report(), cid=2)])
    comments = load_comments(page1 + page2 + '\n')
    assert [c['id'] for c in comments] == [1, 2]
    assert check(comments, SHA, STARTED)[0]


def test_main_exits_non_zero_on_silence(tmp_path):
    path = tmp_path / 'comments.json'
    path.write_text('[]', encoding='utf-8')
    assert main(['x', str(path), SHA, STARTED]) == 1
    path.write_text(json.dumps([comment(report())]), encoding='utf-8')
    assert main(['x', str(path), SHA, STARTED]) == 0


# -------------------------------------------------------------------- wiring

def _steps():
    """(name, body-text) for each step of the audit job, in order."""
    if not WORKFLOW.is_file():
        pytest.skip("booth-pr-audit.yml not present in this checkout")
    lines = WORKFLOW.read_text(encoding='utf-8').splitlines()
    steps, current = [], None
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('- name:') and line.startswith('      - '):
            current = [stripped[len('- name:'):].strip(), []]
            steps.append(current)
        elif current is not None and not stripped.startswith('#'):
            current[1].append(line)
    return [(name, '\n'.join(body)) for name, body in steps]


def _index(steps, predicate, what):
    hits = [i for i, (name, body) in enumerate(steps) if predicate(name, body)]
    assert len(hits) == 1, f"expected exactly one step that {what}, found {len(hits)}: {[s[0] for s in steps]}"
    return hits[0]


def test_the_scan_finds_the_steps_it_is_about():
    """Vacuity guard: a parser that finds nothing would pass every ordering test."""
    names = [name for name, _ in _steps()]
    assert 'Run Booth' in names and len(names) >= 5, names


def test_the_check_runs_after_booth():
    steps = _steps()
    booth = _index(steps, lambda n, b: 'anthropics/claude-code-action' in b, 'runs Booth')
    check_step = _index(steps, lambda n, b: 'booth_report_posted' in b and 'gh api' in b,
                        'checks for a report')
    assert check_step > booth, "the report check runs before Booth has had a chance to post"
    body = steps[check_step][1]
    assert 'continue-on-error' not in body, "a report check that cannot fail the job checks nothing"
    assert '|| true' not in body and 'true ||' not in body, (
        "the checker's exit code is swallowed; a report check that cannot fail the job checks nothing"
    )
    assert '--paginate' in body, "without --paginate a report past the first page of comments is invisible"


def test_sha_and_start_time_are_recorded_before_booth_and_used_by_the_check():
    steps = _steps()
    booth = _index(steps, lambda n, b: 'anthropics/claude-code-action' in b, 'runs Booth')
    record = _index(steps, lambda n, b: 'git rev-parse HEAD' in b and 'GITHUB_OUTPUT' in b,
                    'records the audited SHA')
    assert record < booth, (
        "the audited SHA is recorded after Booth ran; Booth may have checked out "
        "another commit by then"
    )
    record_body = steps[record][1]
    assert 'id: audited' in record_body and 'started=' in record_body
    check_body = next(b for n, b in steps if 'booth_report_posted' in b and 'gh api' in b)
    assert 'steps.audited.outputs.sha' in check_body
    assert 'steps.audited.outputs.started' in check_body


def test_the_checker_is_copied_out_before_booth_touches_the_tree():
    steps = _steps()
    booth = _index(steps, lambda n, b: 'anthropics/claude-code-action' in b, 'runs Booth')
    copy = _index(steps, lambda n, b: 'cp src/agents/booth_report_posted.py' in b, 'copies the checker out')
    assert copy < booth
    assert 'src/agents/booth_verdict.py' in steps[copy][1], "the checker imports booth_verdict; copy both"
    check_body = next(b for n, b in steps if 'booth_report_posted' in b and 'gh api' in b)
    assert 'cd "$RUNNER_TEMP/booth-check"' in check_body and '-m src.agents.booth_report_posted' in check_body, (
        "the check runs the script from the working tree Booth left behind"
    )


# --- the check runs from a copy, outside the checkout -------------------------

def copied_modules(workflow_text):
    """The src/agents/ modules booth-pr-audit.yml copies into $RUNNER_TEMP/booth-check."""
    import re
    m = re.search(r'^\s*cp ((?:src/agents/\S+\.py\s+)+)"\$RUNNER_TEMP/booth-check/src/agents/"', workflow_text, re.M)
    assert m, 'the copy into booth-check is gone from booth-pr-audit.yml -- re-anchor this guard'
    return [p.split('/')[-1][:-3] for p in m.group(1).split() if not p.endswith('__init__.py')]


def local_imports(source, candidates):
    """The modules of src/ a module imports, by module name.

    `from src.agents.booth_verdict import x` and `from src.agents import
    booth_verdict` both name booth_verdict; a bare `import booth_verdict` is
    still counted, so an import written the old way is seen too."""
    import ast
    names = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            names |= {a.name.split('.')[-1] for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            parts = node.module.split('.')
            if parts[0] == 'src' and len(parts) == 2:
                names |= {a.name for a in node.names}
            else:
                names.add(parts[-1] if parts[0] == 'src' else parts[0])
    return names & candidates


def test_the_copied_check_imports_only_what_is_copied():
    """Stage 30 item 5, found on PR #219 itself. The workflow copies the report
    check and its one helper out of the checkout before Booth runs, so the
    audit cannot edit the check that judges it. A new import of another src/
    module passed every test here -- they run inside the checkout -- and failed
    only in CI, where the copy stands alone: "Fail if Booth posted no report"
    went red on a run whose report was sitting on the PR."""
    root = Path(__file__).resolve().parents[1]
    wf = (root / '.github' / 'workflows' / 'booth-pr-audit.yml').read_text(encoding='utf-8')
    copied = copied_modules(wf)
    assert 'booth_report_posted' in copied and len(copied) >= 2, f'copied: {copied}'
    src_modules = {p.stem for p in (root / 'src').glob('*/*.py')} - {'__init__'}
    stray = {}
    for mod in copied:
        imported = local_imports((root / 'src' / 'agents' / f'{mod}.py').read_text(encoding='utf-8'), src_modules)
        missing = imported - set(copied)
        if missing:
            stray[mod] = sorted(missing)
    assert not stray, (f'modules copied into booth-check import src/ modules that are not copied: '
                       f'{stray}. Add them to the cp line, or keep the import out of these files.')


def test_the_import_check_sees_an_import():
    """Synthetic, so the failing branch is reachable while the real files are clean."""
    src = 'import json\nfrom collect_agent_log import BOOTH_ACCOUNTS\nimport booth_verdict as bv\n'
    assert local_imports(src, {'collect_agent_log', 'booth_verdict', 'x'}) == {'collect_agent_log', 'booth_verdict'}
    src = 'from src.agents.collect_agent_log import BOOTH_ACCOUNTS\nfrom src.agents import booth_verdict as bv\n'
    assert local_imports(src, {'collect_agent_log', 'booth_verdict', 'x'}) == {'collect_agent_log', 'booth_verdict'}
