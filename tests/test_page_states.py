"""
Stage 10's page states (2026-09-23).

Before this, "nothing to show" was built from three different components:
an `.empty-state` box, a `.table-note`, and a `.method-block` with a heading.
The kinds a reader must tell apart were not told apart: "no games have been
played yet" (normal, will fill) and "the page was built without its data
file" (something is broken) wore the same dashed box. The broken one reading
as the calm one is the flattering direction, so it is the one that matters.

Now every state is written by stateHtml() in one of four kinds -- waiting,
filtered, missing, note -- and which kind each branch uses is pinned below,
so a missing file cannot quietly become a "not yet".

There is no loading kind because nothing is fetched after the page is built;
test_the_page_fetches_nothing holds that premise, so the day something is
fetched, this file says a loading state is now owed.

Run with: pytest tests/test_page_states.py -v
"""
import re
from pathlib import Path

import pytest

TEMPLATE = Path(__file__).parent.parent / 'src' / 'dashboard_template.html'

#: Which kinds each render function may use. A new state anywhere else, or a
#: kind changing, fails -- decide it on purpose.
EXPECTED = {
    'renderGames': {'waiting', 'filtered'},
    'renderPicksGrid': {'waiting'},
    'renderAccuracy': {'waiting'},
    'renderTeamDive': {'missing', 'waiting'},
    'renderTeamGames': {'note'},
    'renderAgentLog': {'missing'},
    'renderChangelog': {'missing'},
}


def strip_comments(src):
    src = re.sub(r'/\*.*?\*/', '', src, flags=re.S)
    src = re.sub(r'<!--.*?-->', '', src, flags=re.S)
    return re.sub(r'(?m)^\s*//.*$', '', src)


def state_calls(src):
    """{function name: {kind, ...}} for every stateHtml(...) call site, plus
    the raw text of each call for the per-kind checks."""
    by_fn, calls = {}, []
    fn_starts = [(m.start(), m.group(1)) for m in re.finditer(r'function\s+(\w+)\s*\(', src)]
    for m in re.finditer(r"stateHtml\(\s*'(\w+)'", src):
        owner = [name for start, name in fn_starts if start < m.start()][-1]
        if owner == 'stateHtml':
            continue
        by_fn.setdefault(owner, set()).add(m.group(1))
        depth, i = 0, m.start() + len('stateHtml')
        while i < len(src):
            depth += {'(': 1, ')': -1}.get(src[i], 0)
            i += 1
            if depth == 0:
                break
        calls.append((m.group(1), src[m.start():i]))
    return by_fn, calls


@pytest.fixture(scope='module')
def src():
    return strip_comments(TEMPLATE.read_text(encoding='utf-8'))


def test_the_old_state_classes_are_retired(src):
    for cls in ('empty-state', 'empty-readable', 'table-note'):
        assert not re.search(r'\b' + cls + r'\b', src), (
            f'.{cls} is back. Every state goes through stateHtml() now, so a '
            f'second way to say "nothing here" is the thing this stage removed.')


def test_every_state_is_one_of_the_four_kinds(src):
    kinds = re.search(r"const STATE_KINDS = \[([^\]]*)\]", src)
    assert kinds, 'STATE_KINDS is gone -- re-anchor this guard'
    declared = set(re.findall(r"'(\w+)'", kinds.group(1)))
    assert declared == {'waiting', 'filtered', 'missing', 'note'}
    used = set().union(*state_calls(src)[0].values())
    assert used <= declared, f'undeclared kinds: {used - declared}'


def test_each_branch_uses_the_kind_it_was_decided_to(src):
    assert state_calls(src)[0] == EXPECTED


def test_a_filtered_state_offers_its_undo(src):
    filtered = [c for k, c in state_calls(src)[1] if k == 'filtered']
    assert filtered, 'no filtered state found -- re-anchor this guard'
    for call in filtered:
        assert re.search(r'\{\s*label\s*:', call), f'a filtered state with no way back: {call[:80]}'


def test_the_kinds_that_must_look_different_do(src):
    css = src[:src.index('</style>')]
    missing = re.search(r'\.state--missing\s*\{([^}]*)\}', css)
    # border-style specifically: the first draft checked for the word 'solid'
    # anywhere in the rule, and a mutation to a dashed border SURVIVED it,
    # because the heavier left rule also says solid.
    assert missing and re.search(r'border-style\s*:\s*solid', missing.group(1)), (
        'a missing-data state no longer looks different from a waiting one')
    assert re.search(r'border-left\s*:\s*3px', missing.group(1))
    assert re.search(r'\.state--note\s*\{', css)
    assert re.search(r'role="status"', src), 'states are no longer announced'


def test_the_page_fetches_nothing(src):
    """The premise behind having no loading state at all."""
    assert not re.search(r'\bfetch\(|XMLHttpRequest|\bimport\(', src), (
        'the page now loads something after it is built, so it owes a loading '
        'state -- add one to stateHtml() and to the Page states comment')
