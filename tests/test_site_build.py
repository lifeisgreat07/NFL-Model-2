"""The site is built one sport at a time, and one sport's failure is its own
(Stage 53, src/site/build.py and src/site/alert_failed.py).

The builders are replaced by fakes, so nothing here runs a real build or
reaches the network. What is checked is the contract: where each page lands,
that a failing sport keeps its live page while the others publish, that the
NFL having no page at all stops the publish, that the root sends a visitor on
with a shared-picks link intact, and that each failed sport gets its own issue.

Run with: pytest tests/test_site_build.py -v
"""
import json
from pathlib import Path

import pytest

from src.site import alert_failed, build

PAGE = '<!DOCTYPE html><html><body>{sport} page</body></html>'
LIVE = 'https://example.test/site'


class FakeRunner:
    """Pretends to be each sport's builder: writes the page it would write,
    or fails for the sports named in `fail`."""

    def __init__(self, out: Path, fail=(), leave=None):
        self.out, self.fail, self.leave, self.calls = out, set(fail), leave or {}, []

    def __call__(self, cmd):
        self.calls.append(cmd)
        mod = cmd[3]
        # The NFL's builders are src.pipeline's until Stage 52 moves them.
        sport = 'nfl' if mod.startswith('src.pipeline.') else mod.split('.')[2]
        if sport in self.fail:
            return 1
        html = self.leave.get(sport, PAGE.format(sport=sport))
        if sport == 'nfl':
            if mod.endswith('generate_dashboard'):
                (build.ROOT / 'index.html').write_text(html, encoding='utf-8')
            return 0
        page = Path(cmd[cmd.index('--out') + 1])
        page.parent.mkdir(parents=True, exist_ok=True)
        page.write_text(html, encoding='utf-8')
        return 0


@pytest.fixture
def root_page(monkeypatch, tmp_path):
    """The NFL builder writes index.html at the repository root; point the
    root at a scratch folder so nothing here touches the checkout."""
    fake_root = tmp_path / 'repo'
    (fake_root / 'assets' / 'og').mkdir(parents=True)
    for rel in build.SHARED_FILES.values():
        (fake_root / rel).write_bytes(b'x')
    (fake_root / 'dist').mkdir()
    (fake_root / 'dist' / 'picks_2026_week5.pdf').write_bytes(b'%PDF')
    monkeypatch.setattr(build, 'ROOT', fake_root)
    return fake_root


def no_network(url):
    raise AssertionError(f'fetched {url} though every sport built')


def test_every_sport_lands_in_its_own_folder(root_page, tmp_path):
    out = tmp_path / 'site'
    results = build.build_site(out, LIVE, runner=FakeRunner(out), fetcher=no_network)
    assert [(r.sport, r.built) for r in results] == [('nfl', True), ('nhl', True), ('nba', True), ('home', True)]
    for sport in build.SPORTS:
        assert (out / sport / 'index.html').read_text(encoding='utf-8') == PAGE.format(sport=sport)
    assert (out / 'nfl' / 'dist' / 'picks_2026_week5.pdf').exists()
    for published in build.SHARED_FILES:
        assert (out / published).exists(), published


def test_a_failing_sport_keeps_its_live_page_and_the_others_publish(root_page, tmp_path):
    out = tmp_path / 'site'
    asked = []

    def fetcher(url):
        asked.append(url)
        return b'<html>last good NHL page</html>'

    results = {r.sport: r for r in build.build_site(out, LIVE, runner=FakeRunner(out, fail={'nhl'}), fetcher=fetcher)}
    assert asked == [f'{LIVE}/nhl/']
    assert results['nhl'].kept_live and not results['nhl'].built and 'exited 1' in results['nhl'].error
    assert (out / 'nhl' / 'index.html').read_bytes() == b'<html>last good NHL page</html>'
    assert results['nfl'].built and results['nba'].built


def test_a_page_with_an_unfilled_placeholder_is_a_failed_build(root_page, tmp_path):
    out = tmp_path / 'site'
    runner = FakeRunner(out, leave={'nba': '<html>__NBA_JSON__</html>'})
    results = {r.sport: r for r in build.build_site(out, None, runner=runner, fetcher=no_network)}
    assert not results['nba'].published
    assert '__NBA_JSON__' in results['nba'].error
    assert not (out / 'nba').exists()


def test_the_nfl_falls_back_to_the_old_root_page_but_never_to_the_redirect(root_page, tmp_path):
    """The NFL's board was the root until this stage, so its first deploy
    here may keep it from there; the root as it is after this stage is the
    redirect, which is not the board."""
    out = tmp_path / 'site'
    board = b'<html>the old NFL board</html>'
    results = build.build_site(out, LIVE, runner=FakeRunner(out, fail={'nfl'}),
                               fetcher=lambda url: board if url == f'{LIVE}/' else None)
    assert results[0].kept_live
    assert (out / 'nfl' / 'index.html').read_bytes() == board

    for root in (build.redirect_page().encode('utf-8'), b'<html data-site-home><body>home</body></html>'):
        results = build.build_site(out, LIVE, runner=FakeRunner(out, fail={'nfl'}),
                                   fetcher=lambda url, root=root: root if url == f'{LIVE}/' else None)
        assert not results[0].published


def test_no_nfl_page_at_all_refuses_to_publish(root_page, tmp_path, monkeypatch):
    out = tmp_path / 'site'
    monkeypatch.setattr(build, 'build_site', lambda o, live: [build.SportResult('nfl', error='boom'),
                                                               build.SportResult('nhl', built=True)])
    assert build.main(['--out', str(out), '--report', str(tmp_path / 'r.json')]) == 1
    monkeypatch.setattr(build, 'build_site', lambda o, live: [build.SportResult('nfl', built=True),
                                                               build.SportResult('nhl', error='boom')])
    assert build.main(['--out', str(out), '--report', str(tmp_path / 'r.json')]) == 0
    report = json.loads((tmp_path / 'r.json').read_text(encoding='utf-8'))
    assert [s['published'] for s in report['sports']] == [True, False]


def test_the_root_sends_a_visitor_on_with_the_shared_picks_intact():
    """A shared-picks link carries its picks in the hash. The old address
    was the board itself, so every link already shared points at the root."""
    page = build.redirect_page()
    assert "location.replace('nfl/' + location.search + location.hash)" in page
    assert '<meta http-equiv="refresh" content="0; url=nfl/">' in page
    assert '<a href="nfl/">' in page
    assert build.REDIRECT_MARK in page


def test_the_report_is_written_outside_the_published_folder(tmp_path, monkeypatch):
    out = tmp_path / 'site'
    report = tmp_path / 'site-report.json'

    def fake(o, live):
        o.mkdir(parents=True, exist_ok=True)
        return [build.SportResult('nfl', built=True)]

    monkeypatch.setattr(build, 'build_site', fake)
    assert build.main(['--out', str(out), '--report', str(report)]) == 0
    assert report.exists()
    assert not list(out.rglob('*.json'))


def test_each_sport_is_built_in_a_process_of_its_own():
    """A crash or sys.exit in one sport's code must not stop the others, so
    the builders are separate processes, never imports."""
    cmds = {s: build.build_commands(s, Path('_site')) for s in build.SPORTS}
    assert [c[3] for c in cmds['nfl']] == ['src.pipeline.lock_proof', 'src.pipeline.generate_dashboard',
                                           'src.pipeline.check_build', 'src.pipeline.picks_csv']
    assert cmds['nhl'][0][3:] == ['src.sports.nhl.site', '--out', str(Path('_site') / 'nhl' / 'index.html')]
    source = Path(build.__file__).read_text(encoding='utf-8')
    assert 'import src.sports' not in source and 'from src.sports' not in source


# --- one issue per failed sport ----------------------------------------------

def test_only_failed_sports_get_an_issue_titled_for_them(tmp_path, monkeypatch):
    opened = []
    monkeypatch.setattr(alert_failed.alerts, 'open_or_comment',
                        lambda title, body: opened.append((title, body)) or ('opened', 1))
    report = tmp_path / 'r.json'
    report.write_text(json.dumps({'sports': [
        {'sport': 'nfl', 'built': True, 'kept_live': False, 'error': '', 'log': []},
        {'sport': 'nhl', 'built': False, 'kept_live': True, 'error': 'src.sports.nhl.site exited 1',
         'log': ['src.sports.nhl.site --out x: exit 1']},
    ]}), encoding='utf-8')
    assert alert_failed.main([str(report), '--run-url', 'https://run']) == 0
    assert [t for t, _ in opened] == ['NHL: page build failed']
    body = opened[0][1]
    assert 'https://run' in body and 'exited 1' in body and 'published again unchanged' in body


# --- the deploy runs it --------------------------------------------------------

WORKFLOW = Path(__file__).parent.parent / '.github' / 'workflows' / 'deploy-pages.yml'


def test_the_deploy_builds_the_site_and_alerts_per_sport_before_uploading():
    text = WORKFLOW.read_text(encoding='utf-8')
    build_at = text.index('python -m src.site.build --out _site --live-url')
    alert_at = text.index('python -m src.site.alert_failed site-report.json')
    upload_at = text.index('upload-pages-artifact')
    assert build_at < alert_at < upload_at
    alert_step = text[text.rindex('      - name:', 0, alert_at):alert_at]
    assert '!cancelled()' in alert_step, 'the per-sport alert must run when the build step failed'
    assert 'issues: write' in text
