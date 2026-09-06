/*
 * Executes the dashboard's real share-link functions and reports what they do.
 *
 * The point is that this does NOT reimplement the encoding. It lifts the
 * actual source out of dashboard_template.html and runs it, so the test can
 * fail when the shipped code changes -- which a Python-side reimplementation
 * could never do, and which grepping the template for strings cannot do
 * either. Those greps prove the text is present; this proves it works.
 *
 * Driven by tests/test_share_link.py, which parses the JSON on stdout.
 */
const fs = require('fs');
const path = require('path');

const TEMPLATE = path.join(__dirname, '..', 'src', 'dashboard_template.html');
const tpl = fs.readFileSync(TEMPLATE, 'utf8');

const START = 'const SHARE_VERSION';
const END = 'function copyShareLink';
const i = tpl.indexOf(START), j = tpl.indexOf(END);
if (i === -1 || j === -1 || j <= i) {
  console.log(JSON.stringify({fatal:
    `could not locate the share-link block between ${START!==undefined?START:''} and ${END} ` +
    `(start=${i}, end=${j}) -- the markers moved and this harness is testing nothing`}));
  process.exit(0);
}
const src = tpl.slice(i, j);
for (const needed of ['scheduleFingerprint', 'encodeSharedPicks', 'decodeSharedPicks']) {
  if (!src.includes('function ' + needed)) {
    console.log(JSON.stringify({fatal: `extracted block has no ${needed}()`}));
    process.exit(0);
  }
}

// Stubs are passed in as parameters rather than globals, so the extracted
// source runs against exactly the two things it actually depends on.
let currentPicks = {};
const WEEK = '2026_week1';
const baseGames = [
  {home: 'NE',  away: 'SEA'},
  {home: 'SF',  away: 'LA'},
  {home: 'CHI', away: 'CAR'},
  {home: 'TB',  away: 'CIN'},
];
const mkWeeks = (games) => ({[WEEK]: {games}});

function api(games) {
  const make = new Function('weeks', 'loadMyPicks',
    src + '\nreturn {scheduleFingerprint, encodeSharedPicks, decodeSharedPicks, SHARE_VERSION};');
  return make(mkWeeks(games), () => currentPicks);
}

const results = {};
const record = (name, fn) => {
  try { results[name] = fn(); }
  catch (e) { results[name] = {threw: String(e && e.message || e)}; }
};

const SENDER = {
  [`${WEEK}|NE|SEA`]:  'NE',
  [`${WEEK}|SF|LA`]:   'LA',
  [`${WEEK}|CHI|CAR`]: 'CHI',
};

record('round_trip', () => {
  currentPicks = {...SENDER};
  const a = api(baseGames);
  const enc = a.encodeSharedPicks(WEEK);
  const dec = a.decodeSharedPicks(enc.token);
  return {token: enc.token, picked: enc.picked,
          decoded: dec.picks, error: dec.error || null,
          matches: JSON.stringify(dec.picks) === JSON.stringify(SENDER)};
});

record('no_picks_yields_no_link', () => {
  currentPicks = {};
  return {token: api(baseGames).encodeSharedPicks(WEEK)};
});

record('token_stays_short', () => {
  currentPicks = {...SENDER};
  return {length: api(baseGames).encodeSharedPicks(WEEK).token.length};
});

record('tampered_fingerprint_refused', () => {
  currentPicks = {...SENDER};
  const a = api(baseGames);
  const t = a.encodeSharedPicks(WEEK).token.split('~');
  t[3] = t[3] === 'zzzz' ? 'yyyy' : 'zzzz';
  return a.decodeSharedPicks(t.join('~'));
});

record('truncated_bits_refused', () => {
  currentPicks = {...SENDER};
  const a = api(baseGames);
  const t = a.encodeSharedPicks(WEEK).token.split('~');
  t[2] = t[2].slice(0, -1);
  return a.decodeSharedPicks(t.join('~'));
});

record('wrong_version_refused', () => {
  currentPicks = {...SENDER};
  const a = api(baseGames);
  const t = a.encodeSharedPicks(WEEK).token.split('~');
  t[0] = '9';
  return a.decodeSharedPicks(t.join('~'));
});

record('unknown_week_refused', () => {
  currentPicks = {...SENDER};
  const a = api(baseGames);
  const t = a.encodeSharedPicks(WEEK).token.split('~');
  t[1] = '2026_week99';
  return a.decodeSharedPicks(t.join('~'));
});

record('malformed_token_refused', () => {
  currentPicks = {...SENDER};
  return api(baseGames).decodeSharedPicks('not-a-real-token');
});

// The case the fingerprint exists for, and the one no amount of length
// checking would catch: the SAME number of games in a DIFFERENT order.
// Decoding positionally here would hand every pick to the wrong fixture and
// look completely normal doing it.
record('reordered_schedule_refused', () => {
  currentPicks = {...SENDER};
  const sender = api(baseGames);
  const token = sender.encodeSharedPicks(WEEK).token;
  const shuffled = [baseGames[2], baseGames[0], baseGames[3], baseGames[1]];
  const receiver = api(shuffled);
  const dec = receiver.decodeSharedPicks(token);
  return {error: dec.error || null,
          would_have_been: dec.picks || null,
          same_length: shuffled.length === baseGames.length};
});

// A swapped home/away on one fixture is the subtlest version of the same
// problem -- the game "exists" either way, but the pick would flip sides.
record('flipped_home_away_refused', () => {
  currentPicks = {...SENDER};
  const sender = api(baseGames);
  const token = sender.encodeSharedPicks(WEEK).token;
  const flipped = baseGames.map((g, k) => k === 1 ? {home: g.away, away: g.home} : g);
  return api(flipped).decodeSharedPicks(token);
});

console.log(JSON.stringify(results, null, 2));
