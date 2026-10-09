"""
The backtest's published figures, held to the files they came from.

data/nfl/calibration.json and data/nfl/bootstrap_brier_gap.json carry the model
version of the backtest that wrote them (2.4). MODEL_VERSION is 2.5, and 2.5
changed only which quarterback the live picks use: the backtest was always
scored with the real starter, so its numbers did not move (VERSION_HISTORY's
2.5 entry says so). That allowance is written down here, with its reason, so
the next version bump has to either re-run the backtest or add itself to the
list and say why. Nothing else in the suite noticed the gap between 2.4 and
2.5.

The Methodology page's backtest table is held to data/nfl/calibration.json, and
README's table is held to the page by test_readme_accuracy.py, so both
published tables now trace back to the file. Log loss, Brier and AUC must be
the file's figures to the three decimals printed, and accuracy the file's
figure to the one decimal printed. Until 2026-09-29 accuracy was allowed
rounding plus two games, the allowance reproducibility_audit.py uses for a
re-run on another machine, and the page used it: it printed 62.8% and 68.2%
where the file says 62.74% and 68.26%. Mark chose to print the file's own
figures, so the page is now held to them exactly. The machine allowance
still belongs where machines differ, in the reproducibility audit.

data/nfl/reproducibility_audit.json carries no model version; it is tied to
calibration.json by generated_at in test_reproducibility_audit.py.

The version check covers every file under data/ that names both a
model_version and the backtest_seasons it scored, found by looking rather
than listed by hand. Until 2026-10-03 it named calibration.json and
bootstrap_brier_gap.json only, so ats_evaluation.json (the ATS finding) and
low_confidence_finding.json, both from model 2.4 as well, could have been
left behind by a release that re-ran the other two. KNOWN_BACKTEST_FILES is
a floor under the search, so a search that stops finding files fails
instead of passing on nothing.

Run with: pytest tests/test_backtest_figures_tie.py -v
"""
import json
import re
from pathlib import Path

import pytest

REPO = Path(__file__).parent.parent

from src.core.template_parts import JOINED_TEMPLATE
from src.sports.nfl.config import VERSION_HISTORY

CALIBRATION = 'data/nfl/calibration.json'
BOOTSTRAP = 'data/nfl/bootstrap_brier_gap.json'
TEMPLATE = JOINED_TEMPLATE

# Releases after the backtest files were written that did not change what
# the backtest scores. Re-running the backtest under a newer version empties
# this; a release that is not here and is newer than the files fails.
BACKTEST_UNCHANGED = {
    '2.5': 'the live picks use the listed starter; the backtest always used the real one',
}

# Methodology table row -> calibration.json model.
PAGE_ROWS = {
    'Model A -- live, 4 features, weekly refit': 'model_a',
    'Vegas market alone': 'market',
    'Model B -- live, 4 features + market, weekly refit': 'model_b',
}


def load(rel):
    return json.loads((REPO / rel).read_text(encoding='utf-8'))


def backtest_files(root):
    """Every JSON file under root/data that records the model version and
    the backtest seasons it was scored on, as repo-relative paths."""
    found = []
    for path in sorted((root / 'data').rglob('*.json')):
        try:
            doc = json.loads(path.read_text(encoding='utf-8'))
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
        if isinstance(doc, dict) and 'model_version' in doc and 'backtest_seasons' in doc:
            found.append(path.relative_to(root).as_posix())
    return found


# Files the search must find. A floor, not the list: anything else that
# carries both keys is checked too.
KNOWN_BACKTEST_FILES = {
    CALIBRATION,
    BOOTSTRAP,
    'data/nfl/ats_evaluation.json',
    'data/nfl/low_confidence_finding.json',
}
BACKTEST_FILES = backtest_files(REPO)


def version_key(v):
    return tuple(int(p) for p in v.split('.'))


def unexplained(file_version, history, allowance):
    """Releases newer than the backtest files that the allowance does not cover."""
    return [e['version'] for e in history
            if version_key(e['version']) > version_key(file_version)
            and e['version'] not in allowance]


def methodology_table(html):
    """(intro paragraph, {label: [cells]}) for the Methodology backtest table."""
    block = re.search(r'Backtest Results .*?<p>(.*?)</p>.*?<tbody>(.*?)</tbody>', html, re.S)
    assert block, "the Methodology backtest table was not found; the matcher is broken"
    rows = {}
    for tr in re.findall(r'<tr>(.*?)</tr>', block.group(2), re.S):
        cells = [re.sub(r'<[^>]+>', '', c).strip()
                 for c in re.findall(r'<td[^>]*>(.*?)</td>', tr, re.S)]
        rows[cells[0]] = cells[1:]
    return block.group(1), rows


def mismatches(cells, metrics, model):
    """What in one printed row disagrees with the backtest's metrics."""
    accuracy, log_loss, brier, auc = cells
    wrong = [f"{name} prints {shown}, the file says {metrics[key]:.3f}"
             for name, key, shown in (('log loss', 'log_loss', log_loss),
                                      ('Brier', 'brier', brier), ('AUC', 'auc', auc))
             if shown != f"{metrics[key]:.3f}"]
    if accuracy != f"{100 * metrics['accuracy']:.1f}%":
        wrong.append(f"accuracy prints {accuracy}, the file says "
                     f"{100 * metrics['accuracy']:.1f}%")
    return wrong


# --- the model version -------------------------------------------------------

def test_the_search_finds_every_known_backtest_file():
    missing = KNOWN_BACKTEST_FILES - set(BACKTEST_FILES)
    assert not missing, (
        f"the search for backtest files under data/ did not find {sorted(missing)}; "
        "either the search is broken or a file lost its model_version/backtest_seasons")


@pytest.mark.parametrize('rel', BACKTEST_FILES)
def test_every_release_since_the_backtest_left_it_unchanged(rel):
    version = load(rel)['model_version']
    assert version in {e['version'] for e in VERSION_HISTORY}, (
        f"{rel} was written by model {version}, which VERSION_HISTORY never released")
    missing = unexplained(version, VERSION_HISTORY, BACKTEST_UNCHANGED)
    assert not missing, (
        f"{rel} is from model {version}, but {missing} came after it and is not in "
        "BACKTEST_UNCHANGED. Re-run the script under src/sports/nfl/research/ that writes it (for "
        "calibration.json also src/sports/nfl/research/reproducibility_audit.py), or add the "
        "release to the allowance with the reason its numbers did not move.")


def test_the_two_backtest_files_come_from_the_same_run():
    cal, boot = load(CALIBRATION), load(BOOTSTRAP)
    assert cal['model_version'] == boot['model_version']
    assert cal['backtest_seasons'] == boot['backtest_seasons']


def test_the_allowance_names_only_releases_newer_than_the_backtest():
    """Once the backtest is re-run, an old allowance would excuse nothing and
    mislead the next reader, so it has to go. Measured against the OLDEST
    backtest file: an entry stays while any file still needs it."""
    version = min((load(rel)['model_version'] for rel in BACKTEST_FILES), key=version_key)
    released = {e['version'] for e in VERSION_HISTORY}
    for v in BACKTEST_UNCHANGED:
        assert v in released, f"BACKTEST_UNCHANGED names {v}, which was never released"
        assert version_key(v) > version_key(version), (
            f"BACKTEST_UNCHANGED names {v}, but the backtest files are from {version}; "
            "delete the entry")


def test_a_release_the_allowance_does_not_cover_is_caught():
    """Synthetic, so the failing branch stays reachable while the two agree."""
    history = [{'version': '2.6'}] + list(VERSION_HISTORY)
    assert unexplained('2.4', history, BACKTEST_UNCHANGED) == ['2.6']
    assert unexplained('2.4', VERSION_HISTORY, {}) == ['2.5']


def test_the_search_skips_files_without_both_keys(tmp_path):
    """Synthetic: only a file naming both keys counts as a backtest file."""
    data = tmp_path / 'data' / 'sub'
    data.mkdir(parents=True)
    (data / 'both.json').write_text('{"model_version": "2.4", "backtest_seasons": [2022]}',
                                    encoding='utf-8')
    (data / 'version_only.json').write_text('{"model_version": "2.4"}', encoding='utf-8')
    (data / 'a_list.json').write_text('[1, 2]', encoding='utf-8')
    (data / 'broken.json').write_text('{', encoding='utf-8')
    assert backtest_files(tmp_path) == ['data/sub/both.json']


# --- the published table -----------------------------------------------------

@pytest.mark.parametrize('row,model', PAGE_ROWS.items())
def test_the_methodology_table_prints_the_backtest_file(row, model):
    _, rows = methodology_table(TEMPLATE.read_text(encoding='utf-8'))
    assert row in rows, f"the Methodology table has no row {row!r}"
    metrics = load(CALIBRATION)['models'][model]['metrics']
    wrong = mismatches(rows[row], metrics, model)
    assert not wrong, f"{row}: " + '; '.join(wrong)


def test_the_table_covers_every_model_the_backtest_scored():
    assert set(PAGE_ROWS.values()) == set(load(CALIBRATION)['models'])


def test_the_table_names_the_seasons_and_games_the_backtest_used():
    intro, _ = methodology_table(TEMPLATE.read_text(encoding='utf-8'))
    cal = load(CALIBRATION)
    seasons = cal['backtest_seasons']
    n = {m['metrics']['n'] for m in cal['models'].values()}
    assert len(n) == 1, f"the models were scored on different game counts: {n}"
    assert f"Evaluated on {min(seasons)}-{max(seasons)} ({n.pop():,} games)" in intro


def test_a_drifted_figure_is_caught():
    """Synthetic: the comparison has to fail on a figure a digit off and on an
    accuracy one game off, or the tests above prove nothing."""
    metrics = load(CALIBRATION)['models']['model_a']['metrics']
    good = [f"{100 * metrics['accuracy']:.1f}%", f"{metrics['log_loss']:.3f}",
            f"{metrics['brier']:.3f}", f"{metrics['auc']:.3f}"]
    assert mismatches(good, metrics, 'model_a') == []
    assert mismatches([good[0], '0.651', good[2], good[3]], metrics, 'model_a')
    one_off = metrics['accuracy'] + 1 / metrics['n']
    assert f"{100 * one_off:.1f}%" != good[0], "one game does not move the printed figure here"
    assert mismatches([f"{100 * one_off:.1f}%"] + good[1:], metrics, 'model_a')
