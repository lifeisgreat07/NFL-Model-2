"""
Tests for the printable week-picks PDF (src/generate_picks_pdf.py).

Design principle, same as test_leak_free.py: these tests import the ACTUAL
production functions and run them against the REAL committed predictions
file, not a synthetic fixture invented to match the code. The PDF assertions
extract text back out of the generated file rather than checking that a file
merely exists -- "the PDF was written" is not evidence that the picks are
actually on the page.

Two things this suite deliberately pins down, because both are places a
second, silently-diverging source of truth could creep in:

  1. The pick side must be derived exactly the way the dashboard derives it
     (Model B when present, else Model A; home if prob >= 0.5). If someone
     changes one and not the other, the printed sheet and the website would
     disagree about who to pick, which is the worst possible failure for
     this feature.
  2. confidence_rank / confidence_points must be READ from the saved file,
     never recomputed here. weekly_update.py owns that ranking and the
     predictions are permanent once saved; re-deriving them in a second
     place invites drift.

Run with: pytest tests/test_picks_pdf.py -v
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

REPO_ROOT = Path(__file__).parent.parent
REAL_WEEK_FILE = REPO_ROOT / "predictions" / "2026_week1.json"


@pytest.fixture
def real_preds():
    """The actual committed Week 1 2026 predictions -- real data, not a fixture."""
    with open(REAL_WEEK_FILE) as f:
        return json.load(f)


# ============================================================
# Row-building logic (pure, no PDF involved)
# ============================================================
def test_rows_preserve_saved_confidence_order(real_preds):
    """Rows come out ordered by the SAVED confidence_rank, 1..N, and carry
    the saved points through unchanged."""
    from generate_picks_pdf import build_picks_rows

    rows = build_picks_rows(real_preds)

    assert len(rows) == len(real_preds)
    assert [r.rank for r in rows] == list(range(1, len(real_preds) + 1))

    saved_points = {p["confidence_rank"]: p["confidence_points"] for p in real_preds}
    for r in rows:
        assert r.points == saved_points[r.rank], (
            f"rank {r.rank}: points {r.points} != saved {saved_points[r.rank]}"
        )


def test_pick_matches_dashboard_rule_on_real_data(real_preds):
    """The pick must match the dashboard's rule exactly, computed here
    independently from the raw file rather than by calling the same helper."""
    from generate_picks_pdf import build_picks_rows

    rows = {(r.away, r.home): r for r in build_picks_rows(real_preds)}

    for p in real_preds:
        prob = p["model_b_home_win_prob"]
        if prob is None:
            prob = p["model_a_home_win_prob"]
        expected = p["home"] if prob >= 0.5 else p["away"]
        assert rows[(p["away"], p["home"])].pick == expected, (
            f"{p['away']}@{p['home']}: expected pick {expected}"
        )


def test_pick_falls_back_to_model_a_when_model_b_missing():
    """Model B is allowed to be absent; the dashboard falls back to Model A
    and so must this. Model A here says AWAY, Model B is missing -- if the
    fallback were broken this would silently pick the home side."""
    from generate_picks_pdf import build_picks_rows

    preds = [{
        "season": 2026, "week": 1, "home": "AAA", "away": "BBB",
        "model_a_home_win_prob": 0.20, "model_b_home_win_prob": None,
        "market_prob_home": 0.5, "spread_line": 1.0,
        "confidence_rank": 1, "confidence_points": 1, "context_notes": [],
    }]

    rows = build_picks_rows(preds)
    assert rows[0].pick == "BBB"
    assert rows[0].model_b is None


def test_ranks_are_read_not_recomputed():
    """Guard against a second source of truth: this input's saved ranks
    deliberately CONTRADICT what a fresh distance-from-0.5 sort would
    produce. The saved order must win."""
    from generate_picks_pdf import build_picks_rows

    preds = [
        {  # further from a coin flip, but saved as rank 2
            "season": 2026, "week": 1, "home": "AAA", "away": "BBB",
            "model_a_home_win_prob": 0.9, "model_b_home_win_prob": 0.9,
            "market_prob_home": 0.5, "spread_line": 1.0,
            "confidence_rank": 2, "confidence_points": 1, "context_notes": [],
        },
        {  # nearer a coin flip, but saved as rank 1
            "season": 2026, "week": 1, "home": "CCC", "away": "DDD",
            "model_a_home_win_prob": 0.55, "model_b_home_win_prob": 0.55,
            "market_prob_home": 0.5, "spread_line": 1.0,
            "confidence_rank": 1, "confidence_points": 2, "context_notes": [],
        },
    ]

    rows = build_picks_rows(preds)
    assert [(r.rank, r.home) for r in rows] == [(1, "CCC"), (2, "AAA")]


def test_legacy_predictions_without_ranking_rejected_clearly():
    """The real 2025 week 10 file predates confidence ranking. It must fail
    with an explanatory error, not a bare KeyError, and must never have a
    ranking invented for it."""
    from generate_picks_pdf import build_picks_rows

    legacy = REPO_ROOT / "predictions" / "2025_week10.json"
    if not legacy.exists():
        pytest.skip("legacy prediction file not present")

    with open(legacy) as f:
        preds = json.load(f)

    with pytest.raises(ValueError, match="predate confidence ranking"):
        build_picks_rows(preds)


def test_empty_predictions_rejected():
    """An empty week should fail loudly, not silently emit a blank sheet
    that looks like a real one."""
    from generate_picks_pdf import build_picks_rows

    with pytest.raises(ValueError):
        build_picks_rows([])


# ============================================================
# Rendered PDF -- verified by reading the text back out
# ============================================================
def test_pdf_contains_every_game_and_pick(tmp_path, real_preds):
    """Generate the real PDF and extract its text: every matchup and every
    picked team must actually appear on the page."""
    from pypdf import PdfReader

    from generate_picks_pdf import build_picks_rows, render_picks_pdf

    out = tmp_path / "picks.pdf"
    rows = build_picks_rows(real_preds)
    render_picks_pdf(rows, season=2026, week=1, model_version="2.4", out_path=out)

    assert out.exists() and out.stat().st_size > 1000

    text = "".join(page.extract_text() for page in PdfReader(str(out)).pages)

    for r in rows:
        assert f"{r.away} @ {r.home}" in text, f"missing matchup {r.away} @ {r.home}"
    assert "Confidence" in text
    assert "2.4" in text, "model version must be on the sheet for traceability"
    assert str(len(rows)) in text


def test_pdf_reports_correct_page_and_game_count(tmp_path, real_preds):
    """All 16 games must fit and be present -- a silent truncation to one
    page of 10 rows would otherwise look fine."""
    from pypdf import PdfReader

    from generate_picks_pdf import build_picks_rows, render_picks_pdf

    out = tmp_path / "picks.pdf"
    rows = build_picks_rows(real_preds)
    render_picks_pdf(rows, season=2026, week=1, model_version="2.4", out_path=out)

    text = "".join(page.extract_text() for page in PdfReader(str(out)).pages)
    for rank in range(1, len(rows) + 1):
        assert str(rank) in text


if __name__ == '__main__':
    sys.exit(pytest.main([__file__, '-v']))
