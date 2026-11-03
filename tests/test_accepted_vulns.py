"""
Stage 83 item 2: an accepted vulnerability is ignored by the nightly audit
until its review date, and audited again after it.

Run with: pytest tests/test_accepted_vulns.py -v
"""
import json
from datetime import date
from pathlib import Path

import pytest

from src.core import accepted_vulns as av

ROOT = Path(__file__).resolve().parents[1]
ROW = {'id': 'CVE-2026-1', 'package': 'pandas', 'reason': 'pinned on purpose', 'review_by': '2026-12-01'}


def test_an_entry_in_date_is_ignored():
    args, notes = av.ignore_args({'accepted': [ROW]}, date(2026, 11, 2))
    assert args == ['--ignore-vuln', 'CVE-2026-1'] and notes == []


def test_an_entry_past_its_review_date_is_audited_again():
    args, notes = av.ignore_args({'accepted': [ROW]}, date(2026, 12, 2))
    assert args == [] and 'passed its review date' in notes[0]


def test_an_entry_without_a_reason_or_date_is_refused():
    for k in ('reason', 'review_by'):
        with pytest.raises(av.AcceptedVulnError):
            av.entries({'accepted': [{**ROW, k: ''}]})


def test_the_committed_list_reads_and_the_audit_uses_it():
    doc = json.loads((ROOT / '.github' / 'accepted-vulnerabilities.json').read_text(encoding='utf-8'))
    av.entries(doc)
    wf = (ROOT / '.github' / 'workflows' / 'nightly-dependency-audit.yml').read_text(encoding='utf-8')
    assert 'ignore=$(python -m src.core.accepted_vulns .github/accepted-vulnerabilities.json)' in wf
    assert '-o audit.md $ignore' in wf
