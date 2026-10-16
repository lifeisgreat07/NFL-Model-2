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
// A start's time, in Eastern time or the visitor's own (Stage 80 item 57, src/core/prefs.js).
const FMT_TIP = new Intl.DateTimeFormat('en-US', {hour: 'numeric', minute: '2-digit', timeZone: startZone()});
/* Until the first pick is saved, the board says so above the rows, with the
   backtest's own verdict on Model B against the market (H3). */
function preseasonHtml(){
  if(Object.keys(BD.picks || {}).length || !FIRST_GAME) return '';
  /* The label and the direction come from the results file, as the
     Model Lab's table's do: nothing here is written by hand. */
  const h3 = Q.H3 || null;
  /* Stage 77 item 21 (the 2026-10-13 audit's copy fix 10): the verdict in
     plain words. The label, the log-loss gap and its sign stay on the Model
     Lab, one tap away; here the sign alone picks the sentence. */
  const seasons = P.confirmation_seasons.length;
  const howMany = ['no', 'one', 'two', 'three', 'four'][seasons] || String(seasons);
  const verdict = h3 && typeof h3.diff === 'number'
    ? (h3.diff < 0
      ? ` In the ${howMany} test seasons Model B beat the betting market, so the live picks will show whether that holds.`
      : ` In the ${howMany} test seasons Model B did not beat the betting market, so the first live picks are a real test, not a victory lap.`)
    : '';
  const countdown = countdownText(todayEt());
  return `<div class="nba-preseason" role="note">${countdown ? `<p class="nba-countdown">${escapeHtml(countdown)}</p>` : ''}<p><b>No picks yet.</b> The first is saved by the run before the season's first tip-off, `
    + `${escapeHtml(FMT_DAY.format(dayDate(OPENING_DAY)))}${tipSet(FIRST_GAME) ? ` at ${escapeHtml(FMT_TIP.format(new Date(FIRST_GAME.start)))}${startMark()}` : ', its tip-off time still to be set'}, and never changed.${verdict}</p>`
    + `<button type="button" class="nba-to-lab" data-route="modellab">See the backtest in the Model Lab</button></div>`;
}
/* Stage 80 item 60 (the 2026-10-13 audit's F17): until the first pick is
   saved, the note leads with when it locks and how long that is from today
   (Eastern calendar days). The clock time is given only when every opening-
   night tip-off is set: a placeholder tip (item 33) would give a wrong lock. */
const FMT_LOCK_DAY = new Intl.DateTimeFormat('en-US', {weekday: 'short', month: 'short', day: 'numeric', timeZone: 'UTC'});
function countdownText(today){
  if(!FIRST_GAME) return '';
  const days = Math.round((Date.parse(OPENING_DAY) - Date.parse(today)) / 86400000);
  if(days < 0) return '';
  const opening = BD.games.filter(g => g.day === OPENING_DAY && g.start);
  const runs = opening.every(tipSet) ? opening.map(g => lockRunFor(g.start)).filter(Boolean) : [];
  const first = runs.length ? new Date(Math.min(...runs.map(r => r.getTime()))) : null;
  const when = `${FMT_LOCK_DAY.format(dayDate(OPENING_DAY))}${first ? `, ${FMT_TIP.format(first)}${startMark()}` : ''}`;
  const away = days === 0 ? 'today' : days === 1 ? 'tomorrow' : `${days} days`;
  return `First picks lock ${when} — ${away}`;
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
const FMT_TIME = new Intl.DateTimeFormat('en-US', {hour: 'numeric', minute: '2-digit', timeZone: startZone()});
const FMT_ET_DATE = new Intl.DateTimeFormat('en-CA', {year: 'numeric', month: '2-digit', day: '2-digit', timeZone: ET});
function todayEt(){ return FMT_ET_DATE.format(new Date()); }
/* Whether a game's tip-off time is set, by ESPN's own word (`tv`, the
   competition's timeValid, carried by the daily run's schedule file). Only
   an explicit false reads "time TBD"; a schedule written before the field
   existed prints the time. Stage 77 item 33 guessed from the hour instead
   (a weekday tip before 5 PM Eastern was a placeholder), and that hid
   opening night's BOS at DET, a real 3 PM game on NBC, and Christmas Day's
   noon and 2:30 games (found 2026-10-15). */
function tipSet(g){
  return Boolean(g.start) && g.tv !== false;
}
function startLabel(g){
  const day = FMT_DAY.format(dayDate(g.day));
  if(!g.start) return day;
  return tipSet(g) ? `${day} · ${FMT_TIME.format(new Date(g.start))}${startMark()}` : `${day} · time TBD`;
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
/* The saved pick and the chance its leading model gave it, as the row and
   the card both print it (Stage 75 item 2): "TOR 63%", or "TOR 51% · even"
   inside EVEN_BAND, where the card's headline used to call the game too
   close beside a row that said "TOR 51%". */
function pickText(g, p){
  const lead = p.b !== null && p.b !== undefined ? p.b : p.a;
  const chance = Math.round((p.pick === g.home ? lead : 1 - lead) * 100);
  return `${p.pick} ${chance}%${Math.abs(lead * 100 - 50) < EVEN_BAND ? ' · even' : ''}`;
}
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
/* Stage 80 item 61 (F15): a game not yet final is marked for src/core/scores.js,
   which the build puts on the page and which fills the empty slots with
   ESPN's score while the game is on. */
function scoreMark(g){
  if(!g.start || g.status === 'final' || g.status === 'cancelled' || g.status === 'postponed') return '';
  return ` data-score-sport="nba" data-score-key="${g.away}@${g.home}" data-score-start="${g.start}" data-score-id="${g.id}"`;
}
const scoreSlot = (name, cls) => `<span class="score-on ${cls || ''}" data-score-slot="${name}"></span>`;
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
    return `Market (Kalshi, the fallback: ESPN had no price): ${g.away} <b>${pct(m.ap)}</b> · ${g.home} <b>${pct(m.hp)}</b>, so ${sideText(side(m.prob * 100, g))}; with a price, Model B made the pick`;
  }
  return `Market (${escapeHtml(m.book || 'sportsbook')} via ESPN): ${g.away} <b>${american(m.ap)}</b> · ${g.home} <b>${american(m.hp)}</b>, so ${sideText(side(m.prob * 100, g))} with the margin out; with a price, Model B made the pick`;
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
/* Stage 80 item 63 (F13): what this card's shared image says. src/core/share_card.js,
   which the build puts on the page, draws it when "Share image" is pressed. */
function shareAttr(g, p){
  const vals = {b: p.b === null ? null : p.b * 100, a: p.a * 100, market: p.market ? p.market.prob * 100 : null};
  const lead = vals.b !== null ? ['Model B', vals.b] : ['Model A', vals.a];
  const s = side(lead[1], g);
  const forecasts = [['Model B', vals.b], ['Market', vals.market], ['Model A', vals.a]]
    .filter(([, v]) => v !== null).map(([label, v]) => ({label, text: sideText(side(v, g))}));
  const result = p.result === 'correct' ? 'Correct' : p.result === 'wrong' ? 'Missed' : null;
  const extra = g.lp === 'OT' ? ' (OT)' : g.lp === 'SO' ? ' (SO)' : '';
  const score = g.status === 'final' && g.hs !== null && g.hs !== undefined ? `Final: ${g.away} ${g.as}, ${g.home} ${g.hs}${extra}` : null;
  // Inside the even band the card still names the saved pick ("NJD 51% · even").
  const even = !s.team, team = even ? p.pick : s.team, pct = even ? (p.pick === g.home ? lead[1] : 100 - lead[1]) : s.pct;
  return escapeHtml(JSON.stringify({sport: 'NBA', away: g.away, home: g.home, colours: p.colours, lead: lead[0], team, even,
    pct, homePct: lead[1], forecasts, when: startLabel(g), result, score}));
}
const SHARE_BUTTON = '<button type="button" class="btn btn-link share-btn" data-share-card>Share image</button>';
function pickedCard(g, p){
  const vals = {b: p.b === null ? null : p.b * 100, a: p.a * 100, market: p.market ? p.market.prob * 100 : null};
  const lead = vals.b !== null ? vals.b : vals.a;
  const leadLabel = vals.b !== null ? 'Model B' : 'Model A';
  const s = side(lead, g);
  const done = g.status === 'final';
  const headline = s.team
    ? `<span class="card-hl-label">${leadLabel}${done ? ' picked' : ''}</span> <b>${s.team} ${Math.round(s.pct)}%</b> <span class="card-hl-to">to win</span>`
    : `<span class="card-hl-label">${leadLabel}${done ? ' picked' : ''}</span> <b>${pickText(g, p).replace(' · even', '')}</b> <span class="card-hl-to">· even</span>`;
  const ln = lanes(vals);
  // One axis (Stage 75 item 1): the bar draws the away team first, so a
  // home share v sits at 100 - v from the left, and the lead model's
  // marker lands on the split. tests/browser/check_card_axis.py.
  const mark = k => vals[k] === null ? '' :
    `<svg class="card-mk" data-series="${k}" style="left:${100 - vals[k]}%; top:calc(50% + ${ln[k] * 12}px)" width="12" height="12" viewBox="0 0 12 12" aria-hidden="true">${markerPath(SERIES[k].shape, 6, 6, 4.5)} fill="${SERIES[k].color}"/></svg>`;
  const key = k => vals[k] === null ? '' :
    `<span class="card-key"><svg width="12" height="12" viewBox="0 0 14 14" aria-hidden="true">${markerPath(SERIES[k].shape, 7, 7, 5)} fill="${SERIES[k].color}"/></svg>${SERIES[k].label} <b>${sideText(side(vals[k], g))}</b></span>`;
  const aria = ['b', 'market', 'a'].filter(k => vals[k] !== null).map(k => `${SERIES[k].label} ${sideText(side(vals[k], g))}`).join('. ') + '.';
  const [awayC, homeC] = p.colours;
  const graded = p.result === 'correct' || p.result === 'wrong';
  const tag = graded ? `<span class="graded-tag ${p.result === 'correct' ? 'correct' : 'incorrect'}">${p.result === 'correct' ? 'Correct' : 'Missed'}</span>`
    : (p.result === 'cancelled' ? '<span class="graded-tag tie">Cancelled</span>' : lockedTag(g, p));
  const status = scoreLine(g);
  return `<div class="game-card"${scoreMark(g)} data-share="${shareAttr(g, p)}">
    <div class="matchup-header">${g.away} <span class="at-symbol">at</span> ${g.home}</div>
    <div class="card-kickoff">${startLabel(g)}</div>
    ${status ? `<div class="nba-card-status score-off">${status}</div>` : ''}
    <div class="nba-card-status score-on" data-score-slot="line"></div>
    ${resultLine(g, p)}
    ${tag ? `<div class="game-top"><div class="tag-row">${tag}</div></div>` : ''}
    <div class="card-hl">${headline}</div>
    <div class="card-viz">
      <span class="card-end">${favStar('nba', g.away, escapeHtml((BD.teams[g.away] || {}).name || g.away))}${badge(p.pick === g.away, p.result)}${endTeam(g.away)}</span>
      <div class="card-scale" role="img" aria-label="${escapeHtml(aria)}">
        <div class="tele-bar">
          <div class="tele-bar-seg" style="width:${100 - lead}%; background:${awayC};"></div>
          <div class="tele-bar-seg" style="width:${lead}%; background:${homeC};"></div>
        </div>
        <div class="card-line"><span class="card-mid"></span><span class="card-mid-label">50%</span>${mark('a')}${mark('market')}${mark('b')}</div>
      </div>
      <span class="card-end">${badge(p.pick === g.home, p.result)}${endTeam(g.home)}${favStar('nba', g.home, escapeHtml((BD.teams[g.home] || {}).name || g.home))}</span>
    </div>
    <div class="card-keys">${key('b')}${key('market')}${key('a')}</div>
    <div class="market-ref">${marketText(g, p)}</div>
    <div class="card-qbs">${availText(g, p)}</div>
    ${proofLine(g, p, BD.proof)}
    ${SHARE_BUTTON}
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
    return s === null ? '' : `<span class="nba-model-result">${label} ${s}, <b>${s === won ? 'correct' : 'missed'}</b></span>`;
  };
  const market = p.market ? one('Market', p.market.prob) : '';
  return `<div class="nba-result-line">Winner <b>${won}</b>${one('Model B', p.b)}${one('Model A', p.a)}${market}</div>`;
}
function lockedTag(g, p){
  if(g.status === 'final' || g.status === 'cancelled' || g.status === 'postponed') return '';
  const when = p.saved ? ` ${whenEt(new Date(p.saved))}` : '';
  return `<span class="graded-tag tag-fill nba-locked">Locked${when}</span>`;
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
  return `<div class="game-card nba-not-saved"${scoreMark(g)}>
    <div class="matchup-header">${g.away} <span class="at-symbol">at</span> ${g.home}</div>
    <div class="card-kickoff">${startLabel(g)}</div>
    ${status ? `<div class="nba-card-status score-off">${status}</div>` : ''}
    <div class="nba-card-status score-on" data-score-slot="line"></div>
    <div class="nba-wait-note">${note}</div>
  </div>`;
}

/* ---------- rows, a day at a time ---------- */
const FMT_HOUR = new Intl.DateTimeFormat('en-US', {hour: 'numeric', minute: '2-digit', timeZone: startZone()});
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
    // Stage 77 item 25 (copy row 14): a game under way says Live, not Locked;
    // the time cell then keeps the start time rather than saying Live twice.
    if(g.status === 'in_progress') return {text: 'Live', cls: 'live'};
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
  // On a phone "even" takes its own line under the pick (nba.css).
  const pick = pickText(g, p).replace(' · even', '<span class="row-even"><span class="row-even-sep"> · </span>even</span>');
  return `${pick}${p.market ? '' : ' <span class="nba-no-price">no price</span>'}`;
}
function rowTime(g, p){
  if(g.status === 'final') return 'Final';
  if(g.status === 'in_progress' && !p) return 'Live';
  if(!g.start) return 'TBD';
  return tipSet(g) ? FMT_HOUR.format(new Date(g.start)) : 'time TBD';
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
  if(graded.length) s += `, ${right} of ${graded.length} correct so far`;
  else {
    const locked = games.filter(g => picks[g.id]).length;
    if(locked) s += `, ${locked} locked`;
  }
  return s;
}
const CHEVRON = '<svg class="game-row-chev nba-row-chev" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 9l6 6 6-6"/></svg>';
/* Stage 75 item 3: an opened card is brought on screen. A row near the
   bottom of a phone opened its card below the fold and never scrolled
   (NHL card 612 to 1052 px, NFL 704 to 1195 px, on an 844 px phone). 'nearest'
   leaves a card that is already in view where it is. */
function revealOpened(panel){
  const still = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;
  panel.scrollIntoView({block: 'nearest', behavior: still ? 'auto' : 'smooth'});
}
function rowHtml(g, p, nowMs){
  const r = rowResult(g, p, nowMs);
  const id = `nba-detail-${g.id}`;
  return `<li class="nba-row-item">
    <button type="button" class="game-row nba-row" aria-expanded="false" aria-controls="${id}"${scoreMark(g)}>
      <span class="nba-row-time"><span class="score-off">${rowTime(g, p)}</span>${scoreSlot('clock')}</span>
      <span class="nba-row-game"><span class="score-off">${rowGame(g)}</span>${scoreSlot('game')}</span>
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
/* Set by installRoutes at the end of the script (Stage 76 item 7): a chip
   or a week step replaces the address's #board/<day>. */
let replaceRoute = () => {};
/* The rows open on the board, by their card's id (one per game), kept
   across every redraw (Stage 75 item 4). */
const OPEN_ROWS = new Set();
/* Stage 77 item 32 (the 2026-10-13 audit's B1): the board's eyebrow names the
   week it shows. Before opening night the board opens on the week of the
   first games, and it said "This Week" over "Week of Oct 19" on the 13th. */
function weekEyebrow(week, thisWeek){
  if(week === thisWeek) return 'This Week';
  const next = dayDate(thisWeek);
  next.setUTCDate(next.getUTCDate() + 7);
  if(week === dayIso(next)) return 'Next Week';
  return week > thisWeek ? 'Coming Up' : 'Earlier';
}
/* Stage 79 item 48 (B3): the column beside the board at 1280 px and wider,
   as the NHL's (Stage 68 item 37): who is out for each game with a saved
   pick, from the injury report that pick read, and the day before's record.
   Before a pick is saved there is no report to show, and it says so. */
const ALL_BY_DAY = {};
BD.games.forEach(g => (ALL_BY_DAY[g.day] ||= []).push(g));
function sideHtml(day, byDay){
  const games = byDay[day] || [];
  const picked = games.filter(g => BD.picks[g.id]);
  const names = (team, list) => `${team}: ${list && list.length ? list.map(escapeHtml).join(', ') : 'nobody listed out'}`;
  const out = !games.length ? '<p class="nba-side-note">No games this day.</p>'
    : !picked.length ? '<p class="nba-side-note">No pick is saved for this day yet. Who is out is read from the injury report when each pick is saved, by the last run before its game.</p>'
    : `<ul class="nba-side-list">${picked.map(g => {
        const p = BD.picks[g.id];
        const body = p.avail && p.avail.read
          ? `<span>${names(g.away, p.out && p.out.away)}</span><span>${names(g.home, p.out && p.out.home)}</span>`
          : '<span>The injury report was not read when this pick was saved.</span>';
        return `<li><span class="nba-side-game">${g.away} at ${g.home}</span>${body}</li>`;
      }).join('')}</ul>`;
  const prev = new Date(dayDate(day).getTime() - 864e5).toISOString().slice(0, 10);
  const graded = (byDay[prev] || ALL_BY_DAY[prev] || []).map(g => BD.picks[g.id]).filter(p => p && (p.result === 'correct' || p.result === 'wrong'));
  const won = graded.filter(p => p.result === 'correct').length;
  const record = graded.length ? `<p class="nba-side-record"><b>${won}–${graded.length - won}</b> on ${escapeHtml(FMT_DAY.format(dayDate(prev)))}</p>`
    : `<p class="nba-side-note">No graded pick on ${escapeHtml(FMT_DAY.format(dayDate(prev)))}.</p>`;
  return `<h3 class="nba-side-title">Who is out</h3>${out}<h3 class="nba-side-title">The day before</h3>${record}`;
}
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
  document.querySelector('#page-board .page-eyebrow').textContent = weekEyebrow(currentWeek, mondayOf(todayEt()));
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
    return `<button type="button" class="day-chip nba-day-chip" data-day="${d}" aria-pressed="${d === currentDay}" aria-label="${name}"${d === today ? ' aria-current="date"' : ''}>`
      + `<span>${FMT_SHORT.format(dd)}</span><b>${dd.getUTCDate()}</b><span>${n || '–'}</span></button>`;
  }).join('');
  document.querySelectorAll('.nba-day-chip').forEach(btn => btn.addEventListener('click', () => {
    currentDay = btn.dataset.day;
    renderBoard();
    replaceRoute('board');
    const chip = document.querySelector(`.nba-day-chip[data-day="${currentDay}"]`);
    if(chip) chip.focus();
  }));
  // Stage 80 item 53: a favourite team's games first (src/core/favs.js).
  const dayGames = favFirst('nba', byDay[currentDay] || []);
  const side = document.getElementById('nba-side');
  if(side) side.innerHTML = sideHtml(currentDay, byDay);
  const title = `${FMT_DAY.format(dayDate(currentDay))}${currentDay === today ? ' · Today' : ''}`;
  const head = `<div class="nba-day-top"><h3 class="nba-day-title">${title}</h3>`
    + `<p class="nba-day-summary" aria-live="polite">${daySummary(dayGames, BD.picks)}</p></div>`;
  if(!dayGames.length){
    grid.innerHTML = head + preseasonHtml() + (games.length ? '' : stateHtml('waiting', 'No games this week', ''));
    labLinks(grid);
    return;
  }
  const nowMs = Date.now();
  // Stage 80 item 59: the day's records once a game of it is graded (src/core/accuracy.js).
  const gradedToday = dayGames.map(g => ({p: BD.picks[g.id], g})).filter(x => x.p && (x.p.result === 'correct' || x.p.result === 'wrong'));
  grid.innerHTML = head + preseasonHtml() + accSummaryHtml(accGames(gradedToday), dayGames.length)
    + `<ul class="nba-rows">${dayGames.map(g => rowHtml(g, BD.picks[g.id], nowMs)).join('')}</ul>`;
  labLinks(grid);
  // Stage 75 item 4: rows the reader opened stay open when the board is
  // drawn again (the theme toggle, a day chip and back), by game id.
  grid.querySelectorAll('.nba-row').forEach(btn => {
    if(!OPEN_ROWS.has(btn.getAttribute('aria-controls'))) return;
    btn.setAttribute('aria-expanded', 'true');
    document.getElementById(btn.getAttribute('aria-controls')).hidden = false;
  });
  grid.querySelectorAll('.nba-row').forEach(btn => btn.addEventListener('click', () => {
    const open = btn.getAttribute('aria-expanded') !== 'true';
    btn.setAttribute('aria-expanded', String(open));
    const id = btn.getAttribute('aria-controls');
    if(open) OPEN_ROWS.add(id); else OPEN_ROWS.delete(id);
    const card = document.getElementById(id);
    card.hidden = !open;
    if(open) revealOpened(card);
  }));
}
function stepWeek(by){
  const i = WEEK_KEYS.indexOf(currentWeek) + by;
  if(i < 0 || i >= WEEK_KEYS.length) return;
  currentWeek = WEEK_KEYS[i];
  renderBoard();
  replaceRoute('board');
}
document.getElementById('week-prev').addEventListener('click', () => stepWeek(-1));
document.getElementById('week-next').addEventListener('click', () => stepWeek(1));
/* Stage 80 item 57 (the 2026-10-13 audit's F11): on the day board [ and ]
   step a day and Shift with them a week. A day past the week's edge opens
   the next week on its first day (the week before on its last). */
function stepDay(by){
  const days = weekDays(currentWeek);
  const i = days.indexOf(currentDay) + by;
  if(i >= 0 && i < days.length){
    currentDay = days[i];
  } else {
    const w = WEEK_KEYS.indexOf(currentWeek) + by;
    if(w < 0 || w >= WEEK_KEYS.length) return;
    currentWeek = WEEK_KEYS[w];
    const next = weekDays(currentWeek);
    currentDay = by > 0 ? next[0] : next[next.length - 1];
  }
  renderBoard();
  replaceRoute('board');
}
/* Which way a key steps, and whether a week: Shift+[ arrives as "{". */
function dayKeyStep(e){
  if(e.ctrlKey || e.metaKey || e.altKey) return null;
  const by = e.key === '[' || e.key === '{' ? -1 : e.key === ']' || e.key === '}' ? 1 : 0;
  return by ? {by, week: e.shiftKey || e.key === '{' || e.key === '}'} : null;
}
document.addEventListener('keydown', e => {
  if(e.target.closest && e.target.closest('input, select, textarea')) return;
  if(!document.getElementById('page-board').classList.contains('active')) return;
  const step = dayKeyStep(e);
  if(!step) return;
  e.preventDefault();
  if(step.week) stepWeek(step.by); else stepDay(step.by);
});

/* ---------- model lab ---------- */
/* Stage 79 item 51 (the 2026-10-13 audit's B4): the NBA's decisions read as
   the NFL Model Lab's do, a neutral pill, and each interval is drawn against
   zero with the NFL's glyph (generate_dashboard.interval_glyph, Stage 18):
   one frame per row with zero at its centre, the interval and its ends, and
   a dot at the difference, on the row's own scale. */
function plainSigned(x){
  let places = 4;
  while(places < 8 && x !== 0 && Number(Math.abs(x).toFixed(places)) === 0) places++;
  return `${x < 0 ? '−' : '+'}${Math.abs(x).toFixed(places)}`;
}
function intervalGlyph(d, lo, hi){
  const width = 96, height = 14, pad = 5, mid = height / 2;
  const span = Math.max(Math.abs(lo), Math.abs(hi), Math.abs(d)) || 1;
  const x = v => Math.round((pad + (v + span) / (2 * span) * (width - 2 * pad)) * 10) / 10;
  const label = `${plainSigned(d)}, interval ${plainSigned(lo)} to ${plainSigned(hi)}, ${lo <= 0 && 0 <= hi ? 'includes zero' : 'excludes zero'}`;
  return `<svg class="lab-ci" role="img" aria-label="${label}" viewBox="0 0 ${width} ${height}" width="${width}" height="${height}">`
    + `<rect class="lab-ci-frame" x="0.5" y="0.5" width="${width - 1}" height="${height - 1}" rx="3"/>`
    + `<line class="lab-ci-zero" x1="${x(0)}" y1="0" x2="${x(0)}" y2="${height}"/>`
    + `<line class="lab-ci-range" x1="${x(lo)}" y1="${mid}" x2="${x(hi)}" y2="${mid}"/>`
    + `<line class="lab-ci-range" x1="${x(lo)}" y1="${mid - 4}" x2="${x(lo)}" y2="${mid + 4}"/>`
    + `<line class="lab-ci-range" x1="${x(hi)}" y1="${mid - 4}" x2="${x(hi)}" y2="${mid + 4}"/>`
    + `<circle class="lab-ci-point" cx="${x(d)}" cy="${mid}" r="3"/></svg>`;
}
function renderModelLab(){
  const rows = Object.entries(Q).map(([id, q]) => `<tr><th scope="row">${id}</th><td>${QUESTION[id] || ''}</td><td class="num">${signed(q.diff, 4)}</td><td class="num"><span class="lab-lead">${intervalGlyph(q.diff, q.low, q.high)}</span>[${signed(q.low, 4)}, ${signed(q.high, 4)}]</td><td>${q.label ? `<span class="lab-tags"><span class="conf-tag tag-neutral">${escapeHtml(q.label)}</span></span>` : 'a measurement'}</td></tr>`).join('');
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
/* Stage 79 item 46: a graded pick as src/core/accuracy.js reads it. */
function accGames(graded){
  return graded.map(({p, g}) => ({day: g.day, a: p.a, b: p.b, m: p.market ? p.market.prob : null,
    home: winnerOf(g) === g.home, c: pickChance(p, g), right: p.result === 'correct'}));
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
    <thead><tr><th scope="col">The pick's chance</th><th scope="col" class="num">Picks</th><th scope="col" class="num">Said, on average</th><th scope="col" class="num">Correct</th></tr></thead>
    <tbody>${rows}</tbody></table></div>`;
}
function renderReliability(){
  document.getElementById('reliability-body').innerHTML = `
    <h2 class="section-title">The live picks so far</h2>
    ${accuracyHtml(accGames(gradedPicks()))}
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
/* The pages the phone nav keeps under More (Stage 77 item 22), as the NHL's does. */
const OVERFLOW_PAGES = ['method', 'reliability'];
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
  document.title = name === 'board' || !heading ? BASE_TITLE : `NBA ${heading.textContent.trim()} — Sportalytics`;
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
/* Stage 78 item 43: a skip link moves focus and nothing else. Followed as a
   link, its #main-content or #bottom-nav reached the router, which read it as
   an unknown page: the board opened, focus went to its heading, and the
   history gained an entry. */
document.querySelectorAll('.skip-link').forEach(a => a.addEventListener('click', e => {
  const target = document.getElementById(a.getAttribute('href').slice(1));
  if(!target) return;
  e.preventDefault();
  target.focus();
}));
/* Stage 78 item 43: the sheet's own close button. */
document.querySelector('#bnav-more-sheet .bnav-more-close').addEventListener('click', () => {
  setMoreSheetOpen(false);
  document.getElementById('bnav-more-btn').focus();
});
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
/* Stage 80 item 53: a star redraws the board with its team's games first. */
installFavStars(renderBoard);
renderModelLab();
renderMethod();
renderReliability();
/* Stage 76 item 7: #board/<day>. The bare address is the board as it
   opened (this week, today or its first day with games). */
const HOME_WEEK = currentWeek, HOME_DAY = currentDay;
replaceRoute = installRoutes(showPage, {
  // Stage 76 item 9: #game/<id> opens that game's day with its row open.
  open: id => {
    const g = BD.games.find(x => x.id === id);
    if(!g) return;
    currentWeek = mondayOf(g.day);
    currentDay = g.day;
    OPEN_ROWS.add(`nba-detail-${id}`);
    renderBoard();
    // As a tap does (Stage 75 item 3): the card, clear of the top bar and the bottom nav.
    const card = document.getElementById(`nba-detail-${id}`);
    if(card) revealOpened(card);
  },
  known: () => ({days: WEEK_KEYS.flatMap(weekDays), games: BD.games.map(g => g.id)}),
  current: page => (page === 'board' && currentDay !== HOME_DAY ? currentDay : undefined),
  apply: (page, value) => {
    if(page !== 'board') return;
    currentWeek = value ? mondayOf(value) : HOME_WEEK;
    currentDay = value || HOME_DAY;
    renderBoard();
  },
});
document.body.classList.remove('is-entering');
