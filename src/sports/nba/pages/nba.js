/* The NBA's pages: the day board (Stage 65) and the registered backtest
   (Stage 61). Everything below reads one JSON block, #nba-data, written by
   src/sports/nba/site.py from the NBA's own files: the saved picks, the
   season's schedule and grades, the backtest's answers, its validation grid
   and the history's coverage. Times are shown in US Eastern. */
const DATA = JSON.parse(document.getElementById('nba-data').textContent);
const ET = 'America/New_York';

function pct(x, digits){ return (x * 100).toFixed(digits ?? 0) + '%'; }
function signed(x, digits){ const v = Number(x).toFixed(digits); return (x > 0 ? '+' : x < 0 ? '−' : '') + v.replace('-', ''); }
function seasonLabel(y){ return `${y}-${String((y + 1) % 100).padStart(2, '0')}`; }
function num(n){ return Number(n).toLocaleString('en-US'); }

/* ---------- tables that scroll ----------
   The NFL board's rule (src/dashboard/app.js, Stage 12), as the NHL's pages
   copy it until Stage 53 moves it into the shared shell: a table wider than
   its box gets the box into the Tab order as a named region, so a keyboard
   user can scroll it (WCAG 2.1.1; axe's scrollable-region-focusable). */
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

/* ---------- the backtest ---------- */
const B = DATA.backtest;
const P = DATA.protocol;
const Q = B.questions;
const QUESTION = {
  H1: 'Does Model A beat knowing only how often the home team wins?',
  H2: 'Does adding the market to Model A improve it?',
  H3: 'Does Model B beat the market alone?',
  M1: 'What does the availability term add? (a measurement, not a test)',
};
const FORECASTS = [
  ['Model A', 'model_a'], ['Model A without availability', 'model_a_no_availability'],
  ['Model B', 'model_b'], ['Market', 'market'], ['Base rate', 'base_rate'],
];
const CONFIRM = P.confirmation_seasons.map(seasonLabel).join(' and ');
const VALIDATE = P.validation_seasons.map(seasonLabel).join(' and ');
function better(diff){ return diff < 0 ? 'lower' : 'higher'; }

/* ---------- the day board (Stage 65) ----------
   The NHL's day board (Stages 63 and 64, src/sports/nhl/pages/nhl.js), for
   the NBA: a strip of the week's seven days opening on today, compact rows
   (time, game, pick, result), and a tap to the full card. Where the NHL's
   card names the goalies, this one says who was listed Out and the
   availability each side was given; where a game had no price it says
   "no price" and why, and that Model A made the pick. */
const BD = DATA.board;
/* Opening night, read from the schedule rather than written in three places
   (Stage 68 item 6): the season's first game and its day. */
const FIRST_GAME = BD.games.filter(g => g.start).sort((a, b) => a.start.localeCompare(b.start))[0] || null;
const OPENING_DAY = FIRST_GAME ? FIRST_GAME.day : (BD.live && BD.live.first_day) || '2026-10-20';
const FMT_TIP = new Intl.DateTimeFormat('en-US', {hour: 'numeric', minute: '2-digit', timeZone: 'America/New_York'});
/* Until the first pick is saved, the board says so above the rows, with the
   backtest's own verdict on Model B against the market (H3). */
function preseasonHtml(){
  if(Object.keys(BD.picks || {}).length || !FIRST_GAME) return '';
  /* The label and the direction come from the results file, as the
     Model Lab's table's do: nothing here is written by hand. */
  const h3 = Q.H3 || null;
  const verdict = h3 && h3.label
    ? ` Before the season, the backtest's answer to H3 was <b>${escapeHtml(h3.label)}</b>: on ${escapeHtml(CONFIRM)}, Model B's log loss was <b>${better(h3.diff)}</b> than the market alone's (${signed(h3.diff, 4)}), and the page will say how it goes live.`
    : '';
  return `<div class="nba-preseason" role="note"><p><b>No picks yet.</b> The first is saved by the run before the season's first tip-off, `
    + `${escapeHtml(FMT_DAY.format(dayDate(OPENING_DAY)))} at ${escapeHtml(FMT_TIP.format(new Date(FIRST_GAME.start)))} ET, and never changed.${verdict}</p>`
    + `<button type="button" class="nba-to-lab">See the backtest in the Model Lab</button></div>`;
}
function stateHtml(kind, title, text){
  return `<div class="state state--${kind}" role="status"><span class="state-title">${title}</span>${text ? `<p>${text}</p>` : ''}</div>`;
}
function dayDate(day){ return new Date(day + 'T12:00:00Z'); }
function dayIso(d){ return d.toISOString().slice(0, 10); }
function mondayOf(day){
  const d = dayDate(day);
  d.setUTCDate(d.getUTCDate() - (d.getUTCDay() + 6) % 7);
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
const WEEKS = {};
/* Team codes reach this page from the league's feed and are drawn into its
   HTML in many places. The schedule build refuses a code that is not two to
   four capital letters; the page checks again before drawing any (Stage 68
   item 8), so a bad one shows as "?" and never as markup. */
const TEAM_CODE = /^[A-Z]{2,4}$/;
function cleanCode(c){ return TEAM_CODE.test(String(c)) ? c : '?'; }
BD.games.forEach(g => { g.home = cleanCode(g.home); g.away = cleanCode(g.away); });
Object.values(BD.picks || {}).forEach(p => { if(p.pick) p.pick = cleanCode(p.pick); });
BD.games.forEach(g => { (WEEKS[mondayOf(g.day)] ||= []).push(g); });
const WEEK_KEYS = Object.keys(WEEKS).sort();
function defaultWeek(){
  const now = mondayOf(todayEt());
  if(WEEKS[now]) return now;
  return WEEK_KEYS.find(k => k >= now) || WEEK_KEYS[WEEK_KEYS.length - 1] || now;
}
let currentWeek = defaultWeek();
function logo(abbr){
  const t = BD.teams[abbr];
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
  return `Final: ${g.away} ${g.as}, ${g.home} ${g.hs}`;
}
/* The market line: the price and who quoted it, or "no price" and why.
   Every pick names its source (experiments/nba/stage65/registry.json):
   ESPN's sportsbook, Kalshi's market as the named fallback, or none. */
function marketText(g, p){
  const m = p.market;
  if(!m) return `Market: <b>no price</b>${p.why ? ` (${escapeHtml(p.why)})` : ''}, so Model A made the pick`;
  if(p.source === 'kalshi'){
    return `Market (Kalshi, the fallback: ESPN had no price): ${g.away} <b>${pct(m.ap)}</b> · ${g.home} <b>${pct(m.hp)}</b>, so ${sideText(side(m.prob * 100, g))}`;
  }
  return `Market (${escapeHtml(m.book || 'sportsbook')} via ESPN): ${g.away} <b>${american(m.ap)}</b> · ${g.home} <b>${american(m.hp)}</b>, so ${sideText(side(m.prob * 100, g))} with the margin out`;
}
/* Who is out, and the availability each side was given: the share of its
   expected minutes from players not listed Out. */
function availText(g, p){
  if(!p.avail || !p.avail.read) return 'Injury report: <b>not read</b> when the pick was saved, so both models ran without availability';
  /* A player listed Out with no minutes yet (a rookie, a new signing) weighs
     nothing, so a side can be at 100% with a name out: the share is of
     expected minutes, and the line says so. */
  const one = (team, share, names) => `${team} <b>${pct(share)}</b>${names.length ? ` (out: ${names.map(escapeHtml).join(', ')})` : ''}`;
  return `Expected minutes available: ${one(g.away, p.avail.away, p.out.away)} · ${one(g.home, p.avail.home, p.out.home)}`;
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
  const status = scoreLine(g);
  return `<div class="game-card">
    <div class="matchup-header">${g.away} <span class="at-symbol">at</span> ${g.home}</div>
    <div class="card-kickoff">${startLabel(g)}</div>
    ${status ? `<div class="nba-card-status">${status}</div>` : ''}
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
    <div class="market-ref">${marketText(g, p)}</div>
    <div class="card-qbs">${availText(g, p)}</div>
    ${proofLine(g, p, BD.proof)}
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
  return `<div class="nba-proof">In the public history ${escapeHtml(whenEt(new Date(pr.committed)))} (commit ${link}), ${before ? 'before the start' : '<b>after the start</b>'}.${later}</div>`;
}
/* A saved pick is a locked pick: the daily run writes a game's pick file only
   when it locks it, at the last run before tip-off (src/sports/nba/lock.py). */
const LOCK_RUNS_UTC = [[16, 0], [21, 30]];    // lock.py's RUNS_UTC, every day
const LOCK_SLACK_MS = 60 * 60 * 1000;         // lock.py's SLACK
/* The run that will save a game starting at `startIso`: the first run before
   the start whose next run, plus the slack, would come too late. The same
   rule as GameLock.decide; tests/test_nba_board.py runs both. */
function lockRunFor(startIso){
  const start = Date.parse(startIso);
  if(Number.isNaN(start)) return null;
  const runs = [];
  const day0 = new Date(start - 3 * 86400000);
  for(let d = 0; d <= 4; d++){
    LOCK_RUNS_UTC.forEach(([h, m]) => runs.push(Date.UTC(day0.getUTCFullYear(), day0.getUTCMonth(), day0.getUTCDate() + d, h, m)));
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
function lockNote(g, nowMs){
  const run = g.start ? lockRunFor(g.start) : null;
  if(!run) return 'The pick locks at the last run before tip-off (16:00 or 21:30 UTC).';
  if(run.getTime() + LOCK_SLACK_MS < nowMs) return `The pick was due to lock ${whenEt(run)} and has not been saved yet.`;
  return `The pick locks ${whenEt(run)}, at the last run before tip-off.`;
}
function modelSide(prob, g){ return prob === null || prob === undefined ? null : (prob >= 0.5 ? g.home : g.away); }
function winnerOf(g){
  if(g.status !== 'final' || g.hs === null || g.hs === undefined || g.as === null || g.as === undefined || g.hs === g.as) return null;
  return g.hs > g.as ? g.home : g.away;
}
function resultLine(g, p){
  const won = winnerOf(g);
  if(!won) return '';
  const one = (label, prob) => {
    const s = modelSide(prob, g);
    return s === null ? '' : `<span class="nba-model-result">${label} ${s}, <b>${s === won ? 'right' : 'wrong'}</b></span>`;
  };
  const market = p.market ? one('Market', p.market.prob) : '';
  return `<div class="nba-result-line">Winner <b>${won}</b>${one('Model B', p.b)}${one('Model A', p.a)}${market}</div>`;
}
function lockedTag(g, p){
  if(g.status === 'final' || g.status === 'cancelled' || g.status === 'postponed') return '';
  const when = p.saved ? ` ${whenEt(new Date(p.saved))}` : '';
  return `<span class="graded-tag nba-locked">Locked${when}</span>`;
}
const FIRST_SAVED = Object.values(BD.picks).map(p => p.saved).filter(Boolean).sort()[0] || null;
function waitingCard(g){
  const status = scoreLine(g);
  let note;
  if(g.status === 'final' || g.status === 'in_progress'){
    note = !FIRST_SAVED || (g.start && g.start < FIRST_SAVED) ? 'Before the first pick was saved.' : 'No pick was saved for this game.';
  } else if(g.status === 'cancelled' || g.status === 'postponed'){
    note = 'No pick: a postponed or cancelled game is never predicted.';
  } else {
    note = lockNote(g, Date.now());
  }
  return `<div class="game-card nba-not-saved">
    <div class="matchup-header">${g.away} <span class="at-symbol">at</span> ${g.home}</div>
    <div class="card-kickoff">${startLabel(g)}</div>
    ${status ? `<div class="nba-card-status">${status}</div>` : ''}
    <div class="nba-wait-note">${note}</div>
  </div>`;
}

/* ---------- rows, a day at a time ---------- */
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
/* The pick in a row: the saved side, the chance the leading model gave it,
   and "no price" when Model A made it for want of one. */
function rowPick(g, p){
  if(!p) return '—';
  const lead = p.b !== null && p.b !== undefined ? p.b : p.a;
  const chance = p.pick === g.home ? lead : 1 - lead;
  return `${p.pick} ${Math.round(chance * 100)}%${p.market ? '' : ' <span class="nba-no-price">no price</span>'}`;
}
function rowTime(g){
  if(g.status === 'final') return 'Final';
  if(g.status === 'in_progress') return 'Live';
  return g.start ? FMT_HOUR.format(new Date(g.start)) : 'TBD';
}
function rowGame(g){
  const won = winnerOf(g);
  const has = g.status === 'final' && g.hs !== null && g.hs !== undefined && g.as !== null && g.as !== undefined;
  const team = (abbr, score) => {
    const text = has ? `${abbr} ${score}` : abbr;
    return `<span class="nba-row-team">${abbr === won ? `<b>${text}</b>` : text}</span>`;
  };
  /* A team and its score never split; on a phone the game wraps at the @,
     since three-digit scores do not fit one line beside the pick. */
  return `${team(g.away, g.as)} <span class="at-symbol">@</span> ${team(g.home, g.hs)}`;
}
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
const CHEVRON = '<svg class="nba-row-chev" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 9l6 6 6-6"/></svg>';
function rowHtml(g, p, nowMs){
  const r = rowResult(g, p, nowMs);
  const id = `nba-detail-${g.id}`;
  return `<li class="nba-row-item">
    <button type="button" class="nba-row" aria-expanded="false" aria-controls="${id}">
      <span class="nba-row-time">${rowTime(g)}</span>
      <span class="nba-row-game">${rowGame(g)}</span>
      <span class="nba-row-pick">${rowPick(g, p)}</span>
      <span class="nba-row-result ${r.cls}">${r.text}</span>${CHEVRON}
    </button>
    <div class="nba-row-detail" id="${id}" hidden>${p ? pickedCard(g, p) : waitingCard(g)}</div>
  </li>`;
}
function labLinks(root){
  root.querySelectorAll('.nba-to-lab').forEach(b => b.addEventListener('click', () => showPage('modellab', {focus: true})));
}
let currentDay = null;
function renderBoard(){
  const grid = document.getElementById('game-grid');
  if(!BD.games.length){
    /* The shared stylesheet sets .week-step's display, which beats the hidden
       attribute, so the whole row is taken out instead. */
    document.getElementById('week-step').closest('.filter-row').style.display = 'none';
    document.getElementById('nba-day-strip').innerHTML = '';
    grid.innerHTML = stateHtml('waiting', 'The board fills from the first daily run',
      `Picks start on opening night, ${escapeHtml(FMT_DAY.format(dayDate(OPENING_DAY)))}. The daily run saves each game's pick before tip-off and never changes it.`);
    return;
  }
  const games = (WEEKS[currentWeek] || []).slice().sort((a, b) => (a.start || '').localeCompare(b.start || '') || a.id.localeCompare(b.id));
  document.getElementById('week-step-label').textContent = `Week of ${FMT_MONTHDAY.format(dayDate(currentWeek))} · ${games.length} game${games.length === 1 ? '' : 's'}`;
  const i = WEEK_KEYS.indexOf(currentWeek);
  document.getElementById('week-prev').disabled = i <= 0;
  document.getElementById('week-next').disabled = i >= WEEK_KEYS.length - 1;
  const today = todayEt();
  const days = weekDays(currentWeek);
  if(!days.includes(currentDay)) currentDay = defaultDay(currentWeek, games, today);
  const byDay = {};
  games.forEach(g => (byDay[g.day] ||= []).push(g));
  document.getElementById('nba-day-strip').innerHTML = days.map(d => {
    const dd = dayDate(d);
    const n = (byDay[d] || []).length;
    const name = `${FMT_DAY.format(dd)}${d === today ? ', today' : ''}, ${n ? `${n} game${n === 1 ? '' : 's'}` : 'no games'}`;
    return `<button type="button" class="nba-day-chip" data-day="${d}" aria-pressed="${d === currentDay}" aria-label="${name}"${d === today ? ' aria-current="date"' : ''}>`
      + `<span>${FMT_SHORT.format(dd)}</span><b>${dd.getUTCDate()}</b><span>${n || '–'}</span></button>`;
  }).join('');
  document.querySelectorAll('.nba-day-chip').forEach(btn => btn.addEventListener('click', () => {
    currentDay = btn.dataset.day;
    renderBoard();
    const chip = document.querySelector(`.nba-day-chip[data-day="${currentDay}"]`);
    if(chip) chip.focus();
  }));
  const dayGames = byDay[currentDay] || [];
  const title = `${FMT_DAY.format(dayDate(currentDay))}${currentDay === today ? ' · Today' : ''}`;
  const head = `<div class="nba-day-top"><h3 class="nba-day-title">${title}</h3>`
    + `<p class="nba-day-summary" aria-live="polite">${daySummary(dayGames, BD.picks)}</p></div>`;
  if(!dayGames.length){
    grid.innerHTML = head + preseasonHtml() + (games.length ? '' : stateHtml('waiting', 'No games this week', ''));
    labLinks(grid);
    return;
  }
  const nowMs = Date.now();
  grid.innerHTML = head + preseasonHtml() + `<ul class="nba-rows">${dayGames.map(g => rowHtml(g, BD.picks[g.id], nowMs)).join('')}</ul>`;
  labLinks(grid);
  grid.querySelectorAll('.nba-row').forEach(btn => btn.addEventListener('click', () => {
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

/* ---------- model lab ---------- */
function renderModelLab(){
  const rows = Object.entries(Q).map(([id, q]) => `<tr><th scope="row">${id}</th><td>${QUESTION[id] || ''}</td><td class="num">${signed(q.diff, 4)}</td><td class="num">[${signed(q.low, 4)}, ${signed(q.high, 4)}]</td><td>${q.label ? `<b>${q.label}</b>` : 'a measurement'}</td></tr>`).join('');
  const scores = FORECASTS.filter(([, k]) => B.scores[k]).map(([n, k]) => { const v = B.scores[k];
    return `<tr><th scope="row">${n}</th><td class="num">${num(v.games)}</td><td class="num">${v.log_loss.toFixed(4)}</td><td class="num">${v.brier.toFixed(4)}</td><td class="num">${pct(v.accuracy, 1)}</td></tr>`; }).join('');
  const chosen = DATA.tuning.chosen;
  const grid = DATA.tuning.grid.map(g => { const on = g.H_days === chosen.H_days && g.lambda === chosen.lambda;
    return `<tr${on ? ' class="nba-chosen"' : ''}><td class="num">${g.H_days}</td><td class="num">${g.lambda}</td><td class="num">${g.log_loss.toFixed(5)}</td><td>${on ? 'chosen' : ''}</td></tr>`; }).join('');
  document.getElementById('modellab-body').innerHTML = `
    <p class="nba-lede">Registered before any NBA model was fitted (<code>experiments/nba/stage61/registry.json</code>), tuned on ${VALIDATE} (H = ${B.H_days} days, ridge strength ${B.lambda}), and answered once on ${CONFIRM}. A difference below zero means the first model forecast better. Each interval is a paired bootstrap of whole game days at ${pct(Q.H1.level, 2)}; a result counts only when the interval excludes zero.</p>
    <div class="table-wrap"><table class="metrics-table nba-table"><caption class="visually-hidden">The backtest's questions</caption>
    <thead><tr><th scope="col">#</th><th scope="col">Question</th><th scope="col" class="num">Log loss difference</th><th scope="col" class="num">Interval</th><th scope="col">Label</th></tr></thead>
    <tbody>${rows}</tbody></table></div>
    <h2 class="section-title">Scores on ${CONFIRM}</h2>
    <div class="table-wrap"><table class="metrics-table nba-table"><caption class="visually-hidden">Scores on the held-out seasons</caption>
    <thead><tr><th scope="col">Forecast</th><th scope="col" class="num">Games</th><th scope="col" class="num">Log loss</th><th scope="col" class="num">Brier</th><th scope="col" class="num">Accuracy</th></tr></thead>
    <tbody>${scores}</tbody></table></div>
    <p class="nba-lede">Accuracy is printed, never decides: at this many games it moves by a game or two between machines, where log loss does not.</p>
    <h2 class="section-title">Tuning on ${VALIDATE}</h2>
    <p class="nba-lede">Model A&#39;s log loss over the validation seasons for each registered pair of half-life (days) and ridge strength. The lowest was kept and fixed before the held-out seasons were scored.</p>
    <div class="table-wrap"><table class="metrics-table nba-table"><caption class="visually-hidden">The tuning grid</caption>
    <thead><tr><th scope="col" class="num">Half-life</th><th scope="col" class="num">Ridge</th><th scope="col" class="num">Log loss</th><th scope="col"></th></tr></thead>
    <tbody>${grid}</tbody></table></div>`;
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
  return `<p class="nba-lede"><b>At the edge of the grid.</b> The chosen ${label}, ${n(v)}, is the largest the registered grid searched. The validation log loss moved by ${gap.toFixed(5)} between ${n(next)} and ${n(v)}, so a wider search would be unlikely to move the picks much; it is for next season's registration, not a change to this one.</p>`;
}
function renderMethod(){
  const cov = DATA.coverage.map(c => `<tr><th scope="row">${seasonLabel(c.season)}</th><td class="num">${num(c.games)}</td><td class="num">${num(c.priced)}</td><td class="num">${num(c.closing)}</td></tr>`).join('');
  document.getElementById('method-body').innerHTML = `
    <p class="nba-lede"><b>Model A</b> reads three numbers about a game, each home minus away. Two are team ratings from a ridge regression of every earlier game&#39;s margin, recent games counting more (half as much every ${B.H_days} days): one on points, one on points per 100 possessions. The third is availability: the share of each team&#39;s expected minutes that plays, where a player&#39;s expected minutes are his recent minutes per team game. A logistic regression turns the three into a home-win probability.</p>
    <p class="nba-lede"><b>Model B</b> is Model A plus the market&#39;s home-win probability: ESPN&#39;s moneyline with the bookmaker&#39;s margin taken out evenly, the closing price where there is one.</p>
    <p class="nba-lede"><b>The test.</b> Every regular-season, play-in and playoff game from ${seasonLabel(P.training_from_season)} on. Before each game day both models are refitted on every earlier game and predict that day&#39;s games, so nothing a game did is known before it. The settings were chosen on ${VALIDATE} only, then fixed, and ${CONFIRM} were scored once. ${P.budget_m} questions shared a ${pct(P.alpha)} error budget, so each interval is at ${pct(1 - P.alpha / P.budget_m, 2)}.</p>
    <p class="nba-lede"><b>The live picks</b> (from ${escapeHtml(FMT_DAY.format(dayDate(OPENING_DAY)))}, registered in <code>experiments/nba/stage65/registry.json</code> before the first was saved): each game's pick is saved by the last run before tip-off and never changed. Model B makes it with ESPN's pre-game price; when ESPN has none, Kalshi's game market is the named fallback, used only when its two sides are quoted within five cents, and the card says so. With neither, the card says <b>no price</b> and Model A makes the pick. Availability comes from ESPN's injury report: every player not listed Out counts as playing.</p>
    <p class="nba-lede"><b>What the backtest knew that a live pick would not:</b> who actually played, from the box score. A live pick would know only the injury report before tip-off. The registration measures that gap (M2) once there are live games to measure it on.</p>
    ${edgeNote(DATA.tuning, 'lambda', 'ridge strength')}
    <p class="nba-lede"><b>Neutral sites.</b> A game at a neutral site (the NBA Cup final, a game abroad) still gives the listed home team its home edge. The NFL has a declared rule for those games since v2.6; none has been registered for basketball.</p>
    <h2 class="section-title">The games</h2>
    <p class="nba-lede">Box scores are ESPN&#39;s. Where ESPN&#39;s is empty (about 500 games of 2015-16 to 2017-18, and six play-in games of 2020-21) they come from SportsDataverse&#39;s copy, and the few games neither has are left out and named in the repository.</p>
    <div class="table-wrap"><table class="metrics-table nba-table"><caption class="visually-hidden">Games and prices per season</caption>
    <thead><tr><th scope="col">Season</th><th scope="col" class="num">Games</th><th scope="col" class="num">With a price</th><th scope="col" class="num">Closing price</th></tr></thead>
    <tbody>${cov}</tbody></table></div>`;
}

/* ---------- checking ---------- */
/* ---------- calibration (Stage 68 item 21) ----------
   The NHL's table (src/sports/nhl/pages/nhl.js), on the NBA's live picks:
   how sure each graded pick was against how often picks that sure came
   true. The chance is the one the model that made the pick gave its side. */
const CAL_BINS = [[0.5, 0.55], [0.55, 0.6], [0.6, 0.65], [0.65, 0.7], [0.7, 1.01]];
const CAL_MIN = 30;
function pickChance(p, g){
  const home = p.by === 'model_b' && p.b !== null && p.b !== undefined ? p.b : p.a;
  return p.pick === g.home ? home : 1 - home;
}
function gradedPicks(){
  const byId = Object.fromEntries(BD.games.map(g => [g.id, g]));
  return Object.entries(BD.picks || {}).map(([id, p]) => ({p, g: byId[id]}))
    .filter(x => x.g && (x.p.result === 'correct' || x.p.result === 'wrong'));
}
function calibrationHtml(graded){
  if(!graded.length){
    return `<h2 class="section-title">How sure, and how often right</h2>
    <p class="nba-lede">No NBA pick has been graded yet. From opening night this table sets each graded pick's chance beside how often picks that sure came true.</p>`;
  }
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
    <p class="nba-lede">Each graded pick by the chance its model gave the side it picked. A well-calibrated model is right about as often as it says.${thin ? ` With ${graded.length} graded picks, most rows hold too few games to read: a row means little under ${CAL_MIN}.` : ''}</p>
    <div class="table-wrap"><table class="metrics-table nba-table"><caption class="visually-hidden">Calibration of the graded picks</caption>
    <thead><tr><th scope="col">The pick's chance</th><th scope="col" class="num">Picks</th><th scope="col" class="num">Said, on average</th><th scope="col" class="num">Right</th></tr></thead>
    <tbody>${rows}</tbody></table></div>`;
}
function renderReliability(){
  document.getElementById('reliability-body').innerHTML = `
    ${calibrationHtml(gradedPicks())}
    <p class="nba-lede"><b>The drift check leans toward flagging.</b> Its baseline was measured with each game's actual players, from the box score: knowing who played lowered the backtest's log loss by ${(-Q.M1.diff).toFixed(3)} (M1). A live pick knows only the injury report before tip-off, so live log loss is expected to run up to about that much worse for a reason that is not drift, and the check may flag sooner than a like-for-like comparison would. The registration says so (<code>experiments/nba/stage65/registry.json</code>), and M2 measures the gap once there are live games.</p>
    <h2 class="section-title">Before anything was fitted</h2>
    <p class="nba-lede">The questions, the seasons, the settings to search, the bootstrap and the labels were written down and committed on ${escapeHtml(DATA.registered)} (<code>experiments/nba/stage61/registry.json</code>), before any NBA feature was computed on a real game. H3 had been expected to come back INCONCLUSIVE; it came back ${Q.H3.label}, and it is reported as it came out. Nothing was re-run or re-tuned.</p>
    <h2 class="section-title">After</h2>
    <p class="nba-lede">Every number on these pages is read from the committed results files when the page is built, and tests hold those files to the registration: the whole grid searched on the validation seasons only, the lowest kept, each label following from its interval. Those tests were checked in turn, by breaking the code on purpose and confirming a test fails.</p>
    <p class="nba-lede">A separate auditing agent, Booth, re-ran the confirmation on a Linux machine before the results were merged: every number agreed with the committed file to the twelfth decimal place. On Windows the full backtest, tuning included, reproduced both files byte for byte.</p>`;
}

/* ---------- pages, theme ----------
   As the NFL board and the NHL's pages do: every button for the page shown
   carries aria-current, the tab's title names the page, and a change the
   reader asked for moves focus to its heading. Four pages fit the phone's
   bottom bar, so there is no More sheet. */
const BASE_TITLE = document.title;
function showPage(name, opts){
  document.querySelectorAll('.page').forEach(p => p.classList.toggle('active', p.id === 'page-' + name));
  document.querySelectorAll('[data-page]').forEach(b => {
    const on = b.dataset.page === name;
    b.classList.toggle('active', on);
    if(on) b.setAttribute('aria-current', 'page'); else b.removeAttribute('aria-current');
  });
  window.scrollTo(0, 0);
  const page = document.getElementById('page-' + name);
  const heading = page && page.querySelector('.page-head h2');
  document.title = name === 'board' || !heading ? BASE_TITLE : `NBA ${heading.textContent.trim()} — Sportalytics`;
  if(opts && opts.focus && heading){
    heading.setAttribute('tabindex', '-1');
    heading.focus({preventScroll: true});
  }
}
document.querySelectorAll('[data-page]').forEach(b => b.addEventListener('click', () => showPage(b.dataset.page, {focus: true})));
/* The browser checks (tests/browser/check_page.py) open each page by its section id. */
window.setActivePage = id => showPage(String(id).replace(/^page-/, ''));
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

document.getElementById('built-line').textContent = `Updated ${new Date(DATA.built_utc).toLocaleString('en-US', {timeZone: ET, month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit'})} ET`;
document.getElementById('board-updated').textContent = `Updated ${new Date(DATA.built_utc).toLocaleString('en-US', {timeZone: ET, month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit'})} ET${BD.schedule_as_of ? `, schedule as of ${BD.schedule_as_of}` : ''}`;
themeLabel();
renderBoard();
renderModelLab();
renderMethod();
renderReliability();
installRoutes(showPage);
document.body.classList.remove('is-entering');
