"""Write-once JSON is written atomically (Stage 24 item 8).

A saved week of picks can never be overwritten (weekly_update.py refuses),
so a file half-written by a killed run would stay broken for good. Before
this, both write-once files -- the week's picks and the skipped-week record
-- were written with open(path, 'w') and json.dump straight into the target.
Now src/atomic_write.py produces the whole text first, writes it beside the
target and swaps it in with os.replace.
"""
import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from atomic_write import write_json_atomic  # noqa: E402


def test_it_writes_what_json_dumps_would(tmp_path):
    obj = [{'home': 'GB', 'p': 0.68}]
    path = write_json_atomic(tmp_path / 'w.json', obj, indent=2)
    assert path.read_text(encoding='utf-8') == json.dumps(obj, indent=2)
    assert write_json_atomic(tmp_path / 'n.json', {}, trailing_newline=True).read_text(
        encoding='utf-8') == '{}\n'


def test_a_failed_write_leaves_nothing_behind(tmp_path):
    """The property that matters: an object that cannot be written leaves no
    file at the target and no temporary file beside it -- not an empty or
    truncated file that a write-once rule would then protect."""
    target = tmp_path / '2026_week4.json'
    with pytest.raises(TypeError):
        write_json_atomic(target, [{'ok': 1}, {'bad': object()}], indent=2)
    assert not target.exists(), 'a failed write left a file at the target'
    assert list(tmp_path.iterdir()) == [], 'a temporary file was left behind'


def test_a_failed_write_leaves_an_existing_file_as_it_was(tmp_path):
    target = tmp_path / 'record.json'
    target.write_text('{"kept": true}', encoding='utf-8')
    with pytest.raises(TypeError):
        write_json_atomic(target, {'bad': object()})
    assert target.read_text(encoding='utf-8') == '{"kept": true}'


def test_a_failed_swap_removes_its_temporary_file(tmp_path, monkeypatch):
    """The two tests above fail inside json.dumps, before the temporary file
    exists, so they cannot see whether it is cleaned up. Here the temporary
    file is written in full and the swap itself fails, as a full disk or a
    locked target would make it: the target keeps its old text and the
    temporary file is gone."""
    import atomic_write
    target = tmp_path / 'record.json'
    target.write_text('{"kept": true}', encoding='utf-8')

    def refuse(src, dst):
        raise OSError('swap refused')
    monkeypatch.setattr(atomic_write.os, 'replace', refuse)
    with pytest.raises(OSError):
        write_json_atomic(target, {'new': 1})
    assert target.read_text(encoding='utf-8') == '{"kept": true}'
    assert sorted(p.name for p in tmp_path.iterdir()) == ['record.json'], (
        'a failed swap left its temporary file beside the target')


def test_the_write_once_files_use_it():
    src = (ROOT / 'src' / 'weekly_update.py').read_text(encoding='utf-8')
    save = re.search(r"out_path = PRED_DIR / f'\{season\}_week\{week\}\.json'(.*?)print\(f\"Saved", src, re.S)
    assert save, "the picks save in main() is not findable -- re-anchor this guard"
    assert 'write_json_atomic(out_path' in save.group(1), (
        'the week of picks is written straight into the target again')
    skip = re.search(r'def record_skipped_week\(.*?\n    return path', src, re.S)
    assert skip and 'write_json_atomic(path' in skip.group(0), (
        'the skipped-week record is written straight into the target again')
