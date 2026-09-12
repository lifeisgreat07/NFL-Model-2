/*
 * Executes the Week Board's real kickoff comparator.
 *
 * Sort order is the kind of thing that looks right at a glance and is wrong in
 * a way nobody reports: a card in the wrong place still looks like a card.
 * These functions live at module scope specifically so they can be run here --
 * the comparator they serve sits inside renderGames(), which needs a DOM and a
 * week of real data, and a sort nobody can execute is a sort nobody can check.
 *
 * Same standard as tests/why_words_harness.js and tests/matchup_header_harness.js.
 *
 * Driven by tests/test_kickoff_order.py.
 */
const fs = require('fs');
const path = require('path');

const TEMPLATE = path.join(__dirname, '..', 'src', 'dashboard_template.html');
const tpl = fs.readFileSync(TEMPLATE, 'utf8');

const START = 'function kickoffKey(';
const END = 'function renderGames(';
const i = tpl.indexOf(START), j = tpl.indexOf(END);
if (i === -1 || j === -1 || j <= i) {
  console.log(JSON.stringify({fatal:
    `could not extract the kickoff comparator (start=${i}, end=${j}) -- the ` +
    `markers moved and this harness is testing nothing`}));
  process.exit(0);
}
eval(tpl.slice(i, j));

const game = (away, home, gameday, gametime_et, confidence_rank) =>
  ({away, home, gameday, gametime_et, confidence_rank});

// Real week-1 slots, transcribed from predictions/2026_week1.json.
const wed = game('NE', 'SEA', '2026-09-09', '20:20', 7);
const thu = game('SF', 'LA', '2026-09-10', '20:35', 9);
const sunEarlyA = game('TB', 'CIN', '2026-09-13', '13:00', 3);
const sunEarlyB = game('CHI', 'CAR', '2026-09-13', '13:00', 11);
const sunLate = game('ARI', 'LAC', '2026-09-13', '16:25', 5);
const mon = game('DEN', 'KC', '2026-09-14', '20:15', 4);
// The London slot: 09:30 Eastern. Sorts before the 13:00 games only because
// the hour is zero-padded, which is the whole reason a string compare is safe.
const london = game('JAX', 'MIA', '2026-09-13', '09:30', 8);
const undated = game('XX', 'YY', null, null, 2);
const dayOnly = game('ZZ', 'WW', '2026-09-13', null, 6);

const names = xs => xs.map(g => g.away + '@' + g.home);

console.log(JSON.stringify({
  keys: {
    normal: kickoffKey(sunEarlyA),
    undated: kickoffKey(undated),
    dayOnly: kickoffKey(dayOnly)
  },
  fullWeek: names([mon, sunEarlyB, wed, sunLate, thu, sunEarlyA, london].sort(byKickoff)),
  tieBreak: names([sunEarlyB, sunEarlyA].sort(byKickoff)),
  undatedSinks: names([undated, sunEarlyA, wed].sort(byKickoff)),
  allUndated: names([game('A','B',null,null,9), game('C','D',null,null,1)].sort(byKickoff)),
  dayOnlyPlacement: names([sunEarlyA, dayOnly, london].sort(byKickoff))
}));
