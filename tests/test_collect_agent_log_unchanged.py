"""The audit-log collector writes only when an audit changed (Stage 68 item 29, E34).

generated_utc moves on every run, so a run with nothing new rewrote
data/agent_log.json and the workflow's auto-commit committed it. Most of
the 28 "Collect Booth's audit log" commits from 2026-10-09 to 10-10 carry
a new audit; the ones that carried only a timestamp stop.

Run with: pytest tests/test_collect_agent_log_unchanged.py -v
"""
import json

from src.agents import collect_agent_log as cal


def run(tmp_path, comments):
    src = tmp_path / 'comments.json'
    src.write_text(json.dumps(comments), encoding='utf-8')
    out = tmp_path / 'agent_log.json'
    assert cal.main(['--comments', str(src), '--out', str(out)]) == 0
    return out


def test_a_second_run_with_the_same_comments_leaves_the_file_alone(tmp_path):
    out = run(tmp_path, [])
    first = out.read_text(encoding='utf-8')
    old = json.loads(first)
    old['generated_utc'] = '2000-01-01T00:00:00Z'
    out.write_text(json.dumps(old, indent=2) + '\n', encoding='utf-8')
    run(tmp_path, [])
    assert json.loads(out.read_text(encoding='utf-8'))['generated_utc'] == '2000-01-01T00:00:00Z'


def test_a_change_to_anything_else_is_written(tmp_path):
    out = run(tmp_path, [])
    old = json.loads(out.read_text(encoding='utf-8'))
    old['generated_utc'] = '2000-01-01T00:00:00Z'
    old['note'] = 'an older note'
    out.write_text(json.dumps(old), encoding='utf-8')
    run(tmp_path, [])
    new = json.loads(out.read_text(encoding='utf-8'))
    assert new['generated_utc'] != '2000-01-01T00:00:00Z' and new['note'] != 'an older note'


def test_a_missing_or_broken_file_is_written(tmp_path):
    out = tmp_path / 'agent_log.json'
    out.write_text('not json', encoding='utf-8')
    assert not cal.unchanged(out, {'generated_utc': 'x'})
    assert not cal.unchanged(tmp_path / 'absent.json', {'generated_utc': 'x'})
