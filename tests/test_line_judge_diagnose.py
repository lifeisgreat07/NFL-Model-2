"""
Stage 44, PR 3: the agent on failure (.github/workflows/line-judge-diagnose.yml,
LINE_JUDGE_PROTOCOL.md).

What is held here:
  - every judged workflow hands its finding on as a job output and calls the
    diagnosis only when its line-judge job failed, with the same alert title
    its finding used; the finding reaches the model's job through the
    environment, never interpolated into a shell;
  - the job that runs the model can read and nothing more, and is handed the
    repository's token (not the Claude app's); the job that comments runs no
    model;
  - the prompt points at the protocol, the finding and the logs, and says the
    run ends when tool calls stop; the protocol names every check the judges
    can report.

Run with: pytest tests/test_line_judge_diagnose.py -v
"""
import re
from pathlib import Path

import pytest

from src.core import line_judge_digest as dg

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / '.github' / 'workflows'
DIAGNOSE = (WORKFLOWS / 'line-judge-diagnose.yml').read_text(encoding='utf-8')
PROTOCOL = (ROOT / 'LINE_JUDGE_PROTOCOL.md').read_text(encoding='utf-8')
CALL = 'uses: ./.github/workflows/line-judge-diagnose.yml'


def job_block(text, name):
    m = re.search(rf'^  {name}:\n((?:    .*\n|\n)*)', text, re.M)
    assert m, name
    return m.group(1)


@pytest.mark.parametrize('workflow', sorted(dg.JUDGED))
def test_every_judged_workflow_calls_the_diagnosis_only_on_a_finding(workflow):
    text = (WORKFLOWS / workflow).read_text(encoding='utf-8')
    judge = job_block(text, 'line-judge')
    assert 'outputs:\n      report: ${{ steps.judge.outputs.report }}' in judge, workflow
    step = judge.split('- name: Judge the run\n', 1)[1]
    assert step.startswith('        id: judge\n'), workflow
    # Written before the step fails, under a delimiter the finding cannot guess.
    assert re.search(r'\{ echo "report<<\$delim"; cat line-judge.md; echo "\$delim"; \} >> "\$GITHUB_OUTPUT"\n\s+exit 1', step), workflow
    assert 'delim="LJ_$(od -An -N8 -tx1 /dev/urandom' in step
    call = job_block(text, 'diagnose')
    assert 'needs: [line-judge]' in call and CALL in call
    assert "if: ${{ failure() && needs.line-judge.result == 'failure' }}" in call
    title = re.search(r'alerts --title "([^"]+)"', judge).group(1)
    assert f'title: "{title}"' in call, f'{workflow}: the diagnosis must land on the alert the finding opened'
    assert 'CLAUDE_CODE_OAUTH_TOKEN: ${{ secrets.CLAUDE_CODE_OAUTH_TOKEN }}' in call
    assert 'report: ${{ needs.line-judge.outputs.report }}' in call


def test_the_finding_reaches_the_model_only_through_the_environment():
    diagnose = job_block(DIAGNOSE, 'diagnose')
    assert 'REPORT: ${{ inputs.report }}' in diagnose
    assert diagnose.count('${{ inputs.report }}') == 1


def test_nothing_else_calls_the_diagnosis():
    callers = {p.name for p in WORKFLOWS.glob('*.yml')
               if p.name != 'line-judge-diagnose.yml' and CALL in p.read_text(encoding='utf-8')}
    assert callers == set(dg.JUDGED)


def test_the_model_job_can_only_read():
    diagnose = job_block(DIAGNOSE, 'diagnose')
    perms = re.search(r'permissions:\n((?:      .*\n)+)', diagnose).group(1)
    assert sorted(perms.split()) == sorted(['contents:', 'read', 'actions:', 'read'])
    assert 'anthropics/claude-code-action@' in diagnose
    assert 'github_token: ${{ secrets.GITHUB_TOKEN }}' in diagnose
    assert 'src.core.alerts' not in diagnose and 'gh issue' not in diagnose
    assert not re.search(r'^permissions:', DIAGNOSE, re.M), 'each job states its own'


def test_the_model_is_given_no_shell_beyond_reading_history():
    tools = re.search(r'--allowedTools "([^"]+)"', DIAGNOSE).group(1).split(',')
    assert tools == ['Read', 'Glob', 'Grep', 'Write', 'Bash(git log:*)', 'Bash(git show:*)']


def test_the_job_that_comments_runs_no_model():
    post = job_block(DIAGNOSE, 'post')
    assert 'claude-code-action' not in post
    assert 'issues: write' in post and 'needs: [diagnose]' in post and 'if: ${{ always() }}' in post
    assert 'TITLE: ${{ inputs.title }}' in post
    assert 'python -m src.core.alerts --title "$TITLE"' in post
    # The input reaches the shell only through the environment.
    run_lines = post.split('run: |', 1)[1]
    assert '${{ inputs.title }}' not in run_lines


def test_the_prompt_points_at_the_protocol_and_ends_on_the_file():
    prompt = DIAGNOSE.split('prompt: |', 1)[1].split('claude_args:', 1)[0]
    for want in ('LINE_JUDGE_PROTOCOL.md', 'line-judge/line-judge.md', 'line-judge/logs/',
                 'line-judge/diagnosis.md', 'ends the\n            moment you stop calling tools'):
        assert want in prompt, want


def test_the_protocol_names_every_check_the_judges_report():
    names = set()
    for module in ('src/sports/nfl/line_judge.py', 'src/core/day_line_judge.py'):
        names |= set(re.findall(r"Finding\('([a-z-]+)'", (ROOT / module).read_text(encoding='utf-8')))
    assert len(names) >= 8
    missing = sorted(n for n in names if f'`{n}`' not in PROTOCOL)
    assert not missing, f'LINE_JUDGE_PROTOCOL.md does not name {missing}'
    assert 'Writing the file is your last tool call' in PROTOCOL
