"""A workflow that writes data the dashboard reads must also cause a rebuild.

The defect this exists for, observed on 2026-09-09 the first time the collector
ever ran end to end:

  "Collect Booth's audit log" ran, produced data/agent_log.json with 44 audits
  in it, and committed it to main. `Auto-regenerate dashboard` watches `data/**`
  and did not run. The live page went on saying "The record has not been
  collected yet" while the record sat in the repository.

The cause is a GitHub rule both workflows already documented and neither had
followed through on: a push made with the default GITHUB_TOKEN cannot trigger
another workflow. Both files describe that rule as a safeguard against a
regeneration loop, which it is. It is also, unavoidably, a severed handoff --
and a safeguard is easy to write down twice without noticing it cuts something
you wanted.

This is the same shape as the bug the collector itself was written to fix: a
step that runs, produces correct output, and has nothing downstream consuming
it. One layer further along the chain. So the check is on the chain, not on
either end of it.

WIDENED 2026-09-15, after the same defect recurred in a second workflow.

The checks above are the collector's chain and only the collector's chain --
DASHBOARD_INPUTS named one file and COLLECTOR named one workflow. "Weekly
update" writes predictions/**, results/** and data/** with the same default
GITHUB_TOKEN, is not in the workflow_run list, and was therefore invisible to
every assertion here. On 2026-09-15 it graded the first real week and locked in
Week 2 at 11:05 UTC; the published page went on serving 04:30 UTC data with no
Week 2 in either week control, and nothing failed.

That is this repo's own "a guard wired into one of several paths reads as a
guard that is present", and the docstring above walked straight into it by
saying the check is on the chain when it was on one of two. The tests added at
the bottom of this file ENUMERATE the writers instead of naming them, and read
the watched path set out of the builder, so a third writer -- or a new watched
path -- is covered without anyone remembering this.
"""

import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
WORKFLOWS = REPO / '.github' / 'workflows'

#: The file the collector writes, and the workflow whose name must appear in a
#: workflow_run trigger for that write to reach a reader.
#:
#: The builder was generate-dashboard.yml until Stage 8c phase 2. That workflow
#: existed to regenerate index.html and COMMIT it; once the artifact stopped
#: being tracked it had nothing left to do, and deploy-pages.yml -- which
#: already carried the identical trigger set, deliberately, for this handoff --
#: became the only builder. The chain this file guards is unchanged; only the
#: far end of it has a different filename.
COLLECTOR = WORKFLOWS / 'collect-agent-log.yml'
BUILDER = WORKFLOWS / 'deploy-pages.yml'

#: Data the dashboard renders. A workflow committing one of these has produced
#: something a reader is meant to see.
DASHBOARD_INPUTS = ('data/agent_log.json',)


def _text(path):
    return path.read_text(encoding='utf-8')


def _workflow_name(path):
    m = re.search(r'^name:\s*(.+?)\s*$', _text(path), re.M)
    assert m, f'{path.name} has no name: field'
    return m.group(1).strip().strip('"\'')


def test_both_workflows_still_exist():
    """If either is renamed or removed, the pairing below is checking nothing
    and should say so loudly rather than pass vacuously."""
    assert COLLECTOR.exists(), 'collect-agent-log.yml is gone'
    assert BUILDER.exists(), 'deploy-pages.yml is gone'


def test_the_collector_commits_a_file_the_dashboard_reads():
    """The premise. If the collector stops committing agent_log.json, the
    trigger below is dead weight and this test says which half changed."""
    text = _text(COLLECTOR)
    assert any(f in text for f in DASHBOARD_INPUTS), (
        f'collect-agent-log.yml no longer mentions any of {DASHBOARD_INPUTS}. '
        f'If it writes something else now, add it to DASHBOARD_INPUTS; if it '
        f'writes nothing the dashboard reads, this whole file can go')


def test_the_builder_runs_when_the_collector_finishes():
    """The actual fix. Not "the builder watches data/**" -- it does, and that is
    precisely what was not enough, because GITHUB_TOKEN pushes do not trigger
    workflows. It has to name the collector in a workflow_run trigger."""
    text = _text(BUILDER)
    assert 'workflow_run:' in text, (
        "deploy-pages.yml has no workflow_run trigger, so a commit made "
        "by another workflow's GITHUB_TOKEN cannot rebuild the dashboard. That "
        "is the 2026-09-09 defect: data collected, page never updated")
    listed = re.search(r'workflow_run:\s*\n\s*workflows:\s*\[(.*?)\]', text, re.S)
    assert listed, 'workflow_run block has no workflows: [...] list'
    names = [n.strip().strip('"\'') for n in listed.group(1).split(',')]
    collector_name = _workflow_name(COLLECTOR)
    assert collector_name in names, (
        f"deploy-pages.yml's workflow_run lists {names}, which does not "
        f"include {collector_name!r}. The name must match collect-agent-log.yml's "
        f"`name:` field exactly -- GitHub matches on the display name, and a "
        f"rename on one side fails silently with no run and no error")


def test_the_builder_ignores_a_failed_collector_run():
    """workflow_run fires on completion, not success. Without this the project
    spends a full rebuild every time the collector errors, producing a
    byte-identical index.html."""
    text = _text(BUILDER)
    assert "workflow_run.conclusion == 'success'" in text, (
        'deploy-pages.yml does not gate on the triggering run having '
        'succeeded, so it rebuilds after a failed collection too')
    assert "github.event_name != 'workflow_run'" in text, (
        'the conclusion check has no escape for push events, which carry no '
        'workflow_run payload -- as written it would disable the push trigger '
        'entirely, which is the larger half of what this workflow is for')


def test_the_reason_is_written_down_where_the_trigger_is():
    """This one is deliberately about a comment, and it is worth a test.

    Both workflows already documented the GITHUB_TOKEN rule -- as a benefit.
    That is exactly why nobody noticed it also broke the handoff. A future
    reader deleting this trigger as redundant ("data/** already covers it")
    would restore the bug, and the diff would look like a simplification.
    """
    text = _text(BUILDER)
    assert 'GITHUB_TOKEN' in text and 'workflow_run' in text, (
        'the workflow_run trigger in deploy-pages.yml is not accompanied '
        'by the GITHUB_TOKEN explanation. Without it the trigger looks '
        'redundant against the data/** paths and invites deletion')


#: The two forms a workflow in this repo uses to commit: the action's
#: file_pattern, and a literal `git add`. Both are matched because
#: booth-regression.yml uses the second and a future workflow may too.
FILE_PATTERN_RE = re.compile(r'^\s*file_pattern:\s*(.+?)\s*$', re.M)
GIT_ADD_RE = re.compile(r'git add\s+(.+?)\s*$', re.M)


def _roots(paths):
    """Top-level directory of each path. Comparing roots rather than globs is
    deliberately coarse: `data/**` and `data/agent_log.json` must both count as
    'writes something under data', and a guard that tried to resolve globs
    against the real tree would pass whenever the tree happened to be empty."""
    out = set()
    for p in paths:
        # Order matters, and getting it wrong is silent: a YAML list item
        # arrives as `- 'src/**'`, so the dash has to come off before the
        # quotes or the leading quote survives and every root reads as "'src".
        p = p.strip().lstrip('-').strip().strip('"\'').strip()
        if p:
            out.add(p.split('/')[0])
    return out


def _watched_roots():
    """What the builder rebuilds for, read out of the builder. One source of
    truth: adding a watched path widens this guard automatically."""
    m = re.search(r'^\s*paths:\s*\n((?:\s*-\s*.+\n)+)', _text(BUILDER), re.M)
    assert m, 'deploy-pages.yml has no paths: list under its push trigger'
    return _roots(m.group(1).splitlines())


def _committed_roots(path):
    text = _text(path)
    tokens = []
    for m in FILE_PATTERN_RE.finditer(text):
        tokens.extend(m.group(1).strip().strip('"\'').split())
    for m in GIT_ADD_RE.finditer(text):
        tokens.append(m.group(1))
    return _roots(tokens)


def _bridged_names():
    listed = re.search(r'workflow_run:\s*\n\s*workflows:\s*\[(.*?)\]',
                       _text(BUILDER), re.S)
    assert listed, 'workflow_run block has no workflows: [...] list'
    return [n.strip().strip('"\'') for n in listed.group(1).split(',')]


def _writer_workflows():
    """Every workflow that commits something the builder watches, discovered
    rather than listed. Returns (path, display name, overlapping roots)."""
    watched = _watched_roots()
    found = []
    for wf in sorted(WORKFLOWS.glob('*.yml')):
        if wf == BUILDER:
            continue  # holds contents: read; it publishes, it cannot commit
        overlap = _committed_roots(wf) & watched
        if overlap:
            found.append((wf, _workflow_name(wf), sorted(overlap)))
    return found


def test_the_writer_scan_finds_the_workflows_we_know_write():
    """Vacuity check, and the reason it is worth one: every assertion below is
    over a list this scan produces. If the regexes stop matching -- an action
    swapped, `file_pattern` renamed -- the scan returns nothing and the real
    check passes while testing nothing at all."""
    names = {wf.name for wf, _, _ in _writer_workflows()}
    for expected in ('weekly-update.yml', 'collect-agent-log.yml'):
        assert expected in names, (
            f'{expected} commits paths the builder watches, but the writer '
            f'scan did not find it (found: {sorted(names) or "nothing"}). '
            f'The scan is broken, not the workflow -- fix the parsing before '
            f'reading anything into the test below')


def test_every_workflow_that_writes_a_dashboard_input_is_bridged_to_the_builder():
    """The widened rule. A `paths:` trigger does NOT cover these, because the
    pushes are made with the default GITHUB_TOKEN and GitHub will not let such
    a push start another workflow. Each writer must be named in the builder's
    workflow_run list, matching its `name:` field exactly."""
    bridged = _bridged_names()
    missing = [(wf.name, name, roots)
               for wf, name, roots in _writer_workflows() if name not in bridged]
    assert not missing, (
        'these workflows commit paths the dashboard is built from, with the '
        'default GITHUB_TOKEN, and are not in deploy-pages.yml\'s '
        'workflow_run list, so what they write never reaches the page:\n'
        + '\n'.join(f'  {f} (name: {n!r}) writes {r}' for f, n, r in missing)
        + f'\ncurrently bridged: {bridged}')


if __name__ == '__main__':
    sys.exit(pytest.main([__file__, '-v']))
