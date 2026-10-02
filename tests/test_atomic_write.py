"""Write-once JSON is written atomically (Stage 24 item 8).

A saved week of picks can never be overwritten (weekly_update.py refuses),
so a file half-written by a killed run would stay broken for good. Before
this, both write-once files -- the week's picks and the skipped-week record
-- were written with open(path, 'w') and json.dump straight into the target.
Now src/pipeline/atomic_write.py produces the whole text first, writes it beside the
target and swaps it in with os.replace.
"""
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

from src.pipeline.atomic_write import write_json_atomic  # noqa: E402


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
    from src.pipeline import atomic_write
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
    src = (ROOT / 'src' / 'pipeline' / 'weekly_update.py').read_text(encoding='utf-8')
    save = re.search(r"out_path = PRED_DIR / f'\{season\}_week\{week\}\.json'(.*?)log\.info\(f\"Saved", src, re.S)
    assert save, "the picks save in main() is not findable -- re-anchor this guard"
    assert 'write_json_atomic(out_path' in save.group(1), (
        'the week of picks is written straight into the target again')
    skip = re.search(r'def record_skipped_week\(.*?\n    return path', src, re.S)
    assert skip and 'write_json_atomic(path' in skip.group(0), (
        'the skipped-week record is written straight into the target again')


def test_each_write_gets_its_own_temporary_file_beside_the_target(tmp_path, monkeypatch):
    """Stage 30 item 8. The temporary name was the fixed <name>.tmp, which
    two writers to one target would share. It must be unique per write, in
    the target's own folder (os.replace cannot cross filesystems), and named
    after the target so a leftover says what it was for."""
    from src.pipeline import atomic_write
    seen = []
    real = atomic_write.os.replace

    def spy(src, dst):
        seen.append(Path(src))
        return real(src, dst)
    monkeypatch.setattr(atomic_write.os, 'replace', spy)
    target = tmp_path / 'record.json'
    write_json_atomic(target, {'a': 1})
    write_json_atomic(target, {'a': 2})
    assert len(seen) == 2 and seen[0] != seen[1], f'one temporary name reused: {seen}'
    for tmp in seen:
        assert tmp.parent == tmp_path, tmp
        assert tmp.name.startswith('record.json.') and tmp.name.endswith('.tmp'), tmp.name
    assert sorted(p.name for p in tmp_path.iterdir()) == ['record.json']


def test_a_leftover_temporary_file_is_never_committed():
    """A run killed before the swap leaves its temporary file in the
    target's folder -- for picks, predictions/, which the weekly workflow
    commits with a predictions/** pattern."""
    lines = (ROOT / '.gitignore').read_text(encoding='utf-8').splitlines()
    assert '*.tmp' in [line.strip() for line in lines], '*.tmp is not gitignored'
