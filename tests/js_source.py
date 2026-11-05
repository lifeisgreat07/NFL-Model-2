"""
One page function's source text, for the tests that run it under node.

Stage 86 item 7 (the 2026-11-02 review): 24 test files each carried their
own copy of `function_source`, 21 of them identical. They read the same way
now: from `function NAME(` to the first line that is a lone closing brace.
A function that cannot be found fails the test that asked for it, with the
name, rather than handing node an empty string.
"""
import re


def function_source(src: str, name: str, *, at_line_start: bool = False) -> str:
    """The text of `function name(...) {...}` in `src`, through the first
    "\\n}\\n" after it. With `at_line_start`, only a declaration that begins
    a line counts (so `function name(` inside a comment or string does not)."""
    flags = re.S | (re.M if at_line_start else 0)
    m = re.search(('^' if at_line_start else '') + r'function ' + re.escape(name) + r'\(.*?\n\}\n', src, flags)
    assert m, f'{name} is not findable -- re-anchor this guard'
    return m.group(0)
