"""The built page drops the template's comments and nothing else (Stage 26
item 11).

src/sports/nfl/page_comments.py strips `<!-- -->`, CSS `/* */` and JS `//` and `/* */`
comments from the template before the build fills it. A stripper that gets
a string, a template literal or a regex wrong eats code up to the next `*/`
or end of line, and the page breaks for a visitor.

Most ways of getting this lexer wrong are loud on the real template: it ends
inside a string or a regex, raises StripError, and conftest.py's build of the
page fails, so the whole session stops. The rest are why this file exists:
the lexer is held to the cases that break naive strippers, including slips
the real template happens not to trip over today, every script on the
stripped template is compiled under node, and every kept line is checked
against the template line it came from.

Also here: the page carries only the part of Booth's audit log it reads, and
its data fills are written compact.

Run with: pytest tests/test_page_comments.py -v
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
from src.core.template_parts import read_template
from src.sports.nfl import generate_dashboard as gd
from src.sports.nfl import page_comments as pc

TEMPLATE = read_template()
NODE = shutil.which('node')


# ---- the lexer ---------------------------------------------------------------

def test_a_whole_line_comment_takes_its_line_with_it():
    assert pc.strip_js("a();\n  // why\nb();") == "a();\nb();"


def test_a_trailing_comment_leaves_the_code():
    assert pc.strip_js("x = 1; // why\ny = 2;") == "x = 1; \ny = 2;"


def test_a_url_in_a_string_is_not_a_comment():
    src = "const u = 'https://x.org/a'; const v = \"//y\";"
    assert pc.strip_js(src) == src


def test_an_escaped_quote_does_not_end_the_string():
    src = "s = 'it\\'s // not a comment'; t = \"a \\\" /* nor this */\";"
    assert pc.strip_js(src) == src


def test_comment_syntax_inside_a_template_literal_is_text():
    src = "const t = `a // not a comment\n/* nor this */ ${b}`;"
    assert pc.strip_js(src) == src


def test_a_comment_inside_a_template_expression_is_a_comment():
    assert pc.strip_js("t = `a${ /* c */ b }d`;") == "t = `a${   b }d`;"


def test_nested_templates_and_braces_keep_their_place():
    src = "t = `${x.map(y => `<${y}>${ {a:1}.a }`).join('')} // text`;"
    assert pc.strip_js(src) == src


def test_a_regex_with_slashes_and_quotes_is_not_a_comment_or_a_string():
    src = "s = s.replace(/\\/\\/'\"/g, ''); r = /[/*]/.test(q);"
    assert pc.strip_js(src) == src


def test_a_slash_inside_a_regex_character_class_does_not_end_it():
    src = "q = s.split(/[/'\"]/); t = 'x'; // c"
    assert pc.strip_js(src) == "q = s.split(/[/'\"]/); t = 'x'; "


def test_an_escaped_backtick_does_not_end_a_template():
    src = "t = `a \\` // still text`; // gone"
    assert pc.strip_js(src) == "t = `a \\` // still text`; "


def test_division_is_not_a_regex():
    src = "a = (b + c) / 2 / d; // half\ne = f[0] / g;"
    assert pc.strip_js(src) == "a = (b + c) / 2 / d; \ne = f[0] / g;"


def test_a_block_comment_across_lines_keeps_the_line_break():
    """Automatic semicolon insertion reads `return a\\nb` and `return a b`
    differently, so a comment that held a line break leaves one behind."""
    assert pc.strip_js("return a /* x\ny */ b") == "return a \n b"
    assert pc.strip_js("return a /* x\ny */\nb") == "return a \nb"


def test_blank_lines_and_trailing_spaces_that_were_there_stay():
    src = "t = `line  \n\n  more`;\n\nz();"
    assert pc.strip_js(src) == src


def test_an_unterminated_literal_stops_the_build():
    for bad in ("x = 'abc", "t = `abc", "/* never closed", "t = `${a`"):
        with pytest.raises(pc.StripError):
            pc.strip_js(bad)


def test_css_comments_go_and_css_strings_stay():
    src = 'a{content:"/* kept */";}\n/* gone */\nb{c:d;} /* gone too */'
    assert pc.strip_css(src) == 'a{content:"/* kept */";}\nb{c:d;}  '


def test_html_comments_go_only_outside_script_and_style():
    page = ('<p>a</p>\n<!-- gone -->\n<p>b<!-- gone --></p>\n'
            '<script>const s = "<!-- kept -->"; // gone\n</script>')
    assert pc.strip_page_comments(page) == (
        '<p>a</p>\n<p>b</p>\n<script>const s = "<!-- kept -->"; \n</script>')


def test_a_tag_named_inside_an_html_comment_is_not_a_tag():
    """The template's comments name <style> and <script> in prose; the
    scanner once read from such a mention to the next </style> as CSS."""
    page = '<!-- the first <style> element -->\n<p>x</p>\n<style>a{}</style>'
    assert pc.strip_page_comments(page) == '<p>x</p>\n<style>a{}</style>'


# ---- the real template -------------------------------------------------------

@pytest.fixture(scope='module')
def stripped():
    return pc.strip_page_comments(TEMPLATE)


def test_the_stripped_template_is_much_smaller(stripped):
    assert len(stripped) < 0.75 * len(TEMPLATE)


def test_no_comment_is_left_outside_scripts(stripped):
    outside = re.sub(r'<script\b.*?</script>', '', stripped, flags=re.S)
    assert '<!--' not in outside
    for css in re.findall(r'<style\b[^>]*>(.*?)</style>', stripped, re.S):
        assert '/*' not in css


def test_every_script_on_the_stripped_template_compiles(stripped):
    if not NODE:
        pytest.skip('node not available')
    found = re.findall(r'<script\b([^>]*)>(.*?)</script>', stripped, re.S)
    # The structured data (Stage 47 item 12) is JSON, not script: it must
    # still parse as JSON after stripping, which also proves no "//" inside
    # its URLs was taken for a comment.
    for attrs, s in found:
        if 'application/ld+json' in attrs:
            json.loads(s)
    scripts = [s for attrs, s in found if 'application/ld+json' not in attrs]
    assert len(scripts) >= 2, 'the scan found fewer scripts than the page has -- re-anchor it'
    for k, s in enumerate(scripts):
        s = re.sub(r'__[A-Z_]+__', 'null', s)   # the build's placeholders
        r = subprocess.run(
            [NODE, '-e', 'let s="";process.stdin.on("data",d=>s+=d).on("end",'
                         '()=>{new (require("vm").Script)(s);})'],
            input=s, capture_output=True, text=True, encoding='utf-8')
        assert r.returncode == 0, f'script {k} no longer compiles after stripping:\n{r.stderr[-800:]}'


def cut_from(original, kept):
    """True when `kept` is `original` with at most one span taken out of it
    (a comment at its end, its start, or inside it). An inline block comment
    leaves one space in its place, so `a/**/b` cannot become `ab`."""
    k = 0
    while k < min(len(kept), len(original)) and kept[k] == original[k]:
        k += 1
    rest = kept[k:]
    if len(kept) > len(original):
        return False
    return rest == '' or original.endswith(rest) or (rest[0] == ' ' and original.endswith(rest[1:]))


def test_every_line_kept_is_a_template_line_with_at_most_a_comment_cut(stripped):
    """Stripping only ever removes, and in order: each kept line is a template
    line, later than the last one matched, with at most one span cut from it.
    A lexer that lost its place would rewrite or join lines, and this says
    where."""
    originals = TEMPLATE.split('\n')
    i = 0
    for line in stripped.split('\n'):
        while i < len(originals) and not cut_from(originals[i], line):
            i += 1
        assert i < len(originals), f'a line the template does not have: {line[:120]!r}'
        i += 1


def test_the_line_check_can_fail():
    assert cut_from('a = 1; // why', 'a = 1; ')
    assert cut_from("  ''} */ x", ' x')
    assert cut_from("f(){ /* c */ }", "f(){   }")
    assert not cut_from('a = 1;', 'a = 2;')
    assert not cut_from('a();', 'a();b();')


# ---- what the build does with it ----------------------------------------------

def test_the_build_strips_the_template_before_filling_it():
    src = (ROOT / 'src' / 'sports' / 'nfl' / 'generate_dashboard.py').read_text(encoding='utf-8')
    read = src.index('template = read_template()')
    strip = src.index('template = strip_page_comments(template)')
    fill = src.index("html = template.replace(")
    assert read < strip < fill


def test_the_page_carries_only_the_agent_log_it_reads():
    log = {'generated_utc': 't', 'note': 'n', 'summary': {'audits': 3}, 'audits': [{'pr': 1}]}
    assert gd.agent_log_for_page(log) == {'generated_utc': 't', 'summary': {'audits': 3}}
    assert gd.agent_log_for_page(None) is None
    reads = set(re.findall(r'agentLog\.(\w+)', TEMPLATE))
    assert reads <= {'generated_utc', 'summary'}, f'the page reads {reads} from the agent log'


def test_every_data_fill_is_compact():
    src = (ROOT / 'src' / 'sports' / 'nfl' / 'generate_dashboard.py').read_text(encoding='utf-8')
    assert 'indent=' not in src, 'a data fill is indented again'
    assert json.dumps({'a': [1, 2]}, **gd.COMPACT) == '{"a":[1,2]}'
