""""Checking the AI's work" -- the page that shows what the verifier caught.

Stage 3 built `src/collect_agent_log.py` and tested it. Stage 7.5 was meant to
rebuild this page around its output. The gap nobody had noticed: THE COLLECTOR
HAD NEVER RUN. It was committed, covered by tests and mutations, and
`data/agent_log.json` did not exist -- nothing invoked it, and
`generate_dashboard.py` had never heard of it. A tested component wired to
nothing looks exactly like a working feature from inside the test suite.

So the tests here are mostly about the WIRING, which is what was missing:
a workflow that produces the file, a loader that reads it, an injection that
reaches the page, and a page that behaves correctly when the file is absent --
which is the state it ships in today and will stay in until the workflow runs.
"""

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / 'src'))

import generate_dashboard as gd  # noqa: E402

TEMPLATE = REPO_ROOT / 'src' / 'dashboard_template.html'
WORKFLOW = REPO_ROOT / '.github' / 'workflows' / 'collect-agent-log.yml'


def _page():
    return TEMPLATE.read_text(encoding='utf-8')


# ---------------------------------------------------------------------------
# The wiring that did not exist
# ---------------------------------------------------------------------------

def test_something_actually_runs_the_collector():
    """The defect this file exists for. `collect_agent_log.py` was committed,
    tested and mutation-covered, and nothing on earth invoked it."""
    assert WORKFLOW.exists(), (
        "no workflow runs src/collect_agent_log.py, so data/agent_log.json is "
        "never produced and the page it feeds has nothing to render")
    text = WORKFLOW.read_text(encoding='utf-8')
    assert 'src/collect_agent_log.py' in text
    assert 'data/agent_log.json' in text, "the workflow never commits its output"


def test_the_collector_workflow_is_not_a_pwn_request():
    """`pull_request_target` runs with the base repository's permissions and
    can be started from a fork. Combined with `contents: write` on a public
    repo that is the shape of the pwn-request vulnerability -- one careless
    "check out the PR head" away from running a stranger's code with a write
    token. The first draft of this workflow had exactly that, for no benefit:
    a push to main is the same signal without the exposure.

    Checked against the YAML with comment lines stripped: the workflow
    explains in a comment why it does not use pull_request_target, and the
    first version of this test failed on that explanation. Third time today a
    guard has matched inside a comment -- strip them before matching.
    """
    lines = [l for l in WORKFLOW.read_text(encoding='utf-8').splitlines()
             if not l.lstrip().startswith('#')]
    assert 'pull_request_target' not in '\n'.join(lines), (
        "collect-agent-log.yml uses pull_request_target while holding "
        "contents: write")


def test_the_collector_workflow_cannot_retrigger_itself():
    """It writes data/agent_log.json; a push to main is its own trigger. The
    path exclusion is the safeguard that does not depend on GitHub's
    token-push rule continuing to exist."""
    text = WORKFLOW.read_text(encoding='utf-8')
    assert 'paths-ignore' in text and 'data/agent_log.json' in text.split('paths-ignore')[1][:300], (
        "the workflow does not exclude its own output from its trigger")


def test_the_generator_loads_and_injects_the_log():
    src = Path(gd.__file__).read_text(encoding='utf-8')
    assert 'def load_agent_log(' in src, "the generator cannot read the log"
    assert '__AGENT_LOG_JSON__' in src, "the generator never injects it"
    assert '__AGENT_LOG_JSON__' in _page(), "the template has no placeholder to fill"
    load = re.search(r'agent_log\s*=\s*load_agent_log\(\)', src)
    assert load, "main() never calls load_agent_log()"


def test_a_missing_log_is_none_and_not_an_empty_dict(tmp_path, monkeypatch):
    """`{}` was how the Team Deep-Dive page rendered empty for months: every
    caller treated it as real data and the page said nothing. Here the two
    states make opposite claims about the verifier -- "no audits recorded yet"
    versus "audits ran and found nothing" -- and the second is the flattering
    one. None forces the page to choose."""
    monkeypatch.setattr(gd, 'DATA_DIR', tmp_path)
    assert gd.load_agent_log() is None


def test_a_present_log_is_read_back(tmp_path, monkeypatch):
    payload = {'summary': {'audits_total': 3}, 'audits': []}
    (tmp_path / 'agent_log.json').write_text(json.dumps(payload), encoding='utf-8')
    monkeypatch.setattr(gd, 'DATA_DIR', tmp_path)
    assert gd.load_agent_log() == payload


# ---------------------------------------------------------------------------
# The page
# ---------------------------------------------------------------------------

def test_the_page_says_so_when_the_log_has_not_been_collected():
    """The state it ships in today. An empty scoreboard would read as "nothing
    was ever caught", which is the opposite of true."""
    page = _page()
    assert 'if(!agentLog || !agentLog.summary)' in page, (
        "renderAgentLog no longer distinguishes a missing log from a real one")
    assert 'has not been collected yet' in page, (
        "the missing-log branch renders nothing that tells the reader why")


def test_the_hand_written_incidents_survived_the_rebuild():
    """The three incidents are the part a reader learns from, and the same
    mistake as the Roadmap was available here: replace a hand-written page
    with a live one and lose the writing."""
    page = _page()
    for phrase in ('Incident 1', 'Incident 2', 'Incident 3', 'The Actual Rule'):
        assert phrase in page, f"{phrase!r} was lost in the rebuild"


def test_the_page_is_named_in_plain_english_everywhere():
    """Two navigations plus the heading. A rename that misses one leaves the
    site calling the same page two different things."""
    page = _page()
    assert 'AI Reliability' not in page, (
        "the old jargon name survives somewhere -- check both navs and the h2")
    assert page.count('Checking the AI&#39;s work') >= 3, (
        "the plain-English name is missing from the heading or one of the navs")


def test_the_numbers_shown_are_the_ones_the_collector_produces():
    """The renderer reads summary keys by name. If the collector renames one,
    the page silently prints `undefined` rather than failing -- so the two
    lists are compared here instead."""
    page = _page()
    render = re.search(r'function renderAgentLog\(\)\{.*?\n\}', page, re.S)
    assert render, "renderAgentLog is gone"
    used = set(re.findall(r's\.([a-z_]+)', render.group(0)))
    produced = set(re.findall(r"'([a-z_]+)':", (REPO_ROOT / 'src' / 'collect_agent_log.py')
                              .read_text(encoding='utf-8').split('def summarise')[1]))
    missing = used - produced
    assert not missing, (
        f"the page reads summary fields the collector does not produce, so they "
        f"render as undefined: {sorted(missing)}")


if __name__ == '__main__':
    sys.exit(pytest.main([__file__, '-v']))
