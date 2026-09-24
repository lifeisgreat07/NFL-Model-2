"""Stage 7's case studies: one copy of each story, and every figure recomputable.

The full write-ups live in docs/case-studies/, for a technical reader. The
"Checking the AI's work" page carries a short card for each and links to it.
Keeping the story in one place is the point -- two full copies drift, which
is the failure this repository keeps paying for -- so the tests here hold the
two halves to each other, and hold every number in a case study to something
that recomputes it:

  * a figure MEASURED for a case study is checked against the data file the
    measuring script wrote (the pattern of test_published_bootstrap_numbers);
  * a figure QUOTED from history is checked against the commit it cites. A
    commit message cannot change, so "it appears in that commit" is a check
    that stays true, where "someone remembered it" is not.
"""

import json
import re
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
CASE_DIR = REPO / 'docs' / 'case-studies'
TEMPLATE = REPO / 'src' / 'dashboard_template.html'
VERIFICATION = REPO / 'VERIFICATION.md'
BLOB = 'https://github.com/lifeisgreat07/NFL-Model-2/blob/main/'

# A backticked 7-40 character hex string is how a case study cites a commit.
SHA_RE = re.compile(r'`([0-9a-f]{7,40})`')


def case_studies():
    """Every case study file. README.md is the index, not a case study."""
    return sorted(p for p in CASE_DIR.glob('*.md') if p.name != 'README.md')


def cards(page):
    """{slug: href} for every case-study card on the page.

    Anchored on the element's own class attribute, never the bare class name,
    so the CSS or a comment mentioning it cannot be counted as a card.
    """
    found = {}
    for m in re.finditer(r'<div class="case-study" data-case-study="([^"]+)"(.*?)</div>',
                         page, re.S):
        slug, body = m.group(1), m.group(2)
        href = re.search(r'<a href="([^"]+)"', body)
        found[slug] = href.group(1) if href else None
    return found


def strip_comments(html):
    return re.sub(r'<!--.*?-->', '', html, flags=re.S)


def _has_history():
    try:
        out = subprocess.run(['git', 'rev-parse', '--is-shallow-repository'], cwd=REPO,
                             capture_output=True, text=True, check=True).stdout.strip()
    except Exception:
        return False
    return out == 'false'


needs_history = pytest.mark.skipif(
    not _has_history(), reason='needs the full git history to resolve cited commits')


def _commit_text(sha):
    """The commit's message and patch, or None if it does not exist."""
    r = subprocess.run(['git', 'show', '--format=%B', sha], cwd=REPO,
                       capture_output=True, text=True, encoding='utf-8', errors='replace')
    return r.stdout if r.returncode == 0 else None


# ---------------------------------------------------------------------------
# One copy of each story: the cards and the files agree
# ---------------------------------------------------------------------------


def test_there_are_case_studies_to_check():
    """Vacuity guard. Every test below is an "every X" over this list, and an
    empty list would pass all of them while checking nothing."""
    assert case_studies(), f"no case studies found in {CASE_DIR}"
    assert cards(strip_comments(TEMPLATE.read_text(encoding='utf-8'))), (
        "no case-study cards found on the page -- the matcher may have gone blind")


def test_every_case_study_has_a_card_and_every_card_a_case_study():
    page = strip_comments(TEMPLATE.read_text(encoding='utf-8'))
    on_page = cards(page)
    in_repo = {p.stem for p in case_studies()}
    assert set(on_page) == in_repo, (
        f"cards without a case study: {sorted(set(on_page) - in_repo)}; "
        f"case studies without a card: {sorted(in_repo - set(on_page))}")


def test_every_card_links_to_its_own_case_study():
    """A card that links to the wrong file, or to none, reads as a working
    link on the page and only fails for the one reader who clicks it."""
    page = strip_comments(TEMPLATE.read_text(encoding='utf-8'))
    for slug, href in cards(page).items():
        assert href == f'{BLOB}docs/case-studies/{slug}.md', (
            f"the {slug!r} card links to {href!r}")


def test_the_index_lists_every_case_study():
    index = (CASE_DIR / 'README.md').read_text(encoding='utf-8')
    for p in case_studies():
        assert f']({p.name})' in index, f"docs/case-studies/README.md does not link {p.name}"


def incidents_missing(verification_text, page):
    """Incident numbers VERIFICATION.md cites that the page no longer has."""
    return [n for n in re.findall(r'Incident (\d+)', verification_text)
            if f'Incident {n} -- ' not in page]


def test_verification_md_names_only_incidents_the_page_still_has():
    """VERIFICATION.md pointed readers at "Incident 3" on the page. When a
    story moves from an incident to a case study, that pointer goes dead and
    nothing else notices."""
    page = strip_comments(TEMPLATE.read_text(encoding='utf-8'))
    missing = incidents_missing(VERIFICATION.read_text(encoding='utf-8'), page)
    assert not missing, f"VERIFICATION.md cites Incident(s) {missing}, which the page no longer has"


def test_the_incident_check_catches_a_dead_pointer():
    """VERIFICATION.md cites no incident today, so the real check runs over
    nothing. This keeps its failing branch reachable."""
    page = '<h3>Incident 1 -- Something</h3>'
    assert incidents_missing('see Incident 1 and Incident 3', page) == ['3']
    assert incidents_missing('see Incident 1', page) == []


# ---------------------------------------------------------------------------
# Every figure has something that recomputes it
# ---------------------------------------------------------------------------


@needs_history
def test_every_commit_a_case_study_cites_exists():
    cited = {(p.name, sha) for p in case_studies()
             for sha in SHA_RE.findall(p.read_text(encoding='utf-8'))}
    assert cited, "no commits cited at all -- the SHA matcher may have gone blind"
    missing = [(name, sha) for name, sha in sorted(cited) if _commit_text(sha) is None]
    assert not missing, f"cited commits that do not exist: {missing}"


# (case study, the figure exactly as the case study prints it, the commit it
# is quoted from, the same figure as that commit prints it). The last column
# exists because a commit and a prose sentence rarely spell a number the same
# way ("4 of 5 of its tests" against "4 of 5 tests failed"). Whitespace is
# collapsed on the commit side, because a commit message wraps wherever its
# line ran out.
QUOTED = [
    ('qb-rating-leak.md', '-0.3995 to 95.87', 'ec30887', '-0.3995 to 95.87'),
    ('qb-rating-leak.md', '4 of 5 of its tests', '8a0899f', '4 of 5 tests failed'),
    ('qb-rating-leak.md', '[-1.65, +1.29]', 'a86c470', '[-1.65, +1.29]'),
    ('qb-rating-leak.md', 'k=8 won 3 of 4', '870f636', 'k=8 wins 3 of 4 metrics'),
]


@needs_history
@pytest.mark.parametrize('doc, as_printed, sha, in_commit', QUOTED,
                         ids=[f'{q[0]}:{q[2]}' for q in QUOTED])
def test_a_figure_quoted_from_a_commit_is_in_that_commit(doc, as_printed, sha, in_commit):
    text = (CASE_DIR / doc).read_text(encoding='utf-8')
    assert as_printed in text, f"{doc} no longer prints {as_printed!r}"
    assert f'`{sha}`' in text, f"{doc} quotes {as_printed!r} but no longer cites `{sha}`"
    commit = _commit_text(sha)
    assert commit is not None, f"{sha} does not exist"
    assert in_commit in ' '.join(commit.split()), f"{sha} does not say {in_commit!r}"


# --- figures measured for the QB-leak case study -----------------------------

LEAK_DOC = CASE_DIR / 'qb-rating-leak.md'
LEAK_DATA = REPO / 'data' / 'qb_leak_effect.json'


def leak_figures(data):
    """Every figure the QB-leak case study prints from the data file, formatted
    the way the case study prints it. Pure, so it can be checked over a
    synthetic payload as well as the real one."""
    out = [f"measured at `{data['measured_at']}`",
           f"over {data['n_games']} games",
           f"`{data['fix_commit']}`"]
    a, b = data['models']['model_a'], data['models']['model_b']

    def ci(m):
        return f"{m['difference']:+.6f} [{m['ci_lo']:+.6f}, {m['ci_hi']:+.6f}]"

    out.append(f"| Picks that change side | {a['picks_flipped']} | {b['picks_flipped']} |")
    out.append(f"| Largest change to one game's probability | "
               f"{a['max_abs_prob_change'] * 100:.1f} points | "
               f"{b['max_abs_prob_change'] * 100:.1f} points |")
    for key, label in (('brier', 'Brier'), ('log_loss', 'Log loss')):
        out.append(f"| {label} difference, 95% interval | "
                   f"{ci(a['metrics'][key])} | {ci(b['metrics'][key])} |")
    return out


def all_inconclusive(data):
    return all(not m['metrics'][k]['excludes_zero']
               for m in data['models'].values() for k in ('brier', 'log_loss'))


def test_the_leak_figures_match_the_file_they_came_from():
    data = json.loads(LEAK_DATA.read_text(encoding='utf-8'))
    text = LEAK_DOC.read_text(encoding='utf-8')
    for fig in leak_figures(data):
        assert fig in text, f"qb-rating-leak.md does not print {fig!r} from {LEAK_DATA.name}"


def test_every_interval_includes_zero_is_what_the_data_says():
    """The case study's conclusion is a sentence, and a re-run that produced a
    real difference would leave the table right and the sentence wrong."""
    data = json.loads(LEAK_DATA.read_text(encoding='utf-8'))
    text = LEAK_DOC.read_text(encoding='utf-8')
    says_inconclusive = 'Every interval includes zero.' in text
    assert says_inconclusive == all_inconclusive(data), (
        "the case study's verdict sentence disagrees with qb_leak_effect.json")


def test_the_case_study_names_the_machine_its_table_came_from():
    """The table's pick counts and last digits are specific to one machine:
    Booth's Linux re-run of #96 got one fewer pick changing side for each
    model. So the case study must name the machine the JSON says produced it,
    and a re-run on another machine that rewrites the JSON makes this fail
    until the sentence is rewritten with it."""
    prov = json.loads(LEAK_DATA.read_text(encoding='utf-8'))['provenance']
    text = LEAK_DOC.read_text(encoding='utf-8')
    named = f"{prov['system']}, Python {prov['python']}"
    assert named in text, f"qb-rating-leak.md does not say its table came from {named!r}"


def test_the_figure_check_fails_on_a_figure_that_moved():
    """Over a synthetic payload, so the failing branch stays reachable however
    the real file reads: one changed figure must produce one missing line."""
    data = json.loads(LEAK_DATA.read_text(encoding='utf-8'))
    text = LEAK_DOC.read_text(encoding='utf-8')
    moved = json.loads(json.dumps(data))
    moved['models']['model_a']['picks_flipped'] += 1
    missing = [f for f in leak_figures(moved) if f not in text]
    assert len(missing) == 1 and 'Picks that change side' in missing[0]


def test_the_verdict_check_notices_a_real_difference():
    data = json.loads(LEAK_DATA.read_text(encoding='utf-8'))
    real = json.loads(json.dumps(data))
    real['models']['model_b']['metrics']['brier']['excludes_zero'] = True
    assert all_inconclusive(real) is False


def test_the_measuring_script_names_the_commit_the_case_study_cites():
    src = (REPO / 'src' / 'measure_qb_leak.py').read_text(encoding='utf-8')
    data = json.loads(LEAK_DATA.read_text(encoding='utf-8'))
    assert f"FIX_COMMIT = '{data['fix_commit']}'" in src
