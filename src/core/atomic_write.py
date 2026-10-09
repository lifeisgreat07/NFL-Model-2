"""Write a JSON file so it is either the old file or the whole new one.

Stage 24, from the 2026-09-28 audit. A saved week of picks is permanent:
weekly_update.py refuses to overwrite predictions/nfl/<season>_week<N>.json. So a
run killed halfway through writing that file (a runner timeout, a cancelled
job) would leave a truncated file that nothing is allowed to replace, and the
Pages build refuses a week it cannot read. Here the text is produced in full
first, written to a temporary file beside the target, and only then moved
into place with os.replace, which is atomic on one filesystem.

Stage 30 item 8, from the 2026-09-29 re-audit: the temporary file used to be
the fixed name <name>.tmp. A run killed between writing it and the swap left
that file in a committed folder (predictions/), where the workflow's
`predictions/nfl/**` pattern would commit it, and two writers to one target
shared one temporary name. It is now a unique name from tempfile.mkstemp in
the same folder, and `*.tmp` is gitignored.
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any


def write_json_atomic(path: str | Path, obj: Any, trailing_newline: bool = False, **dump_kwargs: Any) -> Path:
    """Serialise `obj` completely, then replace `path` with it in one step.

    If serialisation fails, nothing on disk has changed. The temporary file
    sits in the same folder so os.replace never crosses filesystems.
    """
    path = Path(path)
    text = json.dumps(obj, **dump_kwargs) + ('\n' if trailing_newline else '')
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=path.name + '.', suffix='.tmp')
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()
    return path
