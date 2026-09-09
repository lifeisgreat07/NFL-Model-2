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
"""

import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
WORKFLOWS = REPO / '.github' / 'workflows'

#: The file the collector writes, and the workflow whose name must appear in a
#: workflow_run trigger for that write to reach a reader.
COLLECTOR = WORKFLOWS / 'collect-agent-log.yml'
BUILDER = WORKFLOWS / 'generate-dashboard.yml'

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
    assert BUILDER.exists(), 'generate-dashboard.yml is gone'


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
        "generate-dashboard.yml has no workflow_run trigger, so a commit made "
        "by another workflow's GITHUB_TOKEN cannot rebuild the dashboard. That "
        "is the 2026-09-09 defect: data collected, page never updated")
    listed = re.search(r'workflow_run:\s*\n\s*workflows:\s*\[(.*?)\]', text, re.S)
    assert listed, 'workflow_run block has no workflows: [...] list'
    names = [n.strip().strip('"\'') for n in listed.group(1).split(',')]
    collector_name = _workflow_name(COLLECTOR)
    assert collector_name in names, (
        f"generate-dashboard.yml's workflow_run lists {names}, which does not "
        f"include {collector_name!r}. The name must match collect-agent-log.yml's "
        f"`name:` field exactly -- GitHub matches on the display name, and a "
        f"rename on one side fails silently with no run and no error")


def test_the_builder_ignores_a_failed_collector_run():
    """workflow_run fires on completion, not success. Without this the project
    spends a full rebuild every time the collector errors, producing a
    byte-identical index.html."""
    text = _text(BUILDER)
    assert "workflow_run.conclusion == 'success'" in text, (
        'generate-dashboard.yml does not gate on the triggering run having '
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
        'the workflow_run trigger in generate-dashboard.yml is not accompanied '
        'by the GITHUB_TOKEN explanation. Without it the trigger looks '
        'redundant against the data/** paths and invites deletion')


if __name__ == '__main__':
    sys.exit(pytest.main([__file__, '-v']))
