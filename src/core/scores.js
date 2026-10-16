/* Live scores on the rows and cards (Stage 80 item 61, the 2026-10-13
   UI/UX audit's F15). The audit asked for the daily run to write them, but
   no run is on while games are: the NHL's runs at 10 AM and 5 PM Eastern,
   the NBA's at noon and 5:30 PM, the NFL's around its slate. Mark chose
   (2026-10-15) to have the open page ask ESPN's public scoreboard instead,
   about once a minute while a game it shows is on; the daily, lock,
   drift, backtest, weekly update and grading scripts do not change, and
   grading still uses the final score they record.

   A page marks a game it has not yet seen finish with data-score-sport,
   data-score-key ("AWAY@HOME" in the page's own team codes), data-score-start
   (its start, ISO) and, where the page has ESPN's game id (the NBA's),
   data-score-id. Inside, [data-score-slot] elements are left empty and
   .score-on hidden until ESPN has a score; then the element gets
   data-score-live and the slots are filled with text (never HTML).
   Nothing is asked of ESPN when no shown game is on, when the tab is
   hidden, or after ESPN has called a game final. A request that fails
   leaves what was shown. The pages' Content-Security-Policy lets them
   reach site.api.espn.com and nothing else.

   The functions down to the IIFE need no page: tests/test_live_scores.py
   runs them in node. */
const SCORES_URL = 'https://site.api.espn.com/apis/site/v2/sports/';
const SCORES_PATH = {nfl: 'football/nfl', nhl: 'hockey/nhl', nba: 'basketball/nba'};
/* The page's code where ESPN's differs: nflverse's and the NHL's own. */
const SCORES_ALIAS = {nfl: {LA: 'LAR', WAS: 'WSH'}, nhl: {LAK: 'LA', NJD: 'NJ', SJS: 'SJ', TBL: 'TB', UTA: 'UTAH'}, nba: {}};
const SCORES_EVERY_MS = 60 * 1000;
/* Asked about from ten minutes before the start until twelve hours after,
   so a page opened after the game still gets ESPN's final once. */
const SCORES_BEFORE_MS = 10 * 60 * 1000;
const SCORES_AFTER_MS = 12 * 3600 * 1000;
/* An old reading says so: "as of 8:41 PM". */
const SCORES_STALE_MS = 3 * 60 * 1000;
const SCORES_DAY = new Intl.DateTimeFormat('en-CA', {timeZone: 'America/New_York', year: 'numeric', month: '2-digit', day: '2-digit'});

function scoresCode(sport, team){ return (SCORES_ALIAS[sport] || {})[team] || team; }
function scoresKey(sport, away, home){ return `${scoresCode(sport, away)}@${scoresCode(sport, home)}`; }
/* ESPN's scoreboard day, YYYYMMDD, is the Eastern date of the start. */
function scoresDay(startMs){ return SCORES_DAY.format(new Date(startMs)).replace(/-/g, ''); }
function scoresUrl(sport, day){ return `${SCORES_URL}${SCORES_PATH[sport]}/scoreboard?dates=${day}`; }

/* "Q3 4:12", "P2 10:03", "Half", "End Q3", "OT 2:11", "Final", "Final/OT". */
function scoresClock(sport, st){
  const t = (st && st.type) || {};
  if(t.state === 'post') return String(t.shortDetail || 'Final').slice(0, 12);
  const p = Number(st.period) || 0;
  let label;
  if(sport === 'nhl') label = p <= 3 ? `P${p}` : /SO/.test(String(t.shortDetail)) ? 'SO' : p === 4 ? 'OT' : `${p - 3}OT`;
  else label = p <= 4 ? `Q${p}` : p === 5 ? 'OT' : `${p - 4}OT`;
  if(t.name === 'STATUS_HALFTIME') return 'Half';
  if(t.name === 'STATUS_END_PERIOD') return `End ${label}`;
  // A shootout has no clock.
  return st.displayClock && label !== 'SO' ? `${label} ${st.displayClock}` : label;
}

/* ESPN's scoreboard to {"AWAY@HOME": entry, "#id": entry}: only games under
   way or over, with both scores. */
function scoresRead(sport, data, nowMs){
  const out = {};
  for(const ev of (data && data.events) || []){
    const c = (ev.competitions || [])[0];
    if(!c) continue;
    const side = {};
    for(const t of c.competitors || []) side[t.homeAway] = t;
    if(!side.home || !side.away || !side.home.team || !side.away.team) continue;
    const st = c.status || ev.status || {};
    const state = (st.type || {}).state;
    if(state !== 'in' && state !== 'post') continue;
    const n = v => { const x = parseInt(v, 10); return Number.isFinite(x) && x >= 0 ? x : null; };
    const as = n(side.away.score), hs = n(side.home.score);
    if(as === null || hs === null) continue;
    const e = {as, hs, state, clock: scoresClock(sport, st), at: nowMs};
    out[`${side.away.team.abbreviation}@${side.home.team.abbreviation}`] = e;
    if(ev.id) out[`#${ev.id}`] = e;
  }
  return out;
}

function scoresFind(seen, sport, key, id){
  const s = seen[sport] || {};
  if(id && s[`#${id}`]) return s[`#${id}`];
  const [away, home] = key.split('@');
  return s[scoresKey(sport, away, home)] || null;
}

/* Whether a game's start puts it in the window, and ESPN has not ended it. */
function scoresDue(startMs, entry, nowMs){
  if(!Number.isFinite(startMs)) return false;
  if(entry && entry.state === 'post') return false;
  return startMs - SCORES_BEFORE_MS <= nowMs && nowMs < startMs + SCORES_AFTER_MS;
}

/* The scoreboards to ask for: one per sport and Eastern day, for the games due. */
function scoresWant(games, nowMs){
  const want = new Map();
  for(const g of games){
    if(!SCORES_PATH[g.sport] || !scoresDue(g.start, g.entry, nowMs)) continue;
    const url = scoresUrl(g.sport, scoresDay(g.start));
    want.set(url, g.sport);
  }
  return [...want].map(([url, sport]) => ({url, sport}));
}

/* What the slots say, from the page's own team codes. */
function scoresView(key, e, nowMs, fmt){
  const [away, home] = key.split('@');
  const word = e.state === 'post' ? 'Final' : 'Live';
  let line = `${word}: ${away} ${e.as}, ${home} ${e.hs}`;
  if(e.state === 'post') line += e.clock !== 'Final' ? ` (${e.clock.replace(/^Final\/?/, '')})` : '';
  else line += ` · ${e.clock}`;
  line += e.state === 'post' ? ' · picks are graded at the next update' : '';
  if(e.state !== 'post' && nowMs - e.at > SCORES_STALE_MS) line += ` · as of ${fmt(new Date(e.at))}`;
  return {clock: e.clock, game: `${away} ${e.as} @ ${home} ${e.hs}`, line};
}

(function(){
  if(typeof window === 'undefined' || !window.fetch || !document.querySelectorAll) return;
  const seen = {};
  const fmt = d => d.toLocaleTimeString('en-US', {hour: 'numeric', minute: '2-digit'});
  let timer = null, busy = false, lastAsk = 0;
  const marked = () => [...document.querySelectorAll('[data-score-key]')];
  const gameOf = el => {
    const sport = el.dataset.scoreSport, key = el.dataset.scoreKey;
    return {el, sport, key, start: Date.parse(el.dataset.scoreStart), entry: scoresFind(seen, sport, key, el.dataset.scoreId)};
  };
  function paint(){
    const now = Date.now();
    for(const g of marked().map(gameOf)){
      if(!g.entry) continue;
      const v = scoresView(g.key, g.entry, now, fmt);
      for(const slot of g.el.querySelectorAll('[data-score-slot]')){
        // A card inside a marked row is the card's to fill.
        if(slot.closest('[data-score-key]') !== g.el) continue;
        const text = v[slot.dataset.scoreSlot] || '';
        if(slot.textContent !== text) slot.textContent = text;
      }
      if(g.el.getAttribute('data-score-live') !== g.entry.state) g.el.setAttribute('data-score-live', g.entry.state);
    }
  }
  function later(ms){
    clearTimeout(timer);
    timer = setTimeout(tick, Math.max(0, Math.min(ms, 30 * 60 * 1000)));
  }
  async function tick(){
    timer = null;
    if(busy || document.hidden) return;
    const now = Date.now();
    const games = marked().map(gameOf);
    const want = scoresWant(games, now);
    if(!want.length){
      // Nothing on: look again when the next shown game is due.
      const next = games.map(g => g.start - SCORES_BEFORE_MS).filter(t => t > now).sort((a, b) => a - b)[0];
      if(next) later(next - now);
      return;
    }
    busy = true;
    lastAsk = now;
    await Promise.all(want.map(w => fetch(w.url, {credentials: 'omit', cache: 'no-store'})
      .then(r => r.ok ? r.json() : null)
      .then(d => { if(d) seen[w.sport] = Object.assign(seen[w.sport] || {}, scoresRead(w.sport, d, Date.now())); })
      .catch(() => {})));
    busy = false;
    paint();
    later(SCORES_EVERY_MS);
  }
  // A page that redraws (a day step, a sort) gets its scores back at once,
  // and a newly shown game that is on is asked about.
  let queued = false;
  new MutationObserver(() => {
    if(queued) return;
    queued = true;
    requestAnimationFrame(() => { queued = false; paint(); if(!busy && Date.now() - lastAsk >= SCORES_EVERY_MS) later(0); });
  }).observe(document.body, {childList: true, subtree: true});
  document.addEventListener('visibilitychange', () => { if(!document.hidden) later(0); });
  later(0);
})();
