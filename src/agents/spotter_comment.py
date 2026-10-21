"""Spotter's comment: the pictures it lists and the reading it is allowed to post
(Stage 43 item 3; decision record 0007).

The reading job holds a model that can only read files and write one file,
`reading/reading.md`. It never posts. This module is what stands between that
file and the pull request, and it runs from a copy made before the model
starts, so the model cannot have changed it:

* the list of pictures is built here from the files that were uploaded, never
  by the model, so the comment always links every picture that exists;
* the reading is posted only if it passes `check_reading`: it cites pictures
  that exist and cites at least one, carries no verdict word (Booth's report
  is the verdict, decision record 0004), no link or image of its own (a
  rendered image URL is a way to send what the model read to a stranger's
  server), no `@` mention, and nothing that could pose as the marker or as
  another HTML comment;
* a reading that fails is replaced in the comment by the reasons, so a run
  that went wrong is visible on the pull request instead of silent.

Standard library only: it runs on the runner's own Python, with nothing
installed, and the writer job (which has `contents: write`) never runs it.

    python3 -m src.agents.spotter_comment --reading F --renders DIR --repo R --pr N --sha S --out F
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

MARKER = '<!-- spotter-comment -->'
BRANCH = 'spotter-renders'
SHORT = 12
MAX_READING = 8000

PICTURE = re.compile(r'^([a-z]+)-(\d+)x(\d+)-(light|dark)-(head|base)\.png$')
CITE = re.compile(r'\b([a-z]+-\d+x\d+-(?:light|dark)-(?:head|base))\b')

#: Words that make a reading look like a decision. Booth's report is the
#: verdict and a person merges; Spotter only says what it sees.
VERDICT = re.compile(
    r"\b(safe to merge|unsafe|needs human review|do not merge|don't merge|ship it|lgtm|"
    r"approved?|reject(?:ed)?|verdict)\b", re.I)


def pictures(renders: Path) -> list[str]:
    return sorted(p.name for p in renders.glob('*.png') if PICTURE.match(p.name))


def check_reading(text: str, names: list[str]) -> list[str]:
    """Why this reading may not be posted, one line each; empty if it may."""
    problems = []
    if not text.strip():
        return ['the reading is empty']
    if len(text) > MAX_READING:
        problems.append(f'the reading is {len(text)} characters; the limit is {MAX_READING}')
    if VERDICT.search(text):
        # The reason is posted in the comment, so it must not repeat the word.
        problems.append('the reading sounds like a decision; Spotter advises and Booth decides')
    if re.search(r'https?:|www\.|\]\(|!\[|<img|<a\b', text, re.I):
        problems.append('the reading carries a link or an image of its own')
    if re.search(r'(^|\s)@\w', text):
        problems.append('the reading mentions a user')
    if '<!--' in text or MARKER in text:
        problems.append('the reading carries an HTML comment')
    stems = {n[:-4] for n in names}
    cited = set(CITE.findall(text))
    if not cited:
        problems.append('the reading cites no picture by name')
    for gone in sorted(cited - stems):
        problems.append(f'the reading cites {gone}, which was not rendered')
    return problems


def link(repo: str, pr: int, sha: str, name: str) -> str:
    return f'https://github.com/{repo}/blob/{BRANCH}/pr-{pr}/{sha[:SHORT]}/{name}?raw=true'


def gallery(repo: str, pr: int, sha: str, names: list[str]) -> str:
    """One row per page, one column per viewport and theme, base and head."""
    cells: dict[str, dict[tuple[str, str, str], dict[str, str]]] = {}
    for n in names:
        page, w, h, scheme, label = PICTURE.match(n).groups()  # type: ignore[union-attr]
        cells.setdefault(page, {}).setdefault((f'{w}x{h}', scheme, ''), {})[label] = n
    cols = sorted({(vp, s) for rows in cells.values() for vp, s, _ in rows}, key=lambda c: (int(c[0].split('x')[0]), c[1]))
    out = ['| page | ' + ' | '.join(f'{vp} {s}' for vp, s in cols) + ' |',
           '|---|' + '---|' * len(cols)]
    for page in sorted(cells):
        row = []
        for vp, s in cols:
            pair = cells[page].get((vp, s, ''), {})
            parts = [f'[{lab}]({link(repo, pr, sha, pair[lab])})' for lab in ('base', 'head') if lab in pair]
            row.append(' / '.join(parts) or '-')
        out.append(f'| {page} | ' + ' | '.join(row) + ' |')
    return '\n'.join(out)


def compose(repo: str, pr: int, sha: str, names: list[str], reading: str | None, problems: list[str]) -> str:
    head = [
        MARKER,
        '## Spotter: the pages this change can alter',
        '',
        f'Head `{sha[:SHORT]}` against its base, at 390x844 and 1440x900 in the light and the dark theme. '
        "Advisory: this is a reading of the pictures, not an audit. Booth's report and a person decide the merge.",
        '',
        gallery(repo, pr, sha, names),
        '',
        '### Reading',
        '',
    ]
    if reading is not None and not problems:
        body = [reading.strip()]
    else:
        why = problems or ['Spotter produced no reading this run']
        body = ['Spotter did not post a reading this run:', ''] + [f'- {p}' for p in why]
    return '\n'.join(head + body) + '\n'


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else '')
    ap.add_argument('--reading', type=Path, required=True)
    ap.add_argument('--renders', type=Path, required=True)
    ap.add_argument('--repo', required=True)
    ap.add_argument('--pr', type=int, required=True)
    ap.add_argument('--sha', required=True)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args(argv)
    names = pictures(args.renders)
    if not names:
        print('no pictures to list', file=sys.stderr)
        return 1
    reading = args.reading.read_text(encoding='utf-8') if args.reading.exists() else None
    problems = check_reading(reading, names) if reading is not None else []
    args.out.write_text(compose(args.repo, args.pr, args.sha, names, reading, problems), encoding='utf-8')
    for p in problems:
        print(f'reading refused: {p}', file=sys.stderr)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
