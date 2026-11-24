"""Booth's audit has room for a large pull request (Mark, 2026-11-23).

#809, the MLB standings simulation, was cancelled at Booth's 20-minute limit
on its first run and again on its re-run, before the 120-turn cap. The limit
is now 35 minutes and the cap 210 turns: at about 6 turns a minute the cap
still lands inside the clock, so wall-clock stays the backstop the workflow's
comment says it is.

Run with: pytest tests/test_booth_timeout.py -v
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / '.github' / 'workflows' / 'booth-pr-audit.yml'


def text():
    return WORKFLOW.read_text(encoding='utf-8')


def timeout():
    # The audit job's own limit: the post job (Stage 82 item 4) has its own, five minutes, and runs no model.
    t = text().replace('\r\n', '\n')
    audit = t[t.index('\n  audit:\n'):]
    audit = audit[:audit.index('\n  post:\n')] if '\n  post:\n' in audit else audit
    m = re.findall(r'^\s*timeout-minutes:\s*(\d+)', audit, re.M)
    assert len(m) == 1, f'expected one timeout-minutes on the audit job, found {m}'
    return int(m[0])


def turns():
    m = re.findall(r'--max-turns (\d+)', text())
    assert len(m) == 1, f'expected one --max-turns, found {m}'
    return int(m[0])


def test_the_audit_has_room_for_a_large_pull_request():
    assert 30 <= timeout() <= 45, f'timeout-minutes {timeout()}: #809 needed more than 20; keep it 30 to 45'


def test_the_turn_cap_lands_inside_the_clock():
    """Not so low that a slow audit stops on turns with time to spare, nor so high it never binds."""
    assert 5 * timeout() <= turns() <= 8 * timeout(), (
        f'{turns()} turns against {timeout()} minutes: keep the cap at 5 to 8 turns a minute')
