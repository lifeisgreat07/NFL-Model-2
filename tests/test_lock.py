"""
Stage 88 item 3 (the 2026-11-02 review): a full lock with hashes, installed
with --require-hashes, and pip-audit reads the lock.

requirements.txt and requirements-dev.txt pin what this project names;
until now everything those pull in resolved fresh on every CI run, and pip
trusted whatever the index served. requirements.lock and
requirements-dev.lock pin every package, transitive ones included, for every
platform (uv's universal resolution), each with the hashes of its files, and
every workflow installs from them with --require-hashes. A package changed
on the index, or swapped for one with the same version, fails the install.

Run with: pytest tests/test_lock.py -v
"""
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / '.github' / 'workflows'
ENTRY = re.compile(r'^([A-Za-z0-9_.-]+)==([^\s;\\]+)(?:\s*;[^\\\n]*)?\s*\\\n((?:\s+--hash=sha256:[0-9a-f]{64}(?: \\)?\n)+)', re.M)
PIN = re.compile(r'^([A-Za-z0-9_.-]+)==(\S+)', re.M)


def norm(name):
    return re.sub(r'[-_.]+', '-', name).lower()


def lock(name):
    text = (ROOT / name).read_text(encoding='utf-8')
    return {norm(n): (v, h) for n, v, h in ENTRY.findall(text)}, text


def pins(name):
    return {norm(n): v for n, v in PIN.findall((ROOT / name).read_text(encoding='utf-8'))}


@pytest.mark.parametrize('name', ['requirements.lock', 'requirements-dev.lock'])
def test_every_package_in_a_lock_is_pinned_and_hashed(name):
    entries, text = lock(name)
    listed = PIN.findall(text)
    assert len(entries) == len(listed) >= 30, 'an entry the hash pattern did not read'
    for pkg, (version, hashes) in entries.items():
        assert hashes.count('--hash=sha256:') >= 1, pkg


@pytest.mark.parametrize('lockfile, sources', [('requirements.lock', ['requirements.txt']),
                                               ('requirements-dev.lock', ['requirements.txt', 'requirements-dev.txt'])])
def test_each_lock_holds_exactly_the_versions_its_files_pin(lockfile, sources):
    """A pin moved in requirements.txt without regenerating the lock would
    install the old version in CI and say the new one."""
    entries, _ = lock(lockfile)
    for src in sources:
        for pkg, version in pins(src).items():
            assert pkg in entries, f'{src} pins {pkg}, which {lockfile} does not hold'
            assert entries[pkg][0] == version, f'{pkg}: {src} pins {version}, {lockfile} holds {entries[pkg][0]}'


def test_the_dev_lock_installs_the_same_runtime_as_the_runtime_lock():
    runtime, _ = lock('requirements.lock')
    dev, _ = lock('requirements-dev.lock')
    assert {p: dev[p][0] for p in runtime} == {p: v for p, (v, _) in runtime.items()}


def test_each_lock_says_how_it_was_made():
    for name, cmd in (('requirements.lock', 'uv pip compile requirements.txt --universal --python-version 3.11 '
                                              '--generate-hashes -o requirements.lock'),
                      ('requirements-dev.lock', 'uv pip compile requirements.txt requirements-dev.txt --universal '
                                                '--python-version 3.11 --generate-hashes -o requirements-dev.lock')):
        assert cmd in (ROOT / name).read_text(encoding='utf-8'), name


INSTALL = re.compile(r'pip install ([^\n]*-r [^\n]*)')


def test_every_workflow_installs_the_project_from_a_lock_with_hashes():
    """Every install but Booth's audit's. booth-pr-audit.yml still installs from
    the pinned files: Booth cannot vouch for a change to its own workflow (#582
    was NEEDS HUMAN REVIEW for that alone), so its move to the lock is a pull
    request of its own, for Mark."""
    seen = 0
    for p in sorted(WORKFLOWS.glob('*.yml')):
        if p.name == 'spotter.yml':
            continue  # installs the pull request head's requirements.txt to render it, never runs it on main
        for args in INSTALL.findall(p.read_text(encoding='utf-8')):
            seen += 1
            if p.name == 'booth-pr-audit.yml':
                assert args == '-r requirements.txt -r requirements-dev.txt', args
                continue
            assert args in ('--require-hashes -r requirements.lock', '--require-hashes -r requirements-dev.lock'), \
                f'{p.name}: pip install {args}'
    assert seen >= 25, f'only {seen} installs found -- re-anchor the scan'


def test_the_dependency_audit_reads_the_lock():
    t = (WORKFLOWS / 'nightly-dependency-audit.yml').read_text(encoding='utf-8')
    assert 'pip-audit -r requirements-dev.lock --require-hashes --disable-pip ' in t
    assert 'pip-audit -r requirements.txt' not in t
