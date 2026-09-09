/*
 * Executes the Week Board's real "why is this team ahead" sentence code.
 *
 * These sentences are generated from signed numbers, and every sign in them is
 * invisible when wrong. "The betting line agrees" is exactly as plausible a
 * sentence as "the betting line disagrees" -- it reads fine, it is grammatical,
 * and it is on every card. The first version of whyMarketSentence() had the
 * spread convention backwards and shipped confidently wrong text on all
 * sixteen games; nothing in the diff looked wrong and the suite was green.
 *
 * The convention, which tests/team_dive_harness.js already documented:
 * spread_line is the HOME line, positive when the home team is favoured. The
 * card displays it negated ("Vegas line: LAC -10.5"), which is the football
 * convention and the reason it is easy to invert.
 *
 * Runs the shipped functions rather than matching strings in the template, for
 * the same reason as the team-dive and share-link harnesses: matching strings
 * proves the text exists, not that it is right.
 *
 * Driven by tests/test_why_words.py.
 */
const fs = require('fs');
const path = require('path');

const TEMPLATE = path.join(__dirname, '..', 'src', 'dashboard_template.html');
const tpl = fs.readFileSync(TEMPLATE, 'utf8');

const START = 'const WHY_IN_WORDS = {';
const END = 'function whyRow(';
const i = tpl.indexOf(START), j = tpl.indexOf(END);
if (i === -1 || j === -1 || j <= i) {
  console.log(JSON.stringify({fatal:
    `could not extract the why-sentence block (start=${i}, end=${j}) -- the ` +
    `markers moved and this harness is testing nothing`}));
  process.exit(0);
}
const src = tpl.slice(i, j);
for (const needed of ['function whySentence', 'function whyMarketSentence', 'function whyParts']) {
  if (!src.includes(needed)) {
    console.log(JSON.stringify({fatal: `extracted block has no ${needed}()`}));
    process.exit(0);
  }
}

eval(src);

function strip(html){
  return html.replace(/<[^>]+>/g, '').replace(/\s+/g, ' ').trim();
}

// Deliberately asymmetric numbers, so a sign that silently does nothing shows.
const QB_HEAVY = {off_matchup: 0.02, def_matchup: 0.03, qb_matchup: 0.90, qb_change: 0};

const cases = {
  // Home favoured, one factor dominating. Contributions are signed toward
  // home, so all-positive means all pointing at the home team.
  home_dominant: strip(whySentence({
    home: 'KC', away: 'DEN', fbA_home: 78.0, why: QB_HEAVY})),

  // Same magnitudes, mirrored. Away favoured means every contribution must be
  // read the other way round -- this is where a missing flip hides.
  away_dominant: strip(whySentence({
    home: 'KC', away: 'DEN', fbA_home: 22.0,
    why: {off_matchup: -0.02, def_matchup: -0.03, qb_matchup: -0.90, qb_change: 0}})),

  // The favourite is ahead overall while the biggest single factor points at
  // the underdog. The sentence must not quietly drop that.
  counterweight: strip(whySentence({
    home: 'KC', away: 'DEN', fbA_home: 60.0,
    why: {off_matchup: -0.30, def_matchup: 0.40, qb_matchup: 0.35, qb_change: 0}})),

  // Two comparable factors: neither should be promoted to "almost entirely".
  shared: strip(whySentence({
    home: 'KC', away: 'DEN', fbA_home: 60.0,
    why: {off_matchup: 0.30, def_matchup: 0.28, qb_matchup: 0.02, qb_change: 0}})),

  // Nothing meaningful in it at all.
  flat: strip(whySentence({
    home: 'KC', away: 'DEN', fbA_home: 50.5,
    why: {off_matchup: 0.01, def_matchup: 0.01, qb_matchup: 0.01, qb_change: 0}})),

  // --- the market sentence, where the sign bug lived ---

  // Model likes home; spread_line positive = home favoured. Agreement.
  market_agree_home: strip(whyMarketSentence({
    home: 'SEA', away: 'NE', fbA_home: 65.0, spread: 3.5, why: QB_HEAVY})),

  // Model likes away; spread_line positive = HOME favoured. Disagreement, and
  // the line's favourite is the home team. This is the real ARI @ LAC card:
  // Model A had the away side at 80.5% while the line had the home side by
  // 10.5, and the first version reported that as agreement.
  market_disagree_home_favoured: strip(whyMarketSentence({
    home: 'LAC', away: 'ARI', fbA_home: 19.5, spread: 10.5, why: QB_HEAVY})),

  // Negative spread_line = away favoured, and the model agrees.
  market_agree_away: strip(whyMarketSentence({
    home: 'KC', away: 'DEN', fbA_home: 30.0, spread: -3.0, why: QB_HEAVY})),

  // No line at all: say nothing rather than guess.
  market_absent: strip(whyMarketSentence({
    home: 'KC', away: 'DEN', fbA_home: 60.0, spread: null, why: QB_HEAVY})),

  // No contributions recorded: say nothing rather than invent a reason.
  no_why: strip(whySentence({home: 'KC', away: 'DEN', fbA_home: 60.0, why: null})),
};

console.log(JSON.stringify(cases, null, 2));
