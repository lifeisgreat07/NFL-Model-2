"""Team Deep-Dive's "This week" block: short, sourced, and honest (Stage 16).

src/sports/nfl/team_news.py writes each locked week's team news; generate_dashboard.py
attaches it to weeks[k].news while the week is still being played; the
template's teamNewsItems() and renderTeamNews() turn it into at most five
lines, each with its source and date. The lines are generated prose over data
that has holes in it -- a report not yet out, a team with no depth chart, a
pick saved before the quarterback fields -- so they are executed here in node
over each case rather than read.

Run with: pytest tests/test_team_dive_news.py -v
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from src.core.template_parts import JOINED_TEMPLATE

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = JOINED_TEMPLATE

from src.sports.nfl import generate_dashboard as gd

NODE = shutil.which('node')
READ = '2026-09-28T02:00:00Z'   # Sunday 22:00 in New York, Monday in UTC


def function_source(src, name):
    m = re.search(r'function ' + name + r'\(.*?\n\}\n', src, re.S)
    assert m, f'{name} is not findable -- re-anchor this guard'
    return m.group(0)


def run_js(body):
    if not NODE:
        pytest.skip('node not available')
    src = TEMPLATE.read_text(encoding='utf-8')
    js = ''.join(function_source(src, n) for n in
                 ('escapeHtml', 'newsWeekKey', 'newsDate', 'teamNewsItems', 'renderTeamNews')) + body
    # utf-8 explicitly: the source line carries a middle dot, and Windows would
    # otherwise decode node's output as cp1252.
    r = subprocess.run([NODE, '-e', js], capture_output=True, encoding='utf-8')
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def items(entry, week=4, read_at=READ):
    return run_js(f'process.stdout.write(JSON.stringify(teamNewsItems('
                  f'{json.dumps(entry)}, {week}, {json.dumps(read_at)})));')


def texts(entry, **kw):
    return [i['text'] for i in items(entry, **kw)]


def published(**kw):
    return dict({'qb': None, 'injury_report': 'published', 'out': [], 'doubtful': [],
                 'questionable_starters': 0}, **kw)


WILLIAMS = {'name': 'Caleb Williams', 'position': 'QB', 'injury': 'Hamstring'}
MOORE = {'name': 'D.J. Moore', 'position': 'WR', 'injury': None}


def test_out_and_doubtful_starters_are_named_with_position_and_injury():
    got = texts(published(out=[WILLIAMS, MOORE], doubtful=[{'name': 'Puka Nacua',
                                                           'position': 'WR', 'injury': 'Hip'}]))
    assert got == ['Out: Caleb Williams (QB, hamstring), D.J. Moore (WR).',
                   'Doubtful: Puka Nacua (WR, hip).']


def test_questionable_starters_are_a_count_not_a_list():
    assert texts(published(questionable_starters=1)) == ['1 starter listed as questionable.']
    assert texts(published(questionable_starters=3)) == ['3 starters listed as questionable.']


def test_a_published_report_with_no_starters_on_it_says_so():
    assert texts(published()) == ['No starters listed as out, doubtful or questionable.']


def test_an_unpublished_report_never_reads_as_nobody_hurt():
    got = texts({'qb': None, 'injury_report': 'not yet published'})
    assert got == ['The week 4 injury report is not out yet, so there is no injury news.']
    assert not any('No starters' in t for t in got)


def test_a_team_with_no_depth_chart_says_it_could_not_be_checked():
    got = texts({'qb': None, 'injury_report': 'no depth chart for this team'})
    assert got == ['Starters could not be checked: there is no depth chart for this team.']


def test_the_quarterback_line_comes_first_and_says_whether_he_is_new():
    same = {'name': 'Jared Goff', 'basis': 'last_game', 'changed_from': None}
    new = {'name': 'Tyson Bagent', 'basis': 'override', 'changed_from': 'Caleb Williams'}
    assert texts(published(qb=same))[0] == 'Quarterback: Jared Goff, the same starter as last game.'
    assert texts(published(qb=new))[0] == 'New starting quarterback: Tyson Bagent, in place of Caleb Williams.'


def test_a_pick_made_with_a_quarterback_now_listed_out_says_so_on_its_own_line():
    qb = {'name': 'Caleb Williams', 'basis': 'last_game', 'changed_from': None}
    got = texts(published(qb=qb, out=[WILLIAMS]))
    assert got[0] == ("The model's pick was made with Caleb Williams at quarterback, "
                      "and he is listed as out.")
    got = texts(published(qb=qb, doubtful=[WILLIAMS]))
    assert got[0].endswith('and he is listed as doubtful.')


def test_every_line_carries_its_source_and_the_date_it_was_read_in_new_york():
    got = items(published(qb={'name': 'Jared Goff', 'changed_from': None}, out=[WILLIAMS]))
    assert got[0]['source'] == "The quarterback the model's week 4 pick was made with"
    assert got[1]['source'] == 'Official injury report, via nflverse · read Sun, Sep 27'


def test_never_more_than_five_lines():
    qb = {'name': 'Jared Goff', 'changed_from': 'Hendon Hooker'}
    everything = published(qb=qb, out=[WILLIAMS, MOORE] * 5, doubtful=[MOORE] * 5,
                           questionable_starters=6)
    assert len(items(everything)) <= 5


WEEKS = {
    '2026_week3': {'season': 2026, 'week': 3, 'games': [{'home': 'GB', 'away': 'ATL'}],
                   'news': {'read_at': READ, 'teams': {'ATL': published(out=[WILLIAMS])}}},
    '2026_week4': {'season': 2026, 'week': 4,
                   'games': [{'home': 'CHI', 'away': 'DET'}, {'home': 'NO', 'away': 'ATL'}],
                   'news': {'read_at': READ, 'teams': {
                       'CHI': published(out=[{'name': '<b>Bold</b>', 'position': 'QB',
                                              'injury': None}]),
                       'DET': published(), 'NO': published(), 'ATL': published()}}},
    '2026_week5': {'season': 2026, 'week': 5, 'games': [{'home': 'CHI', 'away': 'GB'}]},
}


def render(team, weeks=WEEKS):
    keys = sorted(weeks, key=lambda k: (weeks[k]['season'], weeks[k]['week']))
    return run_js(f'const weeks={json.dumps(weeks)};const weekKeysSorted={json.dumps(keys)};'
                  f'process.stdout.write(JSON.stringify(renderTeamNews({json.dumps(team)})));')


def test_the_block_shows_the_newest_week_that_has_news():
    html = render('ATL')
    assert 'Week 4, @ NO.' in html and 'No starters listed' in html
    assert 'Caleb Williams' not in html, 'week 3 is older news than week 4'


def test_a_team_without_a_game_that_week_is_told_so():
    assert 'GB have no game in week 4.' in render('GB')


def test_no_week_with_news_says_when_news_appears():
    html = render('CHI', {k: {kk: vv for kk, vv in v.items() if kk != 'news'}
                          for k, v in WEEKS.items()})
    assert "No team news right now. It appears once a week's picks are locked" in html


def test_names_are_escaped():
    html = render('CHI')
    assert '&lt;b&gt;Bold&lt;/b&gt;' in html and '<b>Bold</b>' not in html


def test_the_block_sits_above_the_rating_history():
    body = function_source(TEMPLATE.read_text(encoding='utf-8'), 'renderTeamDive')
    news, rows = body.find('renderTeamNews(team)'), body.find('${rowsHtml}')
    assert news != -1 and rows != -1 and news < rows


# ---- the generator: what reaches the page, and when it expires ----

def _write(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj), encoding='utf-8')


def test_week_files_are_read_by_season_and_week(tmp_path):
    _write(tmp_path / '2026_week4.json', {'read_at': READ, 'sources': {},
                                          'teams': {'CHI': published()}})
    _write(tmp_path / 'notes.json', {})
    news = gd.load_team_news(tmp_path)
    assert list(news) == [(2026, 4)]
    assert news[(2026, 4)] == {'read_at': READ, 'teams': {'CHI': published()}}


def test_no_news_folder_means_no_news_and_says_so(tmp_path, capsys):
    assert gd.load_team_news(tmp_path / 'missing') == {}
    assert 'team news has not been read yet' in capsys.readouterr().out


def test_news_expires_once_every_pick_in_its_week_is_graded():
    news = {'read_at': READ, 'teams': {}}
    two = [{'home': 'CHI', 'away': 'DET'}, {'home': 'NO', 'away': 'ATL'}]
    assert gd.week_news(two, [], news) is news
    assert gd.week_news(two, two[:1], news) is news, 'Monday night is still to be graded'
    assert gd.week_news(two, two, news) is None
    assert gd.week_news(two, [], None) is None
