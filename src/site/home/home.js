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

function nhlCard(f){
  if(!f || !f.built) return notBuilt('nhl', 'NHL');
  const games = (f.games || []).map(([start, st]) => ({t: Date.parse(start), st}));
  const today = games.filter(g => dayKey(g.t) === dayKey(NOW));
  const upcoming = games.filter(g => g.t > NOW - 3 * HOUR && g.st !== 'final');
  let status, rows = [[f.record.label, record(f.record)]];
  if(today.length){
    const evening = new Date(Math.min(...today.map(g => g.t))).getHours() >= 17;
    status = {text:`${today.length} game${today.length === 1 ? '' : 's'} ${evening ? 'tonight' : 'today'}`, cls:'is-live'};
    rows.push(['First puck drop', clock(Math.min(...today.map(g => g.t)))]);
  } else if(upcoming.length){
    const next = Math.min(...upcoming.map(g => g.t));
    const n = games.filter(g => dayKey(g.t) === dayKey(next)).length;
    status = {text:`Next: ${n} game${n === 1 ? '' : 's'} ${weekday(next)}`};
    rows.push(['First puck drop', when(next)]);
  } else {
    status = {text:'No games scheduled', cls:'is-quiet'};
  }
  return card('nhl', 'NHL', 'nhl/', status, 'Picks lock game by game', rows, 'Open the NHL board');
}

function nbaCard(f){
  if(!f || !f.built) return notBuilt('nba', 'NBA');
  return card('nba', 'NBA', 'nba/', {text:'Backtest only', cls:'is-quiet'},
              'No live picks this season', [], 'Open the NBA backtest');
}

document.getElementById('home-cards').innerHTML = nflCard(HOME.nfl) + nhlCard(HOME.nhl) + nbaCard(HOME.nba);
