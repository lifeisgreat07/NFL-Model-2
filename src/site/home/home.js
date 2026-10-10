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

// Each sport's icon, as at the top left of its page (Stage 62.2: the football,
// puck P3 and ball B2 of the "Sportalytics Icons and Wordmark" canvas).
const ICON_PARTS = {
  nfl: '<g transform="rotate(-28 10 10)"><ellipse cx="10" cy="10" rx="8.6" ry="5.2"/>'
     + '<path stroke-width="1.2" d="M5.6 10h8.8M7 8.1v3.8M9 8.1v3.8M11 8.1v3.8M13 8.1v3.8"/></g>',
  nhl: '<g transform="rotate(-28 10 10)"><ellipse cx="10" cy="8.4" rx="8.4" ry="3.2"/>'
     + '<path d="M1.6 8.4v3.2a8.4 3.2 0 0 0 16.8 0V8.4"/></g>',
  nba: '<g transform="rotate(-28 10 10)"><circle cx="10" cy="10" r="8.4"/>'
     + '<path stroke-width="1.2" d="M10 1.6v16.8M1.6 10h16.8M4.1 4c2.5 2.3 3 9.2 0 12M15.9 4c-2.5 2.3-3 9.2 0 12"/></g>',
};
function icon(sport){
  const parts = ICON_PARTS[sport];
  return parts ? '<svg class="home-icon" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.4" '
    + 'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + parts + '</svg>' : '';
}

function card(sport, name, href, status, big, rows, go){
  const kv = rows.length
    ? `<dl class="home-kv">${rows.map(([k, v]) => `<dt>${esc(k)}</dt><dd>${esc(v)}</dd>`).join('')}</dl>` : '';
  const inner = `<div class="home-card-top"><span class="home-sport">${icon(sport)}${esc(name)}</span>`
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

/* Before a day sport's first pick is saved (the NBA until opening night,
   Stage 65), the card says when picks start, read from the schedule's
   first game, instead of a record of "—" (Stage 68 item 6). It used to
   wait for no games within two weeks, which the schedule never allowed. */
function beforeFirstPick(f){
  const first = f.first_game ? Date.parse(f.first_game) : NaN;
  return !f.picks && first > NOW - 3 * HOUR ? first : null;
}
function nbaCard(f){
  if(!f || !f.built) return notBuilt('nba', 'NBA');
  const d = dayStatus(f, 'tip-off');
  const first = beforeFirstPick(f);
  if(first !== null){
    const day = new Date(first).toLocaleDateString([], {weekday:'short', month:'short', day:'numeric'});
    return card('nba', 'NBA', 'nba/', {text:`Live from ${day}`}, 'Picks lock game by game',
                [['First tip-off', when(first)]], 'Open the NBA board');
  }
  return card('nba', 'NBA', 'nba/', d.status || {text:'No games scheduled', cls:'is-quiet'},
              'Picks lock game by game', d.rows, 'Open the NBA board');
}

document.getElementById('home-cards').innerHTML = nflCard(HOME.nfl) + nhlCard(HOME.nhl) + nbaCard(HOME.nba);

// The hero's one action (Stage 68 item 34, option A2): the sport whose next
// game starts first, from the same facts the cards read.
const SPORT_NAME = {nfl:'NFL', nhl:'NHL', nba:'NBA'};
function nextGame(){
  const ahead = [];
  const n = HOME.nfl;
  if(n && n.built) (n.kickoffs || []).map(Date.parse).filter(t => t > NOW).forEach(t => ahead.push(['nfl', t]));
  for(const s of ['nhl', 'nba']){
    const f = HOME[s];
    if(f && f.built) (f.games || []).forEach(([st, status]) => { const t = Date.parse(st); if(t > NOW && status !== 'final') ahead.push([s, t]); });
  }
  ahead.sort((a, b) => a[1] - b[1]);
  return ahead[0] || null;
}
(function(){
  const box = document.getElementById('home-cta');
  if(!box) return;
  const g = nextGame();
  if(!g){ box.remove(); return; }
  const [s, t] = g;
  const tonight = dayKey(t) === dayKey(NOW);
  const label = s === 'nfl' ? `See the NFL's Week ${HOME.nfl.week} picks`
    : `See ${tonight ? "tonight's" : weekday(t) + "'s"} ${SPORT_NAME[s]} picks`;
  box.innerHTML = `<a class="home-cta-btn" href="${s}/">${esc(label)} <span aria-hidden="true">→</span></a>`
    + `<span class="home-cta-when">Next game ${esc(tonight ? clock(t) : when(t))}</span>`;
})();

// The scoreboard above the cards (Stage 66, option A): each sport's record
// from the same facts the cards read, and what every pick has in common.
function tile(label, value, sub, words){
  return `<div class="home-tile"><span>${esc(label)}</span><b${words ? ' class="is-words"' : ''}>${esc(value)}</b>`
    + `<small>${esc(sub)}</small></div>`;
}
function scoreTile(f, label){
  if(!f || !f.built) return tile(label, '\u2013', 'page not built this time');
  const n = f.record.won + f.record.lost;
  return tile(label, record(f.record), n ? `after ${n} game${n === 1 ? '' : 's'}` : 'no graded games yet');
}
document.getElementById('home-score').innerHTML = scoreTile(HOME.nfl, 'NFL, Model B')
  + scoreTile(HOME.nhl, 'NHL, picks') + tile('Every pick', 'saved before the start', 'checked after', true);

// The theme button: the same choice, under the same key, as every sport's page.
(function(){
  const btn = document.querySelector('.home-theme');
  if(!btn) return;
  const light = () => document.documentElement.getAttribute('data-theme') === 'light';
  const label = () => btn.setAttribute('aria-label', light() ? 'Switch to the dark theme' : 'Switch to the light theme');
  label();
  btn.addEventListener('click', () => {
    if(light()) document.documentElement.removeAttribute('data-theme');
    else document.documentElement.setAttribute('data-theme', 'light');
    try{ localStorage.setItem('site:theme', light() ? 'light' : 'dark'); }catch(e){}
    label();
  });
})();

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
