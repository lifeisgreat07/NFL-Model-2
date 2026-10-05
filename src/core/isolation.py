"""The isolation rules of decision record 0006, as checks (Stage 50 item 4).

Each function takes a repository root and returns its violations as
sentences, empty when the rule holds. `tests/test_sport_isolation.py` runs
them over this repository, and over small synthetic repositories that break
each rule on purpose, so a check that has stopped catching anything fails
there rather than passing quietly here. Standard library only: the core
imports no sport and nothing heavy.

The four static rules:

1. No sport imports another (`src/sports/<a>/` never names `src.sports.<b>`).
2. The core imports no sport. Until Stage 52 moves the NFL, `src/pipeline/`
   and `src/research/` are the NFL, so they count as a sport here.
3. A sport's workflow writes only its own folders.
4. Every name a sport owns carries the sport: its workflows' files, names
   and alert titles, its browser storage keys and its CSS.

Only `src/site/` may see more than one sport, and nothing imports it.

**The legacy lists may only shrink.** They name what the NFL owns today
under its pre-multi-sport names. Stage 52 moves those and empties
`LEGACY_NFL_WORKFLOWS` and `LEGACY_NFL_PACKAGES`; nothing new is ever added
to either.
"""
from __future__ import annotations

import ast
import re
from collections.abc import Iterator
from pathlib import Path

SPORT_CODE = re.compile(r'^[a-z]{2,5}$')

#: The folders a sport may write, each followed by /<code>/.
SPORT_FOLDERS = ('data', 'predictions', 'results', 'experiments', 'site')

#: Packages that are the NFL until Stage 52 moves them to src/sports/nfl/.
LEGACY_NFL_PACKAGES = ('src.pipeline', 'src.research')

#: The NFL's workflows under their pre-multi-sport names (Stage 52 renames
#: them nfl-*.yml). Exempt from rules 3 and 4 until then.
LEGACY_NFL_WORKFLOWS = frozenset({
    'nfl-schedule-probe.yml', 'nightly-canary.yml', 'run-backtest.yml',
    'weekend-refresh.yml', 'weekly-update.yml',
})

#: Workflows that serve every sport: the PR loop, the suite, the deploy.
SHARED_WORKFLOWS = frozenset({
    'booth-alert.yml', 'booth-pr-audit.yml', 'booth-regression.yml',
    'browser-checks.yml', 'collect-agent-log.yml', 'deploy-pages.yml',
    'nightly-mutation.yml', 'nightly-random-order.yml', 'releases.yml',
    'run-tests.yml', 'scout-preflight.yml',
})


def sports(root: Path) -> list[str]:
    """Every sport with a package under src/sports/, plus the NFL, which is
    a sport before it has one."""
    found = {'nfl'}
    base = root / 'src' / 'sports'
    if base.is_dir():
        found |= {p.name for p in base.iterdir() if p.is_dir() and (p / '__init__.py').exists()}
    return sorted(found)


def _layer(module: str) -> tuple[str, str | None]:
    """('core'|'sport'|'site'|'other', sport code or None) for a dotted name."""
    parts = module.split('.')
    if parts[:2] == ['src', 'core']:
        return 'core', None
    if parts[:2] == ['src', 'site']:
        return 'site', None
    if parts[:2] == ['src', 'sports'] and len(parts) > 2:
        return 'sport', parts[2]
    if any(module == p or module.startswith(p + '.') for p in LEGACY_NFL_PACKAGES):
        return 'sport', 'nfl'
    return 'other', None


def _module_name(root: Path, path: Path) -> str:
    rel = path.relative_to(root).with_suffix('')
    parts = list(rel.parts)
    if parts[-1] == '__init__':
        parts = parts[:-1]
    return '.'.join(parts)


def _imports(path: Path, module: str) -> Iterator[tuple[int, str]]:
    """(line, dotted name) for every import in a file, relative ones resolved."""
    tree = ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
    package = module if path.name == '__init__.py' else module.rpartition('.')[0]
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield node.lineno, alias.name
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                base = package.split('.')
                base = base[:len(base) - (node.level - 1)]
                stem = '.'.join(base + ([node.module] if node.module else []))
            else:
                stem = node.module or ''
            yield node.lineno, stem
            for alias in node.names:
                yield node.lineno, f'{stem}.{alias.name}'


def _python_files(root: Path) -> Iterator[Path]:
    src = root / 'src'
    if src.is_dir():
        yield from sorted(p for p in src.rglob('*.py') if '__pycache__' not in p.parts)


def import_violations(root: Path) -> list[str]:
    """Rules 1 and 2, and that nothing outside src/site imports it."""
    out: list[str] = []
    for path in _python_files(root):
        module = _module_name(root, path)
        layer, sport = _layer(module)
        for line, name in _imports(path, module):
            target, target_sport = _layer(name)
            where = f'{path.relative_to(root).as_posix()}:{line}'
            if target == 'site' and layer != 'site':
                out.append(f'{where} imports {name}: only src/site sees every sport, and nothing imports it')
            elif layer == 'core' and target == 'sport':
                out.append(f'{where} imports {name}: the core imports no sport')
            elif layer == 'sport' and target == 'sport' and target_sport != sport:
                out.append(f'{where} imports {name}: {sport} imports another sport ({target_sport})')
    return list(dict.fromkeys(out))


def literal_violations(root: Path) -> list[str]:
    """Rule 1 by the side door: a string in one sport's code, or the core's,
    that names another sport's package or folders (an importlib call, a
    path built by hand)."""
    codes = sports(root)
    out = []
    for path in _python_files(root):
        layer, sport = _layer(_module_name(root, path))
        if layer not in ('core', 'sport'):
            continue
        others = [c for c in codes if c != sport]
        if not others:
            continue
        alt = '|'.join(others)
        pattern = re.compile(
            rf'(?:src[./]sports[./](?:{alt})\b|\b(?:{"|".join(SPORT_FOLDERS)})/(?:{alt})\b)')
        tree = ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
        # A docstring or a bare string statement is prose about other sports,
        # not a path the code uses.
        prose = {id(n.value) for n in ast.walk(tree) if isinstance(n, ast.Expr)}
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in prose:
                m = pattern.search(node.value)
                if m:
                    owner = 'the core' if layer == 'core' else sport
                    out.append(f'{path.relative_to(root).as_posix()}:{node.lineno} names {m.group(0)!r}, '
                               f'which belongs to another sport than {owner}')
    return out


def _workflow_sport(name: str, codes: list[str]) -> str | None:
    head = name.split('-', 1)[0]
    return head if head in codes and '-' in name else None


def workflow_violations(root: Path) -> list[str]:
    """Rules 3 and 4 for workflows. Every workflow is a sport's (named
    <code>-*.yml), shared, or legacy NFL; an unclassified one fails, so a
    new workflow cannot arrive outside the rules by having a new name."""
    wf_dir = root / '.github' / 'workflows'
    if not wf_dir.is_dir():
        return []
    codes = sports(root)
    out = []
    for path in sorted(wf_dir.glob('*.y*ml')):
        name = path.name
        if name in SHARED_WORKFLOWS or name in LEGACY_NFL_WORKFLOWS:
            continue
        sport = _workflow_sport(name, codes)
        if sport is None:
            out.append(f'{name}: neither a sport\'s (<code>-*.yml), shared nor legacy NFL; '
                       f'name it for its sport or list it in SHARED_WORKFLOWS with a reason')
            continue
        out.extend(f'{name}: {problem}' for problem in _sport_workflow_problems(path.read_text(encoding='utf-8'), sport))
    return out


def _allowed(path: str, sport: str) -> bool:
    path = path.strip().strip('\'"')
    return any(path == f'{f}/{sport}' or path.startswith(f'{f}/{sport}/') for f in SPORT_FOLDERS)


def _sport_workflow_problems(text: str, sport: str) -> list[str]:
    tag = sport.upper()
    problems = []
    m = re.search(r'^name:\s*(.+)$', text, re.MULTILINE)
    if not m or not m.group(1).strip().strip('\'"').startswith(f'{tag} '):
        problems.append(f'its name must start with "{tag} "')
    for title in re.findall(r'--title\s+"([^"]*)"', text):
        if not title.startswith(f'{tag}: '):
            problems.append(f'alert title {title!r} must start with "{tag}: "')
    for pattern in re.findall(r'file_pattern:\s*(.+)', text):
        for p in pattern.strip().strip('\'"').split():
            if not _allowed(p, sport):
                problems.append(f'commits {p!r}, outside its own folders')
    for args in re.findall(r'\bgit add\b([^\n&|;]*)', text):
        paths = [a for a in args.split() if not a.startswith('-') or a in ('-A', '--all')]
        if not paths:
            problems.append('runs git add with no path')
        for p in paths:
            if p in ('-A', '--all', '.') or not _allowed(p, sport):
                problems.append(f'git add {p!r}, outside its own folders')
    for p in _upload_paths(text):
        if not _allowed(p, sport):
            problems.append(f'uploads {p!r}, outside its own folders')
    return problems


def _upload_paths(text: str) -> list[str]:
    """Every path an actions/upload-artifact step uploads: its `path:` value,
    one line or a `|` block, read until the step ends."""
    lines = text.splitlines()
    paths: list[str] = []
    for i, line in enumerate(lines):
        if 'actions/upload-artifact' not in line:
            continue
        step_indent = len(line) - len(line.lstrip(' -'))
        j = i + 1
        while j < len(lines):
            cur = lines[j]
            stripped = cur.strip()
            indent = len(cur) - len(cur.lstrip(' '))
            if stripped.startswith('- ') and indent < step_indent:
                break
            m = re.match(r'path:\s*(.*)$', stripped)
            if m:
                value = m.group(1).strip()
                if value in ('|', '>', ''):
                    k = j + 1
                    while k < len(lines) and (len(lines[k]) - len(lines[k].lstrip(' '))) > indent and lines[k].strip():
                        paths.append(lines[k].strip())
                        k += 1
                else:
                    paths.append(value)
            j += 1
    return paths


STORAGE_KEY = re.compile(r'''(?:localStorage|sessionStorage)\.(?:get|set|remove)Item\(\s*(['"])(.+?)\1'''
                         r'''|\b[A-Z_]*KEY\s*=\s*(['"])(.+?)\3''')
CSS_RULE = re.compile(r'([^{}@]+)\{[^{}]*\}')


def name_violations(root: Path) -> list[str]:
    """Rule 4 for what a sport's pages own: storage keys and CSS. A sport's
    folder must also be a sport code."""
    base = root / 'src' / 'sports'
    if not base.is_dir():
        return []
    out = []
    for folder in sorted(p for p in base.iterdir() if p.is_dir() and p.name != '__pycache__'):
        code = folder.name
        if not SPORT_CODE.match(code):
            out.append(f'src/sports/{code}: a sport folder is its code ({SPORT_CODE.pattern})')
            continue
        for path in sorted(folder.rglob('*.js')):
            for m in STORAGE_KEY.finditer(path.read_text(encoding='utf-8')):
                key = m.group(2) or m.group(4)
                if not key.startswith((f'{code}:', f'{code}-', f'{code}.')):
                    out.append(f'{path.relative_to(root).as_posix()}: storage key {key!r} must start with "{code}:"')
        for path in sorted(folder.rglob('*.css')):
            text = re.sub(r'/\*.*?\*/', '', path.read_text(encoding='utf-8'), flags=re.DOTALL)
            for m in CSS_RULE.finditer(text):
                for selector in m.group(1).split(','):
                    s = selector.strip()
                    if s and not s.startswith(('from', 'to')) and not s.endswith('%') \
                            and f'[data-sport="{code}"]' not in s and f'.{code}-' not in s:
                        out.append(f'{path.relative_to(root).as_posix()}: selector {s!r} is not scoped to '
                                   f'[data-sport="{code}"] or .{code}-*')
    return out


def all_violations(root: Path) -> list[str]:
    return (import_violations(root) + literal_violations(root)
            + workflow_violations(root) + name_violations(root))
