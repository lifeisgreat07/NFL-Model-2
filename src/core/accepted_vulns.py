"""
Turn the reviewed list of accepted vulnerabilities into pip-audit arguments
(Stage 83 item 2, the 2026-11-02 review).

The nightly dependency audit is report-only, and moving a pin is a decision.
A vulnerability someone has decided to live with for now, such as one in a
package pinned on purpose, used to comment on the same issue every night with
nothing new to say. An entry here silences it until its review_by date, and
not a day after: an acceptance with no end is a finding nobody looks at again.

    python -m src.core.accepted_vulns .github/accepted-vulnerabilities.json
prints `--ignore-vuln ID` for every entry still in date, on one line.
"""
from __future__ import annotations

import json
import sys
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

REQUIRED = ('id', 'package', 'reason', 'review_by')


class AcceptedVulnError(ValueError):
    """An entry the audit cannot honour as written."""


def entries(doc: dict[str, Any]) -> list[dict[str, str]]:
    rows = doc.get('accepted')
    if not isinstance(rows, list):
        raise AcceptedVulnError('"accepted" must be a list')
    for row in rows:
        missing = [k for k in REQUIRED if not str(row.get(k, '')).strip()]
        if missing:
            raise AcceptedVulnError(f'{row.get("id", "?")}: missing {missing}')
        date.fromisoformat(row['review_by'])
    return rows


def ignore_args(doc: dict[str, Any], today: date) -> tuple[list[str], list[str]]:
    """(pip-audit arguments, notes on entries past their review date)."""
    args, notes = [], []
    for row in entries(doc):
        if date.fromisoformat(row['review_by']) < today:
            notes.append(f'{row["id"]} ({row["package"]}) passed its review date {row["review_by"]}: audited again')
        else:
            args += ['--ignore-vuln', row['id']]
    return args, notes


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    doc = json.loads(Path(args[0]).read_text(encoding='utf-8'))
    out, notes = ignore_args(doc, datetime.now(UTC).date())
    for n in notes:
        print(n, file=sys.stderr)
    print(' '.join(out))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
