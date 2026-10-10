"""Does a re-run's results folder say what the committed one says? (Stage 68 item 28)

A re-run of the NHL's backtest on another machine reproduces every label,
every chosen parameter and every count, and moves the last digit or two of
a float (a log loss of ...739324 against ...739323): summing in a
different order. So two results files agree when their structure, strings,
booleans and integers are equal and every float is within a relative
1e-9 of the other. Anything larger is a different result.

    python -m src.core.compare_results COMMITTED_DIR RERUN_DIR

prints each difference and exits 1 when there is one.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

REL = 1e-9


def differences(a: Any, b: Any, where: str = '') -> list[str]:
    """Where `a` and `b` differ beyond float noise; empty when they agree."""
    if isinstance(a, bool) or isinstance(b, bool) or not (isinstance(a, (int, float)) and isinstance(b, (int, float))):
        if type(a) is not type(b):
            return [f'{where or "/"}: {a!r} != {b!r}']
    if isinstance(a, dict):
        out = [f'{where}/{k}: only in one' for k in sorted(set(a) ^ set(b))]
        for k in sorted(set(a) & set(b)):
            out += differences(a[k], b[k], f'{where}/{k}')
        return out
    if isinstance(a, list):
        if len(a) != len(b):
            return [f'{where}: {len(a)} items != {len(b)}']
        return [d for i, (x, y) in enumerate(zip(a, b, strict=True)) for d in differences(x, y, f'{where}[{i}]')]
    if isinstance(a, float) or isinstance(b, float):
        return [] if math.isclose(a, b, rel_tol=REL, abs_tol=REL) else [f'{where}: {a!r} != {b!r}']
    return [] if a == b else [f'{where or "/"}: {a!r} != {b!r}']


def compare_dirs(committed: Path, rerun: Path) -> list[str]:
    out = []
    names = sorted({p.name for p in committed.glob('*.json')} | {p.name for p in rerun.glob('*.json')})
    for name in names:
        a, b = committed / name, rerun / name
        if not (a.exists() and b.exists()):
            out.append(f'{name}: only in {"the re-run" if b.exists() else "the committed results"}')
            continue
        out += [f'{name} {d}' for d in differences(json.loads(a.read_text(encoding='utf-8-sig')),
                                                     json.loads(b.read_text(encoding='utf-8-sig')))]
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description='Compare a re-run results folder with the committed one')
    ap.add_argument('committed', type=Path)
    ap.add_argument('rerun', type=Path)
    args = ap.parse_args(argv)
    diffs = compare_dirs(args.committed, args.rerun)
    for d in diffs:
        print(d)
    print('the re-run matches the committed results' if not diffs else f'{len(diffs)} differences')
    return 1 if diffs else 0


if __name__ == '__main__':
    sys.exit(main())
