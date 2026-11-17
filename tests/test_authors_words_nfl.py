"""Audit 9 D15, the NFL's part: words only the person who wrote the code reads easily.

Run with: pytest tests/test_authors_words_nfl.py -v
"""
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DASH = ROOT / 'src' / 'dashboard'
BODY = (DASH / 'body.html').read_text(encoding='utf-8')
PAGES = (DASH / 'app_pages.js').read_text(encoding='utf-8')


def visible(html):
    """The markup with its comments taken out: what a reader can be shown."""
    return re.sub(r'<!--.*?-->', '', html, flags=re.S)


def test_no_double_hyphen_reaches_a_reader_of_the_nfl_page():
    lines = [ln.strip()[:80] for ln in visible(BODY).splitlines() if ' -- ' in ln]
    assert not lines, f'a "--" a reader sees: {lines}'


@pytest.mark.parametrize('words', ['static site with no backend', '<code>config.py</code>', '>SOS<',
                                   'SOS is blank', 'Net rating over time --'])
def test_the_ledes_and_headers_no_longer_say(words):
    assert words not in visible(BODY)


@pytest.mark.parametrize('old', [
    'What Actually Separates Them', 'Opponent-Adjusted, Recency-Weighted', 'How We Know a Result Is Real',
    'Which Features Actually Do the Work', 'An Honest Accounting', 'Known Gaps', 'Weekly Automated Process',
    'The Short Version', 'Where This Model Stands', 'What Would Actually Close the Gap', 'In Production',
    'Research-Only', 'Prediction Terms', 'Evaluation Terms', 'Betting Terms', 'Version History',
    'Why This Page Exists', 'Case Studies', 'What This Project Learned', 'The Actual Rule'])
def test_the_methodology_and_checking_headings_are_in_sentence_case(old):
    heads = ' | '.join(re.findall(r'<h[34][^>]*>(.*?)</h[34]>', BODY, re.S))
    assert old not in heads


def test_the_schedule_column_keeps_its_explanation():
    th = re.search(r'<th[^>]*data-key="sos"[^>]*>(.*?)</th>', BODY, re.S)
    assert th and th.group(1) == 'Schedule'
    assert 'title="Strength of schedule:' in th.group(0)


def test_checking_dates_its_collections_in_eastern_time_not_iso():
    assert "Collected ${agentLog.generated_utc ? runStartedText(agentLog.generated_utc) + ' ET'" in PAGES
    assert "Read ${recentRuns.read_utc ? runStartedText(recentRuns.read_utc) + ' ET'" in PAGES
    assert '(UTC)' not in PAGES


def test_the_run_table_says_minutes_and_started_late_by():
    head = re.search(r'<thead><tr><th scope="col">Job</th>.*?</tr></thead>', PAGES, re.S).group(0)
    assert '<th scope="col">Minutes</th>' in head and '<th scope="col">Started late by</th>' in head
    assert '>Min<' not in head
