"""
Booth's prompt tells it the run ends when it stops calling tools (2026-09-23).

#94's audit posted nothing twice. The Run Booth log showed a clean finish --
subtype "success", is_error false, 43 of 120 turns, 171 seconds, no
permission denials -- so Booth did not crash or run out of anything. It
stopped. The likeliest reading is that it started the several-minute
mutation corpus in the background and ended its turn to wait for it, which
in this action ends the run. #83's step catches the symptom (a run that
posts nothing goes red); this paragraph goes after the cause.

What can be checked without running Booth is that the instruction is in the
prompt Booth actually receives -- inside the action's `prompt:` block, not in
a YAML comment beside it, where it would read as documentation and reach
nobody. Whether it works is measured by the next audits posting, and that is
the evidence this PR cannot produce for itself: the action skips a PR that
edits its own workflow.

Run with: pytest tests/test_booth_prompt.py -v
"""
import re
from pathlib import Path

WORKFLOW = Path(__file__).parent.parent / '.github' / 'workflows' / 'booth-pr-audit.yml'


def prompt_block(text):
    """The literal `prompt: |` block scalar: every line indented deeper than
    the `prompt:` key, up to the first line that is not."""
    lines = text.splitlines()
    for i, line in enumerate(lines):
        m = re.match(r'^(\s*)prompt:\s*\|\s*$', line)
        if m:
            indent = len(m.group(1))
            body = []
            for nxt in lines[i + 1:]:
                if nxt.strip() and len(nxt) - len(nxt.lstrip()) <= indent:
                    break
                body.append(nxt)
            return '\n'.join(body)
    raise AssertionError('no `prompt: |` block in the workflow -- re-anchor this guard')


def test_the_prompt_says_the_run_ends_when_tool_calls_stop():
    prompt = prompt_block(WORKFLOW.read_text(encoding='utf-8'))
    assert 'THIS RUN ENDS THE MOMENT YOU STOP CALLING TOOLS' in prompt
    assert re.search(r'Never end your turn to\s+"wait"', prompt)
    assert re.search(r'poll it', prompt), 'the prompt no longer says how to wait instead'


def test_the_prompt_still_asks_for_the_report_first():
    """The older instruction this sits beside. Both are needed: one is about
    running out of turns, the other about stopping early."""
    prompt = prompt_block(WORKFLOW.read_text(encoding='utf-8'))
    assert 'POST\n' in prompt or 'POST YOUR REPORT' in prompt.replace('\n', ' ')
    assert 'gh pr comment' in prompt


def test_the_block_reader_is_not_blind():
    """A reader that returned the whole file would find the phrase in the
    YAML comment below the block and pass for the wrong reason."""
    text = WORKFLOW.read_text(encoding='utf-8')
    prompt = prompt_block(text)
    assert 'You are Booth.' in prompt
    assert 'claude_args' not in prompt, 'the prompt block ran past its end'
    assert '# 120, not the 30' not in prompt
