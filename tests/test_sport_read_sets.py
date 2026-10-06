"""Stage 60 item 1: what each sport's page build actually opens.

Decision record 0006 says nothing bleeds between sports, and
`src/core/isolation.py` checks it statically: imports, path strings,
workflows, names. This file checks it at run time. Each build runs in its
own interpreter with an audit hook that records every file it opens, source
files included (an import opens its module), and the test reads the list:

- **the NFL's build** opens nothing that belongs to another sport: no file
  under `data/`, `predictions/`, `results/` or `experiments/` in another
  sport's folder, and no module under `src/sports/<another sport>/`;
- **the NBA's build** likewise opens only its own package, the core, its
  own folders, the shared stylesheet and the font;
- **the NHL's build** opens no other sport's folder either, and nothing of the
  repository's but its own package, the core, its own folders, the shared
  stylesheet and the self-hosted font (until Stage 53 moves the stylesheet
  into the shared shell).

A file the build never opens cannot move a byte of its page, so an NHL change
cannot change the NFL's page, and the reverse, while these hold.

Run with: pytest tests/test_sport_read_sets.py -v
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

from src.core import isolation

ROOT = Path(__file__).resolve().parents[1]
FOLDERS = ('data', 'predictions', 'results', 'experiments')

HOOK = textwrap.dedent('''
    import json, os, sys
    opened = set()
    def hook(event, args):
        if event == 'open' and args and isinstance(args[0], (str, bytes, os.PathLike)):
            opened.add(os.path.abspath(os.fsdecode(args[0])))
    sys.addaudithook(hook)
    import runpy
    sys.argv = [sys.argv[0]] + json.loads(os.environ['READ_SET_ARGV'])
    target = os.environ['READ_SET_TARGET']
    try:
        if target.endswith('.py'):
            runpy.run_path(target, run_name='__main__')
        else:
            runpy.run_module(target, run_name='__main__')
    except SystemExit as exc:
        if exc.code not in (0, None):
            raise
    with open(os.environ['READ_SET_OUT'], 'w', encoding='utf-8') as f:
        json.dump(sorted(opened), f)
''')


def read_set(target: str, argv: list[str], out: Path) -> list[Path]:
    """Every file `target` (a module name, or a script path) opens when run
    with `argv`, as paths relative to the repository; files outside it (the
    interpreter, site-packages, a test's scratch folder) are left out."""
    env = {**os.environ, 'READ_SET_TARGET': target, 'READ_SET_ARGV': json.dumps(argv),
           'READ_SET_OUT': str(out), 'PYTHONPATH': str(ROOT)}
    run = subprocess.run([sys.executable, '-B', '-c', HOOK], cwd=str(ROOT), env=env,
                         capture_output=True, text=True, timeout=300)
    assert run.returncode == 0, run.stderr[-2000:]
    rel = []
    for p in json.loads(out.read_text(encoding='utf-8')):
        try:
            rel.append(Path(p).resolve().relative_to(ROOT.resolve()))
        except ValueError:
            continue
    return rel


def owner(rel: Path, codes: list[str]) -> str | None:
    """The sport a repository path belongs to by folder, or None."""
    parts = rel.parts
    if len(parts) >= 2 and parts[0] in FOLDERS and parts[1] in codes:
        return parts[1]
    if len(parts) >= 3 and parts[:2] == ('src', 'sports') and parts[2] in codes:
        return parts[2]
    return None


def test_the_nfl_build_opens_nothing_of_another_sport(tmp_path: Path) -> None:
    codes = isolation.sports(ROOT)
    opened = read_set('src.pipeline.generate_dashboard', [], tmp_path / 'nfl.json')
    assert len(opened) > 20, 'the hook saw almost nothing: it is not recording the build'
    foreign = [p.as_posix() for p in opened if owner(p, codes) not in (None, 'nfl')]
    assert not foreign, f"the NFL's build opened another sport's files: {foreign}"


def test_the_nhl_build_opens_only_its_own_files_and_the_shared_ones(tmp_path: Path) -> None:
    codes = isolation.sports(ROOT)
    # The build reads the daily run's files; give it a season of its own in a
    # scratch copy of the NHL's folders so the test does not depend on a run.
    scratch = tmp_path / 'repo'
    sched = {'as_of': '2026-10-06', 'games': [
        {'game_id': '1', 'slate': '2026-10-06', 'start_utc': '2026-10-06T23:00:00Z', 'home': 'TOR', 'away': 'MTL',
         'status': 'scheduled', 'game_type': 'regular', 'home_score': None, 'away_score': None,
         'last_period': None, 'neutral_site': False}]}
    (scratch / 'results' / 'nhl').mkdir(parents=True)
    (scratch / 'results' / 'nhl' / 'schedule_2026.json').write_text(json.dumps(sched), encoding='utf-8')
    driver = tmp_path / 'driver.py'
    driver.write_text(textwrap.dedent(f'''
        from pathlib import Path
        from src.core.sport import SportPaths
        from src.sports.nhl import site
        site.PATHS = SportPaths('nhl', root=Path({str(scratch)!r}))
        raise SystemExit(site.main(['--out', {str(tmp_path / 'nhl.html')!r}, '--season', '2026']))
    '''), encoding='utf-8')
    opened = read_set(str(driver), [], tmp_path / 'nhl.json')
    assert (tmp_path / 'nhl.html').exists()
    seen = {p.as_posix() for p in opened}
    assert {'src/sports/nhl/site.py', 'src/dashboard/styles.css'} <= seen, 'the hook did not record the build'
    foreign = [p.as_posix() for p in opened if owner(p, codes) not in (None, 'nhl')]
    assert not foreign, f"the NHL's build opened another sport's files: {foreign}"
    allowed = ('src/sports/nhl/', 'src/core/', 'src/__init__', 'src/__pycache__/', 'src/sports/__init__',
               'src/sports/__pycache__/', 'src/dashboard/styles.css', 'assets/fonts/')
    stray = [p.as_posix() for p in opened
             if not p.as_posix().startswith(allowed) and owner(p, codes) != 'nhl']
    assert not stray, f"the NHL's build opened files that are neither its own nor shared: {stray}"


def test_the_nba_build_opens_only_its_own_files_and_the_shared_ones(tmp_path: Path) -> None:
    codes = isolation.sports(ROOT)
    opened = read_set('src.sports.nba.site', ['--out', str(tmp_path / 'nba.html')], tmp_path / 'nba.json')
    assert (tmp_path / 'nba.html').exists()
    seen = {p.as_posix() for p in opened}
    assert {'src/sports/nba/site.py', 'src/dashboard/styles.css',
            'experiments/nba/stage61/results/confirmation.json'} <= seen, 'the hook did not record the build'
    foreign = [p.as_posix() for p in opened if owner(p, codes) not in (None, 'nba')]
    assert not foreign, f"the NBA's build opened another sport's files: {foreign}"
    allowed = ('src/sports/nba/', 'src/core/', 'src/__init__', 'src/__pycache__/', 'src/sports/__init__',
               'src/sports/__pycache__/', 'src/dashboard/styles.css', 'assets/fonts/')
    stray = [p.as_posix() for p in opened
             if not p.as_posix().startswith(allowed) and owner(p, codes) != 'nba']
    assert not stray, f"the NBA's build opened files that are neither its own nor shared: {stray}"
