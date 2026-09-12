/*
 * Executes the My Picks card's two shipped builders: kickoffLabel and
 * pickButton.
 *
 * kickoffLabel is the one that needs running rather than reading. It converts
 * a 24-hour Eastern time into words, and every failure mode produces a
 * plausible-looking string: 20:20 rendered as "8:20 AM", or midnight as
 * "0:00 PM", or the whole thing silently carrying the reader's timezone
 * because somebody built a Date. None of those look wrong on a card.
 *
 * teamLogo is STUBBED to `LOGO:<abbr>` on purpose. What matters here is that
 * pickButton passes the right team through to it; the real URL builder is a
 * lookup table tested by the page loading, and stubbing makes the assertion
 * about wiring rather than about ESPN's path format.
 *
 * Driven by tests/test_picks_card.py.
 */
const fs = require('fs');
const path = require('path');

const TEMPLATE = path.join(__dirname, '..', 'src', 'dashboard_template.html');
const tpl = fs.readFileSync(TEMPLATE, 'utf8');

const START = 'function pickButton(';
const END = 'function renderGames(';
const i = tpl.indexOf(START), j = tpl.indexOf(END);
if (i === -1 || j === -1 || j <= i) {
  console.log(JSON.stringify({fatal:
    `could not extract the picks-card builders (start=${i}, end=${j}) -- the ` +
    `markers moved and this harness is testing nothing`}));
  process.exit(0);
}

function teamLogo(abbr){ return 'LOGO:' + abbr; }
eval(tpl.slice(i, j));

const g = (gameday, gametime_et, weekday) => ({away: 'NE', home: 'SEA',
                                              gameday, gametime_et, weekday});

console.log(JSON.stringify({
  evening: kickoffLabel(g('2026-09-09', '20:20', 'Wednesday')),
  earlyAfternoon: kickoffLabel(g('2026-09-13', '13:00', 'Sunday')),
  london: kickoffLabel(g('2026-09-13', '09:30', 'Sunday')),
  noon: kickoffLabel(g('2026-09-13', '12:00', 'Sunday')),
  midnight: kickoffLabel(g('2026-09-13', '00:15', 'Sunday')),
  dayOnly: kickoffLabel(g('2026-09-13', null, 'Sunday')),
  noWeekday: kickoffLabel(g('2026-09-13', '13:00', null)),
  undated: kickoffLabel(g(null, null, null)),
  buttonUnpicked: pickButton('NE', undefined),
  buttonPicked: pickButton('NE', 'NE'),
  buttonOther: pickButton('SEA', 'NE')
}));
