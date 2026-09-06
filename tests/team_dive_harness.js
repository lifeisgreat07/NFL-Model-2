/*
 * Executes the Team Deep-Dive drill-down's real perspective-flipping code.
 *
 * Everything in `weeks` is stored from the HOME side: fbA_home and mktB_home
 * are home win probabilities, spread_line is the home line (positive when
 * home is favoured), actual_home_win is the home result, and why{} holds
 * contributions toward the home team. The drill-down presents all of it from
 * ONE selected team's point of view, so every field has to flip when that
 * team is away.
 *
 * A wrong flip is invisible. 55.7% is as plausible a number as 44.3%, and a
 * page showing the opponent's win probability under your team's name looks
 * completely normal. That is why this runs the shipped function instead of
 * matching strings in the template.
 *
 * Driven by tests/test_team_dive.py.
 */
const fs = require('fs');
const path = require('path');

const TEMPLATE = path.join(__dirname, '..', 'src', 'dashboard_template.html');
const tpl = fs.readFileSync(TEMPLATE, 'utf8');

const START = 'function asBool(v){';
const END = 'const WHY_LABELS';
const i = tpl.indexOf(START), j = tpl.indexOf(END);
if (i === -1 || j === -1 || j <= i) {
  console.log(JSON.stringify({fatal:
    `could not extract the drill-down block (start=${i}, end=${j}) -- the ` +
    `markers moved and this harness is testing nothing`}));
  process.exit(0);
}
const src = tpl.slice(i, j);
if (!src.includes('function teamGamesFor')) {
  console.log(JSON.stringify({fatal: 'extracted block has no teamGamesFor()'}));
  process.exit(0);
}

// One completed game and one unplayed one, with deliberately asymmetric
// numbers so a flip that silently does nothing is visible.
const WEEKS = {
  '2025_week10': {games: [{
    home: 'DEN', away: 'LV',
    fbA_home: 63.7, mktB_home: 80.6, spread: -9.5,
    graded: true, actual_home_win: 1,        // 1, not true -- as the files store it
    model_a_correct: 1, model_b_correct: 0,
    why: {off_matchup: 0.0131, def_matchup: -0.1022, qb_matchup: 0.25},
  }]},
  '2026_week1': {games: [{
    home: 'KC', away: 'DEN',
    fbA_home: 64.9, mktB_home: 64.9, spread: 3.0,
    graded: false, actual_home_win: null,
    model_a_correct: null, model_b_correct: null,
    why: null,
  }]},
};

function api() {
  const make = new Function('weeks', 'weekKeysSorted', 'weekLabel',
    src + '\nreturn {asBool, teamGamesFor};');
  return make(WEEKS, Object.keys(WEEKS), k => k);
}

const {teamGamesFor, asBool} = api();
const results = {};

const den = teamGamesFor('DEN');
const lv = teamGamesFor('LV');
const kc = teamGamesFor('KC');

const denHome = den.find(g => g.weekKey === '2025_week10');
const lvAway = lv.find(g => g.weekKey === '2025_week10');
const denAway = den.find(g => g.weekKey === '2026_week1');
const kcHome = kc.find(g => g.weekKey === '2026_week1');

results.selection = {
  den_game_count: den.length,
  lv_game_count: lv.length,
  den_sees_both_home_and_away: den.some(g => g.isHome) && den.some(g => !g.isHome),
};

results.probability_flip = {
  home_probA: denHome.probA, away_probA: lvAway.probA,
  sums_to_100: Math.abs(denHome.probA + lvAway.probA - 100) < 1e-9,
  home_unchanged: denHome.probA === WEEKS['2025_week10'].games[0].fbA_home,
  away_probB_sums: Math.abs(denHome.probB + lvAway.probB - 100) < 1e-9,
};

results.line_flip = {
  home_line: denHome.line, away_line: lvAway.line,
  inverts: denHome.line === -lvAway.line,
  home_matches_raw: denHome.line === WEEKS['2025_week10'].games[0].spread,
};

results.result_flip = {
  home_won: denHome.won, away_won: lvAway.won,
  opposite: denHome.won !== lvAway.won,
  home_won_is_true: denHome.won === true,
};

results.why_negation = {
  home: denHome.why, away: lvAway.why,
  all_negate: Object.keys(denHome.why).every(
    k => Math.abs(denHome.why[k] + lvAway.why[k]) < 1e-12),
};

// The 1/0-vs-true/false trap: the graded files store integers, and a
// downstream `=== true` against a 1 is quietly false.
results.correctness_normalised = {
  a_raw: WEEKS['2025_week10'].games[0].model_a_correct,
  b_raw: WEEKS['2025_week10'].games[0].model_b_correct,
  a_is_strict_true: denHome.modelACorrect === true,
  b_is_strict_false: denHome.modelBCorrect === false,
  ungraded_stays_null: denAway.modelACorrect === null && denAway.won === null,
  asBool_null: asBool(null), asBool_undefined: asBool(undefined),
  asBool_one: asBool(1), asBool_zero: asBool(0),
};

results.ungraded = {
  won: denAway.won,
  probs_still_flipped: Math.abs(denAway.probA + kcHome.probA - 100) < 1e-9,
};

console.log(JSON.stringify(results, null, 2));
