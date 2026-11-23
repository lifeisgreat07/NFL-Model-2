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

/* ---------- tables that scroll ----------
   The NFL board's rule (src/dashboard/app.js, Stage 12), as the NBA's page
   has it (Stage 100 item 4: axe found MLB's Model Lab and Methodology
   tables out of the Tab order at 390px): a table wider than
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

/* ---------- standings (Stage 100 item 3; layout B, Mark 2026-11-23) ----------
   The NHL's division tables, plus each league's wild card race: the clubs not leading a division, by record, with
   a line under the third. The race is the table as it stands, not MLB's seeding: level clubs are shown by projected
   wins, and only the simulation applies MLB's tiebreakers (src/sports/mlb/standings.py). */
const LEAGUES = {AL: 'American League', NL: 'National League'};
const RACE_ROWS = 8;
function chance(x){
  if(x <= 0) return '0%';
  if(x >= 1) return '100%';
  return x < 0.005 ? '&lt;1%' : x > 0.995 ? '&gt;99%' : `${Math.round(x * 100)}%`;
}
function winPct(t){ return t.wins_now + t.losses_now ? t.wins_now / (t.wins_now + t.losses_now) : 0; }
function byRecord(a, b){ return winPct(b) - winPct(a) || b.projected_wins - a.projected_wins || (a.team < b.team ? -1 : 1); }
function wildCardRace(teams, league){
  const mine = teams.filter(t => t.league === league);
  const leaders = new Set([...new Set(mine.map(t => t.division))]
    .map(d => mine.filter(t => t.division === d).sort(byRecord)[0].team));
  const rest = mine.filter(t => !leaders.has(t.team)).sort(byRecord);
  const third = rest[2];
  return rest.map((t, i) => ({...t, place: i + 1,
    back: third && i > 2 ? ((third.wins_now - t.wins_now) + (t.losses_now - third.losses_now)) / 2 : 0}));
}
function gamesBack(n){ return n > 0 ? String(n) : '–'; }
function standingsClub(code){
  const c = clubCode(code);
  return `<span class="mlb-club-full">${escapeHtml((BD.teams[c] || {}).name || c)}</span><span class="mlb-club-abbr">${c}</span>`;
}
function divisionTable(teams, division){
  const rows = teams.filter(t => t.division === division).sort((a, b) => b.projected_wins - a.projected_wins);
  return `<div><h3>${escapeHtml(division)}</h3><div class="table-wrap"><table class="metrics-table mlb-table">`
    + `<caption class="visually-hidden">${escapeHtml(division)}</caption><thead><tr><th scope="col">Club</th>`
    + '<th scope="col" class="num">W-L</th><th scope="col" class="num">Proj. W</th><th scope="col" class="num">Division</th>'
    + '<th scope="col" class="num">Postseason</th></tr></thead><tbody>'
    + rows.map(t => `<tr><th scope="row">${standingsClub(t.team)}</th><td class="num">${t.wins_now}-${t.losses_now}</td>`
      + `<td class="num">${t.projected_wins.toFixed(1)}</td><td class="num">${chance(t.division_pct)}</td>`
      + `<td class="num">${chance(t.playoff_pct)}</td></tr>`).join('')
    + '</tbody></table></div></div>';
}
function raceTable(teams, league){
  const race = wildCardRace(teams, league).slice(0, RACE_ROWS);
  return `<div><h3>${league} wild card race</h3><div class="table-wrap"><table class="metrics-table mlb-table">`
    + `<caption class="visually-hidden">${LEAGUES[league]} wild card race</caption><thead><tr><th scope="col">#</th>`
    + '<th scope="col">Club</th><th scope="col" class="num">W-L</th><th scope="col" class="num">GB</th>'
    + '<th scope="col" class="num">Proj. W</th><th scope="col" class="num">Wild card</th></tr></thead><tbody>'
    + race.map(t => `<tr${t.place === 3 ? ' class="mlb-wc-line"' : ''}><td class="rank">${t.place}</td>`
      + `<th scope="row">${standingsClub(t.team)}</th><td class="num">${t.wins_now}-${t.losses_now}</td>`
      + `<td class="num">${gamesBack(t.back)}</td><td class="num">${t.projected_wins.toFixed(1)}</td>`
      + `<td class="num">${chance(t.wildcard_pct)}</td></tr>`).join('')
    + '</tbody></table></div></div>';
}
function renderStandings(){
  const s = BD.standings, el = document.getElementById('standings-body');
  if(!s){
    el.innerHTML = stateHtml('waiting', 'Not simulated yet', 'The daily run simulates the season once games are played.');
    return;
  }
  const head = `<p class="mlb-lede">As of ${escapeHtml(dayText(s.as_of))}: the rest of the regular season played out `
    + `${Number(s.simulations).toLocaleString('en-US')} times. Three division winners and three wild cards per league `
    + 'reach the postseason; the top two seeds skip the Wild Card Series. The wild card race lists the clubs not leading '
    + 'a division, by record, with a line under the third; MLB&#39;s tiebreakers are applied in the simulation, not to '
    + 'this order. Each game&#39;s chance is held fixed for the rest of the season, which makes these odds surer than '
    + 'they should be, most of all early on: real clubs change, and 0% or 100% means only that no simulated season went '
    + 'the other way.</p>';
  el.innerHTML = head + Object.entries(LEAGUES).map(([lg, name]) => {
    const divs = ['East', 'Central', 'West'].map(d => `${lg} ${d}`);
    return `<h2 class="section-title">${name}</h2><div class="mlb-div-grid">`
      + divs.map(d => divisionTable(s.teams, d)).join('') + raceTable(s.teams, lg) + '</div>';
  }).join('');
}

/* ---------- power ratings (Stage 100 item 2; layout C, Mark 2026-11-23) ----------
   Two views behind chips. Clubs: the NHL's and NBA's table, each club's run rating as a bar about zero. Starters:
   every pitcher with enough starts this season, by runs allowed per 27 outs, best first; a club filter, a sort, and
   the first STARTERS_SHOWN until "Show all" (a season has 250 or so). */
const STARTERS_SHOWN = 40;
const RATINGS = {view: 'clubs', club: '', sort: 'best', all: false};
function plusMinus(x, digits){ return (x > 0 ? '+' : x < 0 ? '-' : '') + Math.abs(x).toFixed(digits); }
function startersShown(starters, club, sort, all){
  const mine = starters.filter(s => !club || s.club === club);
  const order = sort === 'starts' ? [...mine].sort((a, b) => b.starts - a.starts || a.rate - b.rate) : mine;
  return {rows: all ? order : order.slice(0, STARTERS_SHOWN), of: order.length};
}
function clubsTable(r){
  const scale = Math.max(...r.clubs.map(c => Math.abs(c.runs)), 0.01);
  const rows = r.clubs.map((c, i) => {
    const w = Math.abs(c.runs) / scale * 50, code = clubCode(c.team);
    return `<tr><td class="rank">${i + 1}</td><td><div class="team-cell"><span class="team-abbr">${code}</span>`
      + `<span class="team-full">${escapeHtml((BD.teams[code] || {}).name || code)}</span></div></td>`
      + `<td class="num"><div class="net-cell-inner"><div class="srs-bar-track diverging" title="${plusMinus(c.runs, 2)} runs a game">`
      + `<div class="srs-bar-fill" style="left:${c.runs >= 0 ? 50 : 50 - w}%; width:${w}%;"></div></div>`
      + `<span class="net-value">${plusMinus(c.runs, 2)}</span></div></td></tr>`;
  }).join('');
  return '<div class="table-wrap"><table class="metrics-table"><caption class="visually-hidden">Club ratings</caption>'
    + `<thead><tr><th scope="col">#</th><th scope="col">Club</th><th scope="col" style="text-align:center;">`
    + `<div class="net-head"><span>Runs a game</span><div class="net-head-row"><div class="net-axis" aria-hidden="true">`
    + `<span class="ax-min">${plusMinus(-scale, 2)}</span><span class="ax-zero">0</span><span class="ax-max">${plusMinus(scale, 2)}</span>`
    + `</div><span></span></div></div></th></tr></thead><tbody>${rows}</tbody></table></div>`;
}
function startersTable(r){
  const shown = startersShown(r.starters, RATINGS.club, RATINGS.sort, RATINGS.all);
  const clubs = [...new Set(r.starters.map(s => clubCode(s.club)))].sort();
  const controls = '<div class="mlb-rating-controls">'
    + `<label>Club <select class="btn" data-ratings-club><option value="">All ${clubs.length}</option>`
    + clubs.map(c => `<option value="${c}"${c === RATINGS.club ? ' selected' : ''}>${c}</option>`).join('') + '</select></label>'
    + `<label>Sort <select class="btn" data-ratings-sort><option value="best"${RATINGS.sort === 'best' ? ' selected' : ''}>Best first</option>`
    + `<option value="starts"${RATINGS.sort === 'starts' ? ' selected' : ''}>Most starts</option></select></label></div>`;
  const rows = shown.rows.map((s, i) => `<tr><td class="rank">${i + 1}</td>`
    + `<th scope="row">${escapeHtml(s.name || s.player_id)}</th><td>${clubCode(s.club)}</td>`
    + `<td class="num">${s.rate.toFixed(2)}</td><td class="num">${plusMinus(r.league_rate - s.rate, 2)}</td>`
    + `<td class="num">${s.starts}</td></tr>`).join('');
  const more = shown.rows.length < shown.of
    ? `<p class="mlb-rating-more">Showing ${shown.rows.length} of ${shown.of} · <button type="button" class="btn-link" data-ratings-all>Show all</button></p>` : '';
  return controls + '<div class="table-wrap"><table class="metrics-table mlb-table"><caption class="visually-hidden">Starting pitchers</caption>'
    + '<thead><tr><th scope="col">#</th><th scope="col">Pitcher</th><th scope="col">Club</th>'
    + '<th scope="col" class="num">Runs per 9</th><th scope="col" class="num">Better than league</th>'
    + `<th scope="col" class="num">Starts</th></tr></thead><tbody>${rows}</tbody></table></div>${more}`;
}
function renderRatings(){
  const r = BD.ratings, el = document.getElementById('ratings-body');
  if(!r){ el.innerHTML = stateHtml('waiting', 'No ratings yet', 'The daily run writes them once games are played.'); return; }
  const chip = (v, label) => `<button type="button" class="btn btn-chip${RATINGS.view === v ? ' active' : ''}" `
    + `aria-pressed="${RATINGS.view === v}" data-ratings-view="${v}">${label}</button>`;
  const lede = RATINGS.view === 'clubs'
    ? `<p class="mlb-lede">As of ${escapeHtml(dayText(r.as_of))}. A club&#39;s rating is how many runs a game better than an average club it has been, fitted to every earlier game&#39;s run margin, recent games counting more and every club pulled a little toward average.</p>`
    : `<p class="mlb-lede">As of ${escapeHtml(dayText(r.as_of))}. A starter&#39;s rating is the runs he allows per 27 outs (nine innings), recent outings counting more and pulled toward the league&#39;s ${r.league_rate.toFixed(2)} by ${Number(r.K_outs).toLocaleString('en-US')} outs, so a pitcher with few innings sits near average. Listed: pitchers with ${r.min_starts} or more starts this season.</p>`;
  el.innerHTML = `<div class="mlb-rating-chips" role="group" aria-label="Ratings to show">${chip('clubs', 'Clubs')}${chip('starters', 'Starters')}</div>`
    + lede + (RATINGS.view === 'clubs' ? clubsTable(r) : startersTable(r));
}
document.getElementById('ratings-body').addEventListener('click', e => {
  const view = e.target.closest('[data-ratings-view]');
  if(view){ RATINGS.view = view.dataset.ratingsView; renderRatings(); return; }
  if(e.target.closest('[data-ratings-all]')){ RATINGS.all = true; renderRatings(); }
});
document.getElementById('ratings-body').addEventListener('change', e => {
  if(e.target.matches('[data-ratings-club]')){ RATINGS.club = e.target.value; RATINGS.all = false; }
  else if(e.target.matches('[data-ratings-sort]')) RATINGS.sort = e.target.value;
  else return;
  renderRatings();
});

/* ---------- model lab and methodology (Stage 100 item 2) ----------
   Read from the registration (experiments/mlb/stage98/registry.json), its tuning, and the confirmation once it has
   run (`python -m src.sports.mlb.backtest confirm`, once, when Retrosheet posts the 2026 game log). Before then each
   question is DEFERRED and says what it waits for. */
const LAB = DATA.lab;
const REGISTRY_URL = 'https://github.com/lifeisgreat07/NFL-Model-2/blob/main/experiments/mlb/stage98/registry.json';
const MODEL_NAMES = {model_a: 'Model A', model_b: 'Model B', market: 'The market', base_rate: 'Home-win base rate',
  model_a_no_starter: 'Model A without the starter'};
function seasonsText(list){ return list.length > 1 ? `${list[0]} and ${list[list.length - 1]}` : String(list[0]); }
function labLevel(p){ return 1 - p.alpha / p.budget_m; }
function signed4(x){ return (x > 0 ? '+' : x < 0 ? '-' : '') + Math.abs(x).toFixed(4); }
/* A tuned setting at either end of the range the registration searched is said so: a wider search could have gone
   further that way (as the NBA's page says of its ridge strength). */
function gridEdges(grid, chosen){
  return Object.keys(grid).filter(k => {
    const v = grid[k], c = chosen[k];
    return v.length > 1 && (c === Math.min(...v) || c === Math.max(...v));
  }).map(k => ({key: k, value: chosen[k], end: chosen[k] === Math.min(...grid[k]) ? 'smallest' : 'largest'}));
}
const GRID_LABEL = {H_days: 'half-life (days)', lambda: 'ridge strength', K_outs: 'starter shrinkage (outs)'};
function questionRow(q, answer){
  const head = `<th scope="row">${q.id}</th><td><b>${escapeHtml(q.title)}</b><br>${escapeHtml(q.question)}</td>`;
  if(!answer){
    const tag = q.kind === 'measurement' ? 'a measurement' : '<span class="conf-tag tag-neutral">DEFERRED</span>';
    const expected = q.expected ? `<br><span class="mlb-lab-note">Expected when registered: ${escapeHtml(q.expected)}</span>` : '';
    return `<tr>${head}<td class="num">-</td><td class="num">-</td><td>${tag}${expected}</td></tr>`;
  }
  const decision = answer.label ? `<span class="conf-tag tag-neutral">${escapeHtml(answer.label)}</span>` : 'a measurement';
  return `<tr>${head}<td class="num">${signed4(answer.diff)}</td><td class="num"><span class="lab-lead">${intervalGlyph(answer.diff, answer.low, answer.high)}</span>`
    + `[${signed4(answer.low)}, ${signed4(answer.high)}]</td><td>${decision}</td></tr>`;
}
function renderModelLab(){
  const el = document.getElementById('modellab-body');
  if(!LAB){ el.innerHTML = stateHtml('waiting', 'Not built yet', ''); return; }
  const p = LAB.protocol, conf = LAB.confirmation, t = LAB.tuning;
  const waiting = conf ? '' : `<p class="mlb-lede"><b>Not answered yet.</b> The confirmation runs once, when Retrosheet posts its ${Math.max(...p.confirmation_seasons)} game log: every season is checked against it before the backtest reads it. Until then each question is DEFERRED.</p>`;
  const answers = (conf && conf.questions) || {};
  const rows = LAB.questions.map(q => questionRow(q, answers[q.id])).join('');
  const scores = conf ? `<h2 class="section-title">Scores on ${seasonsText(conf.seasons)}</h2>
    <div class="table-wrap"><table class="metrics-table mlb-table"><caption class="visually-hidden">Scores on the confirmation seasons</caption>
    <thead><tr><th scope="col">Forecast</th><th scope="col" class="num">Games</th><th scope="col" class="num">Log loss</th><th scope="col" class="num">Brier</th><th scope="col" class="num">Accuracy</th></tr></thead>
    <tbody>${Object.entries(conf.scores).map(([k, s]) => `<tr><th scope="row">${MODEL_NAMES[k] || escapeHtml(k)}</th><td class="num">${s.games.toLocaleString('en-US')}</td><td class="num">${s.log_loss.toFixed(4)}</td><td class="num">${s.brier.toFixed(4)}</td><td class="num">${(s.accuracy * 100).toFixed(1)}%</td></tr>`).join('')}</tbody></table></div>
    <p class="mlb-lede">Accuracy is printed, never decides: at this many games it moves by a game or two between machines, where log loss does not.</p>` : '';
  const tuning = t ? (() => {
    const on = g => g.H_days === t.chosen.H_days && g.lambda === t.chosen.lambda && g.K_outs === t.chosen.K_outs;
    const edges = gridEdges(LAB.grid, t.chosen).map(e => `the ${GRID_LABEL[e.key] || e.key}, ${e.value.toLocaleString('en-US')}, is the ${e.end} the grid searched`);
    const edgeText = edges.length ? `<p class="mlb-lede"><b>At the edge of the grid.</b> In the chosen setting ${edges.join('; ')}. A wider search might have gone further that way; that is for next season&#39;s registration, not a change to this one.</p>` : '';
    return `<h2 class="section-title">Tuning on ${seasonsText(t.seasons)}</h2>
    <p class="mlb-lede">Model A&#39;s log loss over the validation seasons for each registered setting: ${t.searched} were searched, and the ${t.best.length} best are listed. The lowest was kept and fixed before any confirmation season was scored.</p>
    <div class="table-wrap"><table class="metrics-table mlb-table"><caption class="visually-hidden">The tuning grid's best settings</caption>
    <thead><tr><th scope="col" class="num">Half-life (days)</th><th scope="col" class="num">Ridge</th><th scope="col" class="num">Starter shrinkage (outs)</th><th scope="col" class="num">Log loss</th><th scope="col"></th></tr></thead>
    <tbody>${t.best.map(g => `<tr${on(g) ? ' class="mlb-chosen"' : ''}><td class="num">${g.H_days}</td><td class="num">${g.lambda}</td><td class="num">${g.K_outs}</td><td class="num">${g.log_loss.toFixed(5)}</td><td>${on(g) ? 'chosen' : ''}</td></tr>`).join('')}</tbody></table></div>${edgeText}`;
  })() : '';
  el.innerHTML = `<p class="mlb-lede">Registered on ${escapeHtml(dayText(LAB.registered))}, before any MLB model was fitted (<a href="${REGISTRY_URL}">the registration</a>): tuned on ${seasonsText(p.validation_seasons)}, then answered once on ${seasonsText(p.confirmation_seasons)}. A difference below zero means the first model forecast better. Each interval resamples whole game days and is ${(labLevel(p) * 100).toFixed(2)}% sure, wider than the usual 95% because ${p.budget_m} questions share that 95%; a result counts only when the interval excludes zero.</p>
    ${waiting}
    <div class="table-wrap"><table class="metrics-table mlb-table"><caption class="visually-hidden">The backtest's questions</caption>
    <thead><tr><th scope="col">#</th><th scope="col">Question</th><th scope="col" class="num">Log loss difference</th><th scope="col" class="num">Interval</th><th scope="col">Decision</th></tr></thead>
    <tbody>${rows}</tbody></table></div>${scores}${tuning}`;
}
function renderMethod(){
  const el = document.getElementById('method-body');
  if(!LAB){ el.innerHTML = stateHtml('waiting', 'Not built yet', ''); return; }
  const p = LAB.protocol, c = (LAB.tuning || {}).chosen;
  const set = c ? ` (half as much every ${c.H_days} days; ridge strength ${c.lambda}; ${c.K_outs.toLocaleString('en-US')} outs of shrinkage)` : '';
  const cov = LAB.coverage.map(r => `<tr><th scope="row">${r.season}</th><td class="num">${r.games.toLocaleString('en-US')}</td><td class="num">${r.priced.toLocaleString('en-US')}</td><td>${r.checked ? 'yes' : 'not yet'}</td></tr>`).join('');
  el.innerHTML = `
    <p class="mlb-lede"><b>Model A</b> reads two numbers about a game, each favouring the home club when positive. One is the clubs&#39; run ratings, home minus away, from a ridge regression of every earlier game&#39;s run margin, recent games counting more${set}. The other is the starting pitchers: the away starter&#39;s runs allowed per 27 outs minus the home starter&#39;s, each pulled toward the league&#39;s rate until he has pitched enough. A logistic regression turns the two into a home-win probability, and on a game at a neutral park Model A drops its fitted home edge.</p>
    <p class="mlb-lede"><b>Model B</b> is Model A plus the market: the logit of ESPN&#39;s moneyline with the bookmaker&#39;s margin taken out, trained only on games that had a price. It keeps its fitted intercept at a neutral park, because the price already carries the site (an amendment after audit 8, on <a href="${REGISTRY_URL}">the registration</a>).</p>
    <p class="mlb-lede"><b>The test.</b> Every regular-season and postseason game from ${p.training_from_season} on. Before each game day both models are refitted on every earlier game and predict that day&#39;s games, so nothing a game did is known before it. The settings were chosen on ${seasonsText(p.validation_seasons)} only, then fixed, and ${seasonsText(p.confirmation_seasons)} are scored once. ${p.budget_m} questions share a ${(p.alpha * 100).toFixed(0)}% error budget, so each interval is at ${(labLevel(p) * 100).toFixed(2)}%. Log loss decides; accuracy is printed, never decides. The answers are on <a href="#modellab">Model Lab</a>.</p>
    <p class="mlb-lede"><b>The live picks</b> start with the ${p.forward_holdout_season} season, under a forward test registered before the first is saved: each game&#39;s pick saved before first pitch and never changed.</p>
    <p class="mlb-lede"><b>What the backtest knew that a live pick will not:</b> who actually started, from the box score. A live pick knows only the probable pitcher announced before the game. The registration measures that gap (M2) once 200 live games are graded.</p>
    <p class="mlb-lede"><b>Not in this registration</b>, each needing its own: ${LAB.not_registered.map(escapeHtml).join(' ')}</p>
    <h2 class="section-title">The games</h2>
    <p class="mlb-lede">Results, starters and venues are the MLB Stats API&#39;s, every season checked against Retrosheet&#39;s game logs before the backtest reads it. The check compares regular-season games only: the postseason, 32 to 53 games a season, is used unchecked, as the registration discloses. Prices are ESPN&#39;s, without a provider that publishes a model&#39;s output rather than a book&#39;s price.</p>
    <div class="table-wrap"><table class="metrics-table mlb-table"><caption class="visually-hidden">Games and prices per season</caption>
    <thead><tr><th scope="col">Season</th><th scope="col" class="num">Games</th><th scope="col" class="num">With a price</th><th scope="col">Checked against Retrosheet</th></tr></thead>
    <tbody>${cov}</tbody></table></div>`;
}

/* ---------- teams (Stage 100 item 2) ----------
   The NHL's Teams page, one club at a time: its run rating and rank, where it stands in the simulated standings, and
   its games so far; and what baseball adds, the club's starters with their ratings. The pick and grade columns join
   the games table when Stage 101 defines MLB's pick file. */
let currentTeam = null;
try{ currentTeam = localStorage.getItem('mlb:team'); }catch(e){}
function clubName(code){ return (BD.teams[code] || {}).name || code; }
function clubGames(code){
  return BD.games.filter(g => g.home === code || g.away === code)
    .sort((a, b) => (a.start || a.day).localeCompare(b.start || b.day));
}
function gameResult(g, code){
  if(g.status !== 'final' || g.hs === null || g.hs === undefined) return '';
  const mine = g.home === code ? g.hs : g.as, theirs = g.home === code ? g.as : g.hs;
  return `${mine > theirs ? 'W' : mine < theirs ? 'L' : 'T'} ${mine}-${theirs}`;
}
function teamFacts(code, r, s){
  const rank = r ? r.clubs.findIndex(c => c.team === code) : -1;
  const club = rank >= 0 ? r.clubs[rank] : null;
  const odds = s ? s.teams.find(t => t.team === code) : null;
  return [
    club ? `Run rating <b>${plusMinus(club.runs, 2)}</b> a game (${rank + 1} of ${r.clubs.length}).` : 'No ratings yet.',
    odds ? `${odds.wins_now}-${odds.losses_now}; projected <b>${odds.projected_wins.toFixed(1)}</b> wins, the postseason <b>${chance(odds.playoff_pct)}</b>, the ${escapeHtml(odds.division)} title ${chance(odds.division_pct)}.`
      : 'Standings odds not simulated yet.',
  ];
}
function renderTeams(){
  const select = document.getElementById('team-select');
  const clubs = Object.keys(BD.teams).sort((a, b) => clubName(a).localeCompare(clubName(b)));
  if(!currentTeam || !BD.teams[currentTeam]) currentTeam = clubs[0];
  if(!select.options.length){
    select.innerHTML = clubs.map(c => `<option value="${c}">${escapeHtml(clubName(c))}</option>`).join('');
    select.addEventListener('change', () => {
      currentTeam = select.value;
      try{ localStorage.setItem('mlb:team', currentTeam); }catch(e){}
      renderTeams();
    });
  }
  select.value = currentTeam;
  const t = currentTeam, r = BD.ratings, name = escapeHtml(clubName(t));
  const starters = r ? r.starters.filter(s => clubCode(s.club) === t) : [];
  const startersHtml = !r ? '' : starters.length
    ? `<h3 class="mlb-team-sub">Starters this season</h3><div class="table-wrap"><table class="metrics-table mlb-table"><caption class="visually-hidden">${name}: starters</caption>
      <thead><tr><th scope="col">Pitcher</th><th scope="col" class="num">Runs per 9</th><th scope="col" class="num">Better than league</th><th scope="col" class="num">Starts</th></tr></thead>
      <tbody>${starters.map(s => `<tr><th scope="row">${escapeHtml(s.name || s.player_id)}</th><td class="num">${s.rate.toFixed(2)}</td><td class="num">${plusMinus(r.league_rate - s.rate, 2)}</td><td class="num">${s.starts}</td></tr>`).join('')}</tbody></table></div>`
    : `<p class="mlb-lede">No pitcher has made ${r.min_starts} starts for this club yet.</p>`;
  const games = clubGames(t).filter(g => g.status === 'final');
  const gamesHtml = games.length
    ? `<h3 class="mlb-team-sub">Games so far</h3><div class="table-wrap"><table class="metrics-table mlb-table"><caption class="visually-hidden">${name}: games so far</caption>
      <thead><tr><th scope="col">Date</th><th scope="col">Opponent</th><th scope="col">Result</th></tr></thead>
      <tbody>${games.map(g => `<tr><td>${FMT_MONTHDAY.format(dayDate(g.day))}</td><td>${g.home === t ? 'vs' : 'at'} ${clubCode(g.home === t ? g.away : g.home)}</td><td>${gameResult(g, t)}</td></tr>`).join('')}</tbody></table></div>`
    : stateHtml('waiting', 'No games played yet', '');
  document.getElementById('teams-body').innerHTML = `<div class="fav-title"><h2 class="section-title">${name}</h2>${favStar('mlb', t, name)}</div>`
    + `<p class="mlb-lede">${teamFacts(t, r, BD.standings).join(' ')}</p>${startersHtml}${gamesHtml}`;
}

/* ---------- what's changed ----------
   src/sports/mlb/pages/changes.json: every amendment to MLB's registration, each entry naming the ones it covers
   (tests/test_whats_changed_complete.py holds the list to the registration both ways). */
function renderChanges(){
  document.getElementById('changes-body').innerHTML = (DATA.changes || []).map(c => `<div class="mlb-change">`
    + `<span class="mlb-change-date">${escapeHtml(dayText(c.date))}</span><h3>${escapeHtml(c.title)}</h3>`
    + `<p class="mlb-lede">${escapeHtml(c.text)}</p></div>`).join('') || stateHtml('waiting', 'Nothing recorded yet', '');
}

/* ---------- season accuracy and checking the AI's work (Stage 100 item 2) ----------
   Before Opening Day there is nothing to grade, so Season Accuracy says what it will hold and when, and Checking the
   AI's work holds what is true already: what was written down before anything was fitted, and how the published
   numbers are held to it. The record, the forward test, calibration, the drift check and M2 join with Stage 101,
   when MLB's pick file and forward-test registration exist. */
function renderAccuracy(){
  const start = OPENING_DAY ? `on Opening Day, ${escapeHtml(dayText(OPENING_DAY))}` : 'on Opening Day';
  document.getElementById('accuracy-body').innerHTML = stateHtml('waiting', 'Nothing graded yet', `MLB&#39;s picks start ${start}.`)
    + '<p class="mlb-lede mlb-after-state">From then each game&#39;s pick is graded once the game is final; a postponed or cancelled game is never counted. '
    + 'This page will hold the season&#39;s record, the forward test, judged on log loss against the market and the base rate rather than on picks right, '
    + 'how sure each pick was against how often it was right, and every graded pick. The forward test&#39;s rules are registered before the first pick is saved.</p>';
}
function renderReliability(){
  const el = document.getElementById('reliability-body');
  if(!LAB){ el.innerHTML = stateHtml('waiting', 'Not built yet', ''); return; }
  el.innerHTML = `<h2 class="section-title">The drift check</h2>
    <p class="mlb-lede">Starts with the live picks. Its rule, how often it looks and how far live log loss may run from the backtest&#39;s before it flags, is registered with the forward test before Opening Day.</p>
    <h2 class="section-title">The probable pitcher against who started</h2>
    <p class="mlb-lede">A live pick reads the probable pitcher announced before the game; the backtest read who actually started. The registration measures that gap (M2) and prints it here once 200 live games are graded.</p>
    <h2 class="section-title">Before anything was fitted</h2>
    <p class="mlb-lede">The questions, the seasons, the settings to search, the bootstrap and the labels were written down and committed on ${escapeHtml(dayText(LAB.registered))} (<a href="${REGISTRY_URL}">the registration</a>), before any MLB model, feature or rating was fitted or scored. ${LAB.amendments} amendment${LAB.amendments === 1 ? '' : 's'} followed, each dated, saying what it changed and what had been seen by then, and each listed on <a href="#changes">What&#39;s Changed</a>. One of them says aloud that a single confirmation-season figure had been printed while the feature code was being timed, and was not kept.</p>
    <h2 class="section-title">After</h2>
    <p class="mlb-lede">Every number on these pages is read from the committed files when the page is built, and tests hold those files to the registration: the tuning searched every registered setting, on the validation seasons only, and kept the lowest. Those tests were checked in turn, by breaking the code on purpose and confirming a test fails. When the confirmation runs, it runs once, and a separate auditing agent, Booth, re-runs it on a Linux machine before the result is merged.</p>`;
}

/* ---------- the page around the board ----------
   Each button for the page shown carries aria-current, as on the other sports. On a phone the pages past the first
   three sit in the More sheet (OVERFLOW_PAGES), whose button is lit while one of them is shown. */
const BASE_TITLE = document.title;
const OVERFLOW_PAGES = ['teams', 'modellab', 'method', 'reliability', 'changes'];
function showMlbPage(name, opts){
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
  document.title = name === 'board' || !heading ? BASE_TITLE : `MLB ${heading.textContent.trim()} — Sportalytics`;
  if(opts && opts.focus && heading){
    heading.setAttribute('tabindex', '-1');
    heading.focus({preventScroll: true});
  }
}
document.querySelectorAll('[data-page]').forEach(b => b.addEventListener('click', () => showMlbPage(b.dataset.page, {focus: true})));
/* The More sheet on a phone (src/core/day_board.js setMoreSheetOpen): its button opens and closes it, a tap
   outside it or Esc closes it, and its own close button hands focus back to the button. */
document.getElementById('bnav-more-btn').addEventListener('click', e => {
  e.stopPropagation();
  setMoreSheetOpen(!document.getElementById('bnav-more-sheet').classList.contains('open'));
});
document.addEventListener('click', e => {
  const sheet = document.getElementById('bnav-more-sheet');
  if(sheet.classList.contains('open') && !sheet.contains(e.target) && !e.target.closest('#bnav-more-btn')) setMoreSheetOpen(false);
});
document.addEventListener('keydown', e => { if(e.key === 'Escape') setMoreSheetOpen(false); });
document.querySelector('#bnav-more-sheet .bnav-more-close').addEventListener('click', () => {
  setMoreSheetOpen(false);
  document.getElementById('bnav-more-btn').focus();
});
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
renderStandings();
renderRatings();
renderModelLab();
renderMethod();
renderTeams();
renderChanges();
renderAccuracy();
renderReliability();
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
