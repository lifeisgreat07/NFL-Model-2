"""
The dashboard template's parts, and the two joins that put them together
(Stage 33 item 26).

src/dashboard/page.html includes styles.css, body.html and app.js; the
generator joins them with src/pipeline/template_parts.py and the JavaScript
harnesses with tests/template_source.js. When the parts were cut, the join
was byte-identical to the one file it replaced. What has to stay true after
that is held here:

  * the shell includes each part once, each where its name says it goes:
    the stylesheet inside the first <style>, the script inside the last
    <script>, the markup between them;
  * every file in src/dashboard/ is a part the page includes, so nobody
    edits a file that is not on the page;
  * a broken layout is refused, never guessed at: a stray file, a part
    included twice, a part without its final newline, a directive not alone
    on its line;
  * the Python join and the JavaScript join agree, on the real parts and on
    every broken layout above, so a harness never runs code the page does
    not ship;
  * every read names its encoding, as the generator's own reads do
    (tests/test_generator_encoding.py).

Run with: pytest tests/test_template_parts.py -v
"""
import ast
import shutil
import subprocess
from pathlib import Path

import pytest

from src.pipeline import template_parts as tp

REPO = Path(__file__).resolve().parents[1]
JS = REPO / 'tests' / 'template_source.js'
NODE = shutil.which('node')
needs_node = pytest.mark.skipif(
    NODE is None, reason="node not on PATH -- the JavaScript join cannot be executed")

PARTS = ['styles.css', 'body.html', 'app.js']


def shell():
    return (tp.DASHBOARD_DIR / tp.SHELL).read_text(encoding='utf-8')


# --- the real parts ------------------------------------------------------------

def test_the_shell_includes_each_part_once_in_page_order():
    assert tp.includes(shell()) == PARTS


def test_every_file_in_the_directory_is_on_the_page():
    names = {p.name for p in tp.part_paths()}
    assert names == {tp.SHELL, *PARTS}, (
        f"src/dashboard/ holds {sorted(names)}; every file there must be page.html "
        "or a part it includes")


@pytest.mark.parametrize('before,name,after', [
    ('<style>\n', 'styles.css', '</style>\n'),
    ('</script>\n', 'body.html', '<script>\n'),
    ('<script>\n', 'app.js', '</script>\n'),
])
def test_each_part_sits_where_its_name_says(before, name, after):
    line = f'{{% include "{name}" %}}\n'
    assert f'{before}{line}{after}' in shell(), (
        f"{name} is no longer included between {before.strip()} and {after.strip()}")


def test_the_stylesheet_is_the_first_style_and_the_script_the_last():
    """The guards that read "the stylesheet" take the first <style>, and the
    ones that read "the script" take the last <script>."""
    s = shell()
    assert s.index('<style>\n{% include "styles.css" %}') == s.index('<style')
    assert s.rindex('<script>\n{% include "app.js" %}') == s.rindex('<script')


def test_the_joined_template_is_one_page():
    text = tp.read_template()
    assert text.startswith('<!DOCTYPE html>\n')
    assert text.endswith('</html>\n')
    assert tp.DIRECTIVE not in text
    assert tp.JOINED_TEMPLATE.read_text(encoding='utf-8') == text


@needs_node
def test_the_javascript_join_gives_the_same_page():
    out = subprocess.run([NODE, str(JS)], cwd=REPO, capture_output=True, check=True).stdout
    assert out.decode('utf-8').replace('\r\n', '\n') == tp.read_template()


# --- broken layouts ------------------------------------------------------------

def layout(tmp_path, shell_text, parts):
    d = tmp_path / 'dashboard'
    d.mkdir()
    (d / 'page.html').write_bytes(shell_text.encode('utf-8'))
    for name, text in parts.items():
        (d / name).write_bytes(text.encode('utf-8'))
    return d


GOOD_SHELL = '<p>\n{% include "a.css" %}\n</p>\n'
BROKEN = {
    'a stray file': (GOOD_SHELL, {'a.css': 'x\n', 'b.js': 'y\n'}),
    'a part included twice': ('{% include "a.css" %}\n{% include "a.css" %}\n', {'a.css': 'x\n'}),
    'a part without its newline': (GOOD_SHELL, {'a.css': 'x'}),
    'a directive not alone on its line': ('{% include "a.css" %}\n<p>{% include "a.css" %}</p>\n',
                                          {'a.css': 'x\n'}),
    'a part that does not exist': ('{% include "a.css" %}\n{% include "c.js" %}\n', {'a.css': 'x\n'}),
}


def test_a_good_layout_joins(tmp_path):
    d = layout(tmp_path, GOOD_SHELL, {'a.css': 'x\ny\n'})
    assert tp.read_template(d) == '<p>\nx\ny\n</p>\n'


@needs_node
def test_the_javascript_join_agrees_on_a_good_layout(tmp_path):
    d = layout(tmp_path, GOOD_SHELL, {'a.css': 'x\ny\n'})
    out = subprocess.run([NODE, str(JS), str(d)], capture_output=True, check=True).stdout
    assert out.decode('utf-8') == '<p>\nx\ny\n</p>\n'


@pytest.mark.parametrize('case', BROKEN)
def test_a_broken_layout_is_refused(tmp_path, case):
    d = layout(tmp_path, *BROKEN[case])
    with pytest.raises((ValueError, FileNotFoundError)):
        tp.read_template(d)


@needs_node
@pytest.mark.parametrize('case', BROKEN)
def test_the_javascript_join_refuses_it_too(tmp_path, case):
    d = layout(tmp_path, *BROKEN[case])
    proc = subprocess.run([NODE, str(JS), str(d)], capture_output=True)
    assert proc.returncode != 0, f"the JavaScript join accepted {case}"


# --- encoding ------------------------------------------------------------------

def test_every_read_names_utf8():
    tree = ast.parse((REPO / 'src' / 'pipeline' / 'template_parts.py').read_text(encoding='utf-8'))
    reads = [n for n in ast.walk(tree)
             if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
             and n.func.attr == 'read_text']
    assert len(reads) >= 2, 're-anchor: the shell read and the part read were not found'
    bad = [n.lineno for n in reads
           if not any(k.arg == 'encoding' and getattr(k.value, 'value', None) == 'utf-8'
                      for k in n.keywords)]
    assert not bad, f'read_text() without encoding="utf-8" at lines {bad}'
