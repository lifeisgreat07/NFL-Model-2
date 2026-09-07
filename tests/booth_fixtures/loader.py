"""
Load and validate the Booth regression fixtures.

Each fixture is a miniature pull request that contains a KNOWN defect, used to
ask whether Booth still catches a class of failure it has caught before. Every
one is drawn from a real audit of this repository, not invented.

Layout, one directory per fixture:

    tests/booth_fixtures/<id>/
        fixture.json      metadata, the expectation, and its provenance
        body.md           the PR description the fixture presents
        base/             repository state before the PR
        head/             repository state after it

The runner (separate, and the only part that spends usage) builds a throwaway
git repo, commits `base/`, commits `head/` over it, and hands Booth that diff
plus `body.md`. Everything in this module is free and runs in the ordinary
suite.

Two assertion forms, and a fixture must declare which it uses:

  file-locus   Some claim implicating a named path came back DISCREPANCY.
               Strong: checked directly against the verdict block.

  no-locus     The overall verdict is not SAFE TO MERGE. Weaker, and honestly
               labelled so -- it proves only that Booth did not wave the PR
               through, not that it found the specific defect. Used where the
               defect is in the description and has no file to name. The
               alternative, inventing a pseudo-path like "<description>", is a
               category label wearing a path's clothes, and category-matching
               is exactly what the verdict block was designed to avoid.
"""
import json
from pathlib import Path

FIXTURE_ROOT = Path(__file__).parent

ASSERTIONS = ('file-locus', 'no-locus')

REQUIRED = ('id', 'why', 'provenance', 'assertion', 'assertion_strength')


class FixtureError(ValueError):
    """A fixture is malformed. Loud, because a silently broken fixture
    would report that Booth passed a test it was never actually given."""


def fixture_dirs():
    return sorted(
        p for p in FIXTURE_ROOT.iterdir()
        if p.is_dir() and (p / 'fixture.json').is_file()
    )


def load(path):
    """Load one fixture directory, validating its shape."""
    path = Path(path)
    try:
        meta = json.loads((path / 'fixture.json').read_text(encoding='utf-8'))
    except json.JSONDecodeError as exc:
        raise FixtureError(f"{path.name}/fixture.json is not valid JSON: {exc}") from exc

    for key in REQUIRED:
        if key not in meta:
            raise FixtureError(f"{path.name}: fixture.json is missing {key!r}")

    if meta['id'] != path.name:
        raise FixtureError(
            f"{path.name}: id is {meta['id']!r}; it must match the directory "
            "name so a failure report names something findable"
        )

    if meta['assertion'] not in ASSERTIONS:
        raise FixtureError(
            f"{path.name}: assertion {meta['assertion']!r} is not one of {ASSERTIONS}"
        )

    if meta['assertion'] == 'file-locus':
        if 'expect_discrepancy_implicating' not in meta:
            raise FixtureError(
                f"{path.name}: a file-locus fixture must name the path it "
                "expects a DISCREPANCY to implicate"
            )
        if 'seeded_defect' not in meta:
            raise FixtureError(
                f"{path.name}: a file-locus fixture must describe its seeded "
                "defect, so the corpus can check the defect is really there"
            )
        for key in ('file', 'contains', 'explanation'):
            if key not in meta['seeded_defect']:
                raise FixtureError(
                    f"{path.name}: seeded_defect is missing {key!r}"
                )

    meta['_path'] = path
    return meta


def load_all():
    out = [load(p) for p in fixture_dirs()]
    ids = [m['id'] for m in out]
    dupes = {i for i in ids if ids.count(i) > 1}
    if dupes:
        raise FixtureError(f"duplicate fixture ids: {sorted(dupes)}")
    return out


#: Directories that are build residue rather than fixture content. A fixture
#: tree is source material for Booth, so anything a tool generates inside it
#: is noise -- and reading a .pyc as UTF-8 raises, which surfaced as five
#: fixture tests failing for a reason unrelated to what they assert, and only
#: when the full suite ran. See conftest.py in this directory.
_IGNORED_DIRS = {'__pycache__', '.pytest_cache', '.git'}


def _tree(path):
    """Map of relative posix path -> text, for every file under `path`.

    Generated directories are skipped, and a file that is not UTF-8 text is a
    hard error rather than a silent omission: fixture content is written by
    hand, so a binary file here means something wrote into the tree that
    should not have, and quietly dropping it would hide that.
    """
    if not path.is_dir():
        return {}
    out = {}
    for p in sorted(path.rglob('*')):
        if not p.is_file():
            continue
        rel = p.relative_to(path)
        if _IGNORED_DIRS.intersection(rel.parts):
            continue
        try:
            out[str(rel.as_posix())] = p.read_text(encoding='utf-8')
        except UnicodeDecodeError as exc:
            raise FixtureError(
                f"{path.parent.name}: {rel.as_posix()} is not UTF-8 text. "
                "Fixture trees are hand-written source material; a binary "
                "file here means a tool wrote into the tree."
            ) from exc
    return out


def base_tree(meta):
    return _tree(meta['_path'] / 'base')


def head_tree(meta):
    return _tree(meta['_path'] / 'head')


def body(meta):
    return (meta['_path'] / 'body.md').read_text(encoding='utf-8')


def satisfied_by(meta, verdict):
    """Does a parsed booth-verdict block satisfy this fixture's expectation?

    Returns (bool, explanation). Used by the runner when it records a
    baseline, and again by the free suite every time it re-checks one.
    """
    if verdict is None:
        return False, "no booth-verdict block in the report"

    if meta['assertion'] == 'no-locus':
        ok = verdict['overall'] != 'SAFE TO MERGE'
        return ok, (
            f"overall was {verdict['overall']!r}; expected anything but "
            "'SAFE TO MERGE'"
        ) if not ok else "overall was not SAFE TO MERGE, as required"

    wanted = meta['expect_discrepancy_implicating']
    hits = {
        c['id'] for c in verdict['claims']
        if c['verdict'] == 'DISCREPANCY' and wanted in c['implicates']
    }
    if hits:
        return True, f"claim(s) {sorted(hits)} raised a DISCREPANCY implicating {wanted}"
    return False, (
        f"no DISCREPANCY implicated {wanted!r}; "
        f"discrepancies implicated "
        f"{sorted({p for c in verdict['claims'] if c['verdict'] == 'DISCREPANCY' for p in c['implicates']})}"
    )
