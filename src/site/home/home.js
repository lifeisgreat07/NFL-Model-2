// The home page's cards (Stage 59, option A). The build hands over each
// sport's facts; the status is worked out here against the visitor's own
// clock, so "tonight" is tonight where they are.
const HOME = JSON.parse(document.getElementById('home-data').textContent);
const NOW = Date.now();
const HOUR = 3600 * 1000;

function esc(s){ return String(s).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c])); }
function dayKey(t){ const d = new Date(t); return d.getFullYear() + '-' + d.getMonth() + '-' + d.getDate(); }
function clock(t){ return new Date(t).toLocaleTimeString([], {hour:'numeric', minute:'2-digit'}); }
function weekday(t){ return new Date(t).toLocaleDateString([], {weekday:'short'}); }
function when(t){ return weekday(t) + ' ' + clock(t); }
function record(r){ return r && (r.won + r.lost) > 0 ? `${r.won}–${r.lost}` : '—'; }

function card(sport, name, href, status, big, rows, go){
  const kv = rows.length
    ? `<dl class="home-kv">${rows.map(([k, v]) => `<dt>${esc(k)}</dt><dd>${esc(v)}</dd>`).join('')}</dl>` : '';
  const inner = `<div class="home-card-top"><span class="home-sport">${esc(name)}</span>`
    + `<span class="home-status${status.cls ? ' ' + status.cls : ''}">${esc(status.text)}</span></div>`
    + `<div class="home-big">${esc(big)}</div>${kv}`;
  // A sport with no page in this build gets a card that links nowhere.
  return href
    ? `<a class="home-card" href="${href}" data-sport="${sport}">${inner}<span class="home-go">${esc(go)} →</span></a>`
    : `<div class="home-card is-unbuilt" data-sport="${sport}">${inner}</div>`;
}

function notBuilt(sport, name){
  return card(sport, name, null, {text:'Not built yet', cls:'is-quiet'},
              `The ${name}'s page was not built this time`, [], '');
}

function nflCard(f){
  if(!f || !f.built) return notBuilt('nfl', 'NFL');
  const kicks = (f.kickoffs || []).map(k => Date.parse(k));
  const ahead = kicks.filter(k => k > NOW);
  let status, big;
  if(ahead.length){
    status = {text:`Week ${f.week} locked`};
    const first = new Date(Math.min(...kicks)), last = new Date(Math.max(...kicks));
    big = `${kicks.length} games, ${weekday(first)} to ${weekday(last)}`;
  } else if(f.preview_week){
    status = {text:`Week ${f.preview_week} preview`};
    big = `Week ${f.week} is played; Week ${f.preview_week}'s picks lock before its first kickoff`;
  } else {
    status = {text:`Week ${f.week} played`, cls:'is-quiet'};
    big = `Week ${f.week + 1}'s picks are made on Tuesday and locked before kickoff`;
  }
  const rows = [[f.record.label, record(f.record)]];
  if(ahead.length) rows.push(['Next kickoff', when(Math.min(...ahead))]);
  return card('nfl', 'NFL', 'nfl/', status, big, rows, 'Open the NFL board');
}

/* A sport that locks game by game (the NHL; the NBA from Stage 65): today's
   games, or the next day with games, and the season's record. `start` names
   the moment a game begins in that sport ("puck drop", "tip-off"). */
function dayStatus(f, start){
  const games = (f.games || []).map(([s, st]) => ({t: Date.parse(s), st}));
  const today = games.filter(g => dayKey(g.t) === dayKey(NOW));
  const upcoming = games.filter(g => g.t > NOW - 3 * HOUR && g.st !== 'final');
  let status, rows = [[f.record.label, record(f.record)]];
  if(today.length){
    const evening = new Date(Math.min(...today.map(g => g.t))).getHours() >= 17;
    status = {text:`${today.length} game${today.length === 1 ? '' : 's'} ${evening ? 'tonight' : 'today'}`, cls:'is-live'};
    rows.push([`First ${start}`, clock(Math.min(...today.map(g => g.t)))]);
  } else if(upcoming.length){
    const next = Math.min(...upcoming.map(g => g.t));
    const n = games.filter(g => dayKey(g.t) === dayKey(next)).length;
    status = {text:`Next: ${n} game${n === 1 ? '' : 's'} ${weekday(next)}`};
    rows.push([`First ${start}`, when(next)]);
  } else {
    status = null;
  }
  return {status, rows};
}

function nhlCard(f){
  if(!f || !f.built) return notBuilt('nhl', 'NHL');
  const d = dayStatus(f, 'puck drop');
  return card('nhl', 'NHL', 'nhl/', d.status || {text:'No games scheduled', cls:'is-quiet'},
              'Picks lock game by game', d.rows, 'Open the NHL board');
}

/* The NBA's live picks start on opening night (Stage 65). Until the daily
   run has written the season's schedule, the card says when they start. */
const NBA_OPENING = Date.parse('2026-10-20T23:00:00Z');
function nbaCard(f){
  if(!f || !f.built) return notBuilt('nba', 'NBA');
  const d = dayStatus(f, 'tip-off');
  const status = d.status || (NOW < NBA_OPENING
    ? {text:`Live from ${new Date(NBA_OPENING).toLocaleDateString([], {weekday:'short', month:'short', day:'numeric'})}`}
    : {text:'No games scheduled', cls:'is-quiet'});
  return card('nba', 'NBA', 'nba/', status, 'Picks lock game by game', d.rows, 'Open the NBA board');
}

document.getElementById('home-cards').innerHTML = nflCard(HOME.nfl) + nhlCard(HOME.nhl) + nbaCard(HOME.nba);

// A sport with no page in this build has no pill to follow either: the link
// would open GitHub's 404.
for(const sport of ['nfl', 'nhl', 'nba']){
  if(HOME[sport] && HOME[sport].built) continue;
  const pill = document.querySelector(`.home-switch a[href="${sport}/"]`);
  if(!pill) continue;
  const span = document.createElement('span');
  span.className = 'is-unbuilt';
  span.setAttribute('aria-disabled', 'true');
  span.textContent = pill.textContent;
  pill.replaceWith(span);
}
