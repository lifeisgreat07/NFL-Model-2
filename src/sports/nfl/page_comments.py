"""Strip the template's comments from the page a visitor downloads.

Stage 26 item 11, from the 2026-09-28 audit. The template is written to be
read: its comments carry the reasons behind the page (why a selector is
scoped, which audit found a bug), and they are most of a hundred kilobytes.
None of that does anything in a browser, so the built page drops it. The
template keeps every comment; only the output loses them.

Three kinds of text, handled separately:
  - HTML outside <script> and <style>: `<!-- ... -->` goes.
  - <style>: `/* ... */` goes, outside CSS strings.
  - <script>: `//` and `/* */` comments go, found by a small lexer that
    knows strings, template literals (including `${ }` nesting) and regex
    literals, so a `//` inside a URL string or a template is left alone.

A block comment that spanned a line break is replaced by a line break, so
two statements the comment separated never end up joined on one line and
automatic semicolon insertion reads them as it did before. A line that held
nothing but a comment is dropped; every other line, including blank lines
and trailing spaces inside a template literal or a <pre>, is left exactly
as it was.

tests/test_page_comments.py holds the lexer to the cases that break naive
strippers, and compiles every script on the stripped page under node.
"""
import re

# After one of these (the last non-space character of code), a `/` starts a
# regular expression, not a division.
_REGEX_AFTER_CHAR = set('(,=:[!&|?{};+-*%<>~^')
# ...and after one of these words.
_REGEX_AFTER_WORD = {'return', 'typeof', 'case', 'do', 'else', 'in', 'of',
                     'new', 'delete', 'void', 'throw', 'instanceof', 'yield', 'await'}


class StripError(ValueError):
    """The lexer ended inside a string, template, comment or regex."""


def strip_js(src):
    return _drop_cut_lines(_mark_js(src))


def _mark_js(src):
    out = []
    i, n = 0, len(src)
    # Each entry is the brace depth at which a `${` was opened inside a
    # template literal; when that brace closes, the template resumes.
    template_stack = []
    depth = 0
    last_sig = ''      # last significant (non-space, non-comment) character
    last_word = ''     # the identifier that ended at last_sig, if any

    def regex_allowed():
        if last_sig == '':
            return True
        if last_sig in _REGEX_AFTER_CHAR:
            return True
        return last_word in _REGEX_AFTER_WORD

    def read_template(j):
        """From just after a backtick (or a closing `}` of `${`), copy to the
        closing backtick or to the next `${`. Returns (end, opened_expr)."""
        while j < n:
            c = src[j]
            if c == '\\':
                j += 2
                continue
            if c == '`':
                return j + 1, False
            if c == '$' and j + 1 < n and src[j + 1] == '{':
                return j + 2, True
            j += 1
        raise StripError('unterminated template literal')

    while i < n:
        c = src[i]
        nxt = src[i + 1] if i + 1 < n else ''

        if c in ' \t\r\n':
            out.append(c)
            i += 1
            continue

        if c == '/' and nxt == '/':
            j = src.find('\n', i)
            out.append(CUT)
            i = n if j == -1 else j
            continue

        if c == '/' and nxt == '*':
            j = src.find('*/', i + 2)
            if j == -1:
                raise StripError('unterminated block comment')
            out.append(_cut(src[i:j]) if '\n' in src[i:j] else CUT + ' ')
            i = j + 2
            continue

        if c in '\'"':
            j = i + 1
            while j < n and src[j] != c:
                if src[j] == '\\':
                    j += 1
                elif src[j] == '\n':
                    raise StripError(f'line break inside a {c} string')
                j += 1
            if j >= n:
                raise StripError('unterminated string')
            out.append(src[i:j + 1])
            i = j + 1
            last_sig, last_word = c, ''
            continue

        if c == '`':
            j, opened = read_template(i + 1)
            out.append(src[i:j])
            i = j
            if opened:
                depth += 1
                template_stack.append(depth)
                last_sig, last_word = '{', ''
            else:
                last_sig, last_word = '`', ''
            continue

        if c == '/' and regex_allowed():
            j = i + 1
            in_class = False
            while j < n:
                d = src[j]
                if d == '\\':
                    j += 2
                    continue
                if d == '\n':
                    raise StripError('line break inside a regex literal')
                if d == '[':
                    in_class = True
                elif d == ']':
                    in_class = False
                elif d == '/' and not in_class:
                    break
                j += 1
            if j >= n:
                raise StripError('unterminated regex literal')
            j += 1
            while j < n and (src[j].isalpha()):
                j += 1   # flags
            out.append(src[i:j])
            i = j
            last_sig, last_word = '/', ''
            continue

        if c == '{':
            depth += 1
        elif c == '}':
            if template_stack and template_stack[-1] == depth:
                template_stack.pop()
                depth -= 1
                j, opened = read_template(i + 1)
                out.append(src[i:j])
                i = j
                if opened:
                    depth += 1
                    template_stack.append(depth)
                    last_sig, last_word = '{', ''
                else:
                    last_sig, last_word = '`', ''
                continue
            depth -= 1

        if c.isalnum() or c in '_$':
            j = i
            while j < n and (src[j].isalnum() or src[j] in '_$'):
                j += 1
            word = src[i:j]
            out.append(word)
            i = j
            last_sig, last_word = word[-1], word
            continue

        out.append(c)
        i += 1
        last_sig, last_word = c, ''

    if template_stack:
        raise StripError('unterminated ${ } in a template literal')
    return ''.join(out)


def strip_css(src):
    return _drop_cut_lines(_mark_css(src))


def _mark_css(src):
    out = []
    i, n = 0, len(src)
    while i < n:
        c = src[i]
        if c in '\'"':
            j = i + 1
            while j < n and src[j] != c:
                j += 2 if src[j] == '\\' else 1
            out.append(src[i:j + 1])
            i = j + 1
            continue
        if c == '/' and src[i + 1:i + 2] == '*':
            j = src.find('*/', i + 2)
            if j == -1:
                raise StripError('unterminated CSS comment')
            out.append(_cut(src[i:j]) if '\n' in src[i:j] else CUT + ' ')
            i = j + 2
            continue
        out.append(c)
        i += 1
    return ''.join(out)


# Marks where a comment was taken out, so the lines a removal emptied can be
# told apart from lines that were blank to begin with.
CUT = '\x00'


def _drop_cut_lines(text):
    """Drop a line that is only whitespace and CUT marks; then drop the marks."""
    kept = [ln for ln in text.split('\n')
            if not (CUT in ln and not ln.replace(CUT, '').strip())]
    return '\n'.join(kept).replace(CUT, '')


# An HTML comment is matched first and as a unit: the template's comments
# mention `<style>` and `<script>` in prose, and a scanner that looked for
# those tags inside a comment would read the rest of the page as CSS.
_BLOCK = re.compile(r'(<!--.*?-->)|(<script\b[^>]*>)(.*?)(</script>)|(<style\b[^>]*>)(.*?)(</style>)',
                    re.S | re.I)


def _cut(removed):
    """What stands where a comment was: a mark, and the line break if the
    comment spanned one."""
    return CUT + ('\n' + CUT if '\n' in removed else '')


def strip_page_comments(html):
    """The page with its comments removed. See the module docstring."""
    if CUT in html:
        raise StripError('the page already contains the cut marker')
    out = []
    pos = 0
    for m in _BLOCK.finditer(html):
        out.append(html[pos:m.start()])
        if m.group(1):
            out.append(_cut(m.group(1)))
        elif m.group(2):
            out.append(m.group(2) + _mark_js(m.group(3)) + m.group(4))
        else:
            out.append(m.group(5) + _mark_css(m.group(6)) + m.group(7))
        pos = m.end()
    out.append(html[pos:])
    # Once, over the whole page, so a line that a removal emptied is judged
    # as a whole line even where it runs up to a <script> or <style> tag.
    return _drop_cut_lines(''.join(out))
