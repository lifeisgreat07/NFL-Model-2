"""
Printable / downloadable PDF of one week's picks.

Why this exists: the Week Board is the thing people actually act on, and
confidence pools are frequently filled out on paper or off a phone away
from the site. A print stylesheet was the other option considered and
rejected -- browser print output varies by browser and silently drops
background colors, so "what you printed" wouldn't reliably match "what the
site said". A generated PDF is deterministic and checkable, which also
means it can be tested (see tests/test_picks_pdf.py).

Two deliberate constraints, both about not creating a second source of
truth:

  1. The pick side is derived exactly the way the dashboard derives it --
     Model B's probability when present, Model A's otherwise, home if that
     probability is >= 0.5. That rule lives in dashboard_template.html
     (the `mktB_home >= 50 ? home : away` line) and generate_dashboard.py's
     build_games_js. If this file disagreed with those, the printed sheet
     and the website would recommend different teams, which is the worst
     failure this feature could have.

  2. confidence_rank / confidence_points are READ from the saved
     predictions file, never recomputed. weekly_update.py owns that
     ranking, and saved predictions are permanent once written -- so
     re-deriving the order here would be a second implementation free to
     drift from the one that actually produced the numbers users saw.

Usage:
    python src/generate_picks_pdf.py --season 2026 --week 1
    python src/generate_picks_pdf.py --season 2026 --week 1 --out /tmp/w1.pdf
"""
import argparse
import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Optional, Sequence

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (Paragraph, SimpleDocTemplate, Spacer, Table,
                                TableStyle)

REPO_ROOT = Path(__file__).parent.parent
PRED_DIR = REPO_ROOT / 'predictions'

# Only ASCII and the built-in Helvetica family are used anywhere in this
# file. ReportLab's base-14 fonts have no glyphs for things like check-box
# or arrow characters, and a missing glyph renders as a solid black box
# rather than failing loudly -- so the "mark your result" column is an
# empty cell with grid lines around it, not a drawn checkbox character.
FONT = 'Helvetica'
FONT_BOLD = 'Helvetica-Bold'


@dataclass(frozen=True)
class PickRow:
    """One game's row on the printed sheet."""
    rank: int
    points: int
    away: str
    home: str
    pick: str
    spread: Optional[float]
    model_a: Optional[float]
    model_b: Optional[float]
    market: Optional[float]
    notes: Sequence[str]

    @property
    def matchup(self) -> str:
        return f"{self.away} @ {self.home}"


def _pick_probability(pred: dict) -> float:
    """The probability the dashboard uses for a game: Model B when it's
    available, Model A otherwise. Kept as its own function so the fallback
    is stated in exactly one place."""
    prob = pred.get('model_b_home_win_prob')
    if prob is None:
        prob = pred.get('model_a_home_win_prob')
    if prob is None:
        raise ValueError(
            f"{pred.get('away')}@{pred.get('home')}: prediction has neither "
            "model_b_home_win_prob nor model_a_home_win_prob"
        )
    return prob


def build_picks_rows(preds: Sequence[dict]) -> list[PickRow]:
    """Turn saved predictions into ordered rows for the sheet.

    Ordering comes from the saved confidence_rank -- this function does not
    rank anything itself (see module docstring). Raises on an empty week so
    a missing/empty predictions file can't quietly produce a blank sheet
    that looks like a real one.
    """
    if not preds:
        raise ValueError("no predictions to render -- refusing to emit a blank picks sheet")

    # Predictions saved before confidence ranking existed (e.g. 2025 week 10)
    # have no rank to print and must not have one invented for them here --
    # that would be exactly the second source of truth this module avoids.
    # Fail with a message that names the cause instead of a bare KeyError.
    missing = [f"{p.get('away')}@{p.get('home')}" for p in preds
               if p.get('confidence_rank') is None or p.get('confidence_points') is None]
    if missing:
        raise ValueError(
            "predictions predate confidence ranking (no confidence_rank/"
            f"confidence_points) for {len(missing)} game(s): {', '.join(missing[:4])}"
            f"{'...' if len(missing) > 4 else ''} -- refusing to invent a ranking"
        )

    rows = []
    for p in preds:
        prob = _pick_probability(p)
        rows.append(PickRow(
            rank=p['confidence_rank'],
            points=p['confidence_points'],
            away=p['away'],
            home=p['home'],
            pick=p['home'] if prob >= 0.5 else p['away'],
            spread=p.get('spread_line'),
            model_a=p.get('model_a_home_win_prob'),
            model_b=p.get('model_b_home_win_prob'),
            market=p.get('market_prob_home'),
            notes=tuple(p.get('context_notes') or ()),
        ))

    rows.sort(key=lambda r: r.rank)
    return rows


def _pct(value: Optional[float]) -> str:
    """Home-win probability as a percentage string, or a dash when absent.
    Absent is a real case (Model B needs a spread, which isn't always
    posted yet), and printing a dash is more honest than printing 0%."""
    return '--' if value is None else f"{value * 100:.1f}%"


def _spread(value: Optional[float]) -> str:
    """Spread as posted, from the home team's perspective, sign included so
    the direction is unambiguous on paper."""
    if value is None:
        return '--'
    return f"{value:+.1f}"


def render_picks_pdf(
    rows: Sequence[PickRow],
    season: int,
    week: int,
    model_version: str,
    out_path: Path,
    generated_on: Optional[date] = None,
) -> Path:
    """Render the rows to a letter-size PDF at out_path."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    generated_on = generated_on or date.today()

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'PicksTitle', parent=styles['Title'], fontName=FONT_BOLD,
        fontSize=17, spaceAfter=2, alignment=0,
    )
    sub_style = ParagraphStyle(
        'PicksSub', parent=styles['Normal'], fontName=FONT,
        fontSize=9, textColor=colors.HexColor('#555555'), spaceAfter=10,
    )
    foot_style = ParagraphStyle(
        'PicksFoot', parent=styles['Normal'], fontName=FONT,
        fontSize=7.5, textColor=colors.HexColor('#555555'), leading=10,
    )

    doc = SimpleDocTemplate(
        str(out_path), pagesize=letter,
        leftMargin=0.55 * inch, rightMargin=0.55 * inch,
        topMargin=0.55 * inch, bottomMargin=0.5 * inch,
        title=f"NFL Pick'em {season} Week {week}",
        author=f"NFL-Model-2 v{model_version}",
    )

    story: list[Any] = [
        Paragraph(f"NFL Pick'em &mdash; {season} Week {week}", title_style),
        Paragraph(
            f"{len(rows)} games &nbsp;|&nbsp; model v{model_version} "
            f"&nbsp;|&nbsp; generated {generated_on.isoformat()}",
            sub_style,
        ),
    ]

    header = ['Rank', 'Pts', 'Matchup', 'Pick', 'Spread',
              'Model A', 'Model B', 'Market', 'Result']
    data: list[list[str]] = [header]
    for r in rows:
        data.append([
            str(r.rank), str(r.points), r.matchup, r.pick, _spread(r.spread),
            _pct(r.model_a), _pct(r.model_b), _pct(r.market), '',
        ])

    table = Table(
        data,
        colWidths=[0.45 * inch, 0.38 * inch, 1.30 * inch, 0.62 * inch,
                   0.62 * inch, 0.78 * inch, 0.78 * inch, 0.78 * inch,
                   0.75 * inch],
        repeatRows=1,
    )
    style = [
        ('FONTNAME', (0, 0), (-1, 0), FONT_BOLD),
        ('FONTSIZE', (0, 0), (-1, 0), 8.5),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f2937')),
        ('FONTNAME', (0, 1), (-1, -1), FONT),
        ('FONTSIZE', (0, 1), (-1, -1), 8.5),
        ('FONTNAME', (3, 1), (3, -1), FONT_BOLD),   # the pick itself
        ('ALIGN', (0, 0), (1, -1), 'CENTER'),
        ('ALIGN', (4, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#b8bec9')),
        ('TOPPADDING', (0, 0), (-1, -1), 4.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4.5),
    ]
    # Zebra striping, applied to data rows only.
    for i in range(1, len(data)):
        if i % 2 == 0:
            style.append(('BACKGROUND', (0, i), (-1, i), colors.HexColor('#f2f4f7')))
    table.setStyle(TableStyle(style))
    story.append(table)

    # Any per-game context notes go below the table rather than inside it --
    # they're free text of unpredictable length and would wreck the column
    # widths. Real prediction files often have none at all, in which case
    # this section is omitted entirely rather than printing an empty heading.
    noted = [r for r in rows if r.notes]
    if noted:
        story.append(Spacer(1, 10))
        story.append(Paragraph("<b>Notes</b>", foot_style))
        for r in noted:
            story.append(Paragraph(f"{r.matchup}: {'; '.join(r.notes)}", foot_style))

    story.append(Spacer(1, 12))
    story.append(Paragraph(
        "Confidence points: rank 1 is the most confident pick and carries the most "
        "points; assign them highest-to-lowest in a standard confidence pool. "
        "Model A is football-only (opponent-adjusted EPA and QB ratings). Model B "
        "adds the current Vegas spread. Market is the spread-implied home win "
        "probability. All probabilities are the HOME team's chance of winning; the "
        "Pick column already accounts for that. Spread is from the home team's "
        "perspective.",
        foot_style,
    ))

    doc.build(story)
    return out_path


def load_week(season: int, week: int) -> list[dict]:
    path = PRED_DIR / f'{season}_week{week}.json'
    if not path.exists():
        raise FileNotFoundError(f"no saved predictions at {path}")
    with open(path) as f:
        return json.load(f)


def main() -> None:
    ap = argparse.ArgumentParser(description="Generate a printable PDF of one week's picks.")
    ap.add_argument('--season', type=int, required=True)
    ap.add_argument('--week', type=int, required=True)
    ap.add_argument('--out', type=Path, default=None,
                    help='output path (default: dist/picks_<season>_week<week>.pdf)')
    args = ap.parse_args()

    preds = load_week(args.season, args.week)
    rows = build_picks_rows(preds)

    # Model version comes from the predictions themselves, not config.py --
    # a saved file should print the version that actually produced it, even
    # if config.py has since moved on.
    versions = {p.get('model_version') for p in preds if p.get('model_version')}
    model_version = versions.pop() if len(versions) == 1 else 'mixed'

    out = args.out or (REPO_ROOT / 'dist' / f'picks_{args.season}_week{args.week}.pdf')
    render_picks_pdf(rows, args.season, args.week, model_version, out)
    print(f"Wrote {out} ({len(rows)} games, model v{model_version})")


if __name__ == '__main__':
    main()
