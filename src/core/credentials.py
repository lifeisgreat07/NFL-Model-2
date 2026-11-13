"""
The credentials register, and the check that warns before one expires
(Stage 83 item 6, the 2026-11-02 review).

Two credentials keep the unattended runs going: the OAuth token every agent
runs on, and the token cron-job.org starts the scheduled runs with. Each
expires on a date, and until now that date was written nowhere a check
could read: the first sign of an expired token would have been every agent
run failing, or every scheduled run starting hours late. The register,
`.github/credentials.json`, records each one with its expiry; this module
reads it and names every credential within WARN_DAYS of expiring.

    python -m src.core.credentials .github/credentials.json report.md
exits 0 and writes nothing when no credential is due, exits 1 after writing
the alert body to report.md when one is, and exits 2 after writing why when
the register cannot be read. Standard library only, so the workflow installs
nothing for it.
"""
from __future__ import annotations

import json
import sys
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

WARN_DAYS = 30
REQUIRED = ('name', 'kept_in', 'used_by', 'breaks', 'expires', 'expires_basis', 'renew')


class CredentialsError(ValueError):
    """An entry the check cannot honour as written."""


def entries(doc: dict[str, Any]) -> list[dict[str, str]]:
    rows = doc.get('credentials')
    if not isinstance(rows, list) or not rows:
        raise CredentialsError('"credentials" must be a non-empty list')
    for row in rows:
        missing = [k for k in REQUIRED if not str(row.get(k, '')).strip()]
        if missing:
            raise CredentialsError(f'{row.get("name", "?")}: missing {missing}')
        try:
            date.fromisoformat(row['expires'])
        except ValueError as exc:
            raise CredentialsError(f'{row["name"]}: expires {row["expires"]!r} is not YYYY-MM-DD') from exc
    return rows


def due(doc: dict[str, Any], today: date) -> list[tuple[dict[str, str], int]]:
    """Each credential within WARN_DAYS of its expiry date, or past it, with
    the days left (negative once expired), soonest first."""
    out = []
    for row in entries(doc):
        left = (date.fromisoformat(row['expires']) - today).days
        if left <= WARN_DAYS:
            out.append((row, left))
    return sorted(out, key=lambda pair: pair[1])


def report(rows: list[tuple[dict[str, str], int]]) -> str:
    lines = [f'{len(rows)} credential(s) in `.github/credentials.json` expire within {WARN_DAYS} days or already have.', '']
    for row, left in rows:
        when = f'expired {-left} day(s) ago' if left < 0 else f'expires in {left} day(s)'
        lines += [f'### {row["name"]}: {when} ({row["expires"]})', '',
                  f'- Kept in: {row["kept_in"]}', f'- Used by: {row["used_by"]}',
                  f'- Without it: {row["breaks"]}', f'- How the date is known: {row["expires_basis"]}',
                  f'- To renew: {row["renew"]}', '']
    lines.append('After renewing, update `expires` (and `expires_basis`) in `.github/credentials.json`.')
    return '\n'.join(lines) + '\n'


def main(argv: list[str] | None = None, today: date | None = None) -> int:
    """0: nothing due. 1: something due, report written. 2: the register
    cannot be read, and the report says why, so a broken register is an
    issue of its own rather than a quiet pass or a failed job."""
    args = sys.argv[1:] if argv is None else argv
    try:
        doc = json.loads(Path(args[0]).read_text(encoding='utf-8'))
        rows = due(doc, today or datetime.now(UTC).date())
    except (OSError, ValueError) as exc:  # json.JSONDecodeError and CredentialsError are ValueErrors
        Path(args[1]).write_text(f'`{args[0]}` cannot be read, so no expiry date was checked: {exc}\n', encoding='utf-8')
        print(f'credentials register unreadable: {exc}', file=sys.stderr)
        return 2
    if not rows:
        print(f'No credential expires within {WARN_DAYS} days.')
        return 0
    Path(args[1]).write_text(report(rows), encoding='utf-8')
    for row, left in rows:
        print(f'{row["name"]}: {left} day(s) left ({row["expires"]})')
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
