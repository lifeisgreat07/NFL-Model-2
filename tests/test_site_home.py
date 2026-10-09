"""The site's home page (Stage 59, src/site/home.py and src/site/home/).

The facts each card is built from are read from small synthetic
repositories, so nothing here depends on the week the suite runs in. The
status itself is worked out in the visitor's browser; what is checked here
is that the page carries the facts, forwards an old shared-picks link, says
so when a sport has no page, and is put in place by the site build.

Run with: pytest tests/test_site_home.py -v
"""
import json
from datetime import UTC, datetime
from pathlib import Path

from src.site import build, home

NOW = datetime(2026, 10, 6, 15, 0, tzinfo=UTC)


def write(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj), encoding='utf-8')


def nfl_game(day, clock):
    return {'home': 'CLE', 'away': 'PIT', 'gameday': day, 'gametime_et': clock}


def test_an_nfl_kickoff_is_eastern_time_with_daylight_saving_by_the_date():
    assert home.nfl_kickoff(nfl_game('2026-10-01', '20:15')) == '2026-10-02T00:15:00Z'
    assert home.nfl_kickoff(nfl_game('2026-12-03', '20:15')) == '2026-12-04T01:15:00Z'
    assert home.nfl_kickoff({'gameday': '2026-10-01'}) is None


def test_the_nfl_card_reads_the_latest_locked_week_and_model_bs_record(tmp_path):
    write(tmp_path / 'predictions/nfl/2026_week3.json', [nfl_game('2026-09-24', '20:15')])
    write(tmp_path / 'predictions/nfl/2026_week4.json', [nfl_game('2026-10-01', '20:15'), nfl_game('2026-10-04', '13:00')])
    write(tmp_path / 'predictions/nfl/preview/2026_week5.json', [nfl_game('2026-10-08', '20:15')])
    write(tmp_path / 'results/nfl/2026_week3_graded.json',
          [{'model_b_correct': 1}, {'model_b_correct': 0}, {'model_b_correct': 1}, {'model_b_correct': None}])
    write(tmp_path / 'predictions/nfl/2025_week18.json', [nfl_game('2026-01-04', '13:00')])
    write(tmp_path / 'results/nfl/2025_week18_graded.json', [{'model_b_correct': 1}])
    f = home.nfl_facts(tmp_path)
    assert (f['season'], f['week'], f['preview_week']) == (2026, 4, 5)
    assert f['kickoffs'] == ['2026-10-02T00:15:00Z', '2026-10-04T17:00:00Z']
    assert (f['record']['won'], f['record']['lost']) == (2, 1)


def test_the_nhl_card_carries_two_weeks_of_games_and_the_picks_record(tmp_path):
    games = [{'start_utc': '2026-10-06T23:00:00Z', 'status': 'scheduled', 'game_type': 'regular'},
             {'start_utc': '2026-10-06T23:30:00Z', 'status': 'cancelled', 'game_type': 'regular'},
             {'start_utc': '2026-09-28T23:00:00Z', 'status': 'final', 'game_type': 'preseason'},
             {'start_utc': '2026-11-30T23:00:00Z', 'status': 'scheduled', 'game_type': 'regular'}]
    write(tmp_path / 'results/nhl/schedule_2026.json', {'games': games})
    write(tmp_path / 'results/nhl/graded_2026.json',
          [{'result': 'correct'}, {'result': 'wrong'}, {'result': 'pending'}, {'result': 'cancelled'}])
    f = home.nhl_facts(tmp_path, NOW)
    assert f['games'] == [['2026-10-06T23:00:00Z', 'scheduled']]
    assert (f['record']['won'], f['record']['lost']) == (1, 1)


def test_a_sport_with_no_files_says_so_rather_than_vanishing(tmp_path):
    """The NBA's page is built from its backtest even before the daily run's
    first schedule, so its card is built and says when picks start."""
    f = home.facts(tmp_path, NOW)
    assert f['nfl'] == {'built': False} and f['nhl'] == {'built': False}
    assert f['nba'] == {'built': True, 'games': [], 'record': {'label': 'Picks this season', 'won': 0, 'lost': 0}}


def test_the_nba_card_is_live_as_the_nhls_is_play_in_included(tmp_path):
    """Stage 65: the NBA locks game by game, as the NHL does, so its card
    counts tonight's games and the picks' record the same way."""
    games = [{'start_utc': '2026-10-06T23:00:00Z', 'status': 'scheduled', 'game_type': 'regular'},
             {'start_utc': '2026-10-06T23:30:00Z', 'status': 'scheduled', 'game_type': 'playin'},
             {'start_utc': '2026-10-07T00:00:00Z', 'status': 'postponed', 'game_type': 'regular'}]
    write(tmp_path / 'results/nba/schedule_2026.json', {'games': games})
    write(tmp_path / 'results/nba/graded_2026.json', [{'result': 'correct'}, {'result': 'correct'}, {'result': 'wrong'}])
    f = home.nba_facts(tmp_path, NOW)
    assert f['games'] == [['2026-10-06T23:00:00Z', 'scheduled'], ['2026-10-06T23:30:00Z', 'scheduled']]
    assert (f['record']['won'], f['record']['lost']) == (2, 1)
    js = (home.TEMPLATE / 'home.js').read_text(encoding='utf-8')
    assert "dayStatus(f, 'tip-off')" in js and "'Open the NBA board'" in js
    assert 'No live picks' not in js and 'Backtest only' not in js


def test_the_page_is_filled_and_its_data_cannot_close_its_script():
    data = {'nfl': {'built': False}, 'nhl': {'built': False}, 'nba': {'built': False},
            'x': '</script><script>alert(1)</script>'}
    page = home.render(data)
    assert '__HOME_JSON__' not in page and '{% include' not in page
    assert '</script><script>alert(1)' not in page
    assert '\\u003c/script\\u003e' in page


def test_an_old_shared_picks_link_is_sent_on_to_the_nfl_board():
    """Every #picks= link was made on the NFL board while it lived at the
    root. The home page took the root, so it must keep sending them on."""
    page = (home.TEMPLATE / 'page.html').read_text(encoding='utf-8')
    head = page.split('</head>')[0]
    assert "if(/[#&]picks=/.test(location.hash)) location.replace('nfl/' + location.search + location.hash);" in head


def test_the_root_describes_the_whole_site():
    page = (home.TEMPLATE / 'page.html').read_text(encoding='utf-8')
    assert '<meta property="og:url" content="https://lifeisgreat07.github.io/NFL-Model-2/">' in page
    assert build.HOME_MARK in page, "the NFL's fallback must be able to tell the home page from its board"


def test_the_status_is_worked_out_against_the_visitors_clock():
    js = (home.TEMPLATE / 'home.js').read_text(encoding='utf-8')
    assert 'const NOW = Date.now();' in js
    assert "dayKey(g.t) === dayKey(NOW)" in js, 'tonight must be tonight where the visitor is'


def test_a_sport_with_no_page_gets_a_card_that_links_nowhere():
    js = (home.TEMPLATE / 'home.js').read_text(encoding='utf-8')
    assert "return card(sport, name, null," in js
    assert '`<div class="home-card is-unbuilt"' in js


def test_the_browser_checks_can_walk_the_home_page():
    """tests/browser/check_page.py walks each section.page and reports a page
    with none as the wrong page; the home page has one and no switcher."""
    page = (home.TEMPLATE / 'page.html').read_text(encoding='utf-8')
    assert '<section class="page active home-page" id="page-home">' in page
    checker = (Path(__file__).resolve().parent / 'browser' / 'check_page.py').read_text(encoding='utf-8')
    assert "typeof setActivePage === 'function' && setActivePage(" in checker


def test_a_sport_with_no_page_loses_its_pill_too():
    js = (home.TEMPLATE / 'home.js').read_text(encoding='utf-8')
    assert "if(HOME[sport] && HOME[sport].built) continue;" in js
    assert 'pill.replaceWith(span);' in js


# --- put in place by the site build -------------------------------------------

def test_the_site_build_tells_the_home_page_which_sports_have_no_page(tmp_path):
    seen = []

    def runner(cmd):
        seen.append(cmd)
        return 0

    out = tmp_path / 'site'
    out.mkdir()
    (out / 'index.html').write_text('<html>home</html>', encoding='utf-8')
    res = build.build_home(out, runner, ('nhl',))
    assert res.built
    assert seen[0][3:] == ['src.site.home', '--out', str(out / 'index.html'), '--unpublished', 'nhl']


def test_a_home_page_that_fails_leaves_the_root_forwarding_to_the_nfl(tmp_path):
    out = tmp_path / 'site'
    out.mkdir()
    res = build.build_home(out, lambda cmd: 1)
    assert not res.built and res.kept_live and 'exited 1' in res.error
    assert (out / 'index.html').read_text(encoding='utf-8') == build.redirect_page()


def test_the_command_line_marks_unpublished_sports_as_not_built(tmp_path, monkeypatch):
    monkeypatch.setattr(home, 'facts', lambda: {'nfl': {'built': True, 'season': 2026, 'week': 4, 'kickoffs': [],
                                                        'preview_week': None, 'record': {'label': 'x', 'won': 0, 'lost': 0}},
                                                'nhl': {'built': True}, 'nba': {'built': True, 'live': False}})
    monkeypatch.setattr(home, 'font_faces_css', lambda: '')
    out = tmp_path / 'index.html'
    assert home.main(['--out', str(out), '--unpublished', 'nhl']) == 0
    data = json.loads(out.read_text(encoding='utf-8').split('<script id="home-data" type="application/json">')[1]
                      .split('</script>')[0])
    assert data['nhl'] == {'built': False} and data['nfl']['built']
