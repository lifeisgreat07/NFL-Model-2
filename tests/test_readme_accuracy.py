"""README.md is the recruiter-facing front page, held to the same rule as
CLAUDE.md: it may not name a path that is not there.

It had gone stale in exactly the ways a front page does, and none of it was
visible from inside the repo because nothing checked:

- its fifth line said "see METHODOLOGY.md" for the backtest numbers. There
  has never been a METHODOLOGY.md in this repository. src/tune_qb_shrink_k.py
  had already noticed and written that down; two other files went on pointing
  at it anyway, and so did the README;
- the repo layout named `dashboard.html`, a file that does not exist -- the
  generated dashboard is `index.html`;
- it said `backtest.py` was something you should "add your own copy" of, and
  that `generate_dashboard.py` "isn't built yet". Both have existed for
  stages. A reader following the README would conclude the project is less
  finished than it is.

The numeric claims in the recruiter section are checked against the thing
they describe rather than restated, so "six CI workflows" cannot survive a
seventh being added.
"""

import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
README = REPO / 'README.md'
TEXT = README.read_text(encoding='utf-8')

WORDS = {'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5, 'six': 6,
         'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10}


def _looks_like_a_path(token):
    if any(c in token for c in ' *<>|$(){}'):
        return False
    return token.endswith(('.py', '.yml', '.md', '.json', '.html', '.csv'))


def test_every_path_the_readme_names_in_prose_exists():
    """Backticked paths. The same guard CLAUDE.md, docs/context.md and
    docs/index.md are already held to -- a front page that points at a file
    which is not there is worse than one that says nothing, because the reader
    assumes the omission is theirs."""
    missing = sorted({t for t in re.findall(r'`([^`\n]+)`', TEXT)
                      if _looks_like_a_path(t) and not (REPO / t).exists()})
    assert not missing, f"README.md names {len(missing)} path(s) that do not exist: {missing}"


def _layout_paths():
    """Walk the ``` block under '## Repo layout', tracking the directory a
    line is indented under. A bare `config.py` under `src/` means
    `src/config.py`, and checking it as a top-level file would pass while
    meaning nothing."""
    block = re.search(r'## Repo layout\s*\n```\n(.*?)\n```', TEXT, re.S)
    assert block, "README.md has no '## Repo layout' code block to check"
    prefix = ''
    found = []
    for line in block.group(1).splitlines():
        if not line.strip():
            continue
        indented = line[:1].isspace()
        token = line.strip().split()[0].rstrip(',')
        if not indented:
            prefix = token if token.endswith('/') else ''
        if token.endswith('/'):
            found.append(token)
        elif _looks_like_a_path(token):
            found.append(prefix + token)
    assert found, "the repo layout block parsed to nothing; the parser is broken, not the README"
    return found


def test_every_path_in_the_repo_layout_exists():
    """This is the check that would have caught `dashboard.html`: a layout
    diagram is read as a map of the project, and a wrong entry sends someone
    looking for a file that was renamed three stages ago."""
    missing = sorted({p for p in _layout_paths() if not (REPO / p).exists()})
    assert not missing, f"README.md's repo layout names {len(missing)} path(s) that do not exist: {missing}"


def test_nothing_in_the_repo_points_at_a_methodology_file_that_is_not_there():
    """Scoped to pointer phrasings ("see METHODOLOGY.md", "in METHODOLOGY.md")
    on purpose. Writing down that the file never existed is how the mistake
    stays fixed; this must ban the dangling pointer without banning the
    explanation of it."""
    if (REPO / 'METHODOLOGY.md').exists():
        pytest.skip("METHODOLOGY.md exists, so pointing at it is fine")
    pattern = re.compile(r'\b(?:see|in|per)\s+"?METHODOLOGY\.md', re.I)
    me = Path(__file__).resolve()
    offenders = []
    for path in REPO.rglob('*'):
        if not path.is_file() or path.suffix not in {'.py', '.md', '.yml', '.html'}:
            continue
        if any(part in {'.git', '__pycache__', '.pytest_cache'} for part in path.parts):
            continue
        # This file states the rule, so it necessarily contains the pattern the
        # rule bans. Caught on the first run: the guard's own docstring was its
        # only offender. Excluding it is the honest fix -- the alternative is
        # describing the banned string obliquely enough to dodge your own
        # regex, which makes the rule harder to read to protect the checker.
        if path.resolve() == me:
            continue
        if pattern.search(path.read_text(encoding='utf-8', errors='ignore')):
            offenders.append(str(path.relative_to(REPO)).replace('\\', '/'))
    assert not offenders, (
        f"these files send the reader to a METHODOLOGY.md that does not exist: "
        f"{sorted(offenders)}. Either write the file or repoint them at the "
        f"dashboard's Methodology page")


def test_the_recruiter_section_comes_before_the_statistical_detail():
    """It exists for someone who will give the page thirty seconds. Below the
    ridge regression and the log-loss table it may as well not be there."""
    overview = TEXT.find('## For recruiters')
    assert overview != -1, "README.md has no '## For recruiters' section"
    detail = TEXT.find('## Current model')
    assert detail != -1, "README.md has no '## Current model' section"
    assert overview < detail, (
        "the recruiter overview sits below the model detail; it is meant to be "
        "the first thing on the page after the headline")


def test_the_workflow_count_it_states_is_the_real_one():
    m = re.search(r'\*\*(\w+) CI workflows\*\*', TEXT)
    assert m, "README.md no longer states a CI workflow count in the expected format"
    claimed = WORDS.get(m.group(1).lower(), None)
    assert claimed is not None, f"unrecognised number word in README.md: {m.group(1)!r}"
    real = len(list((REPO / '.github' / 'workflows').glob('*.yml')))
    assert claimed == real, (
        f"README.md claims {claimed} CI workflows; .github/workflows/ holds {real}")


def test_the_mutation_case_count_it_states_is_the_real_one():
    m = re.search(r'`tests/mutation/`,\s*(\d+)\s*cases', TEXT)
    assert m, "README.md no longer states a mutation case count in the expected format"
    claimed = int(m.group(1))
    real = len(list((REPO / 'tests' / 'mutation' / 'cases').glob('*.json')))
    assert claimed == real, (
        f"README.md claims {claimed} mutation cases; tests/mutation/cases/ holds {real}")


def test_the_dashboard_link_matches_the_one_verification_md_uses():
    """Two documents each carrying the published URL is two chances to be
    wrong, and the wrong one is a dead link on the page a recruiter opens
    first. They do not have to be the only copies; they do have to agree."""
    def _links(text):
        return set(re.findall(r'https://[\w.-]+\.github\.io/[\w.-]+/?', text))
    readme = _links(TEXT)
    assert readme, "README.md no longer links the live dashboard"
    verification = _links((REPO / 'VERIFICATION.md').read_text(encoding='utf-8'))
    assert verification, "VERIFICATION.md no longer links the live dashboard"
    assert readme == verification, (
        f"README.md and VERIFICATION.md point at different dashboards: "
        f"{sorted(readme)} vs {sorted(verification)}")


if __name__ == '__main__':
    sys.exit(pytest.main([__file__, '-v']))
