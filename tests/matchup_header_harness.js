/*
 * Executes the shipped matchupHeader() rather than matching strings.
 *
 * Same reason as tests/why_words_harness.js and tests/team_dive_harness.js:
 * matching a string in the template proves the text exists, not that the
 * function produces it. This one exists because the markup it builds used to
 * be written twice -- once in renderGames() and once in renderPicksGrid() --
 * and the `@` separator was changed in one of them and not the other. A test
 * that greps for the right markup would have passed on that repository.
 *
 * Driven by tests/test_game_card_header.py.
 */
const fs = require('fs');
const path = require('path');

const TEMPLATE = path.join(__dirname, '..', 'src', 'pipeline', 'dashboard_template.html');
const tpl = fs.readFileSync(TEMPLATE, 'utf8');

const START = 'function matchupHeader(';
const END = 'function renderGames(';
const i = tpl.indexOf(START), j = tpl.indexOf(END);
if (i === -1 || j === -1 || j <= i) {
  console.log(JSON.stringify({fatal:
    `could not extract matchupHeader (start=${i}, end=${j}) -- the markers ` +
    `moved and this harness is testing nothing`}));
  process.exit(0);
}
eval(tpl.slice(i, j));

// The logo URL comes from teamLogo() and its ESPN_CODE table, which sit
// earlier in the script; barTeam() (defined after matchupHeader) uses them.
for (const [name, re] of [['ESPN_CODE', /const ESPN_CODE = \{[\s\S]*?\r?\n\};/],
                          ['teamLogo', /function teamLogo\([\s\S]*?\r?\n\}/]]) {
  const m = tpl.match(re);
  if (!m) {
    console.log(JSON.stringify({fatal: `could not extract ${name} -- this harness is testing nothing`}));
    process.exit(0);
  }
  eval(m[0].replace(/^const /, 'var '));
}

const g = {away: 'NE', home: 'SEA'};
console.log(JSON.stringify({
  board: matchupHeader(g),
  picks: matchupHeader(g, 'quiet'),
  // A variant must not be able to smuggle in a second class list.
  undefinedVariant: matchupHeader(g, undefined),
  emptyVariant: matchupHeader(g, ''),
  // The Week Board's logos, at the ends of Model B's bar since 2026-09-28.
  bar: barTeam('NE')
}));
