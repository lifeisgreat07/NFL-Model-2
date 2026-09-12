"""When a game is played has to survive the trip from schedule to game card.

The queued entry for this work said a week carries only season, week and
games and that no game has a date, kickoff or channel. Half of that was
wrong, and checking cost one query: load_schedules returns 46 columns,
gameday/gametime/weekday are all present with no nulls across 2025 and 2026,
and src/data_loader.py does not subset columns -- so all three were already
in scope at the line in weekly_update.main() that builds a prediction and
were simply never written down. This change writes them down.

The other half was right and stays right: there is NO broadcast-network
column in this source. espn, ftn, pff, pfr, gsis and nfl_detail_id are
cross-reference IDs. "Channel on the card" needs a new external feed and
does not belong to this change.

Two things these tests exist to hold:

  * The zone lives in the field name. gametime is Eastern -- established
    from the distribution, not assumed, because the six Sunday 09:30
    kickoffs in a season are the London and Munich games at 2:30pm local,
    which is only coherent as ET. A time whose zone is unstated is
    unfalsifiable by anyone but its author, the same defect as a measured
    number with no command beside it, so the field is gametime_et.
  * Absent stays absent. predictions/2026_week1.json was saved before these
    fields existed and predictions are permanent once written, so that file
    reaches build_games_js without them forever. The backward-compatible
    path is exercised against that real file rather than a synthetic stand-in,
    because a fixture cannot go stale in the way a shipped file can.
"""
import ast
import io
import inspect
import json
import re
import sys
import tokenize
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

FIELDS = ('gameday', 'gametime_et', 'weekday')


def _code_only(src):
    """Source with comment tokens removed, line structure preserved.

    Same idiom as tests/test_weekly_pipeline.py, and here for the same
    reason: the code these tests guard is deliberately commented with the
    names being checked -- the record builder explains in prose why the
    field is called gametime_et and why there is no channel. A matcher that
    cannot tell a comment from a dict key would read those comments as the
    thing they describe, which is the guard-matches-its-own-docstring
    failure this repository has hit three times.
    """
    lines = src.splitlines()
    cut_at = {}
    for tok in tokenize.generate_tokens(io.StringIO(src).readline):
        if tok.type == tokenize.COMMENT:
            row, col = tok.start
            cut_at[row] = min(cut_at.get(row, col), col)
    return "\n".join(line[:cut_at[i]] if i in cut_at else line
                     for i, line in enumerate(lines, start=1))


def test_the_record_builder_writes_all_three_schedule_fields():
    """Structural, because main() needs six seasons of real play-by-play and
    a network round trip to run. The behavioural half is covered downstream
    by the build_games_js tests; this one stops the write being dropped."""
    import weekly_update

    src = _code_only(inspect.getsource(weekly_update.main))
    for field in FIELDS:
        assert re.search(r"'%s'\s*:" % field, src), (
            f"weekly_update.main() no longer writes {field!r} into the "
            "prediction record. Every already-saved week is permanent, so a "
            "field dropped here is absent from that week forever -- there is "
            "no backfill, the file is never rewritten.")


def test_the_kickoff_field_carries_its_timezone_in_its_name():
    """The rule, stated as a test so it cannot be undone by a tidy-up.

    A reader who renders a bare `gametime` in the browser's local zone turns
    a correct 20:15 into a wrong one for everybody outside ET, and nothing
    downstream can detect it -- the number stays plausible. Naming the field
    is the cheapest guard available, so the bare name is banned where the
    records are built. The source COLUMN is still called gametime; this is
    about the key those modules write.
    """
    import generate_dashboard
    import weekly_update

    for module in (weekly_update, generate_dashboard):
        src = _code_only(inspect.getsource(module))
        assert re.search(r"'gametime_et'\s*:", src), (
            f"{module.__name__} no longer writes a 'gametime_et' key")
        assert not re.search(r"'gametime'\s*:", src), (
            f"{module.__name__} writes a bare 'gametime' key. The value is "
            "Eastern and nothing downstream can tell -- a renderer that "
            "treats it as local time produces a wrong kickoff that still "
            "looks right. Keep the zone in the name.")


def test_the_game_payload_carries_them_through():
    """The behavioural half: a saved record reaches the card with its date."""
    import generate_dashboard

    pred = {'home': 'GB', 'away': 'ATL', 'model_a_home_win_prob': 0.61,
            'model_b_home_win_prob': 0.58, 'spread_line': 7.5,
            'gameday': '2026-09-24', 'gametime_et': '20:15',
            'weekday': 'Thursday'}
    games = generate_dashboard.build_games_js([pred], {})

    assert len(games) == 1
    for field in FIELDS:
        assert games[0][field] == pred[field], (
            f"{field} did not survive build_games_js")


def test_a_week_saved_without_these_fields_still_renders():
    """Absent stays absent -- the property, now on a synthetic record.

    THIS TEST USED THE REAL predictions/2026_week1.json AND DELIBERATELY NO
    LONGER DOES. That is worth reading rather than skipping.

    It asserted that the shipped week-1 file carried none of these fields, on
    the reasoning that predictions are write-once so the pre-fields shape was
    permanent. Its failure message said: either the write-once rule was broken
    or this test is guarding the wrong file, find out which before changing
    the assertion. The rule was bent, on purpose, with the reasoning recorded
    in src/backfill_game_dates.py -- these three are schedule facts rather
    than model outputs, and they became the Week Board's default sort key, so
    leaving the only saved week unsorted to protect a rule about model outputs
    was the wrong trade.

    So the example moved and the property did not. What is being guarded is
    that a record lacking the fields renders with None rather than a
    fabricated date -- the 'correct arithmetic on absent data' failure this
    repo has already shipped once, on Season Accuracy. A synthetic record is a
    weaker example than a real file, and the test below is the compensation:
    it pins what the real file is supposed to look like now.
    """
    import generate_dashboard

    legacy = {'home': 'SEA', 'away': 'NE', 'model_a_home_win_prob': 0.44,
              'model_b_home_win_prob': 0.60, 'spread_line': 3.5,
              'confidence_rank': 7, 'confidence_points': 10}
    games = generate_dashboard.build_games_js([legacy], {})

    assert games, 'a record without these fields stopped producing a game card'
    for field in FIELDS:
        assert games[0][field] is None, (
            f"{field} came back as {games[0][field]!r} for a record that does "
            "not carry it. Absent must stay absent; a fabricated date is the "
            "'correct arithmetic on absent data' failure again.")


def test_every_saved_week_now_carries_its_dates():
    """The other half of the swap above, and the reason it is safe.

    Every prediction file on disk should now be dated -- the ones written
    since the fields existed by weekly_update, and the ones written before by
    the backfill. If a file appears without them, either the backfill was not
    run for it or a week was saved by something that does not write them, and
    both make the Week Board's default sort silently partial.

    `--check` is the mechanical version of this and exits non-zero if any file
    would gain a field; this test states the invariant in the suite so it
    cannot rot unnoticed between runs of that script.
    """
    paths = sorted((ROOT / 'predictions').glob('*_week*.json'))
    assert paths, 'no prediction files on disk at all'
    for path in paths:
        for rec in json.loads(path.read_text(encoding='utf-8')):
            for field in ('gameday', 'gametime_et'):
                assert rec.get(field), (
                    f"{path.name}: {rec['away']}@{rec['home']} has no "
                    f"{field}. Run `python src/backfill_game_dates.py` -- and "
                    "if it reports the record as unmatched, that is a finding "
                    "about the schedule, not a formatting problem.")


def _required_schedule_cols_from(path):
    """The REQUIRED_SCHEDULE_COLS literal, read out of a file's source.

    data_loader keeps its copy inside `if __name__ == '__main__'`, so it
    cannot be imported. Parsing the literal is the only way to compare the
    two without executing a module whose main block fetches the network.
    """
    src = path.read_text(encoding='utf-8')
    m = re.search(r'REQUIRED_SCHEDULE_COLS\s*=\s*(\[.*?\])', src, re.S)
    assert m, f'no REQUIRED_SCHEDULE_COLS literal found in {path.name}'
    return ast.literal_eval(m.group(1))


def test_the_two_required_column_lists_agree():
    """Two copies of one list is the duplication this repo keeps paying for.

    A comment asking the next person to keep them in step is not a check --
    'a note is not a check' is already a trap entry here, written after a
    document pointed at a file that had never existed for months. So the
    agreement is asserted.

    The list is also the closest thing to a guard that the schedule really
    supplies these columns: the suite cannot reach nflverse, but
    verify_data_source_fallback checks every name in this list against both
    sources when it is run for real.
    """
    loader = _required_schedule_cols_from(ROOT / 'src' / 'data_loader.py')
    fallback = _required_schedule_cols_from(
        ROOT / 'src' / 'verify_data_source_fallback.py')

    assert sorted(loader) == sorted(fallback), (
        'the two REQUIRED_SCHEDULE_COLS lists have drifted: '
        f'only in data_loader {sorted(set(loader) - set(fallback))}, '
        f'only in verify_data_source_fallback {sorted(set(fallback) - set(loader))}')

    for column in ('gameday', 'gametime', 'weekday'):
        assert column in loader, (
            f"{column!r} left REQUIRED_SCHEDULE_COLS. weekly_update.main() "
            "reads it off the schedule frame, so dropping it here means the "
            "fallback source can stop supplying it and the only symptom is a "
            "game card that quietly loses its kickoff.")
