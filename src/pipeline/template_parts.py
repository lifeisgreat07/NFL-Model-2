"""
The dashboard template, kept as parts and joined into one page.

Stage 33 item 26. Until 2026-10-03 the page's template was one file of
some 6,500 lines: stylesheet, markup and script together. It now lives
under src/dashboard/ as a shell, page.html, and the parts it includes:

    page.html    the document: head, the small theme script, the closing tags
    styles.css   the main stylesheet, the body of the first <style> element
    body.html    the markup between the theme script and the main script
    app.js       the main script, the body of the last <script> element

A line in page.html that reads exactly

    {% include "styles.css" %}

is replaced by that part's text, which ends with its own newline. Nothing
else is expanded: no nesting, no other syntax. The joined text is the same
template the generator always filled, byte for byte (proved when the parts
were cut, and held by tests/test_template_parts.py), so the page it builds
is unchanged.

The generator joins the parts. The tests read the joined text through
read_template(), or through JOINED_TEMPLATE where a test was written
against a path and calls read_text() on it. The JavaScript harnesses use
tests/template_source.js, which joins the same way and is held to this
module by a test.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DASHBOARD_DIR = ROOT / 'src' / 'dashboard'
SHELL = 'page.html'

#: The whole of the include syntax: one directive, alone on its line, with
#: the line's own newline (a CRLF checkout included).
INCLUDE_LINE = re.compile(r'^\{% include "([A-Za-z0-9_.-]+)" %\}\r?\n', re.M)
DIRECTIVE = '{% include'


def includes(shell_text):
    """The part names the shell includes, in order."""
    return INCLUDE_LINE.findall(shell_text)


def join(shell_text, read_part):
    """The shell with each include line replaced by its part's text.

    read_part(name) returns a part's text. A part included twice, a part
    without its final newline, or a directive that is not alone on its own
    line is an error, not a guess: the join has to give back one page."""
    names = includes(shell_text)
    if len(names) != len(set(names)):
        raise ValueError(f"a part is included more than once: {names}")
    if shell_text.count(DIRECTIVE) != len(names):
        raise ValueError("page.html has an include directive that is not alone on its own line")

    def expand(m):
        part = read_part(m.group(1))
        if not part.endswith('\n'):
            raise ValueError(f"part {m.group(1)} does not end with a newline")
        return part

    return INCLUDE_LINE.sub(expand, shell_text)


def part_paths(directory=DASHBOARD_DIR):
    """Every file in the dashboard directory: the shell and its parts."""
    return sorted(p for p in directory.iterdir() if p.is_file())


def read_template(directory=DASHBOARD_DIR):
    """The template, joined, as the generator fills it.

    Every file in the directory must be the shell or a part the shell
    includes: a stray file would be a part someone believes is on the page."""
    shell = (directory / SHELL).read_text(encoding='utf-8')
    names = includes(shell)
    present = {p.name for p in part_paths(directory)} - {SHELL}
    if present != set(names):
        raise ValueError(
            f"{directory.name}/ holds {sorted(present)} but {SHELL} includes {names}")
    return join(shell, lambda name: (directory / name).read_text(encoding='utf-8'))


class JoinedTemplate:
    """The joined template, readable the way the template's Path was read.

    About a hundred tests were written against the one template file as
    `TEMPLATE.read_text(encoding='utf-8')`. This stands in for that Path so
    they read the joined page, with the line that names it the only change."""

    def read_text(self, encoding='utf-8', errors=None):
        return read_template()

    def __repr__(self):
        return '<the dashboard template, joined from src/dashboard/>'


JOINED_TEMPLATE = JoinedTemplate()
