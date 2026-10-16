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
/* On the home page as on the NBA's board (nba.js tipSet): a tip-off time
   is printed unless ESPN says it is not set yet. The build lists those
   starts (home.py `unset`). Stage 77 item 33 guessed from the hour, which
   hid opening night's real 3 PM BOS at DET (found 2026-10-15). */
const UNSET_TIPS = new Set(((HOME.nba || {}).unset || []).map(s => Date.parse(s)));
function tipSet(t){ return !UNSET_TIPS.has(t); }
function tipClock(t){ return tipSet(t) ? clock(t) : 'time TBD'; }
function tipWhen(t){ return tipSet(t) ? when(t) : `${weekday(t)} · time TBD`; }
/* Which moments can be placeholders: only the NBA's tip-off. */
const PLACEHOLDER_TIMES = {'tip-off': [tipClock, tipWhen]};
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

/* Stage 80 item 52 (the 2026-10-13 audit's F2): the best pick on each card,
   "COL 57% over DAL · 8:30 PM", from the slate the build hands over
   (home.py slate()): the strongest saved pick among `games` not started. */
function bestPick(games, timeOf){
  const ahead = games.filter(r => (r.k === 'pick' || r.k === 'lean') && Date.parse(r.t) > NOW);
  if(!ahead.length) return null;
  const r = ahead.reduce((x, y) => y.c > x.c ? y : x);
  return `${r.p} ${r.c}% over ${r.p === r.h ? r.a : r.h} · ${timeOf(Date.parse(r.t))}`;
}
const START_SPORT = {'puck drop': 'nhl', 'tip-off': 'nba'};
function slateOf(sport){ return (HOME.slate || []).filter(r => r.s === sport); }

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
    /* Stage 77 item 30 (H2): once the week has begun, how much is left. The
       home has each game's kickoff, not its result, so it counts kickoffs. */
    const started = kicks.length - ahead.length;
    status = {text:`Week ${f.week} locked${started ? ` · ${started} kicked off, ${ahead.length} to play` : ''}`};
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
  /* The locked week's strongest pick still to play, or before it the
     preview's strongest lean. */
  const kind = ahead.length ? 'pick' : 'lean', wk = ahead.length ? f.week : f.preview_week;
  const best = wk ? bestPick(slateOf('nfl').filter(r => r.k === kind), when) : null;
  if(best) rows.push([`Strongest ${kind}, Week ${wk}`, best]);
  return card('nfl', 'NFL', 'nfl/', status, big, rows, 'Open the NFL board');
}

/* A sport that locks game by game (the NHL; the NBA from Stage 65): today's
   games, or the next day with games, and the season's record. `start` names
   the moment a game begins in that sport ("puck drop", "tip-off"). */
function dayStatus(f, start){
  const [atClock, atWhen] = PLACEHOLDER_TIMES[start] || [clock, when];
  const games = (f.games || []).map(([s, st]) => ({t: Date.parse(s), st}));
  const today = games.filter(g => dayKey(g.t) === dayKey(NOW));
  const upcoming = games.filter(g => g.t > NOW - 3 * HOUR && g.st !== 'final');
  let status, rows = [[f.record.label, record(f.record)]];
  if(today.length){
    const first = Math.min(...today.map(g => g.t));
    const evening = new Date(first).getHours() >= 17;
    /* Stage 77 item 12 (the 2026-10-13 audit's copy fix 1): how many of
       today's games are over, and once the first has started, when the next
       one does, not the first again. */
    const finals = today.filter(g => g.st === 'final').length;
    const done = !finals ? '' : finals === today.length ? ' · all final' : ` · ${finals} final, ${today.length - finals} to play`;
    status = {text:`${today.length} game${today.length === 1 ? '' : 's'} ${evening ? 'tonight' : 'today'}${done}`, cls:'is-live'};
    const later = today.filter(g => g.t > NOW && g.st !== 'final').map(g => g.t);
    if(first > NOW || !later.length) rows.push([`First ${start}`, atClock(first)]);
    else rows.push([`Next ${start}`, atClock(Math.min(...later))]);
    const best = bestPick(slateOf(START_SPORT[start]).filter(r => r.k === 'pick' && dayKey(Date.parse(r.t)) === dayKey(NOW)), atClock);
    if(best) rows.push([`Best pick ${evening ? 'tonight' : 'today'}`, best]);
  } else if(upcoming.length){
    const next = Math.min(...upcoming.map(g => g.t));
    const n = games.filter(g => dayKey(g.t) === dayKey(next)).length;
    status = {text:`Next: ${n} game${n === 1 ? '' : 's'} ${weekday(next)}`};
    rows.push([`First ${start}`, atWhen(next)]);
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
                [['First tip-off', tipWhen(first)]], 'Open the NBA board');
  }
  return card('nba', 'NBA', 'nba/', d.status || {text:'No games scheduled', cls:'is-quiet'},
              'Picks lock game by game', d.rows, 'Open the NBA board');
}

document.getElementById('home-cards').innerHTML = nflCard(HOME.nfl) + nhlCard(HOME.nhl) + nbaCard(HOME.nba);
/* Stage 77 item 30 (H2): "Updated ... ET", as on each sport's page. */
function updatedText(iso){
  if(!iso) return '';
  return `Updated ${new Date(iso).toLocaleString('en-US', {timeZone: 'America/New_York', month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit'})} ET`;
}
document.getElementById('home-updated').textContent = updatedText(HOME.built_utc);

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
    + `<span class="home-cta-when">Next game ${esc(s === 'nba' ? (tonight ? tipClock(t) : tipWhen(t)) : (tonight ? clock(t) : when(t)))}</span>`;
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
/* Stage 77 item 13 (the 2026-10-13 audit's copy fix 2): "NFL picks" and "NHL
   picks", and the third tile counts what the site has graded, every sport's
   record added up, where it said "Every pick / saved before the start". */
function gradedTile(sports){
  const built = sports.filter(f => f && f.built);
  const graded = built.reduce((t, f) => t + (f.record ? f.record.won + f.record.lost : 0), 0);
  return tile(`${built.length} sport${built.length === 1 ? '' : 's'}`, String(graded), `pick${graded === 1 ? '' : 's'} graded`);
}
document.getElementById('home-score').innerHTML = scoreTile(HOME.nfl, 'NFL picks')
  + scoreTile(HOME.nhl, 'NHL picks') + gradedTile([HOME.nfl, HOME.nhl, HOME.nba]);

/* Stage 80 item 54 (the 2026-10-13 audit's F8): "Since your last visit".
   Each visit leaves each sport's record in this browser; the next one says
   what was graded in between: "Since Sunday: NFL 10 of 14 right, NHL 5 of
   7 right." Only sports with new graded games are named, and a record that
   went down (a new season) names nothing. The session keeps the sentence it
   showed, so a reload does not take it away while the stored record moves
   on. Nothing leaves the browser. */
const SINCE_KEY = 'site:lastVisit', SINCE_SHOWN = 'site:sinceShown';
function sinceLabel(at, now){
  const midnight = t => { const d = new Date(t); d.setHours(0, 0, 0, 0); return d.getTime(); };
  const days = Math.round((midnight(now) - midnight(at)) / (24 * HOUR));
  if(days <= 0) return 'earlier today';
  if(days === 1) return 'yesterday';
  if(days < 7) return new Date(at).toLocaleDateString('en-US', {weekday: 'long'});
  return new Date(at).toLocaleDateString('en-US', {month: 'short', day: 'numeric'});
}
function sinceText(prev, sports, now){
  if(!prev || !prev.rec || !prev.at) return '';
  const parts = [];
  for(const s of ['nfl', 'nhl', 'nba']){
    const f = sports[s], p = prev.rec[s];
    if(!f || !f.built || !f.record || !p) continue;
    const won = f.record.won - p[0], lost = f.record.lost - p[1];
    if(won < 0 || lost < 0 || won + lost === 0) continue;
    parts.push(`${SPORT_NAME[s]} ${won} of ${won + lost} right`);
  }
  return parts.length ? `Since ${sinceLabel(prev.at, now)}: ${parts.join(', ')}.` : '';
}
function sinceSnapshot(sports, now){
  const rec = {};
  for(const s of ['nfl', 'nhl', 'nba']){
    const f = sports[s];
    if(f && f.built && f.record) rec[s] = [f.record.won, f.record.lost];
  }
  return {at: now, rec};
}
(function(){
  const el = document.getElementById('home-since');
  if(!el) return;
  const sports = {nfl: HOME.nfl, nhl: HOME.nhl, nba: HOME.nba};
  let text = null;
  try{ text = sessionStorage.getItem(SINCE_SHOWN); }catch(e){}
  if(text === null){
    let prev = null;
    try{ prev = JSON.parse(localStorage.getItem(SINCE_KEY) || 'null'); }catch(e){}
    text = sinceText(prev, sports, NOW);
    try{
      sessionStorage.setItem(SINCE_SHOWN, text);
      localStorage.setItem(SINCE_KEY, JSON.stringify(sinceSnapshot(sports, NOW)));
    }catch(e){}
  }
  el.textContent = text;
})();

/* Stage 80 item 53 (the 2026-10-13 audit's F7): "Your teams tonight". The
   teams starred on any sport's page (site:favs, src/core/favs.js) and
   today's games they play, from the build's slate, each a link to its
   board with its pick. Nothing is shown before a team is starred. */
function yoursText(r){
  const pick = r.k === 'pick' ? `${r.p} ${r.c}%${r.e ? ' · even' : ''}` : r.k === 'lean' ? `leans ${r.p} ${r.c}%` : 'pick to come';
  const t = Date.parse(r.t);
  return `${r.a} @ ${r.h} ${r.s === 'nba' ? tipClock(t) : clock(t)}, ${pick}`;
}
function yoursHtml(slate, favs, now){
  const mine = slate.filter(r => {
    const list = Array.isArray(favs[r.s]) ? favs[r.s] : [];
    const t = Date.parse(r.t);
    return (list.includes(r.a) || list.includes(r.h)) && dayKey(t) === dayKey(now) && t > now - 3 * HOUR;
  });
  if(!mine.length) return '';
  const evening = mine.every(r => new Date(Date.parse(r.t)).getHours() >= 17);
  return `<b>Your teams ${evening ? 'tonight' : 'today'}:</b> `
    + mine.map(r => `<a href="${r.s}/">${esc(yoursText(r))}</a>`).join('; ');
}
(function(){
  const el = document.getElementById('home-yours');
  if(!el) return;
  let favs = {};
  try{ favs = JSON.parse(localStorage.getItem('site:favs') || '{}') || {}; }catch(e){}
  const html = yoursHtml(HOME.slate || [], favs, NOW);
  el.innerHTML = html;
  el.hidden = !html;
})();

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
