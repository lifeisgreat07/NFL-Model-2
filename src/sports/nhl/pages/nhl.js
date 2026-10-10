/* The NHL's pages (Stage 57). Everything below reads one JSON block,
   #nhl-data, written by src/sports/nhl/site.py from the NHL's own files.
   Times are shown in US Eastern, as the NFL board shows them, and the board
   pages by week with the week grouped by day (Mark, 2026-10-05, option C),
   with a strip of the week's days pinned above as jump links. */
const DATA = JSON.parse(document.getElementById('nhl-data').textContent);
const ET = 'America/New_York';

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

/* ---------- tables that scroll ----------
   The NFL board's rule (src/dashboard/app.js, Stage 12), copied until
   Stage 53 moves it into the shared shell: a table wider than its box gets
   the box into the Tab order as a named region, so a keyboard user can
   scroll it (WCAG 2.1.1; axe's scrollable-region-focusable). A box that
   fits leaves the Tab order again, and the shared stylesheet's .fits
   applies. Only what this added is removed (data-scroll-stop lists it). */
const FOCUSABLE_INSIDE = 'a[href], button, input, select, textarea, [tabindex]:not([tabindex="-1"])';
function scrollStopLabel(el){
  const cap = el.querySelector('caption');
  let heading = null;
  for(let node = el; node && !heading && !node.matches('.page'); node = node.parentElement){
    for(let sib = node.previousElementSibling; sib; sib = sib.previousElementSibling){
      if(sib.matches('h2, h3, h4')){ heading = sib; break; }
    }
  }
  const name = (cap || heading) ? (cap || heading).textContent.trim().replace(/\s+/g, ' ') : '';
  return (name ? `Table: ${name}` : 'Table') + ', scrolls sideways';
}
function setScrollStop(el, scrolls){
  const attrs = {tabindex: () => '0', role: () => 'region', 'aria-label': scrollStopLabel};
  const marked = el.hasAttribute('data-scroll-stop');
  const added = marked ? el.getAttribute('data-scroll-stop').split(' ').filter(Boolean) : [];
  if(scrolls && !el.querySelector(FOCUSABLE_INSIDE)){
    for(const [name, value] of Object.entries(attrs)){
      if(added.includes(name)) el.setAttribute(name, value(el));
      else if(!el.hasAttribute(name)){ el.setAttribute(name, value(el)); added.push(name); }
    }
    el.setAttribute('data-scroll-stop', added.join(' '));
  } else if(marked){
    added.forEach(name => el.removeAttribute(name));
    el.removeAttribute('data-scroll-stop');
  }
}
function fitTables(){
  document.querySelectorAll('.table-wrap').forEach(w => {
    const t = w.querySelector('table');
    if(!t || !w.clientWidth) return;
    const fits = t.offsetWidth <= w.clientWidth;
    w.classList.toggle('fits', fits);
    setScrollStop(w, !fits);
  });
}
(function(){
  let queued = false;
  const later = () => { if(queued) return; queued = true; requestAnimationFrame(() => { queued = false; fitTables(); }); };
  window.addEventListener('resize', later);
  if(document.fonts && document.fonts.ready) document.fonts.ready.then(later);
  const root = document.querySelector('main');
  if(root && window.MutationObserver){
    new MutationObserver(later).observe(root, {childList: true, subtree: true, attributes: true, attributeFilter: ['class']});
  }
  later();
})();

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
/* Team codes reach this page from the league's feed and are drawn into its
   HTML in many places. The schedule build refuses a code that is not two to
   four capital letters; the page checks again before drawing any (Stage 68
   item 8), so a bad one shows as "?" and never as markup. */
const TEAM_CODE = /^[A-Z]{2,4}$/;
function cleanCode(c){ return TEAM_CODE.test(String(c)) ? c : '?'; }
DATA.games.forEach(g => { g.home = cleanCode(g.home); g.away = cleanCode(g.away); });
Object.values(DATA.picks || {}).forEach(p => { if(p.pick) p.pick = cleanCode(p.pick); });
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
    : (p.result === 'cancelled' ? '<span class="graded-tag tie">Cancelled</span>' : lockedTag(g, p));
  const m = p.market;
  const market = m
    ? `Market (${escapeHtml(m.book || 'sportsbook')}): ${g.away} <b>${american(m.ap)}</b> · ${g.home} <b>${american(m.hp)}</b>, so ${sideText(side(m.prob * 100, g))} with the margin out`
    : 'Market: no price was posted when the pick was saved, so Model A made it';
  const status = scoreLine(g);
  return `<div class="game-card">
    <div class="matchup-header">${g.away} <span class="at-symbol">at</span> ${g.home}</div>
    <div class="card-kickoff">${startLabel(g)}</div>
    ${status ? `<div class="nhl-card-status">${status}</div>` : ''}
    ${resultLine(g, p)}
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
    ${proofLine(g, p, DATA.proof)}
  </div>`;
}
/* Stage 68 item 20: the commit that put this pick in the public history,
   when, and whether that was before the start (src/core/pick_proof.py). */
function proofLine(g, p, proof){
  const pr = (proof || {})[g.id];
  if(!pr || !/^[0-9a-f]{40}$/.test(pr.sha)) return '';
  const before = g.start && pr.committed < g.start;
  const link = `<a href="https://github.com/lifeisgreat07/NFL-Model-2/commit/${pr.sha}" rel="noopener">${pr.sha.slice(0, 7)}</a>`;
  const later = pr.changes ? ` Changed ${pr.changes === 1 ? 'once' : `${pr.changes} times`} since.` : '';
  return `<div class="nhl-proof">In the public history ${escapeHtml(whenEt(new Date(pr.committed)))} (commit ${link}), ${before ? 'before the start' : '<b>after the start</b>'}.${later}</div>`;
}
/* Stage 63: what a card says about its pick's state. A saved pick is a
   locked pick: the daily run writes a game's pick file only when it locks
   it, at the last run before puck drop (src/sports/nhl/lock.py). */
const LOCK_RUN_HOURS_UTC = [14, 21];        // lock.py's RUNS_UTC, every day
const LOCK_SLACK_MS = 60 * 60 * 1000;       // lock.py's SLACK
/* The run that will save a game starting at `startIso`: the first run before
   the start whose next run, plus the slack, would come too late. The same
   rule as GameLock.decide; tests/test_nhl_board_states.py runs both. */
function lockRunFor(startIso){
  const start = Date.parse(startIso);
  if(Number.isNaN(start)) return null;
  const runs = [];
  const day0 = new Date(start - 3 * 86400000);
  for(let d = 0; d <= 4; d++){
    LOCK_RUN_HOURS_UTC.forEach(h => runs.push(Date.UTC(day0.getUTCFullYear(), day0.getUTCMonth(), day0.getUTCDate() + d, h)));
  }
  runs.sort((x, y) => x - y);
  for(let i = 0; i < runs.length - 1; i++){
    if(runs[i] >= start) break;
    if(start < runs[i + 1] + LOCK_SLACK_MS) return new Date(runs[i]);
  }
  return null;
}
const FMT_WHEN = new Intl.DateTimeFormat('en-US', {weekday: 'short', hour: 'numeric', minute: '2-digit', timeZone: ET});
function whenEt(d){ return `${FMT_WHEN.format(d)} ET`; }
/* An unsaved game that has not started: when its pick will lock, or that
   the run that should have locked it has passed without saving it. */
function lockNote(g, nowMs){
  const run = g.start ? lockRunFor(g.start) : null;
  if(!run) return 'The pick locks at the last run before puck drop (14:00 or 21:00 UTC).';
  if(run.getTime() + LOCK_SLACK_MS < nowMs) return `The pick was due to lock ${whenEt(run)} and has not been saved yet.`;
  return `The pick locks ${whenEt(run)}, at the last run before puck drop.`;
}
/* A model's side is the side of 50% its chance for the home team falls on,
   the rule the saved pick follows (exactly 50% picks the home team). */
function modelSide(prob, g){ return prob === null || prob === undefined ? null : (prob >= 0.5 ? g.home : g.away); }
function winnerOf(g){
  if(g.status !== 'final' || g.hs === null || g.hs === undefined || g.as === null || g.as === undefined || g.hs === g.as) return null;
  return g.hs > g.as ? g.home : g.away;
}
/* A played game: the winner, and each model's side with right or wrong. */
function resultLine(g, p){
  const won = winnerOf(g);
  if(!won) return '';
  const one = (label, prob) => {
    const s = modelSide(prob, g);
    return s === null ? '' : `<span class="nhl-model-result">${label} ${s}, <b>${s === won ? 'right' : 'wrong'}</b></span>`;
  };
  const market = p.market ? one('Market', p.market.prob) : '';
  return `<div class="nhl-result-line">Winner <b>${won}</b>${one('Model B', p.b)}${one('Model A', p.a)}${market}</div>`;
}
/* A saved pick on a game not yet final: locked, and when. */
function lockedTag(g, p){
  if(g.status === 'final' || g.status === 'cancelled' || g.status === 'postponed') return '';
  const when = p.saved ? ` ${whenEt(new Date(p.saved))}` : '';
  return `<span class="graded-tag nhl-locked">Locked${when}</span>`;
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
    note = lockNote(g, Date.now());
  }
  return `<div class="game-card nhl-not-saved">
    <div class="matchup-header">${g.away} <span class="at-symbol">at</span> ${g.home}</div>
    <div class="card-kickoff">${startLabel(g)}</div>
    ${status ? `<div class="nhl-card-status">${status}</div>` : ''}
    <div class="nhl-wait-note">${note}</div>
  </div>`;
}

/* ---------- the board: a day at a time (Stage 64) ----------
   Mark chose it from the rendered "NHL Day Board Options" (2026-10-09):
   option A's strip of the week's seven days, opening on today, with option
   B's compact rows. A row is the time, the game, the pick and the result; a
   tap opens the full card below it (both models, the market, the lock time
   and the goalies). The NFL keeps its week view: it plays by the week. */
const FMT_HOUR = new Intl.DateTimeFormat('en-US', {hour: 'numeric', minute: '2-digit', timeZone: ET});
function weekDays(week){
  const out = [];
  const d = dayDate(week);
  for(let i = 0; i < 7; i++){ out.push(dayIso(d)); d.setUTCDate(d.getUTCDate() + 1); }
  return out;
}
function defaultDay(week, games, today){
  if(weekDays(week).includes(today)) return today;
  const days = [...new Set(games.map(g => g.day))].sort();
  return days[0] || week;
}
/* What a row says in its last column, and its class. */
function rowResult(g, p, nowMs){
  if(g.status === 'postponed' || g.status === 'cancelled') return {text: g.status === 'postponed' ? 'Postponed' : 'Cancelled', cls: 'off'};
  if(p){
    if(p.result === 'correct') return {text: 'Correct', cls: 'right'};
    if(p.result === 'wrong') return {text: 'Missed', cls: 'wrong'};
    return {text: g.status === 'final' ? 'Grading' : 'Locked', cls: 'locked'};
  }
  if(g.status === 'final' || g.status === 'in_progress') return {text: 'No pick', cls: 'off'};
  const run = g.start ? lockRunFor(g.start) : null;
  if(!run) return {text: 'Not locked', cls: 'open'};
  if(run.getTime() + LOCK_SLACK_MS < nowMs) return {text: 'Late', cls: 'open'};
  return {text: `Locks ${FMT_HOUR.format(run).replace(':00', '')}`, cls: 'open'};
}
/* The pick in a row: the saved side, with the chance the leading model gave it. */
function rowPick(g, p){
  if(!p) return '—';
  const lead = p.b !== null && p.b !== undefined ? p.b : p.a;
  const pct = p.pick === g.home ? lead : 1 - lead;
  return `${p.pick} ${Math.round(pct * 100)}%`;
}
function rowTime(g){
  if(g.status === 'final') return g.lp === 'OT' ? 'Final/OT' : g.lp === 'SO' ? 'Final/SO' : 'Final';
  if(g.status === 'in_progress') return 'Live';
  return g.start ? FMT_HOUR.format(new Date(g.start)) : 'TBD';
}
function rowGame(g){
  const won = winnerOf(g);
  const has = g.status === 'final' && g.hs !== null && g.hs !== undefined && g.as !== null && g.as !== undefined;
  const team = (abbr, score) => {
    const text = has ? `${abbr} ${score}` : abbr;
    return abbr === won ? `<b>${text}</b>` : text;
  };
  return `${team(g.away, g.as)} <span class="at-symbol">@</span> ${team(g.home, g.hs)}`;
}
/* "3 games, 1 of 1 right so far", from the saved picks' grades. */
function daySummary(games, picks){
  const n = games.length;
  if(!n) return 'No games this day.';
  const graded = games.map(g => picks[g.id]).filter(p => p && (p.result === 'correct' || p.result === 'wrong'));
  const right = graded.filter(p => p.result === 'correct').length;
  let s = `${n} game${n === 1 ? '' : 's'}`;
  if(graded.length) s += `, ${right} of ${graded.length} right so far`;
  else {
    const locked = games.filter(g => picks[g.id]).length;
    if(locked) s += `, ${locked} locked`;
  }
  return s;
}
const CHEVRON = '<svg class="nhl-row-chev" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 9l6 6 6-6"/></svg>';
function rowHtml(g, p, nowMs){
  const r = rowResult(g, p, nowMs);
  const id = `nhl-detail-${g.id}`;
  return `<li class="nhl-row-item">
    <button type="button" class="nhl-row" aria-expanded="false" aria-controls="${id}">
      <span class="nhl-row-time">${rowTime(g)}</span>
      <span class="nhl-row-game">${rowGame(g)}</span>
      <span class="nhl-row-pick">${rowPick(g, p)}</span>
      <span class="nhl-row-result ${r.cls}">${r.text}</span>${CHEVRON}
    </button>
    <div class="nhl-row-detail" id="${id}" hidden>${p ? pickedCard(g, p) : waitingCard(g)}</div>
  </li>`;
}
let currentDay = null;
function renderBoard(){
  const games = (WEEKS[currentWeek] || []).slice().sort((a, b) => (a.start || '').localeCompare(b.start || '') || a.id.localeCompare(b.id));
  const label = document.getElementById('week-step-label');
  label.textContent = `Week of ${FMT_MONTHDAY.format(dayDate(currentWeek))} · ${games.length} game${games.length === 1 ? '' : 's'}`;
  const i = WEEK_KEYS.indexOf(currentWeek);
  document.getElementById('week-prev').disabled = i <= 0;
  document.getElementById('week-next').disabled = i >= WEEK_KEYS.length - 1;
  const today = todayEt();
  const days = weekDays(currentWeek);
  if(!days.includes(currentDay)) currentDay = defaultDay(currentWeek, games, today);
  const byDay = {};
  games.forEach(g => (byDay[g.day] ||= []).push(g));
  document.getElementById('nhl-day-strip').innerHTML = days.map(d => {
    const dd = dayDate(d);
    const n = (byDay[d] || []).length;
    const name = `${FMT_DAY.format(dd)}${d === today ? ', today' : ''}, ${n ? `${n} game${n === 1 ? '' : 's'}` : 'no games'}`;
    return `<button type="button" class="nhl-day-chip" data-day="${d}" aria-pressed="${d === currentDay}" aria-label="${name}"${d === today ? ' aria-current="date"' : ''}>`
      + `<span>${FMT_SHORT.format(dd)}</span><b>${dd.getUTCDate()}</b><span>${n || '–'}</span></button>`;
  }).join('');
  document.querySelectorAll('.nhl-day-chip').forEach(btn => btn.addEventListener('click', () => {
    currentDay = btn.dataset.day;
    renderBoard();
    const chip = document.querySelector(`.nhl-day-chip[data-day="${currentDay}"]`);
    if(chip) chip.focus();
  }));
  const dayGames = byDay[currentDay] || [];
  const grid = document.getElementById('game-grid');
  const title = `${FMT_DAY.format(dayDate(currentDay))}${currentDay === today ? ' · Today' : ''}`;
  const head = `<div class="nhl-day-top"><h3 class="nhl-day-title">${title}</h3>`
    + `<p class="nhl-day-summary" aria-live="polite">${daySummary(dayGames, DATA.picks)}</p></div>`;
  if(!dayGames.length){
    grid.innerHTML = head + (games.length ? '' : stateHtml('waiting', 'No games this week', ''));
    return;
  }
  const nowMs = Date.now();
  grid.innerHTML = head + `<ul class="nhl-rows">${dayGames.map(g => rowHtml(g, DATA.picks[g.id], nowMs)).join('')}</ul>`;
  grid.querySelectorAll('.nhl-row').forEach(btn => btn.addEventListener('click', () => {
    const open = btn.getAttribute('aria-expanded') !== 'true';
    btn.setAttribute('aria-expanded', String(open));
    document.getElementById(btn.getAttribute('aria-controls')).hidden = !open;
  }));
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
/* Stage 68 item 26 (the 2026-10-09 audit's E21): a tuned setting chosen at
   the top of the grid the registration searched is said so, with how
   little the validation score moved across the top of it. Read from the
   results file, so the page cannot say it of a setting that is not. */
function edgeNote(tuning, key, label){
  if(!tuning || !tuning.grid || !tuning.chosen) return '';
  const vals = [...new Set(tuning.grid.map(g => g[key]))].sort((a, b) => a - b);
  const top = vals[vals.length - 1], next = vals[vals.length - 2], v = tuning.chosen[key];
  if(v !== top || next === undefined) return '';
  const at = k => tuning.grid.find(g => g.H_days === tuning.chosen.H_days && g[key] === k);
  if(!at(top) || !at(next)) return '';
  const gap = Math.abs(at(top).log_loss - at(next).log_loss);
  const n = x => Number(x).toLocaleString('en-US');
  return `<p class="nhl-lede"><b>At the edge of the grid.</b> The chosen ${label}, ${n(v)}, is the largest the registered grid searched. The validation log loss moved by ${gap.toFixed(5)} between ${n(next)} and ${n(v)}, so a wider search would be unlikely to move the picks much; it is for next season's registration, not a change to this one.</p>`;
}
function renderMethod(){
  const b = DATA.backtest;
  document.getElementById('method-body').innerHTML = `
    <p class="nhl-lede"><b>Model A</b> reads three numbers about a game: the two clubs&#39; goal ratings, their shot ratings, and their starting goalies&#39; ratings, each as a difference, home minus away. Ratings come from every game since 2015-16 that ended before the game&#39;s day, recent games counting more (half as much every ${b ? b.H_days : 120} days). A logistic regression turns the three into a home-win probability, refitted before every game day.</p>
    <p class="nhl-lede"><b>Model B</b> is Model A plus the market&#39;s home-win probability: the two-way moneyline with the bookmaker&#39;s margin taken out evenly. Where a game has no price when its pick is saved, Model A makes the pick.</p>
    <p class="nhl-lede"><b>A pick</b> is saved once, by the last run before puck drop (14:00 or 21:00 UTC), with the projected goalies Daily Faceoff lists and the market price at that moment, and is never rewritten. A goalie no roster matches falls back to his club&#39;s last starter, and the card says so. Only a game that is final is graded; a postponed or cancelled one never counts.</p>
    <p class="nhl-lede"><b>What the backtest knew that the live pick does not:</b> it used each game&#39;s actual starting goalie, from the box score. The live pick knows only the projection. The registration measures that gap once there are games to measure it on.</p>
    ${edgeNote(DATA.tuning, 'K_shots', 'shot-rating K')}
    <p class="nhl-lede"><b>Neutral sites.</b> A game at a neutral site (a Global Series game abroad, say) still gives the listed home club its home edge. The NFL has a declared rule for those games since v2.6; none has been registered for hockey.</p>`;
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

/* ---------- pages, theme ----------
   As the NFL board does (src/dashboard/app.js, Stage 26 item 2): every
   button for the page shown carries aria-current, the tab's title names the
   page, and a change the reader asked for moves focus to its heading. On a
   phone the bottom bar and its More sheet carry the menu; the sheet is
   inert while closed, so its buttons are not in the Tab order. */
const OVERFLOW_PAGES = ['teams', 'modellab', 'method', 'reliability', 'changes'];
const BASE_TITLE = document.title;
function setMoreSheetOpen(open){
  const sheet = document.getElementById('bnav-more-sheet');
  if(!sheet) return;
  sheet.classList.toggle('open', open);
  sheet.inert = !open;
}
function showPage(name, opts){
  document.querySelectorAll('.page').forEach(p => p.classList.toggle('active', p.id === 'page-' + name));
  document.querySelectorAll('[data-page]').forEach(b => {
    const on = b.dataset.page === name;
    b.classList.toggle('active', on);
    if(on) b.setAttribute('aria-current', 'page'); else b.removeAttribute('aria-current');
  });
  const more = document.getElementById('bnav-more-btn');
  if(more) more.classList.toggle('active', OVERFLOW_PAGES.includes(name));
  setMoreSheetOpen(false);
  window.scrollTo(0, 0);
  const page = document.getElementById('page-' + name);
  const heading = page && page.querySelector('.page-head h2');
  document.title = name === 'board' || !heading ? BASE_TITLE : `NHL ${heading.textContent.trim()} — Sportalytics`;
  if(opts && opts.focus && heading){
    heading.setAttribute('tabindex', '-1');
    heading.focus({preventScroll: true});
  }
}
document.querySelectorAll('[data-page]').forEach(b => b.addEventListener('click', () => showPage(b.dataset.page, {focus: true})));
const moreBtn = document.getElementById('bnav-more-btn');
if(moreBtn) moreBtn.addEventListener('click', e => {
  e.stopPropagation();
  setMoreSheetOpen(!document.getElementById('bnav-more-sheet').classList.contains('open'));
});
document.addEventListener('click', e => {
  const sheet = document.getElementById('bnav-more-sheet');
  if(sheet && sheet.classList.contains('open') && !sheet.contains(e.target) && !e.target.closest('#bnav-more-btn')) setMoreSheetOpen(false);
});
document.addEventListener('keydown', e => { if(e.key === 'Escape') setMoreSheetOpen(false); });
/* The browser checks (tests/browser/check_page.py) open each page by its section id, as they do the NFL's. */
window.setActivePage = id => showPage(String(id).replace(/^page-/, ''));
/* The top bar's height, for the table headers that stick below it under
   1080px (the shared stylesheet's --topbar-h; app.js's initTopbarHeight). */
(function(){
  const bar = document.querySelector('.topbar');
  if(!bar) return;
  const write = () => document.documentElement.style.setProperty('--topbar-h', bar.offsetHeight + 'px');
  write();
  if(typeof ResizeObserver === 'function') new ResizeObserver(write).observe(bar, {box: 'border-box'});
  window.addEventListener('resize', write);
})();
function currentTheme(){ return document.documentElement.getAttribute('data-theme') === 'light' ? 'light' : 'dark'; }
function themeLabel(){ const l = document.getElementById('theme-toggle-label'); if(l) l.textContent = currentTheme() === 'light' ? 'Dark mode' : 'Light mode'; }
document.querySelectorAll('#theme-toggle, .topbar-theme').forEach(btn => btn.addEventListener('click', () => {
  const next = currentTheme() === 'light' ? 'dark' : 'light';
  if(next === 'light') document.documentElement.setAttribute('data-theme', 'light');
  else document.documentElement.removeAttribute('data-theme');
  try{ localStorage.setItem('site:theme', next); }catch(e){}
  themeLabel();
  renderBoard();
}));

document.getElementById('board-updated').textContent = `Updated ${new Date(DATA.built_utc).toLocaleString('en-US', {timeZone: ET, month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit'})} ET`;
document.getElementById('built-line').textContent = `Updated ${new Date(DATA.built_utc).toLocaleString('en-US', {timeZone: ET, month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit'})} ET`;
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
