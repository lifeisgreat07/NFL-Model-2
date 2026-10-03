/*
 * Executes the shipped teamDiveDefault() -- the team Team Deep-Dive opens on
 * when no #team/<code> link names one (Stage 19).
 *
 * Driven by tests/test_team_dive_default.py.
 */
const fs = require('fs');
const path = require('path');

const { readTemplate } = require('./template_source');
const tpl = readTemplate().replace(/\r\n/g, '\n');

const START = 'function teamDiveDefault(';
const i = tpl.indexOf(START);
const j = i === -1 ? -1 : tpl.indexOf('\n}\n', i);
if (i === -1 || j === -1) {
  console.log(JSON.stringify({fatal:
    `could not extract teamDiveDefault (start=${i}, end=${j}) -- the ` +
    `function moved and this harness is testing nothing`}));
  process.exit(0);
}
const teamDiveDefault = new Function(tpl.slice(i, j + 2) + '\nreturn teamDiveDefault;')();

const NAMES = {ARI: 'Arizona Cardinals', BUF: 'Buffalo Bills', KC: 'Kansas City Chiefs', LA: 'LA Rams'};
const RATED = [
  {team: 'LA', rank: 2},
  {team: 'BUF', rank: 1},
  {team: 'KC', rank: 3},
  {team: 'ARI', rank: 4},
];

console.log(JSON.stringify({
  top_rated: teamDiveDefault(NAMES, RATED),
  // Order in the ratings file must not matter: rank does.
  top_rated_reversed: teamDiveDefault(NAMES, RATED.slice().reverse()),
  no_ratings: teamDiveDefault(NAMES, []),
  ratings_missing: teamDiveDefault(NAMES, undefined),
  no_rank_one: teamDiveDefault(NAMES, [{team: 'LA', rank: 2}]),
  rank_one_without_history: teamDiveDefault(NAMES, [{team: 'NYJ', rank: 1}]),
  // A name that sorts first even though its code does not.
  alphabetical_by_name: teamDiveDefault({ZZ: 'Aardvarks', AA: 'Zebras'}, []),
}));
