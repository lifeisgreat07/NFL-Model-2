"""
The pages' Content-Security-Policy names the hash of each inline script.

Stage 88 item 5 (the 2026-11-02 review). Every page carried
`script-src 'unsafe-inline'`, which lets ANY inline script run, including one
an attacker manages to inject through a data field the page prints. Naming
the SHA-256 of each script the build wrote lets those run and nothing else:
an injected `<script>` or inline event handler (`onclick="..."`) is refused
by the browser. The pages therefore carry no inline handlers; each page
attaches its listeners from its own script (`data-act` buttons, and
`data-hide-on-error` images).

`harden` is applied to a finished page. It recomputes the list from the page
as it stands, so it can run again after something injects another script
(src/site/build.py does, after its last injection). Data blocks
(`<script type="application/json">` and the like) are not run, so they are
not listed. A page with no CSP meta, or none whose script-src it can read, is
refused: a page that cannot be hardened must not ship looking as if it were.

Standard library only.
"""
from __future__ import annotations

import base64
import hashlib
import re

#: An inline script: no src, and a type the browser runs (none, a JavaScript type, or a module).
SCRIPT_RE = re.compile(r'<script(?P<attrs>(?:\s[^>]*)?)>(?P<body>.*?)</script>', re.S | re.I)
RUNNABLE_TYPES = ('', 'text/javascript', 'application/javascript', 'module')
CSP_RE = re.compile(r'(<meta http-equiv="Content-Security-Policy" content=")(?P<policy>[^"]*)(")', re.I)
SCRIPT_SRC_RE = re.compile(r"script-src [^;]*")
#: An inline handler attribute, in the page's markup or in markup a script writes. The common
#: event names only: a looser `on[a-z]+=` also matches JavaScript such as `const one =`.
HANDLER_RE = re.compile(r'\son(?:click|error|load|change|input|submit|keydown|keyup|keypress|focus|blur'
                        r'|mouseover|mouseout|mouseenter|mouseleave|pointerdown|pointerup|touchstart|scroll)'
                        r'\s*=\s*["\'\\]', re.I)


class CSPError(ValueError):
    """The page cannot be given a hash-based script-src."""


def _type(attrs: str) -> str:
    m = re.search(r'''\btype\s*=\s*["']?([^"'\s>]+)''', attrs, re.I)
    return m.group(1).lower() if m else ''


def inline_scripts(html: str) -> list[str]:
    """The text of every inline script the browser would run, in page order."""
    out = []
    for m in SCRIPT_RE.finditer(html):
        attrs = m.group('attrs') or ''
        if re.search(r'\bsrc\s*=', attrs, re.I):
            continue
        if _type(attrs) in RUNNABLE_TYPES:
            out.append(m.group('body'))
    return out


def digest(script: str) -> str:
    """The CSP source for one script: 'sha256-<base64 of its UTF-8 bytes' SHA-256>'."""
    return "'sha256-" + base64.b64encode(hashlib.sha256(script.encode('utf-8')).digest()).decode('ascii') + "'"


def harden(html: str) -> str:
    """The page with its CSP's script-src replaced by the hashes of its inline scripts."""
    if HANDLER_RE.search(html):
        where = HANDLER_RE.search(html)
        assert where is not None
        raise CSPError(f'an inline event handler would be refused: {where.group(0)[:120]!r}')
    metas = list(CSP_RE.finditer(html))
    if len(metas) != 1:
        raise CSPError(f'expected one Content-Security-Policy meta, found {len(metas)}')
    policy = metas[0].group('policy')
    if len(SCRIPT_SRC_RE.findall(policy)) != 1:
        raise CSPError(f'expected one script-src in the policy: {policy!r}')
    hashes = list(dict.fromkeys(digest(s) for s in inline_scripts(html)))
    source = ' '.join(hashes) if hashes else "'none'"
    new_policy = SCRIPT_SRC_RE.sub(lambda _m: 'script-src ' + source, policy)
    m = metas[0]
    return html[:m.start('policy')] + new_policy + html[m.end('policy'):]
