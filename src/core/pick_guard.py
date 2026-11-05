"""
A day sport's pick that could have seen its own result is never written.

Stage 91 item 5 (audit 7, 2026-11-04, finding M5). 34 saved picks were fitted
on games finished earlier on their own slate day (disclosed in both live
registrations' `deviation` amendments). Stage 85 item 4 fixed the fit, and a
suite test holds the committed picks to it; but nothing in the writer
refused such a record, so a regression would be saved first and caught, at
best, by the next pull request's test run, after the pick was permanent.

`refuse_leak` is called by each day sport's `save_once` before anything is
written. It refuses a record whose models were fitted through its own slate
day or later, that was saved at or after its game's start, or whose market
price was read at or after the start. A field a record does not carry is not
checked. Times are the files' '%Y-%m-%dT%H:%M:%SZ' strings, which order as
times; days are ISO dates. Standard library only.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any


class LeakedPick(ValueError):
    """The record could have seen the result it predicts."""


def problems(record: Mapping[str, Any]) -> list[str]:
    """Why the record must not be saved; empty when it may be."""
    out = []
    slate, start = record.get('slate'), record.get('start_utc')
    through = record.get('training_through')
    if slate and through and str(through) >= str(slate):
        out.append(f'fitted through {through}, on or after its slate day {slate}')
    saved = record.get('saved_utc')
    if start and saved and str(saved) >= str(start):
        out.append(f'saved at {saved}, at or after the start {start}')
    market = record.get('market')
    read = market.get('read_utc') if isinstance(market, Mapping) else None
    if start and read and str(read) >= str(start):
        out.append(f'market read at {read}, at or after the start {start}')
    return out


def refuse_leak(record: Mapping[str, Any]) -> None:
    found = problems(record)
    if found:
        raise LeakedPick(f"pick {record.get('game_id')} not saved: " + '; '.join(found))
