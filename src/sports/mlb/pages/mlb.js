/* The Content-Security-Policy names the hash of each inline script, so the page has no inline handlers. A logo
   that fails to load (data-hide-on-error) is hidden by this one listener. */
document.addEventListener('error', e => {
  const t = e.target;
  if (t instanceof HTMLImageElement && t.hasAttribute('data-hide-on-error')) t.style.display = 'none';
}, true);
/* MLB's day board (Stage 100 item 1; layout A, Mark 2026-11-22): the NHL's and NBA's board, a strip of the
   week's days and a row a game, with what baseball adds to each row: the two starting pitchers, the game's
   place in its series and how the series stands, and a doubleheader's game number. Everything reads one JSON
   block, #mlb-data, written by src/sports/mlb/site.py. There are no picks yet: MLB's pick file is fixed with
   its writer in Stage 101, and every row until then is a scheduled game. Times are shown in US Eastern, or in
   the visitor's own zone when the Settings sheet says so (src/core/prefs.js). */
const DATA = JSON.parse(document.getElementById('mlb-data').textContent);
const ET = 'America/New_York';
const BD = DATA.board;

/* ---------- days and weeks ---------- */
function dayDate(day){ return new Date(`${day}T12:00:00Z`); }
function dayIso(d){ return d.toISOString().slice(0, 10); }
/* The Monday that starts a day's week: MLB's board steps a week at a time, as the NHL's and NBA's do. */
function mondayOf(day){
  const monday = dayDate(day);
  monday.setUTCDate(monday.getUTCDate() - (monday.getUTCDay() + 6) % 7);
  return dayIso(monday);
}
const FMT_DAY = new Intl.DateTimeFormat('en-US', {weekday: 'long', month: 'short', day: 'numeric', timeZone: 'UTC'});
const FMT_SHORT = new Intl.DateTimeFormat('en-US', {weekday: 'short', timeZone: 'UTC'});
const FMT_MONTHDAY = new Intl.DateTimeFormat('en-US', {month: 'short', day: 'numeric', timeZone: 'UTC'});
const FMT_TIME = new Intl.DateTimeFormat('en-US', {hour: 'numeric', minute: '2-digit', timeZone: startZone()});
const FMT_ET_DATE = new Intl.DateTimeFormat('en-CA', {year: 'numeric', month: '2-digit', day: '2-digit', timeZone: ET});
function todayEt(){ return FMT_ET_DATE.format(new Date()); }
/* A game's first pitch: the day, then the time when the league has set one. An unset start's time in the
   schedule is a placeholder (3:33 AM at the park), and game 2 of a one-ticket doubleheader starts when game 1
   ends, so neither is printed (site.py's 'time'). */
function startLabel(g){
  const day = FMT_DAY.format(dayDate(g.day));
  if(g.time === 'after') return `${day} · after game 1`;
  if(g.time === 'tbd' || !g.start) return `${day} · time TBD`;
  return `${day} · ${FMT_TIME.format(new Date(g.start))}${startMark()}`;
}
/* A day's order: by first pitch, an unset start last (its placeholder would put it first), a doubleheader's
   game 2 straight after game 1 by its estimate. */
function firstPitchOrder(a, b){
  const late = g => (g.time === 'tbd' || !g.start ? 1 : 0);
  return late(a) - late(b) || (a.start || '').localeCompare(b.start || '') || a.id.localeCompare(b.id);
}

/* Club codes reach this page from the schedule and are drawn into its HTML. site.py writes '?' for a club it
   does not know; the page checks again before drawing any, so a bad code shows as "?" and never as markup. */
const TEAM_CODE = /^[A-Z]{2,4}$/;
function clubCode(c){ return TEAM_CODE.test(String(c)) ? c : '?'; }
BD.games.forEach(g => { g.home = clubCode(g.home); g.away = clubCode(g.away); });
const WEEKS = {};
BD.games.forEach(g => { (WEEKS[mondayOf(g.day)] ||= []).push(g); });
const WEEK_KEYS = Object.keys(WEEKS).sort();
/* This week if it has games, else the next week that does, else the last. */
function openingWeek(){
  const now = mondayOf(todayEt());
  if(WEEKS[now]) return now;
  return WEEK_KEYS.find(k => k >= now) || WEEK_KEYS[WEEK_KEYS.length - 1] || now;
}
let currentWeek = openingWeek();
let currentDay = null;
/* Set by installRoutes at the end of the script: a chip or a week step replaces the address's #board/<day>. */
let replaceRoute = () => {};

/* ---------- Opening Day ---------- */
const FIRST_GAME = BD.games.filter(g => g.start).sort(firstPitchOrder)[0] || null;
const OPENING_DAY = FIRST_GAME ? FIRST_GAME.day : null;
/* "Opening Day Thu, Mar 25 — 123 days", in Eastern calendar days, until the day itself. */
const FMT_OPENING = new Intl.DateTimeFormat('en-US', {weekday: 'short', month: 'short', day: 'numeric', timeZone: 'UTC'});
function openingCountdown(today){
  if(!OPENING_DAY) return '';
  const days = Math.round((Date.parse(OPENING_DAY) - Date.parse(today)) / 86400000);
  if(days < 0) return '';
  const away = days === 0 ? 'today' : days === 1 ? 'tomorrow' : `${days} days`;
  return `Opening Day ${FMT_OPENING.format(dayDate(OPENING_DAY))} — ${away}`;
}
/* Until a pick is saved, the board says so above the rows. */
function preseasonHtml(){
  if(Object.keys(BD.picks || {}).length || !FIRST_GAME) return '';
  const countdown = openingCountdown(todayEt());
  return `<div class="mlb-preseason" role="note">${countdown ? `<p class="mlb-countdown">${escapeHtml(countdown)}</p>` : ''}`
    + `<p><b>No picks yet.</b> MLB's picks start on Opening Day, each saved before its first pitch and never changed. `
    + 'Until then the board shows the schedule, the starting pitchers once each club names one, and where each series stands.</p></div>';
}

/* ---------- baseball's lines ---------- */
/* The starters, away first as the game is written: "Joe Ryan v Kenta Maeda". A club that has not named its
   starter yet reads "to be named". */
function startersText(g){
  if(!g.asp && !g.hsp) return '';
  const one = name => (name ? escapeHtml(name) : 'to be named');
  return `${one(g.asp)} v ${one(g.hsp)}`;
}
/* "Game 2 of 4 · DET leads 1-0", from the series' earlier games that are final (site.py counts them). */
function seriesText(g){
  const s = g.series;
  if(!s) return '';
  const place = `Game ${s.game} of ${s.of}`;
  if(s.home_won === s.away_won) return s.home_won ? `${place} · tied ${s.home_won}-${s.away_won}` : place;
  const lead = s.home_won > s.away_won ? g.home : g.away;
  return `${place} · ${lead} leads ${Math.max(s.home_won, s.away_won)}-${Math.min(s.home_won, s.away_won)}`;
}
function doubleheaderTag(g){
  return g.dh ? `<span class="mlb-dh">Doubleheader · game ${g.dh}</span>` : '';
}
function scoreLine(g){
  if(g.status === 'cancelled') return 'Cancelled';
  if(g.status === 'postponed') return 'Postponed';
  if(g.status === 'suspended') return 'Suspended';
  if(g.status === 'in_progress') return 'In progress';
  if(g.status !== 'final' || g.hs === null || g.as === null) return '';
  return `Final: ${g.away} ${g.as}, ${g.home} ${g.hs}`;
}

/* ---------- the card ---------- */
function waitingCard(g){
  const status = scoreLine(g);
  const starters = startersText(g);
  const series = seriesText(g);
  let note;
  if(g.status === 'postponed' || g.status === 'cancelled' || g.status === 'suspended') note = 'No pick: a postponed, suspended or cancelled game is not predicted.';
  else if(g.status === 'final' || g.status === 'in_progress') note = 'No pick was saved for this game.';
  else note = 'Picks start on Opening Day, each saved before its first pitch.';
  return `<div class="game-card mlb-not-saved">
    <div class="matchup-header">${g.away} <span class="at-symbol">at</span> ${g.home}</div>
    <div class="card-kickoff">${startLabel(g)}</div>
    ${status ? `<div class="mlb-card-status">${status}</div>` : ''}
    <div class="mlb-card-line">Starting pitchers: ${starters ? `<b>${starters}</b>` : 'not named yet'}</div>
    ${series || g.dh ? `<div class="mlb-card-line">${doubleheaderTag(g)}${series ? `<span class="mlb-series">${series}</span>` : ''}</div>` : ''}
    <div class="mlb-wait-note">${note}</div>
  </div>`;
}

/* ---------- rows, a day at a time ---------- */
const FMT_HOUR = new Intl.DateTimeFormat('en-US', {hour: 'numeric', minute: '2-digit', timeZone: startZone()});
function mlbResult(g){
  if(g.status === 'postponed') return {text: 'Postponed', cls: 'off'};
  if(g.status === 'suspended') return {text: 'Suspended', cls: 'off'};
  if(g.status === 'cancelled') return {text: 'Cancelled', cls: 'off'};
  if(g.status === 'in_progress') return {text: 'Live', cls: 'live'};
  if(g.status === 'final') return {text: 'No pick', cls: 'off'};
  return {text: '', cls: 'open'};
}
function mlbTime(g){
  if(g.status === 'final') return 'Final';
  if(g.time === 'after') return 'After G1';
  if(g.time === 'tbd' || !g.start) return 'TBD';
  return FMT_HOUR.format(new Date(g.start));
}
function mlbGame(g){
  const won = winnerOf(g);
  const has = g.status === 'final' && g.hs !== null && g.hs !== undefined && g.as !== null && g.as !== undefined;
  const team = (abbr, score) => {
    const text = has ? `${abbr} ${score}` : abbr;
    return `<span class="mlb-row-team">${abbr === won ? `<b>${text}</b>` : text}</span>`;
  };
  const starters = startersText(g);
  // The place and the standing each stay whole; on a phone the line wraps between them.
  const series = seriesText(g).split(' · ').filter(Boolean).map(s => `<span class="mlb-series">${s}</span>`).join(' · ');
  const meta = doubleheaderTag(g) + series;
  return `${team(g.away, g.as)} <span class="at-symbol">@</span> ${team(g.home, g.hs)}`
    + (starters ? `<span class="mlb-row-sp">${starters}</span>` : '')
    + (meta ? `<span class="mlb-row-meta">${meta}</span>` : '');
}
const CHEVRON = '<svg class="game-row-chev mlb-row-chev" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 9l6 6 6-6"/></svg>';
function mlbRow(g){
  const r = mlbResult(g);
  const id = `mlb-detail-${g.id}`;
  return `<li class="mlb-row-item">
    <button type="button" class="game-row mlb-row" aria-expanded="false" aria-controls="${id}">
      <span class="mlb-row-time">${mlbTime(g)}</span>
      <span class="mlb-row-game">${mlbGame(g)}</span>
      <span class="mlb-row-pick">—</span>
      <span class="mlb-row-result ${r.cls}">${r.text}</span>${CHEVRON}
    </button>
    <div class="mlb-row-detail" id="${id}" hidden>${waitingCard(g)}</div>
  </li>`;
}
/* The rows the reader opened, by their card's id, kept across every redraw. */
const OPEN_ROWS = new Set();
function renderBoard(){
  const grid = document.getElementById('game-grid');
  if(!BD.games.length){
    document.getElementById('week-step').closest('.filter-row').style.display = 'none';
    document.getElementById('mlb-day-strip').innerHTML = '';
    grid.innerHTML = stateHtml('waiting', 'The board fills from the first daily run',
      "MLB's schedule arrives with the daily run (Stage 101). Picks start on Opening Day, each saved before its first pitch and never changed.");
    return;
  }
  const games = (WEEKS[currentWeek] || []).slice().sort(firstPitchOrder);
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
  document.getElementById('mlb-day-strip').innerHTML = days.map(d => {
    const dd = dayDate(d);
    const n = (byDay[d] || []).length;
    const name = `${FMT_DAY.format(dd)}${d === today ? ', today' : ''}, ${n ? `${n} game${n === 1 ? '' : 's'}` : 'no games'}`;
    return `<button type="button" class="day-chip mlb-day-chip" data-day="${d}" aria-pressed="${d === currentDay}" aria-label="${name}"${d === today ? ' aria-current="date"' : ''}>`
      + `<span>${FMT_SHORT.format(dd)}</span><b>${dd.getUTCDate()}</b><span>${n || '–'}</span></button>`;
  }).join('');
  document.querySelectorAll('.mlb-day-chip').forEach(btn => btn.addEventListener('click', () => {
    currentDay = btn.dataset.day;
    renderBoard();
    replaceRoute('board');
    const chip = document.querySelector(`.mlb-day-chip[data-day="${currentDay}"]`);
    if(chip) chip.focus();
  }));
  // A favourite club's games first (src/core/favs.js).
  const dayGames = favFirst('mlb', byDay[currentDay] || []);
  const title = `${FMT_DAY.format(dayDate(currentDay))}${currentDay === today ? ' · Today' : ''}`;
  const head = `<div class="mlb-day-top"><h3 class="mlb-day-title">${title}</h3>`
    + `<p class="mlb-day-summary" aria-live="polite">${daySummary(dayGames, BD.picks)}</p></div>`;
  if(!dayGames.length){
    grid.innerHTML = head + preseasonHtml() + (games.length ? '' : stateHtml('waiting', 'No games this week', ''));
    return;
  }
  grid.innerHTML = head + preseasonHtml() + `<ul class="mlb-rows">${dayGames.map(mlbRow).join('')}</ul>`;
  grid.querySelectorAll('.mlb-row').forEach(btn => {
    if(!OPEN_ROWS.has(btn.getAttribute('aria-controls'))) return;
    btn.setAttribute('aria-expanded', 'true');
    document.getElementById(btn.getAttribute('aria-controls')).hidden = false;
  });
  grid.querySelectorAll('.mlb-row').forEach(btn => btn.addEventListener('click', () => {
    const open = btn.getAttribute('aria-expanded') !== 'true';
    btn.setAttribute('aria-expanded', String(open));
    const id = btn.getAttribute('aria-controls');
    if(open) OPEN_ROWS.add(id); else OPEN_ROWS.delete(id);
    const card = document.getElementById(id);
    card.hidden = !open;
    if(open) revealOpened(card);
  }));
}
document.getElementById('week-prev').addEventListener('click', () => stepWeek(-1));
document.getElementById('week-next').addEventListener('click', () => stepWeek(1));
document.addEventListener('keydown', e => {
  if(e.target.closest && e.target.closest('input, select, textarea')) return;
  const step = dayKeyStep(e);
  if(!step) return;
  e.preventDefault();
  if(step.week) stepWeek(step.by); else stepDay(step.by);
});

/* ---------- the page around the board ----------
   One page so far (the board); the others arrive with Stage 100 item 2, and each button for the page shown
   carries aria-current, as on the other sports. */
const BASE_TITLE = document.title;
function showMlbPage(name, opts){
  document.querySelectorAll('.page').forEach(p => p.classList.toggle('active', p.id === 'page-' + name));
  document.querySelectorAll('[data-page]').forEach(b => {
    const on = b.dataset.page === name;
    b.classList.toggle('active', on);
    if(on) b.setAttribute('aria-current', 'page'); else b.removeAttribute('aria-current');
  });
  window.scrollTo(0, 0);
  const page = document.getElementById('page-' + name);
  const heading = page && page.querySelector('.page-head h2');
  document.title = name === 'board' || !heading ? BASE_TITLE : `MLB ${heading.textContent.trim()} — Sportalytics`;
  if(opts && opts.focus && heading){
    heading.setAttribute('tabindex', '-1');
    heading.focus({preventScroll: true});
  }
}
document.querySelectorAll('[data-page]').forEach(b => b.addEventListener('click', () => showMlbPage(b.dataset.page, {focus: true})));
/* A skip link moves focus and nothing else, so the router never reads it as a page. */
document.querySelectorAll('.skip-link').forEach(a => a.addEventListener('click', e => {
  const target = document.getElementById(a.getAttribute('href').slice(1));
  if(!target) return;
  e.preventDefault();
  target.focus();
}));
/* The browser checks open each page by its section id. */
window.setActivePage = id => showMlbPage(String(id).replace(/^page-/, ''));
(function(){
  const bar = document.querySelector('.topbar');
  if(!bar) return;
  const write = () => document.documentElement.style.setProperty('--topbar-h', bar.offsetHeight + 'px');
  write();
  if(typeof ResizeObserver === 'function') new ResizeObserver(write).observe(bar, {box: 'border-box'});
  window.addEventListener('resize', write);
})();
function mlbTheme(){ return document.documentElement.getAttribute('data-theme') === 'light' ? 'light' : 'dark'; }
function mlbThemeLabel(){ const l = document.getElementById('theme-toggle-label'); if(l) l.textContent = mlbTheme() === 'light' ? 'Dark mode' : 'Light mode'; }
document.querySelectorAll('#theme-toggle, .topbar-theme').forEach(btn => btn.addEventListener('click', () => {
  const next = mlbTheme() === 'light' ? 'dark' : 'light';
  if(next === 'light') document.documentElement.setAttribute('data-theme', 'light');
  else document.documentElement.removeAttribute('data-theme');
  try{ localStorage.setItem('site:theme', next); }catch(e){}
  mlbThemeLabel();
  renderBoard();
}));

const BUILT = new Date(DATA.built_utc).toLocaleString('en-US', {timeZone: ET, month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit'});
document.getElementById('built-line').textContent = `Updated ${BUILT} ET`;
document.getElementById('board-updated').textContent = `Updated ${BUILT} ET${BD.schedule_as_of ? `, schedule as of ${dayText(BD.schedule_as_of)}` : ''}`;
mlbThemeLabel();
renderBoard();
/* A star redraws the board with its club's games first. */
installFavStars(renderBoard);
/* #board/<day> and #game/<id>, as on the other day boards (src/core/routes.js). */
const HOME_WEEK = currentWeek, HOME_DAY = currentDay;
replaceRoute = installRoutes(showMlbPage, {
  open: id => {
    const g = BD.games.find(x => x.id === id);
    if(!g) return;
    currentWeek = mondayOf(g.day);
    currentDay = g.day;
    OPEN_ROWS.add(`mlb-detail-${id}`);
    renderBoard();
    const card = document.getElementById(`mlb-detail-${id}`);
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
window.addEventListener('beforeprint', () => {
  const at = new Date().toLocaleDateString('en-US', {weekday: 'long', month: 'long', day: 'numeric', year: 'numeric'});
  document.querySelectorAll('[data-print-date]').forEach(el => { el.textContent = `Printed ${at}.`; });
});
