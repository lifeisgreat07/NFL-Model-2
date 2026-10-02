/*
 * Executes the My Picks kickoff lock (Stage 11): kickoffInstant,
 * isPickLocked, pickVerdict, tallyMyPicks, leftOutSentence and
 * stampUnlockedPicks, extracted from the shipped template.
 *
 * The lock compares an Eastern wall-clock kickoff with the visitor's clock,
 * which is the one place the page has to turn a schedule time into an
 * instant. The failure that matters -- reading the time in the visitor's
 * own zone -- produces a lock that works perfectly for anyone in New York,
 * so this harness is run twice by the test, under two TZ settings, and the
 * answers must be identical.
 *
 * Driven by tests/test_my_picks_kickoff_lock.py.
 */
const fs = require('fs');
const path = require('path');

const TEMPLATE = path.join(__dirname, '..', 'src', 'pipeline', 'dashboard_template.html');
const tpl = fs.readFileSync(TEMPLATE, 'utf8');

const START = 'function easternOffsetHours(';
const END = '/* ---------- end of the picks lock ---------- */';
const i = tpl.indexOf(START), j = tpl.indexOf(END);
if (i === -1 || j === -1 || j <= i) {
  console.log(JSON.stringify({fatal:
    `could not extract the picks lock (start=${i}, end=${j}) -- the ` +
    `markers moved and this harness is testing nothing`}));
  process.exit(0);
}
eval(tpl.slice(i, j));

const iso = ms => ms === null ? null : new Date(ms).toISOString();
const game = (gameday, gametime_et, extra) =>
  Object.assign({away: 'NE', home: 'SEA', gameday, gametime_et, graded: false,
                 actual_home_win: null}, extra || {});

// Real 2026 slots plus the two daylight-saving edges and a January game.
const instants = {
  sundayEarly: iso(kickoffInstant(game('2026-09-13', '13:00'))),
  london: iso(kickoffInstant(game('2026-09-13', '09:30'))),
  mondayNight: iso(kickoffInstant(game('2026-09-14', '20:15'))),
  lastDaylightSunday: iso(kickoffInstant(game('2026-10-25', '13:00'))),
  fallBackSunday: iso(kickoffInstant(game('2026-11-01', '13:00'))),
  standardSunday: iso(kickoffInstant(game('2026-11-08', '13:00'))),
  january: iso(kickoffInstant(game('2027-01-10', '16:30'))),
  springForwardSunday: iso(kickoffInstant(game('2027-03-14', '13:00'))),
  dayBeforeSpringForward: iso(kickoffInstant(game('2027-03-13', '13:00'))),
  dayOnly: iso(kickoffInstant(game('2026-09-13', null))),
  undated: iso(kickoffInstant(game(null, null))),
};

const sun = game('2026-09-13', '13:00');
const K = kickoffInstant(sun);
const locks = {
  minuteBefore: isPickLocked(sun, K - 60000),
  atKickoff: isPickLocked(sun, K),
  after: isPickLocked(sun, K + 3600000),
  gradedUndatedEarly: isPickLocked(game(null, null, {graded: true}), 0),
  undatedUngraded: isPickLocked(game(null, null), 4102444800000),
  gradedBeforeKickoff: isPickLocked(game('2026-09-13', '13:00', {graded: true}), K - 86400000),
};

const verdicts = {
  before: pickVerdict(new Date(K - 1000).toISOString(), sun),
  atKickoff: pickVerdict(new Date(K).toISOString(), sun),
  after: pickVerdict(new Date(K + 1000).toISOString(), sun),
  none: pickVerdict(undefined, sun),
  garbage: pickVerdict('yesterday', sun),
  unknownKickoff: pickVerdict(new Date(0).toISOString(), game(null, null)),
};

// A graded week of four games, all home wins, kickoff Sunday 13:00 ET.
const wk = '2026_week1';
const teams = [['A1', 'H1'], ['A2', 'H2'], ['A3', 'H3'], ['A4', 'H4']];
const weekMap = {[wk]: {games: teams.map(([a, h]) =>
  ({away: a, home: h, gameday: '2026-09-13', gametime_et: '13:00',
    graded: true, actual_home_win: 1}))}};
const pid = ([a, h]) => `${wk}|${h}|${a}`;
const before = new Date(K - 3600000).toISOString();
const after = new Date(K + 86400000).toISOString();
const allWinners = {};
teams.forEach(t => { allWinners[pid(t)] = t[1]; });

const tallies = {
  // The exploit measured on 2026-09-26: every winner written in after the
  // results. With times after kickoff, none of it counts.
  allWinnersAfterResults: tallyMyPicks(allWinners, Object.fromEntries(teams.map(t => [pid(t), after])), [wk], weekMap),
  // The same picks with no times at all: saved before this change existed.
  legacy: tallyMyPicks(allWinners, {}, [wk], weekMap),
  // Mixed: two made in time (one right, one wrong), one late, one untimed.
  mixed: tallyMyPicks(
    {[pid(teams[0])]: 'H1', [pid(teams[1])]: 'A2', [pid(teams[2])]: 'H3', [pid(teams[3])]: 'H4'},
    {[pid(teams[0])]: before, [pid(teams[1])]: before, [pid(teams[2])]: after},
    [wk], weekMap),
  // An ungraded game is not in the tally at all, whatever its pick.
  ungraded: tallyMyPicks({[`${wk}|X|Y`]: 'X'}, {[`${wk}|X|Y`]: before},
    [wk], {[wk]: {games: [{away: 'Y', home: 'X', gameday: '2026-09-13', gametime_et: '13:00', graded: false, actual_home_win: null}]}}),
};

const sentences = {
  none: leftOutSentence({wins: 3, losses: 1, late: 0, untimed: 0}),
  oneLate: leftOutSentence({wins: 0, losses: 0, late: 1, untimed: 0}),
  mixed: leftOutSentence({wins: 0, losses: 0, late: 2, untimed: 3}),
  oneUntimed: leftOutSentence({wins: 0, losses: 0, late: 0, untimed: 1}),
};

// Stamping: an open game's untimed pick is stamped with now; a locked
// game's is not; an existing time is never replaced.
const openGame = game('2026-09-20', '13:00', {away: 'OA', home: 'OH'});
const lockedGame = game('2026-09-13', '13:00', {away: 'LA', home: 'LH'});
const games = {'w|OH|OA': openGame, 'w|LH|LA': lockedGame, 'w|TH|TA': openGame};
const now = K + 3600000;  // an hour after the locked game's kickoff
const stampTimes = {'w|TH|TA': '2026-09-01T00:00:00.000Z'};
const stamped = stampUnlockedPicks({'w|OH|OA': 'OH', 'w|LH|LA': 'LH', 'w|TH|TA': 'TH'},
  stampTimes, p => games[p] || null, now);

console.log(JSON.stringify({instants, locks, verdicts, tallies, sentences,
  stamp: {stamped, times: stampTimes, nowIso: new Date(now).toISOString()}}));
