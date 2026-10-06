/* The NHL's pages (Stage 57). Everything below reads one JSON block,
   #nhl-data, written by src/sports/nhl/site.py from the NHL's own files.
   Times are shown in US Eastern, as the NFL board shows them, and the board
   pages by week with the week grouped by day (Mark, 2026-10-05, option C),
   with a strip of the week's days pinned above as jump links. */
const DATA = JSON.parse(document.getElementById('nhl-data').textContent);
const ET = 'America/New_York';

function escapeHtml(s){
  return String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}
function stateHtml(kind, title, text){
  return `<div class="state state--${kind}" role="status"><span class="state-title">${title}</span>${text ? `<p>${text}</p>` : ''}</div>`;
}
function pct(x, digits){ return (x * 100).toFixed(digits ?? 0) + '%'; }
/* An odds figure never rounds to a certainty it is not: 99.92% prints as
   >99%, and 0.3% as <1%. Only 0 and 1 print as 0% and 100%. */
function odds(x){
  if(x > 0 && x < 0.005) return '<1%';
  if(x < 1 && x >= 0.995) return '>99%';
  return pct(x);
}
function signed(x, digits){ const v = Number(x).toFixed(digits); return (x > 0 ? '+' : x < 0 ? '−' : '') + v.replace('-', ''); }

/* ---------- dates ----------
   A game's `day` is the league's date (YYYY-MM-DD). It is turned into a Date
   at noon UTC so no time zone can move it to the day before. */
function dayDate(day){ return new Date(day + 'T12:00:00Z'); }
function dayIso(d){ return d.toISOString().slice(0, 10); }
function mondayOf(day){
  const d = dayDate(day);
  const back = (d.getUTCDay() + 6) % 7;
  d.setUTCDate(d.getUTCDate() - back);
  return dayIso(d);
}
const FMT_DAY = new Intl.DateTimeFormat('en-US', {weekday: 'long', month: 'short', day: 'numeric', timeZone: 'UTC'});
const FMT_SHORT = new Intl.DateTimeFormat('en-US', {weekday: 'short', timeZone: 'UTC'});
const FMT_MONTHDAY = new Intl.DateTimeFormat('en-US', {month: 'short', day: 'numeric', timeZone: 'UTC'});
const FMT_TIME = new Intl.DateTimeFormat('en-US', {hour: 'numeric', minute: '2-digit', timeZone: ET});
const FMT_ET_DATE = new Intl.DateTimeFormat('en-CA', {year: 'numeric', month: '2-digit', day: '2-digit', timeZone: ET});
function todayEt(){ return FMT_ET_DATE.format(new Date()); }
function startLabel(g){
  const day = FMT_DAY.format(dayDate(g.day));
  return g.start ? `${day} · ${FMT_TIME.format(new Date(g.start))} ET` : day;
}

/* ---------- weeks ---------- */
const WEEKS = {};
DATA.games.forEach(g => { (WEEKS[mondayOf(g.day)] ||= []).push(g); });
const WEEK_KEYS = Object.keys(WEEKS).sort();
function defaultWeek(){
  const now = mondayOf(todayEt());
  if(WEEKS[now]) return now;
  const next = WEEK_KEYS.find(k => k >= now);
  return next || WEEK_KEYS[WEEK_KEYS.length - 1];
}
let currentWeek = defaultWeek();

function teamName(abbr){ return (DATA.teams[abbr] || {}).name || abbr; }
/* A table's club cell: the full name, and on a phone the three letters, so
   the odds columns fit without scrolling sideways. */
function clubCell(abbr){ return `<span class="nhl-club-full">${escapeHtml(teamName(abbr))}</span><span class="nhl-club-abbr">${escapeHtml(abbr)}</span>`; }
function logo(abbr){
  const t = DATA.teams[abbr];
  if(!t) return '';
  return document.documentElement.getAttribute('data-theme') === 'light' ? t.logo_light : t.logo;
}

/* ---------- the card ---------- */
const SERIES = {
  a:      {label: 'Model A', color: 'var(--series-a)', shape: 'circle'},
  b:      {label: 'Model B', color: 'var(--series-b)', shape: 'square'},
  market: {label: 'Market',  color: 'var(--series-c)', shape: 'triangle'},
};
const EVEN_BAND = 2, NEAR = 7, LANE = {market: -1, b: 0, a: 1};
function markerPath(shape, cx, cy, r){
  const s = r * 0.92;
  if(shape === 'square') return `<rect x="${(cx-s).toFixed(1)}" y="${(cy-s).toFixed(1)}" width="${(2*s).toFixed(1)}" height="${(2*s).toFixed(1)}" rx="1"`;
  if(shape === 'triangle') return `<polygon points="${cx},${(cy-r*1.15).toFixed(1)} ${cx+r},${(cy+r*0.75).toFixed(1)} ${cx-r},${(cy+r*0.75).toFixed(1)}"`;
  return `<circle cx="${cx}" cy="${cy}" r="${r}"`;
}
function side(pHome, g){
  if(pHome === null || pHome === undefined) return null;
  if(Math.abs(pHome - 50) < EVEN_BAND) return {team: null, pct: Math.max(pHome, 100 - pHome)};
  return pHome >= 50 ? {team: g.home, pct: pHome} : {team: g.away, pct: 100 - pHome};
}
function sideText(s){ return s.team ? `${s.team} ${Math.round(s.pct)}%` : `even (${Math.round(s.pct)}%)`; }
function lanes(vals){
  const keys = Object.keys(vals).filter(k => vals[k] !== null && vals[k] !== undefined);
  const out = {};
  keys.forEach(k => { out[k] = keys.some(o => o !== k && Math.abs(vals[o] - vals[k]) < NEAR) ? LANE[k] : 0; });
  return out;
}
function american(p){ return p > 0 ? `+${p}` : `−${Math.abs(p)}`; }
function endTeam(abbr){
  const src = logo(abbr);
  const img = src ? `<img class="card-end-logo" src="${src}" alt="" loading="lazy" referrerpolicy="no-referrer" onerror="this.style.display='none'">` : '';
  return `<span class="card-end-team">${img}${abbr}</span>`;
}
function badge(picked, result){
  if(!picked) return '<span class="pick-badge placeholder"></span>';
  const graded = result === 'correct' || result === 'wrong';
  const state = !graded ? 'picked' : (result === 'correct' ? 'correct' : 'incorrect');
  const path = state === 'incorrect' ? '<path d="M6 6l12 12M18 6L6 18"/>' : '<path d="M20 6L9 17l-5-5"/>';
  return `<span class="pick-badge ${state}"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round">${path}</svg></span>`;
}
function scoreLine(g){
  if(g.status === 'cancelled') return 'Cancelled';
  if(g.status === 'postponed') return 'Postponed';
  if(g.status === 'in_progress') return 'In progress';
  if(g.status !== 'final' || g.hs === null || g.as === null) return '';
  const extra = g.lp === 'OT' ? ' (OT)' : g.lp === 'SO' ? ' (SO)' : '';
  return `Final: ${g.away} ${g.as}, ${g.home} ${g.hs}${extra}`;
}
function goalieText(team, gl){
  if(!gl || !gl.name) return `${team} <b>none named</b>`;
  let pill;
  if(gl.basis !== 'projected') pill = '<span class="nhl-goalie unreported">Last start</span>';
  else if(gl.status === 'Confirmed') pill = '<span class="nhl-goalie confirmed">Confirmed</span>';
  else if(gl.status === 'Likely') pill = '<span class="nhl-goalie likely">Likely</span>';
  else pill = '<span class="nhl-goalie unreported">No report yet</span>';
  return `${team} <b>${escapeHtml(gl.name)}</b>${pill}`;
}
function pickedCard(g, p){
  const vals = {b: p.b === null ? null : p.b * 100, a: p.a * 100, market: p.market ? p.market.prob * 100 : null};
  const lead = vals.b !== null ? vals.b : vals.a;
  const leadLabel = vals.b !== null ? 'Model B' : 'Model A';
  const s = side(lead, g);
  const done = g.status === 'final';
  const headline = s.team
    ? `<span class="card-hl-label">${leadLabel}${done ? ' picked' : ''}</span> <b>${s.team} ${Math.round(s.pct)}%</b> <span class="card-hl-to">to win</span>`
    : `<span class="card-hl-label">${leadLabel}</span> <b>Too close to call</b> <span class="card-hl-to">· saved pick ${p.pick}</span>`;
  const ln = lanes(vals);
  const mark = k => vals[k] === null ? '' :
    `<svg class="card-mk" style="left:${vals[k]}%; top:calc(50% + ${ln[k] * 12}px)" width="12" height="12" viewBox="0 0 12 12" aria-hidden="true">${markerPath(SERIES[k].shape, 6, 6, 4.5)} fill="${SERIES[k].color}"/></svg>`;
  const key = k => vals[k] === null ? '' :
    `<span class="card-key"><svg width="12" height="12" viewBox="0 0 14 14" aria-hidden="true">${markerPath(SERIES[k].shape, 7, 7, 5)} fill="${SERIES[k].color}"/></svg>${SERIES[k].label} <b>${sideText(side(vals[k], g))}</b></span>`;
  const aria = ['b', 'market', 'a'].filter(k => vals[k] !== null).map(k => `${SERIES[k].label} ${sideText(side(vals[k], g))}`).join('. ') + '.';
  const [awayC, homeC] = p.colours;
  const graded = p.result === 'correct' || p.result === 'wrong';
  const tag = graded ? `<span class="graded-tag ${p.result === 'correct' ? 'correct' : 'incorrect'}">${p.result === 'correct' ? 'Correct' : 'Missed'}</span>`
    : (p.result === 'cancelled' ? '<span class="graded-tag tie">Cancelled</span>' : '');
  const m = p.market;
  const market = m
    ? `Market (${escapeHtml(m.book || 'sportsbook')}): ${g.away} <b>${american(m.ap)}</b> · ${g.home} <b>${american(m.hp)}</b>, so ${sideText(side(m.prob * 100, g))} with the margin out`
    : 'Market: no price was posted when the pick was saved, so Model A made it';
  const status = scoreLine(g);
  return `<div class="game-card">
    <div class="matchup-header">${g.away} <span class="at-symbol">at</span> ${g.home}</div>
    <div class="card-kickoff">${startLabel(g)}</div>
    ${status ? `<div class="nhl-card-status">${status}</div>` : ''}
    ${tag ? `<div class="game-top"><div class="tag-row">${tag}</div></div>` : ''}
    <div class="card-hl">${headline}</div>
    <div class="card-viz" role="img" aria-label="${escapeHtml(aria)}">
      <span class="card-end">${badge(p.pick === g.away, p.result)}${endTeam(g.away)}</span>
      <div class="card-scale">
        <div class="tele-bar">
          <div class="tele-bar-seg" style="width:${100 - lead}%; background:${awayC};"></div>
          <div class="tele-bar-seg" style="width:${lead}%; background:${homeC};"></div>
        </div>
        <div class="card-line"><span class="card-mid"></span><span class="card-mid-label">50%</span>${mark('a')}${mark('market')}${mark('b')}</div>
      </div>
      <span class="card-end">${badge(p.pick === g.home, p.result)}${endTeam(g.home)}</span>
    </div>
    <div class="card-keys">${key('b')}${key('market')}${key('a')}</div>
    <div class="market-ref">${market}</div>
    <div class="card-qbs">Goalies: ${goalieText(g.away, p.goalies.away)} · ${goalieText(g.home, p.goalies.home)}</div>
  </div>`;
}
const FIRST_SAVED = Object.values(DATA.picks).map(p => p.saved).filter(Boolean).sort()[0] || null;
function waitingCard(g){
  const status = scoreLine(g);
  let note;
  if(g.status === 'final' || g.status === 'in_progress') {
    note = FIRST_SAVED && g.start && g.start < FIRST_SAVED ? 'Before the first pick was saved.' : 'No pick was saved for this game.';
  } else if(g.status === 'cancelled' || g.status === 'postponed') {
    note = 'No pick: a postponed or cancelled game is never predicted.';
  } else {
    note = 'The pick is saved by the last run before puck drop (14:00 or 21:00 UTC).';
  }
  return `<div class="game-card nhl-not-saved">
    <div class="matchup-header">${g.away} <span class="at-symbol">at</span> ${g.home}</div>
    <div class="card-kickoff">${startLabel(g)}</div>
    ${status ? `<div class="nhl-card-status">${status}</div>` : ''}
    <div class="nhl-wait-note">${note}</div>
  </div>`;
}

/* ---------- the board ---------- */
function renderBoard(){
  const games = (WEEKS[currentWeek] || []).slice().sort((a, b) => (a.start || '').localeCompare(b.start || '') || a.id.localeCompare(b.id));
  const label = document.getElementById('week-step-label');
  label.textContent = `Week of ${FMT_MONTHDAY.format(dayDate(currentWeek))} · ${games.length} game${games.length === 1 ? '' : 's'}`;
  const i = WEEK_KEYS.indexOf(currentWeek);
  document.getElementById('week-prev').disabled = i <= 0;
  document.getElementById('week-next').disabled = i >= WEEK_KEYS.length - 1;
  const byDay = {};
  games.forEach(g => (byDay[g.day] ||= []).push(g));
  const days = Object.keys(byDay).sort();
  const today = todayEt();
  document.getElementById('nhl-day-strip').innerHTML = days.map(d => {
    const dd = dayDate(d);
    return `<button type="button" class="nhl-day-chip" data-day="${d}"${d === today ? ' aria-current="true"' : ''}>`
      + `<span>${FMT_SHORT.format(dd)}</span><b>${dd.getUTCDate()}</b><span>${byDay[d].length}</span></button>`;
  }).join('');
  document.querySelectorAll('.nhl-day-chip').forEach(btn => btn.addEventListener('click', () => {
    const head = document.getElementById('day-' + btn.dataset.day);
    if(head) head.scrollIntoView({behavior: 'smooth', block: 'start'});
  }));
  const grid = document.getElementById('game-grid');
  if(!games.length){
    grid.innerHTML = stateHtml('waiting', 'No games this week', '');
    return;
  }
  grid.innerHTML = days.map(d => {
    const n = byDay[d].length;
    return `<h3 class="nhl-day-head" id="day-${d}">${FMT_DAY.format(dayDate(d))}<span class="slot-count"> · ${n} game${n === 1 ? '' : 's'}</span></h3>`
      + byDay[d].map(g => DATA.picks[g.id] ? pickedCard(g, DATA.picks[g.id]) : waitingCard(g)).join('');
  }).join('');
}
function stepWeek(by){
  const i = WEEK_KEYS.indexOf(currentWeek) + by;
  if(i < 0 || i >= WEEK_KEYS.length) return;
  currentWeek = WEEK_KEYS[i];
  renderBoard();
}
document.getElementById('week-prev').addEventListener('click', () => stepWeek(-1));
document.getElementById('week-next').addEventListener('click', () => stepWeek(1));
document.addEventListener('keydown', e => {
  if(e.target.closest && e.target.closest('input, select, textarea')) return;
  if(!document.getElementById('page-board').classList.contains('active')) return;
  if(e.key === '[') stepWeek(-1);
  if(e.key === ']') stepWeek(1);
});

/* ---------- standings ---------- */
const CONFERENCES = {Eastern: ['Atlantic', 'Metropolitan'], Western: ['Central', 'Pacific']};
function renderStandings(){
  const s = DATA.standings, el = document.getElementById('standings-body');
  if(!s){
    el.innerHTML = stateHtml('waiting', 'Not simulated yet', 'The daily run simulates the season in every run that saves picks.');
    return;
  }
  const head = `<p class="nhl-lede">As of ${escapeHtml(s.as_of)}: the rest of the regular season played out ${s.simulations.toLocaleString('en-US')} times from Model A, with today&#39;s ratings held fixed. A game goes to overtime ${pct(s.overtime_share)} of the time and, once there, to a shootout ${pct(s.shootout_share_of_overtime)} of the time, as in the last two seasons. The top three of each division and two wild cards per conference make the playoffs.</p>`;
  const table = div => {
    const rows = s.teams.filter(t => t.division === div).sort((a, b) => b.projected_points - a.projected_points);
    return `<div><h3>${div}</h3><div class="table-wrap"><table class="metrics-table nhl-table"><caption class="visually-hidden">${div} division</caption>
      <thead><tr><th scope="col">Club</th><th scope="col" class="num">Points</th><th scope="col" class="num">Projected</th><th scope="col" class="num">Playoffs</th><th scope="col" class="num">Division</th></tr></thead>
      <tbody>${rows.map(t => `<tr><th scope="row">${clubCell(t.team)}</th><td class="num">${t.points_now}</td><td class="num">${t.projected_points.toFixed(1)}</td><td class="num">${odds(t.playoff_pct)}</td><td class="num">${odds(t.division_pct)}</td></tr>`).join('')}</tbody></table></div></div>`;
  };
  el.innerHTML = head + Object.entries(CONFERENCES).map(([conf, divs]) =>
    `<h2 class="section-title">${conf} Conference</h2><div class="nhl-div-grid">${divs.map(table).join('')}</div>`).join('');
}

/* ---------- ratings ---------- */
function renderRatings(){
  const r = DATA.ratings, el = document.getElementById('ratings-body');
  if(!r){ el.innerHTML = stateHtml('waiting', 'No ratings yet', 'The daily run writes them every run.'); return; }
  const teams = `<p class="nhl-lede">As of ${escapeHtml(r.as_of)}. A club&#39;s goal rating is how many goals a game better than an average club it has been, from a ridge regression of every earlier game&#39;s goal margin, recent games counting more. The shot rating is the same on shots on goal. Model A reads the difference between the two clubs in a game.</p>
    <div class="table-wrap"><table class="metrics-table nhl-table"><caption class="visually-hidden">Team ratings</caption>
    <thead><tr><th scope="col" class="num">#</th><th scope="col">Club</th><th scope="col" class="num">Goals a game</th><th scope="col" class="num">Shots a game</th></tr></thead>
    <tbody>${r.teams.map((t, i) => `<tr><td class="num">${i + 1}</td><th scope="row">${clubCell(t.team)}</th><td class="num">${signed(t.goal, 2)}</td><td class="num">${signed(t.shot, 1)}</td></tr>`).join('')}</tbody></table></div>`;
  const named = r.goalies.filter(g => g.name);
  const goalies = `<h2 class="section-title">Goalies</h2><p class="nhl-lede">Goals saved above the league&#39;s save rate per 100 shots faced, shrunk toward zero by ${Number(r.K_shots).toLocaleString('en-US')} shots, so a goalie with few shots sits near average. Listed: goalies who started this season or last, and whom a saved pick has named.</p>
    ${named.length ? `<div class="table-wrap"><table class="metrics-table nhl-table"><caption class="visually-hidden">Goalie ratings</caption>
    <thead><tr><th scope="col">Goalie</th><th scope="col" class="num">Saved per 100 shots</th><th scope="col" class="num">Shots weighed</th></tr></thead>
    <tbody>${named.map(g => `<tr><th scope="row">${escapeHtml(g.name)}</th><td class="num">${signed(g.rating * 100, 2)}</td><td class="num">${Math.round(g.weighted_shots).toLocaleString('en-US')}</td></tr>`).join('')}</tbody></table></div>`
      : stateHtml('waiting', 'No goalie named yet', 'A goalie is listed once a saved pick names him.')}`;
  el.innerHTML = teams + goalies;
}

/* ---------- calibration ----------
   How sure each pick was against how often picks that sure came true. The
   chance is the one the model that made the pick gave its side. */
const CAL_BINS = [[0.5, 0.55], [0.55, 0.6], [0.6, 0.65], [0.65, 0.7], [0.7, 1.01]];
const CAL_MIN = 30;
function pickChance(p, g){
  const home = p.by === 'model_b' && p.b !== null ? p.b : p.a;
  return p.pick === g.home ? home : 1 - home;
}
function calibrationHtml(graded){
  const rows = CAL_BINS.map(([lo, hi]) => {
    const inBin = graded.filter(x => { const c = pickChance(x.p, x.g); return c >= lo && c < hi; });
    const n = inBin.length;
    const said = n ? inBin.reduce((t, x) => t + pickChance(x.p, x.g), 0) / n : null;
    const right = n ? inBin.filter(x => x.p.result === 'correct').length / n : null;
    const label = hi > 1 ? `${Math.round(lo * 100)}% and up` : `${Math.round(lo * 100)}% to ${Math.round(hi * 100)}%`;
    return `<tr><th scope="row">${label}</th><td class="num">${n}</td><td class="num">${said === null ? '' : pct(said, 1)}</td><td class="num">${right === null ? '' : pct(right, 1)}</td></tr>`;
  }).join('');
  const thin = graded.length < CAL_MIN * CAL_BINS.length;
  return `<h2 class="section-title">How sure, and how often right</h2>
    <p class="nhl-lede">Each graded pick by the chance its model gave the side it picked. A well-calibrated model is right about as often as it says.${thin ? ` With ${graded.length} graded picks, most rows hold too few games to read: a row means little under ${CAL_MIN}.` : ''}</p>
    <div class="table-wrap"><table class="metrics-table nhl-table"><caption class="visually-hidden">Calibration of the graded picks</caption>
    <thead><tr><th scope="col">The pick's chance</th><th scope="col" class="num">Picks</th><th scope="col" class="num">Said, on average</th><th scope="col" class="num">Right</th></tr></thead>
    <tbody>${rows}</tbody></table></div>`;
}

/* ---------- accuracy ---------- */
function renderAccuracy(){
  const el = document.getElementById('accuracy-body');
  const rows = Object.entries(DATA.picks).map(([id, p]) => ({p, g: DATA.games.find(x => x.id === id)})).filter(x => x.g);
  const graded = rows.filter(x => x.p.result === 'correct' || x.p.result === 'wrong');
  if(!graded.length){
    el.innerHTML = stateHtml('waiting', 'Nothing graded yet', `${rows.length} pick${rows.length === 1 ? '' : 's'} saved. A pick is graded once its game is final; a cancelled game is never counted.`);
    return;
  }
  const right = graded.filter(x => x.p.result === 'correct').length;
  const list = graded.sort((a, b) => (b.g.start || '').localeCompare(a.g.start || ''));
  el.innerHTML = `<p class="nhl-lede"><b>${right} of ${graded.length}</b> picks right (${pct(right / graded.length, 1)}). The pick is Model B&#39;s where the market had a price when it was saved, Model A&#39;s otherwise. The forward test is judged on log loss once 100 games are graded; see Checking the AI&#39;s work.</p>
    ${calibrationHtml(graded)}
    <h2 class="section-title">Every graded pick</h2>
    <div class="table-wrap"><table class="metrics-table nhl-table"><caption class="visually-hidden">Graded picks</caption>
    <thead><tr><th scope="col">Date</th><th scope="col">Game</th><th scope="col">Pick</th><th scope="col">Model</th><th scope="col">Result</th></tr></thead>
    <tbody>${list.map(x => `<tr><td>${FMT_MONTHDAY.format(dayDate(x.g.day))}</td><td>${x.g.away} at ${x.g.home}</td><td>${x.p.pick}</td><td>${x.p.by === 'model_b' ? 'Model B' : 'Model A'}</td><td><span class="graded-tag ${x.p.result === 'correct' ? 'correct' : 'incorrect'}">${x.p.result === 'correct' ? 'Correct' : 'Missed'}</span></td></tr>`).join('')}</tbody></table></div>`;
}

/* ---------- teams ---------- */
let currentTeam = null;
try{ currentTeam = localStorage.getItem('nhl:team'); }catch(e){}
function teamGames(abbr){
  return DATA.games.filter(g => g.home === abbr || g.away === abbr)
    .sort((a, b) => (a.start || a.day).localeCompare(b.start || b.day));
}
function renderTeams(){
  const select = document.getElementById('team-select');
  const clubs = Object.keys(DATA.teams).sort((a, b) => teamName(a).localeCompare(teamName(b)));
  if(!currentTeam || !DATA.teams[currentTeam]) currentTeam = clubs[0];
  if(!select.options.length){
    select.innerHTML = clubs.map(c => `<option value="${c}">${escapeHtml(teamName(c))}</option>`).join('');
    select.addEventListener('change', () => {
      currentTeam = select.value;
      try{ localStorage.setItem('nhl:team', currentTeam); }catch(e){}
      renderTeams();
    });
  }
  select.value = currentTeam;
  const t = currentTeam, el = document.getElementById('teams-body');
  const board = DATA.ratings, st = DATA.standings;
  const rated = board ? board.teams.findIndex(x => x.team === t) : -1;
  const rating = rated >= 0 ? board.teams[rated] : null;
  const odds_ = st ? st.teams.find(x => x.team === t) : null;
  const facts = [
    rating ? `Goal rating <b>${signed(rating.goal, 2)}</b> a game (${rated + 1} of ${board.teams.length}), shot rating <b>${signed(rating.shot, 1)}</b>.` : 'No ratings yet.',
    odds_ ? `${odds_.points_now} points; projected <b>${odds_.projected_points.toFixed(1)}</b>, playoffs <b>${odds(odds_.playoff_pct)}</b>, the ${escapeHtml(odds_.division)} title ${odds(odds_.division_pct)}.` : 'Standings odds not simulated yet.',
  ];
  const games = teamGames(t).filter(g => g.status === 'final' || DATA.picks[g.id]);
  const row = g => {
    const home = g.home === t, opp = home ? g.away : g.home, p = DATA.picks[g.id];
    const score = g.status === 'final' && g.hs !== null ? `${home ? g.hs : g.as}-${home ? g.as : g.hs}${g.lp === 'OT' ? ' OT' : g.lp === 'SO' ? ' SO' : ''}` : '';
    const won = g.status === 'final' && g.hs !== null ? ((home ? g.hs > g.as : g.as > g.hs) ? 'W' : 'L') : '';
    const graded = p && (p.result === 'correct' || p.result === 'wrong');
    const tag = graded ? `<span class="graded-tag ${p.result === 'correct' ? 'correct' : 'incorrect'}">${p.result === 'correct' ? 'Correct' : 'Missed'}</span>` : (p ? 'Not final' : '');
    return `<tr><td>${FMT_MONTHDAY.format(dayDate(g.day))}</td><td>${home ? 'vs' : 'at'} ${opp}</td><td>${won} ${score}</td><td>${p ? p.pick : 'No pick'}</td><td>${tag}</td></tr>`;
  };
  el.innerHTML = `<h2 class="section-title">${escapeHtml(teamName(t))}</h2><p class="nhl-lede">${facts.join(' ')}</p>
    ${games.length ? `<div class="table-wrap"><table class="metrics-table nhl-table"><caption class="visually-hidden">${escapeHtml(teamName(t))}: games so far</caption>
    <thead><tr><th scope="col">Date</th><th scope="col">Opponent</th><th scope="col">Result</th><th scope="col">Pick</th><th scope="col">Graded</th></tr></thead>
    <tbody>${games.map(row).join('')}</tbody></table></div>` : stateHtml('waiting', 'No games played yet', '')}`;
}

/* ---------- what's changed ---------- */
function renderChanges(){
  const el = document.getElementById('changes-body');
  el.innerHTML = (DATA.changes || []).map(c => `<div class="nhl-change"><span class="nhl-change-date">${escapeHtml(c.date)}</span><h3>${escapeHtml(c.title)}</h3><p class="nhl-lede">${escapeHtml(c.text)}</p></div>`).join('')
    || stateHtml('waiting', 'Nothing recorded yet', '');
}

/* ---------- model lab ---------- */
const QUESTION = {
  H1: 'Does Model A beat knowing only how often the home team wins?',
  H2: 'Does adding the market to Model A improve it?',
  H3: 'Does Model B beat the market alone?',
  M1: 'What does the goalie term add? (a measurement, not a test)',
};
function renderModelLab(){
  const b = DATA.backtest, el = document.getElementById('modellab-body');
  if(!b){ el.innerHTML = stateHtml('waiting', 'No backtest results', ''); return; }
  const rows = Object.entries(b.questions).map(([id, q]) => `<tr><th scope="row">${id}</th><td>${QUESTION[id] || ''}</td><td class="num">${signed(q.diff, 4)}</td><td class="num">[${signed(q.low, 4)}, ${signed(q.high, 4)}]</td><td>${q.label ? `<b>${q.label}</b>` : 'a measurement'}</td></tr>`).join('');
  const s = b.scores;
  el.innerHTML = `<p class="nhl-lede">Registered before any NHL model was fitted (<code>experiments/nhl/stage56/registry.json</code>), tuned on 2022-23 and 2023-24 (H = ${b.H_days} days, K = ${Number(b.K_shots).toLocaleString('en-US')} shots), and answered once on 2024-25 and 2025-26. A difference below zero means the first model forecast better. Each interval is a paired day-block bootstrap at ${pct(b.questions.H1.level, 2)}; a result counts only when the interval excludes zero.</p>
    <div class="table-wrap"><table class="metrics-table nhl-table"><caption class="visually-hidden">The backtest's questions</caption>
    <thead><tr><th scope="col">#</th><th scope="col">Question</th><th scope="col" class="num">Log loss difference</th><th scope="col" class="num">Interval</th><th scope="col">Label</th></tr></thead>
    <tbody>${rows}</tbody></table></div>
    <h2 class="section-title">Log loss on the held-out seasons</h2>
    <div class="table-wrap"><table class="metrics-table nhl-table"><caption class="visually-hidden">Scores</caption>
    <thead><tr><th scope="col">Forecast</th><th scope="col" class="num">Games</th><th scope="col" class="num">Log loss</th><th scope="col" class="num">Accuracy</th></tr></thead>
    <tbody>${[['Model A', s.model_a], ['Base rate', s.base_rate], ['Model B', s.model_b], ['Market', s.market]].filter(r => r[1]).map(([n, v]) => `<tr><th scope="row">${n}</th><td class="num">${v.games}</td><td class="num">${v.log_loss.toFixed(4)}</td><td class="num">${pct(v.accuracy, 1)}</td></tr>`).join('')}</tbody></table></div>
    <p class="nhl-lede">Accuracy is printed, never decides: at this many games it moves by a game or two between machines, where log loss does not.</p>`;
}

/* ---------- methodology ---------- */
function renderMethod(){
  const b = DATA.backtest;
  document.getElementById('method-body').innerHTML = `
    <p class="nhl-lede"><b>Model A</b> reads three numbers about a game: the two clubs&#39; goal ratings, their shot ratings, and their starting goalies&#39; ratings, each as a difference, home minus away. Ratings come from every game since 2015-16 that ended before the game&#39;s day, recent games counting more (half as much every ${b ? b.H_days : 120} days). A logistic regression turns the three into a home-win probability, refitted before every game day.</p>
    <p class="nhl-lede"><b>Model B</b> is Model A plus the market&#39;s home-win probability: the two-way moneyline with the bookmaker&#39;s margin taken out evenly. Where a game has no price when its pick is saved, Model A makes the pick.</p>
    <p class="nhl-lede"><b>A pick</b> is saved once, by the last run before puck drop (14:00 or 21:00 UTC), with the projected goalies Daily Faceoff lists and the market price at that moment, and is never rewritten. A goalie no roster matches falls back to his club&#39;s last starter, and the card says so. Only a game that is final is graded; a postponed or cancelled one never counts.</p>
    <p class="nhl-lede"><b>What the backtest knew that the live pick does not:</b> it used each game&#39;s actual starting goalie, from the box score. The live pick knows only the projection. The registration measures that gap once there are games to measure it on.</p>`;
}

/* ---------- checking ---------- */
function renderReliability(){
  const d = DATA.drift, rule = DATA.drift_rule, el = document.getElementById('reliability-body');
  const saved = Object.keys(DATA.picks).length;
  const min = rule ? rule.rule.min_games : 100;
  const status = !d || !d.games
    ? `No pick has been graded yet, so the drift check has nothing to test.`
    : d.games < min
      ? `${d.games} of the ${min} graded games the drift check needs before it can flag. Model A&#39;s mean log loss so far is ${d.mean_log_loss.toFixed(4)}, against ${d.baseline.toFixed(4)} in the backtest.`
      : (d.flagged ? `<b>Flagged.</b> Model A&#39;s log loss over ${d.games} games is significantly above its backtest. An issue is open.` : `Not flagged: Model A&#39;s log loss over ${d.games} games is ${d.mean_log_loss.toFixed(4)}, against ${d.baseline.toFixed(4)} in the backtest.`);
  el.innerHTML = `<h2 class="section-title">The drift check</h2><p class="nhl-lede">${status}</p>
    <p class="nhl-lede">The rule was registered before the season (<code>experiments/nhl/stage58/registry.json</code>): it flags when the one-sided ${rule ? pct(rule.rule.one_sided_level) : '95%'} lower bound of Model A&#39;s log loss is above the backtest&#39;s ${rule ? rule.baseline.value.toFixed(4) : ''}, once ${min} games are graded.</p>
    <h2 class="section-title">What runs unattended</h2>
    <p class="nhl-lede">The daily run at 14:00 and 21:00 UTC saves and grades the picks; a nightly canary at 06:40 UTC reads every source it needs and writes nothing. Either one failing opens a GitHub issue titled &ldquo;NHL: &hellip;&rdquo;. ${saved} pick${saved === 1 ? '' : 's'} saved so far this season.</p>`;
}

/* ---------- pages, theme ---------- */
function showPage(name){
  document.querySelectorAll('.page').forEach(p => p.classList.toggle('active', p.id === 'page-' + name));
  document.querySelectorAll('.nav-btn').forEach(b => {
    const on = b.dataset.page === name;
    b.classList.toggle('active', on);
    if(on) b.setAttribute('aria-current', 'page'); else b.removeAttribute('aria-current');
  });
  window.scrollTo(0, 0);
}
document.querySelectorAll('.nav-btn').forEach(b => b.addEventListener('click', () => showPage(b.dataset.page)));
function currentTheme(){ return document.documentElement.getAttribute('data-theme') === 'light' ? 'light' : 'dark'; }
function themeLabel(){ const l = document.getElementById('theme-toggle-label'); if(l) l.textContent = currentTheme() === 'light' ? 'Dark mode' : 'Light mode'; }
document.querySelectorAll('#theme-toggle, .topbar-theme').forEach(btn => btn.addEventListener('click', () => {
  const next = currentTheme() === 'light' ? 'dark' : 'light';
  if(next === 'light') document.documentElement.setAttribute('data-theme', 'light');
  else document.documentElement.removeAttribute('data-theme');
  try{ localStorage.setItem('nhl:theme', next); }catch(e){}
  themeLabel();
  renderBoard();
}));

document.getElementById('board-updated').textContent = `Updated ${new Date(DATA.built_utc).toLocaleString('en-US', {timeZone: ET, month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit'})} ET`;
document.getElementById('built-line').textContent = `Schedule as of ${DATA.schedule_as_of || 'unknown'}`;
themeLabel();
renderBoard();
renderStandings();
renderRatings();
renderAccuracy();
renderModelLab();
renderMethod();
renderReliability();
renderTeams();
renderChanges();
document.body.classList.remove('is-entering');
