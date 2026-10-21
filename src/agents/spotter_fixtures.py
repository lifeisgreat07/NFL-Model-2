"""Spotter's regression fixtures: a planted defect it must name, and a clean
change it must leave alone (Stage 43 item 4; decision record 0007).

    python -m src.agents.spotter_fixtures apply  planted-defects --checkout DIR
    python -m src.agents.spotter_fixtures record planted-defects --comment F --pr N --head SHA
    python -m src.agents.spotter_fixtures check

A fixture (tests/spotter_fixtures/<id>/) is one small change to a stylesheet,
`change.css.txt`, appended to the file it names. (Named `.txt` because a
`.css` file is a page file to Scout's pre-flight and to Spotter's page map,
and a fragment that only makes sense appended elsewhere is not one.) Committed on a branch from the
current main and opened as a draft pull request, it is what Spotter's own
workflow photographs and reads. Two are kept:

* `planted-defects` makes the day board overflow a phone's screen and makes
  the result labels unreadable in the dark theme: Spotter must name both;
* `clean-control` restates a declaration the file already makes, so the
  page does not change: Spotter must say it sees nothing wrong.

Like Booth's fixtures (tests/booth_fixtures), asking is rare and re-checking
is free. The reading costs a model run, so it is recorded once, as the
comment Spotter posted. `check` re-derives the verdict from that stored
reading and the answer key in `fixture.json` on every suite run, so a
fixture whose key or change is edited stops counting as passed.

The answer key is never Spotter grading itself. `fixture.json` says which
pictures must be cited and which words must appear beside them, written
before the reading existed; Spotter writes the reading.

Why the guard that the planted rule is RENDERED exists: the first trial
(#531, 2026-10-20) planted its defects on `.nhl-table`, a class the day
board never draws, on a base days behind main. Spotter said it saw nothing
wrong, which was true, and the run proved nothing. A planted rule must name
a class the page's own script draws on the page that is photographed.

Standard library only apart from the check it reuses from spotter_comment;
tests/test_spotter_fixtures.py holds each fixture's page to spotter_pages.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.agents import spotter_comment

REPO = Path(__file__).resolve().parents[2]
FIXTURE_ROOT = REPO / 'tests' / 'spotter_fixtures'
BASELINE = 'baseline.json'
NOTHING = 'Nothing that I can see.'

REQUIRED = ('id', 'why', 'provenance', 'target', 'page', 'script', 'rendered_by', 'change', 'expect')
RULE = re.compile(r'([^{}]+)\{([^{}]*)\}')
COMMENT = re.compile(r'/\*.*?\*/', re.S)
CLASS = re.compile(r'\.([A-Za-z_][\w-]*)')
PICTURE_IN_COMMENT = re.compile(r'/([a-z]+-\d+x\d+-(?:light|dark)-(?:head|base))\.png\?raw=true')


def load(path: Path) -> dict[str, Any]:
    meta: dict[str, Any] = json.loads((path / 'fixture.json').read_text(encoding='utf-8'))
    meta['_path'] = str(path)
    return meta


def load_all(root: Path = FIXTURE_ROOT) -> list[dict[str, Any]]:
    return [load(p) for p in sorted(root.iterdir()) if (p / 'fixture.json').is_file()]


def change_text(meta: dict[str, Any]) -> str:
    """The stylesheet text the fixture appends, with LF line ends."""
    raw: str = (Path(meta['_path']) / meta['change']).read_bytes().decode('utf-8')
    return raw.replace('\r\n', '\n')


def change_sha(meta: dict[str, Any]) -> str:
    return hashlib.sha256(change_text(meta).encode('utf-8')).hexdigest()


def rules(css: str) -> list[tuple[str, dict[str, str]]]:
    """(selector, declarations) for every plain rule, comments removed. A rule
    inside an @media block is listed like any other."""
    out = []
    for sel, body in RULE.findall(COMMENT.sub('', css)):
        decls = {}
        for part in body.split(';'):
            if ':' in part:
                k, v = part.split(':', 1)
                decls[k.strip()] = ' '.join(v.split())
        out.append((' '.join(sel.split()), decls))
    return out


def function_source(script: str, name: str) -> str | None:
    """The text of one top-level function in a page script, up to the next."""
    m = re.search(rf'^(?:async\s+)?function\s+{re.escape(name)}\s*\(', script, re.M)
    if m is None:
        return None
    nxt = re.search(r'^(?:async\s+)?function\s+\w+\s*\(', script[m.end():], re.M)
    return script[m.start(): m.end() + (nxt.start() if nxt else len(script))]


def unrendered_classes(meta: dict[str, Any], script: str | None = None) -> list[str]:
    """The classes the change's rules name that the page's drawing functions
    never write. A planted defect on one of these is invisible, whatever it says."""
    if script is None:
        script = (REPO / meta['script']).read_text(encoding='utf-8')
    drawn = ''
    for name in meta['rendered_by']:
        src = function_source(script, name)
        if src is None:
            return [f'function {name}() is not in {meta["script"]}']
        drawn += src
    gone: list[str] = []
    for sel, _ in rules(change_text(meta)):
        for cls in CLASS.findall(sel):
            if cls not in gone and not re.search(rf'(?<![\w-]){re.escape(cls)}(?![\w-])', drawn):
                gone.append(cls)
    return gone


def adds_nothing_new(meta: dict[str, Any], base_css: str) -> list[str]:
    """For a clean change: each declaration it makes must already be made, for
    the same selector, by the file it is appended to."""
    have: dict[str, dict[str, str]] = {}
    for sel, decls in rules(base_css):
        have.setdefault(sel, {}).update(decls)
    new = []
    for sel, decls in rules(change_text(meta)):
        for k, v in decls.items():
            if have.get(sel, {}).get(k) != v:
                new.append(f'{sel} {{ {k}: {v} }}')
    return new


def reading_section(reading: str, heading: str) -> str | None:
    m = re.search(rf'^#### {re.escape(heading)}[ \t]*\n(.*?)(?=^#### |\Z)', reading, re.S | re.M)
    return m.group(1).strip() if m else None


def satisfied_by(meta: dict[str, Any], reading: str) -> tuple[bool, str]:
    """Does this reading meet the fixture's answer key? Only the section
    "What looks wrong" is read. A defect is named when ONE bullet of it cites
    a picture the key lists and uses a word the key lists. A bullet about
    something the key does not list is not counted against the reading of
    the planted defects: the key asks what must be found, not what may be
    said. For the clean control it is the other way round: nothing may be
    blamed on the change, so a problem is allowed only where its bullet says
    the base has it too."""
    wrong = reading_section(reading, 'What looks wrong')
    if wrong is None:
        return False, 'the reading has no "What looks wrong" section'
    expect = meta['expect']
    # "Nothing that I can see." may be followed by a note on what was set aside
    # (trial #531 added one); it still says nothing is wrong unless a bullet follows.
    said_nothing = wrong.startswith(NOTHING) and not re.search(r'^- ', wrong, re.M)
    if expect['kind'] == 'clean':
        if said_nothing:
            return True, 'the reading found nothing wrong in a page that did not change'
        # SPOTTER_PROTOCOL.md asks for what looks wrong in the head picture
        # "whether or not the base had it", so a reading of a page with a
        # standing quirk (a fixed tab bar in a whole-page photograph) lists it.
        # What a clean change must not do is have a problem blamed on it: each
        # bullet has to say the base shows it too. The first key asked for
        # "Nothing that I can see." and failed the control for obeying the protocol.
        bullets = [b for b in re.split(r'\n(?=- )', wrong) if b.startswith('- ')]
        if bullets and all('base' in b.lower() for b in bullets):
            return True, 'every problem the reading lists is one the base picture shows too'
        return False, 'the reading reported a problem on a change that alters nothing visible'
    if said_nothing:
        return False, 'the reading found nothing, and the page has planted defects'
    units = [u for u in re.split(r'\n(?=- )|\n\s*\n', wrong) if u.strip()]
    missed = []
    for d in expect['defects']:
        hit = any(
            any(f'`{p}`' in u for p in d['pictures_any'])
            and any(w in u.lower() for w in d['words_any'])
            for u in units)
        if not hit:
            missed.append(d['id'])
    if missed:
        return False, 'the reading did not name: ' + ', '.join(missed)
    return True, 'the reading named every planted defect: ' + ', '.join(d['id'] for d in expect['defects'])


def baseline_path(meta: dict[str, Any]) -> Path:
    return Path(meta['_path']) / BASELINE


def load_baseline(meta: dict[str, Any]) -> dict[str, Any] | None:
    p = baseline_path(meta)
    return json.loads(p.read_text(encoding='utf-8')) if p.is_file() else None


def parse_comment(comment: str) -> tuple[str, list[str], str | None]:
    """(the reading, the pictures the comment lists, the head sha it names)."""
    if not comment.startswith(spotter_comment.MARKER):
        raise ValueError('this is not a Spotter comment: it does not start with the marker')
    cut = comment.find('### Reading')
    if cut < 0:
        raise ValueError('the comment has no "### Reading" section')
    names = sorted(set(PICTURE_IN_COMMENT.findall(comment)))
    head = re.search(r'Head `([0-9a-f]{7,40})`', comment)
    return comment[cut + len('### Reading'):].strip(), names, head.group(1) if head else None


def check_one(meta: dict[str, Any]) -> tuple[bool | None, str]:
    """Re-check a recorded reading against the key. Free. The verdict is
    re-derived from the stored reading, never read from the stored flag, and
    a reading recorded against a different change stops counting."""
    base = load_baseline(meta)
    if base is None:
        return None, 'no baseline recorded yet'
    if base.get('change_sha256') != change_sha(meta):
        return False, 'the change was edited after the reading was recorded; record it again'
    problems = spotter_comment.check_reading(base.get('reading', ''), [n + '.png' for n in base.get('names', [])])
    if problems:
        return False, 'the stored reading would be refused today: ' + '; '.join(problems)
    return satisfied_by(meta, base.get('reading', ''))


def record(meta: dict[str, Any], comment: str, pr: int, head: str) -> tuple[bool, str]:
    reading, names, named_head = parse_comment(comment)
    if not named_head or not (head.startswith(named_head) or named_head.startswith(head)):
        ok, why = False, f'the comment names head {named_head!r} but {head!r} was given'
    else:
        ok, why = satisfied_by(meta, reading)
    payload = {
        'fixture': meta['id'],
        'recorded_utc': datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'pr': pr,
        'head': head,
        'change_sha256': change_sha(meta),
        'names': names,
        'satisfied': ok,
        'explanation': why,
        'reading': reading,
    }
    baseline_path(meta).write_text(json.dumps(payload, indent=2) + '\n', encoding='utf-8')
    return ok, why


def apply(meta: dict[str, Any], checkout: Path) -> Path:
    """Append the change to the target in a checkout. Nothing else is touched."""
    target: Path = checkout / str(meta['target'])
    if not target.is_file():
        raise FileNotFoundError(f'{target} does not exist')
    with target.open('ab') as f:
        f.write(change_text(meta).encode('utf-8'))
    return target


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or '').splitlines()[0])
    sub = ap.add_subparsers(dest='cmd', required=True)
    for name in ('apply', 'record'):
        p = sub.add_parser(name)
        p.add_argument('fixture')
        if name == 'apply':
            p.add_argument('--checkout', type=Path, required=True)
        else:
            p.add_argument('--comment', type=Path, required=True, help="a file holding Spotter's comment")
            p.add_argument('--pr', type=int, required=True)
            p.add_argument('--head', required=True, help='the commit Spotter read')
    sub.add_parser('check')
    args = ap.parse_args(argv)

    if args.cmd == 'check':
        failed = 0
        for meta in load_all():
            ok, why = check_one(meta)
            print(f'  [{"NO BASELINE" if ok is None else "PASS" if ok else "FAIL"}] {meta["id"]}\n      {why}')
            failed += ok is not True
        return 1 if failed else 0

    meta = load(FIXTURE_ROOT / args.fixture)
    if args.cmd == 'apply':
        print(f'appended {meta["change"]} to {apply(meta, args.checkout)}')
        return 0
    ok, why = record(meta, args.comment.read_text(encoding='utf-8'), args.pr, args.head)
    print(('SATISFIED: ' if ok else 'NOT SATISFIED: ') + why)
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
