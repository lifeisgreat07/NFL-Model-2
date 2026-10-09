"""The NBA data probe judges each source on the shape a later stage needs.

Stage 61, the NBA's Stage 51. `src/sports/nba/data_probe.py` reads every
source the NBA's go/no-go (`docs/nba-data.md`) relies on; the network part runs
in `.github/workflows/nba-data-probe.yml`, from GitHub's own runners. Payloads
here are small and synthetic, in ESPN's, the league's and the fallback's shapes.

Run with: pytest tests/test_nba_data_probe.py -v
"""
import json
import re
from pathlib import Path

from src.sports.nba import data_probe as probe

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / '.github' / 'workflows' / 'nba-data-probe.yml'


def event(eid='401705534', home='BKN', away='BOS', date='2025-03-15T23:30Z', state='STATUS_FINAL', done=True):
    return {'id': eid, 'date': date, 'competitions': [{
        'status': {'type': {'name': state, 'completed': done}},
        'competitors': [{'homeAway': 'home', 'team': {'abbreviation': home}},
                        {'homeAway': 'away', 'team': {'abbreviation': away}}]}]}


def test_a_complete_scoreboard_passes():
    assert probe.check_scoreboard({'events': [event()]}) == []


def test_a_scoreboard_game_missing_what_the_lock_needs_is_named():
    assert 'two teams' in probe.check_scoreboard({'events': [event(away='BKN')]})[0]
    assert 'a UTC start' in probe.check_scoreboard({'events': [event(date='2025-03-15T19:30-04:00')]})[0]
    assert 'a state' in probe.check_scoreboard({'events': [event(state='')]})[0]
    assert probe.check_scoreboard({'events': []}) == ['no games on a date that had games']


def box(drop=None):
    stats = [s for s in probe.POSSESSION_STATS if s != drop] + ['assists']
    return {'boxscore': {'teams': [{'team': {'abbreviation': t}, 'statistics': [{'name': s} for s in stats]}
                                   for t in ('BOS', 'BKN')]}}


def test_a_box_score_with_what_possessions_need_passes_and_one_without_fails():
    assert probe.check_box_score(box()) == []
    assert 'no offensiveRebounds' in probe.check_box_score(box(drop='offensiveRebounds'))[0]
    assert probe.check_box_score({'boxscore': {'teams': []}}) == ['0 teams in the box score, not 2']


def test_odds_need_both_moneylines():
    ok = {'items': [{'homeTeamOdds': {'moneyLine': 450}, 'awayTeamOdds': {'moneyLine': -650}}]}
    assert probe.check_odds(ok) == []
    assert probe.check_odds({'items': [{'homeTeamOdds': {'moneyLine': 450}, 'awayTeamOdds': {}}]}) == [
        'a moneyline is missing for one team']
    assert probe.check_odds({'items': []}) == ['no odds for a past game']


def test_injuries_need_players_with_a_status():
    ok = {'injuries': [{'injuries': [{'status': 'Out'}, {'status': 'Day-To-Day'}]}]}
    assert probe.check_injuries(ok) == []
    assert probe.check_injuries({'injuries': [{'injuries': [{'status': 'Out'}, {}]}]}) == [
        '1 of 2 injuries have no status']
    assert probe.check_injuries({'injuries': []}) == ['no injury list']


def test_a_parquet_file_is_known_by_its_magic_bytes():
    assert probe.check_parquet(b'PAR1' + b'x' * 20 + b'PAR1') == []
    assert 'not a parquet file' in probe.check_parquet(b'<!DOCTYPE html>404')[0]
    assert 'not a parquet file' in probe.check_parquet(b'')[0]


def test_the_season_is_named_by_the_year_it_ends():
    from datetime import UTC, datetime
    assert probe.season_end_year(datetime(2026, 10, 6, tzinfo=UTC)) == 2027
    assert probe.season_end_year(datetime(2026, 9, 30, tzinfo=UTC)) == 2026


def test_the_league_feeds_shapes():
    assert probe.check_cdn_scoreboard({'scoreboard': {'games': []}}) == []
    assert probe.check_cdn_scoreboard({}) == ['no games list']
    assert probe.check_cdn_odds({'games': [{}]}) == [] and probe.check_cdn_odds({}) == ['no games list']
    assert probe.check_cdn_schedule({'leagueSchedule': {'gameDates': [{}]}}) == []
    assert probe.check_cdn_schedule({'leagueSchedule': {'gameDates': []}}) == ['no game dates']


def fake_get(responses):
    def get(url):
        for pattern, body in responses.items():
            if pattern in url:
                if isinstance(body, Exception):
                    raise body
                return body if isinstance(body, str) else json.dumps(body)
        raise AssertionError(f'unexpected url {url}')
    return get


PARQUET = b'PAR1' + b'0' * 32 + b'PAR1'


def fake_bytes(bad=()):
    def get(url):
        if any(b in url for b in bad):
            raise OSError('HTTP Error 404: Not Found')
        assert url.startswith((probe.HOOPR, probe.INJURIES)), url
        return PARQUET
    return get


GOOD = {
    '/scoreboard?': {'events': [event()]},
    '/summary': box(),
    '/odds?': {'items': [{'homeTeamOdds': {'moneyLine': 450}, 'awayTeamOdds': {'moneyLine': -650}}]},
    '/competitions/': {'items': [{'homeTeamOdds': {'moneyLine': 450}, 'awayTeamOdds': {'moneyLine': -650}}]},
    '/injuries': {'injuries': [{'injuries': [{'status': 'Out'}]}]},
    'todaysScoreboard': {'scoreboard': {'games': []}},
    'odds_todaysGames': {'games': []},
    'scheduleLeagueV2': {'leagueSchedule': {'gameDates': [{}]}},
    'draftkings.com': None,   # filled below, once the helpers exist
    'kalshi.com': None,
    'polymarket.com': None,
    'timestamp.json': {'last_updated': '2026-10-08 15:12:01 EDT'},
}
NOW = __import__('datetime').datetime(2026, 10, 6, tzinfo=__import__('datetime').UTC)


def test_every_required_source_usable_exits_zero_and_reads_this_seasons_files(capsys):
    seen = []

    def get_bytes(url):
        seen.append(url)
        return PARQUET
    assert probe.main(get=fake_get(GOOD), get_bytes=get_bytes, now=NOW) == 0
    assert [u.rsplit('/', 1)[1] for u in seen] == ['nba_schedule_2027.parquet', 'team_box_2026.parquet',
                                                    'player_box_2026.parquet', 'injuries_2027.parquet']
    assert 'all usable from here' in capsys.readouterr().out


def test_a_required_source_missing_fails_the_run_and_says_which(capsys):
    assert probe.main(get=fake_get(GOOD), get_bytes=fake_bytes(bad=('player_box',)), now=NOW) == 1
    out = capsys.readouterr().out
    assert 'hoopR player box 2026: UNREACHABLE' in out and 'NOT all usable' in out


def test_a_candidate_refused_is_reported_and_does_not_fail_the_run(capsys):
    refused = dict(GOOD, **{'/scoreboard?': OSError('HTTP Error 403: Forbidden'),
                            'odds_todaysGames': OSError('HTTP Error 403: Forbidden')})
    assert probe.main(get=fake_get(refused), get_bytes=fake_bytes(), now=NOW) == 0
    out = capsys.readouterr().out
    assert 'ESPN scoreboard: UNREACHABLE' in out and 'league odds (cdn.nba.com): UNREACHABLE' in out


def test_the_workflow_runs_the_probe_on_its_own_pull_requests_and_writes_nothing():
    wf = WORKFLOW.read_text(encoding='utf-8')
    assert re.search(r'^name: NBA ', wf, re.M)
    assert "'src/sports/nba/data_probe.py'" in wf and "'.github/workflows/nba-data-probe.yml'" in wf
    assert 'workflow_dispatch' in wf and 'schedule:' not in wf
    assert 'python -m src.sports.nba.data_probe' in wf
    assert re.search(r'permissions:\s*\n\s*contents: read\s*\n', wf)
    assert 'git-auto-commit' not in wf and 'git add' not in wf and 'git push' not in wf


# ---------------------------------------------------------------- Stage 65: a price and an injury list

def draftkings(odds=(1.84, 2.05), start='2026-10-20T19:00:00.0000000Z', market='Moneyline'):
    return {'events': [{'id': '1', 'startEventDate': start}],
            'markets': [{'id': 'm1', 'eventId': '1', 'marketType': {'name': market}}],
            'selections': [{'marketId': 'm1', 'trueOdds': o} for o in odds]}


def kalshi(bid='0.4500', ask='0.4700', ticker='KXNBAGAME-26OCT20BOSDET'):
    return {'markets': [{'event_ticker': ticker, 'yes_bid_dollars': bid, 'yes_ask_dollars': ask}]}


def polymarket(prices='["0.535", "0.465"]', tag='games'):
    return [{'title': 'Rockets vs. Mavericks', 'tags': [{'slug': 'nba'}, {'slug': tag}],
             'markets': [{'outcomes': '["Rockets", "Mavericks"]', 'outcomePrices': prices}]}]


GOOD.update({'draftkings.com': draftkings(), 'kalshi.com': kalshi(), 'polymarket.com': polymarket()})


def test_a_draftkings_moneyline_needs_both_sides_and_a_start():
    assert probe.check_draftkings(draftkings()) == []
    assert probe.check_draftkings(draftkings(odds=(1.84,))) != []
    assert probe.check_draftkings(draftkings(start=None)) != []
    assert probe.check_draftkings(draftkings(market='Spread')) == ['no Moneyline market']
    assert probe.check_draftkings({}) == ['no NBA events']


def test_a_kalshi_game_needs_a_bid_and_an_ask():
    assert probe.check_kalshi(kalshi()) == []
    assert probe.check_kalshi(kalshi(bid='0.0000')) != []
    assert probe.check_kalshi(kalshi(bid='0.6000', ask='0.4000')) != [], 'a bid above the ask is not a quote'
    assert probe.check_kalshi(kalshi(ticker='KXNBA-26-OKC')) == ['no NBA game markets'], 'a futures market is not a game'


def test_a_polymarket_game_needs_a_two_way_price():
    assert probe.check_polymarket(polymarket()) == []
    assert probe.check_polymarket(polymarket(tag='nba-finals')) == ['no NBA game events']
    assert probe.check_polymarket(polymarket(prices='["0.9", "0.9"]')) != []
    assert probe.check_polymarket({}) == ['no list of events']


def test_the_injury_release_is_read_for_this_season():
    assert probe.check_timestamp({'last_updated': 'x'}) == [] and probe.check_timestamp({}) != []
    names = [n for n, _, _ in probe.candidates(fake_get(GOOD), fake_bytes(), NOW)]
    assert 'SportsDataverse injuries 2027' in names


def test_on_a_runner_one_notice_sums_every_source_up(capsys, monkeypatch):
    monkeypatch.setenv('GITHUB_ACTIONS', 'true')
    refused = dict(GOOD, **{'kalshi.com': OSError('HTTP Error 403: Forbidden')})
    assert probe.main(get=fake_get(refused), get_bytes=fake_bytes(), now=NOW) == 0
    notices = [ln for ln in capsys.readouterr().out.splitlines() if ln.startswith('::notice')]
    assert len(notices) == 1
    for part in ('DraftKings NBA moneylines: ok', 'Kalshi NBA game markets: UNREACHABLE',
                 'Polymarket NBA games: ok', 'SportsDataverse injuries 2027: ok', 'hoopR schedule 2027: ok'):
        assert part in notices[0], part


def test_off_a_runner_there_is_no_notice(capsys, monkeypatch):
    monkeypatch.delenv('GITHUB_ACTIONS', raising=False)
    probe.main(get=fake_get(GOOD), get_bytes=fake_bytes(), now=NOW)
    assert '::notice' not in capsys.readouterr().out
