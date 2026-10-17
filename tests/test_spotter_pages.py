"""Which pages Spotter renders for a change (Stage 43 item 2).

src/agents/spotter_pages.py maps changed files to the built site's pages.
The map is held to the repository: every file `page_files` calls part of a
page has a rule, and every rule matches a file that exists, so a new
template part or a renamed folder fails here and not in a render nobody
reads.

Run with: pytest tests/test_spotter_pages.py -v
"""
import subprocess

import pytest

from src.agents import spotter_pages as sp
from src.agents.scout_preflight import page_files

ROOT = sp.ROOT


def tracked():
    out = subprocess.run(['git', 'ls-files', '--cached', '--others', '--exclude-standard'], cwd=ROOT, capture_output=True, text=True, check=True).stdout
    return [line for line in out.splitlines() if line]


@pytest.mark.parametrize('changed, pages', [
    (['src/dashboard/styles.css'], ('nfl',)),
    (['src/dashboard/app.js', 'src/dashboard/body.html'], ('nfl',)),
    (['src/sports/nhl/pages/nhl.css'], ('nhl',)),
    (['src/sports/nba/pages/body.html'], ('nba',)),
    (['src/sports/nba/site.py'], ('nba',)),
    (['src/site/home/home.css'], ('home',)),
    (['src/sports/nhl/pages/nhl.js', 'src/sports/nba/pages/nba.js'], ('nhl', 'nba')),
    (['assets/favicon.svg'], ('home', 'nfl')),
    (['assets/favicon-nhl.svg'], ('nhl',)),
    (['src/site/build.py'], sp.PAGES),
    (['tests/browser/spotter_render.py'], sp.PAGES),
    (['.github/workflows/spotter.yml'], sp.PAGES),
    (['assets/og/og-card.html'], ()),
    (['src/core/alerts.py', 'README.md'], ()),
    ([], ()),
], ids=['nfl-css', 'nfl-two-parts', 'nhl-css', 'nba-body', 'nba-builder', 'home-css', 'two-sports-in-page-order',
        'shared-favicon', 'nhl-favicon', 'site-builder-all', 'renderer-all', 'workflow-all', 'og-source-none',
        'not-a-page-none', 'empty'])
def test_each_change_renders_the_pages_it_feeds(changed, pages):
    result = sp.plan(changed)
    assert result.pages == pages and result.unmapped == ()


def test_a_page_file_no_rule_knows_renders_every_page_and_says_so():
    result = sp.plan(['src/newthing/layout.css', 'src/sports/nhl/pages/nhl.css'])
    assert result.pages == sp.PAGES and result.unmapped == ('src/newthing/layout.css',)


def test_a_file_that_is_not_a_page_file_and_has_no_rule_is_ignored():
    assert sp.plan(['src/newthing/layout.py']) == sp.Plan((), ())


def test_the_first_matching_rule_wins():
    """The favicons are under assets/, and the og folder is under it too: the
    specific rule is listed first."""
    assert sp.rule_for('assets/favicon-nhl.svg') == ('assets/favicon-nhl.svg', ('nhl',))
    assert sp.rule_for('assets/og/og-nba.html') == ('assets/og/', ())


def test_every_page_file_in_the_repository_has_a_rule():
    """A new template part, stylesheet or svg with no rule fails here."""
    files = tracked()
    flagged = page_files(files)
    assert len(flagged) >= 10, f'the scan found only {flagged}; it has gone blind'
    unmapped = [f for f in flagged if sp.rule_for(f) is None]
    assert not unmapped, f'page files with no Spotter rule (add one to RULES): {unmapped}'


def test_every_rule_matches_a_file_that_exists():
    files = tracked()
    dead = [prefix for prefix, _ in sp.RULES
            if not any(f == prefix or (prefix.endswith('/') and f.startswith(prefix)) for f in files)]
    assert not dead, f'rules that match no file in the repository: {dead}'


def test_every_page_of_the_site_is_fed_by_some_rule():
    fed = {page for _, pages in sp.RULES for page in pages}
    assert fed == set(sp.PAGES)


def test_the_pages_are_the_ones_the_site_builds():
    from src.site import build
    assert set(sp.PAGES) == {'home', *build.SPORTS}
    assert sp.SITE_PATH == {'home': '', **{s: f'{s}/' for s in build.SPORTS}}


def test_the_command_line_prints_the_pages_on_one_line(monkeypatch, capsys):
    monkeypatch.setattr(sp, 'changed_files', lambda base, head: ['src/sports/nhl/pages/nhl.css', 'src/dashboard/app.js'])
    assert sp.main(['--base', 'a', '--head', 'b']) == 0
    assert capsys.readouterr().out == 'nfl,nhl\n'


def test_the_command_line_names_an_unmapped_page_file_on_stderr(monkeypatch, capsys):
    monkeypatch.setattr(sp, 'changed_files', lambda base, head: ['src/newthing/layout.css'])
    sp.main(['--base', 'a', '--head', 'b'])
    out = capsys.readouterr()
    assert out.out == 'home,nfl,nhl,nba\n' and 'src/newthing/layout.css' in out.err


def test_changed_files_reads_the_diff_between_the_merge_base_and_the_head(tmp_path):
    def git(*a):
        subprocess.run(['git', '-c', 'user.name=t', '-c', 'user.email=t@t', *a], cwd=tmp_path, check=True,
                       capture_output=True)
    git('init', '-q', '-b', 'main')
    (tmp_path / 'a.css').write_text('a')
    git('add', '-A')
    git('commit', '-qm', 'one')
    base = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=tmp_path, capture_output=True, text=True).stdout.strip()
    git('checkout', '-q', '-b', 'feature')
    (tmp_path / 'b.css').write_text('b')
    git('add', '-A')
    git('commit', '-qm', 'two')
    # main moves on after the branch started: that file is not the change's.
    git('checkout', '-q', 'main')
    (tmp_path / 'c.css').write_text('c')
    git('add', '-A')
    git('commit', '-qm', 'three')
    assert sp.changed_files('main', 'feature', tmp_path) == ['b.css']
    assert base
