"""Model Lab's reliability diagram sits below the experiments (Stage 18).

The page used to open on the diagram and its paragraphs of explanation before
the first experiment. The diagram now follows the experiment log; its
explanation of how to read the chart, and the definition of the Brier terms,
are behind disclosures in the page's own "How to read this" style. The
findings -- the bootstrap results -- stay in view: they are results, not
reading help.

Run with: pytest tests/test_model_lab_diagram_below.py -v
"""
import re
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parents[1] / 'src' / 'pipeline' / 'dashboard_template.html'


def source():
    return TEMPLATE.read_text(encoding='utf-8').replace('\r\n', '\n')


def diagram_js():
    src = source()
    start = src.index('function buildReliabilityDiagram(')
    return src[start:src.index('\n}\n', start)]


def closed_details_spans(text):
    """(start, end) of every <details>...</details> in text."""
    return [(m.start(), m.end()) for m in re.finditer(r'<details\b.*?</details>', text, re.S)]


def inside_details(text, needle):
    at = text.index(needle)
    return any(a < at < b for a, b in closed_details_spans(text))


def test_the_diagram_follows_the_experiment_log():
    src = source()
    page = src[src.index('id="page-modellab"'):]
    log = page.index('data-scroll-label="Experiment log"')
    diagram = page.index('<div id="reliability-diagram"></div>')
    assert log < diagram, 'the reliability diagram is above the experiments again'
    assert src.count('<div id="reliability-diagram"></div>') == 1


def test_how_to_read_this_holds_the_explanation():
    js = diagram_js()
    m = re.search(r'<details class="rel-how">\s*<summary>How to read this</summary>(.*?)</details>', js, re.S)
    assert m, 'the diagram has no "How to read this" disclosure'
    assert 'Wilson interval' in m.group(1) and 'perfect calibration' in m.group(1)
    assert not inside_details(js, 'does that side actually win about 70% of the time? Each mark is one probability bin across ${n} backtested games, with its 95% interval.'), (
        "the diagram's one-line lead is hidden too, so nothing says what the chart is before it is opened")


def test_the_brier_definition_is_behind_a_disclosure():
    js = diagram_js()
    m = re.search(r'<details class="rel-how">\s*<summary>What these numbers mean</summary>(.*?)</details>', js, re.S)
    assert m and 'Brier = reliability' in m.group(1)


def test_the_findings_stay_in_view():
    js = diagram_js()
    for finding in ('the lead did not survive', 'The same test did find two things that hold'):
        assert finding in js, f'"{finding}" is gone -- re-anchor this guard'
        assert not inside_details(js, finding), f'"{finding}" is a finding, and is now hidden behind a disclosure'


def test_the_diagram_points_at_the_log_not_at_its_own_page():
    js = diagram_js()
    assert 'See <b style="color:var(--text)">Model Lab</b>' not in js, (
        'the diagram is on Model Lab, so "See Model Lab" sends the reader to where they are')
    assert 'the experiment log above' in js


def test_the_disclosure_looks_and_focuses_like_the_other_how_to_read_this():
    css = re.search(r'<style>(.*?)</style>', source(), re.S).group(1)
    css = re.sub(r'/\*.*?\*/', '', css, flags=re.S)
    def selectors_of(prop_re):
        out = set()
        for sel, body in re.findall(r'([^{}]+)\{([^{}]*)\}', css):
            if re.search(prop_re, body):
                out |= {' '.join(s.split()) for s in sel.split(',')}
        return out
    assert '.rel-how summary' in selectors_of(r'min-height\s*:\s*24px'), 'the toggle is under 24px tall'
    assert '.rel-how summary:focus-visible' in selectors_of(r'outline\s*:\s*2px solid var\(--accent\)')
    assert '.rel-how[open] summary::before' in selectors_of(r"content\s*:\s*'\\2212")
