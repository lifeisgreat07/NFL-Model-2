const agentLog = __AGENT_LOG_JSON__;
const recentRuns = __RECENT_RUNS_JSON__;
const lockProof = __LOCK_PROOF_JSON__;
const versionHistory = __VERSION_HISTORY_JSON__;
const modelVersion = __MODEL_VERSION__;
/* Every "nothing to show" on the page goes through here. See the Page states
   block in the stylesheet for what each kind means. `paras` is one string or
   a list of paragraphs; `action` is {label, onclick} and is required for
   'filtered', because a filter that hides everything must say how to undo
   itself. */
/* Stage 88 item 5 (the 2026-11-02 review): the Content-Security-Policy names
   the hash of each inline script, so the page has no inline handlers. A logo
   that fails to load (data-hide-on-error) is hidden by this one listener. */
document.addEventListener('error', e => {
  const t = e.target;
  if (t instanceof HTMLImageElement && t.hasAttribute('data-hide-on-error')) t.style.display = 'none';
}, true);
/* Every button that acts carries data-act, and this table says what each one
   does; one click listener and one change listener run them. */
const ACTIONS = {
  'dismiss-onboarding': () => dismissOnboarding(),
  'import-shared-picks': () => importSharedPicks(),
  'exit-shared-picks': () => exitSharedPicks(),
  'copy-share-link': b => copyShareLink(b),
  'export-my-picks': () => exportMyPicks(),
  'choose-picks-file': () => document.getElementById('picks-import-input').click(),
  'show-all-games': () => document.querySelector('#filter-row [data-filter=all]').click(),
};
document.addEventListener('click', e => {
  const b = e.target instanceof Element ? e.target.closest('[data-act]') : null;
  if (b && ACTIONS[b.dataset.act]) ACTIONS[b.dataset.act](b);
});
document.addEventListener('change', e => {
  if (e.target.id === 'picks-import-input' && e.target.files[0]) importMyPicks(e.target.files[0]);
});
const STATE_KINDS = ['waiting', 'filtered', 'missing', 'note'];
function stateHtml(kind, title, paras, action, extra){
  if(!STATE_KINDS.includes(kind)) throw new Error('unknown page state: ' + kind);
  if(kind === 'filtered' && !action) throw new Error('a filtered state needs its undo action');
  const body = (Array.isArray(paras) ? paras : [paras]).filter(Boolean)
    .map(t => kind === 'note' ? ' ' + t : `<p>${t}</p>`).join('');
  const titleEl = kind === 'note' ? `<b class="state-title">${title}</b>` : `<span class="state-title">${title}</span>`;
  const btn = action ? `<button class="btn" data-act="${action.act}">${action.label}</button>` : '';
  return `<div class="state state--${kind}${extra ? ' ' + extra : ''}" role="status">${titleEl}${body}${btn}</div>`;
}
/* Marks each table wrapper .fits when its table is no wider than its box.
   See the Tables block in the stylesheet for what that switches. Runs on
   load, on resize, once the webfont lands (text widths are what decide it),
   and whenever the page swaps content, since most tables here are rendered
   by script after load. A wrapper on a page that is not showing measures
   0 wide and is left alone until its page is shown. */
function fitTables(){
  document.querySelectorAll('.table-wrap').forEach(w=>{
    const t = w.querySelector('table');
    if(!t || !w.clientWidth) return;
    const fits = t.offsetWidth <= w.clientWidth;
    w.classList.toggle('fits', fits);
    setScrollStop(w, !fits);
  });
  document.querySelectorAll('.formula').forEach(f=>{
    if(!f.clientWidth) return;
    setScrollStop(f, f.scrollWidth > f.clientWidth);
  });
}
/* A box that scrolls sideways has to be reachable from the keyboard, or a
   keyboard user sees a table's first columns and never the rest (WCAG
   2.1.1). axe's scrollable-region-focusable found five such boxes at 390px
   the first time the browser checks ran in CI (Stage 12): the wide tables
   on Accuracy, Model Lab and Method, and the ridge formula. None holds a
   control of its own, so nothing in them could take focus.

   So a box that scrolls joins the Tab order as a named region, and once
   focused the arrow keys scroll it. A box that fits leaves the Tab order
   again: a stop that does nothing when you land on it is noise. Only what
   this function added is removed -- data-scroll-stop lists it -- so a
   tabindex, role or label written into the markup survives the box
   fitting. */
/* The region is named, in order of preference: by data-scroll-label, for a
   box whose nearest heading belongs to something else (Model Lab's
   experiment log comes straight after the reliability diagram's section);
   by the table's caption; or by the heading of the section it sits in --
   the nearest h2-h4 that is an earlier sibling of the box or of one of its
   ancestors, looking no further out than its page. Only siblings count, not
   headings buried inside them: on Accuracy the calibration table follows a
   nested note whose own heading is "Not enough games yet to check", and
   that is a message, not the table's name. */
function headingBefore(el){
  for(let node = el; node && !node.matches('.page'); node = node.parentElement){
    for(let sib = node.previousElementSibling; sib; sib = sib.previousElementSibling){
      if(sib.matches('h2, h3, h4')) return sib;
    }
  }
  return null;
}
function scrollStopLabel(el){
  const given = el.getAttribute('data-scroll-label');
  const heading = given ? null : (el.querySelector('caption') || headingBefore(el));
  const name = given || (heading ? heading.textContent.trim().replace(/\s+/g, ' ') : '');
  const what = el.classList.contains('formula') ? 'Formula' : 'Table';
  return (name ? `${what}: ${name}` : what) + ', scrolls sideways';
}
/* A box holding a control of its own is already reachable: Tab lands on
   the control and the browser scrolls it into view (the Power Ratings
   table's sortable headers do exactly that). A second stop there would be
   one more press for nothing. */
const FOCUSABLE_INSIDE = 'a[href], button, input, select, textarea, [tabindex]:not([tabindex="-1"])';
const SCROLL_STOP_ATTRS = {tabindex: () => '0', role: () => 'region', 'aria-label': scrollStopLabel};
function setScrollStop(el, scrolls){
  const marked = el.hasAttribute('data-scroll-stop');
  const added = marked ? el.getAttribute('data-scroll-stop').split(' ').filter(Boolean) : [];
  if(scrolls && !el.querySelector(FOCUSABLE_INSIDE)){
    for(const [name, value] of Object.entries(SCROLL_STOP_ATTRS)){
      if(added.includes(name)) el.setAttribute(name, value(el));
      else if(!el.hasAttribute(name)){ el.setAttribute(name, value(el)); added.push(name); }
    }
    el.setAttribute('data-scroll-stop', added.join(' '));
  } else if(marked){
    added.forEach(name => el.removeAttribute(name));
    el.removeAttribute('data-scroll-stop');
  }
}
(function(){
  let queued = false;
  const later = ()=>{ if(queued) return; queued = true;
    requestAnimationFrame(()=>{ queued = false; fitTables(); }); };
  window.addEventListener('resize', later);
  if(document.fonts && document.fonts.ready) document.fonts.ready.then(later);
  const root = document.querySelector('main');
  if(root && window.MutationObserver){
    new MutationObserver(later).observe(root,
      {childList:true, subtree:true, attributes:true, attributeFilter:['class','open']});
  }
  later();
})();
/* Model Lab's header used to TYPE the version: "2.4, last updated
   2026-09-04" sat there through the 2.5 release. It is written from the
   same two values the changelog reads, so it cannot drift again. */
(function(){
  const el = document.getElementById('modellab-version');
  if(!el) return;
  const cur = versionHistory.find(v => v.version === modelVersion);
  el.textContent = modelVersion + (cur && cur.date ? ', released ' + cur.date : '');
})();
const teams = __TEAMS_JSON__;
const playoffMeta = __PLAYOFF_META_JSON__;

// Standard ESPN CDN logo pattern -- publicly hosted images, same approach
// used across the NFL analytics open-source community. Most codes match
// our team abbreviations lowercased; a handful of ESPN's own codes differ.
// Team colors for the two-tone confidence bar -- chosen for visibility
// against a dark background. Where a team's official primary color is
// near-black/navy/dark-green (would vanish on our dark theme), using
// their brighter secondary color instead -- standard practice for
// dark-mode sports UIs, still recognizably "that team's color."
const TEAM_COLOR = {
  ARI:'#97233F', ATL:'#A71930', BAL:'#3E1F91', BUF:'#1E4DB7', CAR:'#0085CA',
  CHI:'#C83803', CIN:'#FB4F14', CLE:'#FF3C00', DAL:'#869397', DEN:'#1E4D8C',
  DET:'#0076B6', GB:'#FFB612',  HOU:'#C8102E', IND:'#2A5DAE', JAX:'#D7A22A',
  KC:'#E31837',  LA:'#FFA300',  LAC:'#0080C6', LV:'#A5ACAF',  MIA:'#008E97',
  MIN:'#FFC62F', NE:'#C60C30',  NO:'#D3BC8D',  NYG:'#1848A0', NYJ:'#1D8A5D',
  PHI:'#046A38', PIT:'#A2AAAD', SEA:'#69BE28', SF:'#B3995D',  TB:'#D50A0A',
  TEN:'#4B92DB', WAS:'#8B1538',
};
function teamColor(abbr){ return TEAM_COLOR[abbr] || '#8A93A8'; }

// Per-matchup contrast safety net: even with a clean base palette, the NFL
// has many teams sharing red/blue as a primary color (Chiefs/Bucs/Patriots,
// several blues), so two SPECIFIC teams can still land close together.
// Rather than trying to hand-solve every possible pair, detect low-contrast
// pairings at render time and push them apart.
//
// THIS COMMENT USED TO END "while keeping each team's real hue (so it still
// reads as 'that team,' just more separated)". Measured 2026-09-21 and that
// is not what happens: on the closest pairing of the real 2026 week 2 slate
// the push renders Cincinnati's #FB4F14 as #C43E10 and Houston's #C8102E as
// #D4445C -- an orange gone brown and a deep red gone pink, neither of which
// is the team's colour. The separation is real; the "still reads as that
// team" half was the comment claiming more than the code delivers, which is
// the shape this repository has now shipped six times. Corrected, not
// deleted.
//
// DECIDED 2026-09-21 by Mark: KEEP THIS AS IT IS. The alternatives were
// rendered side by side on real games in both themes and under protan and
// deutan simulation -- a neutral two-step bar, an accent fill, no bar at
// all, and a hybrid keeping team colour except on colliding pairs -- and all
// four were declined. The team-colour bars are wanted on the board as part
// of how the dashboard looks, and the cost below is accepted knowingly.
//
// The accepted cost, measured with src/sports/nfl/research/verify_matchup_cvd.py (CIEDE2000, NOT
// the OKLab ruler tests/test_dashboard_charts.py gates on):
//   - 60 of 496 distinct team pairs sit under 15, 9 under 5, worst ARI/PHI
//     at 0.18; as ordered matchups it is 103 of 992.
//   - On the real 2026 week 2 slate, 3 of 16 games trip this function and
//     1 of 16 (CIN@HOU) is still under 15 after being pushed -- so the net
//     does not always succeed.
//   - Identity is not carried by colour alone in any case: every bar sits
//     between a logo, an abbreviation and a percentage.
//
// Consequences for anyone reading the queue: teamColor(), TEAM_COLOR,
// CONTRAST_THRESHOLD and the #8A93A8 fallback all STAY. That literal remains
// live in this file, reached only for an abbreviation outside the 32 in
// TEAM_COLOR. Do not re-open this as a colour defect; it was measured,
// looked at, and decided.
function hexToRgb(hex){
  const h = hex.replace('#','');
  return [parseInt(h.substr(0,2),16), parseInt(h.substr(2,2),16), parseInt(h.substr(4,2),16)];
}
function rgbToHex(r,g,b){
  const c = v => Math.max(0,Math.min(255,Math.round(v))).toString(16).padStart(2,'0');
  return '#'+c(r)+c(g)+c(b);
}
function colorDistance(hex1, hex2){
  const [r1,g1,b1] = hexToRgb(hex1), [r2,g2,b2] = hexToRgb(hex2);
  return Math.sqrt((r1-r2)**2 + (g1-g2)**2 + (b1-b2)**2);
}
function shade(hex, amount){
  // amount > 0 lightens toward white, < 0 darkens toward black
  const [r,g,b] = hexToRgb(hex);
  const target = amount > 0 ? 255 : 0;
  const t = Math.abs(amount);
  return rgbToHex(r+(target-r)*t, g+(target-g)*t, b+(target-b)*t);
}
const CONTRAST_THRESHOLD = 90;  // roughly: "would look muddy/hard to tell apart side by side"
function matchupColors(awayAbbr, homeAbbr){
  let away = teamColor(awayAbbr), home = teamColor(homeAbbr);
  const dist = colorDistance(away, home);
  if(dist < CONTRAST_THRESHOLD){
    // Too close: darken the away segment and lighten the home segment,
    // proportional to how close they are (closer = bigger push apart).
    const push = 0.35 * (1 - dist/CONTRAST_THRESHOLD) + 0.2;
    away = shade(away, -push);
    home = shade(home, push);
  }
  return [away, home];
}

const ESPN_CODE = {
  ARI:'ari',ATL:'atl',BAL:'bal',BUF:'buf',CAR:'car',CHI:'chi',CIN:'cin',CLE:'cle',
  DAL:'dal',DEN:'den',DET:'det',GB:'gb',HOU:'hou',IND:'ind',JAX:'jax',KC:'kc',
  LA:'lar',LAC:'lac',LV:'lv',MIA:'mia',MIN:'min',NE:'ne',NO:'no',NYG:'nyg',
  NYJ:'nyj',PHI:'phi',PIT:'pit',SEA:'sea',SF:'sf',TB:'tb',TEN:'ten',WAS:'wsh',
};
function teamLogo(abbr){
  const code = ESPN_CODE[abbr] || abbr.toLowerCase();
  return `https://a.espncdn.com/i/teamlogos/nfl/500/${code}.png`;
}
const weeks = __WEEKS_JSON__;       // { "2026_week1": {season, week, games:[...]}, ... }
const latestWeekKey = __LATEST_WEEK__;  // "2026_week1" or null
// Week keys that actually have a generated picks PDF on disk. Injected as a
// real list rather than assumed for every week, so the download control can
// hide itself instead of linking to a 404 for a week whose PDF is missing.
const picksPdfs = __PICKS_PDFS_JSON__;
const accuracy = __ACCURACY_JSON__;
const teamHistory = __TEAM_HISTORY_JSON__;
// Backtest-derived calibration (data/nfl/calibration.json, ~1087 games). null when
// src/sports/nfl/research/calibration.py has never been run in this checkout -- the reliability
// diagram omits itself rather than inventing numbers.
const calibration = __CALIBRATION_JSON__;

const weekKeysSorted = Object.keys(weeks).sort((a,b)=>{
  const wa = weeks[a], wb = weeks[b];
  return (wa.season - wb.season) || (wa.week - wb.week);
});

/* ---------- The football's controller ----------
   brandMark.start() / .stop() are the only public calls. stop() waits for the
   CURRENT revolution to finish so the ball always comes to rest at 0deg rather
   than snapping mid-spin.

   The 900ms fallback is not belt-and-braces, it is load-bearing: if no
   animationiteration event ever arrives -- animations blocked, tab
   backgrounded, or a CSS rule nobody foresaw winning -- the spinner would
   otherwise stay on forever, and a permanently-busy page is a worse bug than
   a spinner that never appeared. One revolution plus slack. */
const brandMark = (function(){
  const body = document.body;
  const spin = document.querySelector('.brand-ball .spin');
  let pending = false, fallback = null;

  function rest(){
    pending = false;
    clearTimeout(fallback); fallback = null;
    body.classList.remove('is-loading');
  }
  if(spin){
    spin.addEventListener('animationiteration', e => {
      if(pending && e.animationName === 'bm-tumble') rest();
    });
    // First paint: drop .is-entering when the settle actually ends rather than
    // on a guessed timer. Reduced motion fires no animationend, hence the timer
    // as a floor.
    spin.addEventListener('animationend', e => {
      if(e.animationName === 'bm-settle') body.classList.remove('is-entering');
    });
  }
  setTimeout(() => body.classList.remove('is-entering'), 800);

  return {
    start(){
      pending = false;
      clearTimeout(fallback); fallback = null;
      body.classList.add('is-loading');
      body.setAttribute('aria-busy', 'true');
    },
    stop(){
      body.removeAttribute('aria-busy');
      if(!body.classList.contains('is-loading')) return;
      if(window.matchMedia('(prefers-reduced-motion: reduce)').matches){ rest(); return; }
      pending = true;
      clearTimeout(fallback);
      fallback = setTimeout(rest, 900);
    }
  };
})();

function weekLabel(key){
  const w = weeks[key];
  // Stage 39 item 2: the playoff weeks by their round. nflverse numbers them
  // on from the regular season, which has run to week 18 since 2021.
  const round = w.season >= 2021
    ? {19: 'Wild Card', 20: 'Divisional', 21: 'Conference Championships', 22: 'Super Bowl'}[w.week] : undefined;
  return `${w.season} · ${round || 'Week ' + w.week}${w.preview ? ' (preview)' : ''}`;
}

// "Tue Sep 29, 16:41 UTC" from a preview's ISO stamp. UTC, like the page's
// "Updated" line, so the two can be compared at a glance.
/* Stage 77 item 15 (the 2026-10-13 audit's copy fix 4): Eastern time, as
   every other time on the board is, and the weekday alone: a preview is
   this week's, so "Tue 7:02 AM ET" says it where "Tue Oct 13, 11:02 UTC"
   made the reader convert. */
function previewWhen(iso){
  const d = iso ? new Date(iso) : null;
  if(!d || isNaN(d)) return 'the last run';
  return `${d.toLocaleString('en-US', {weekday:'short', hour:'numeric', minute:'2-digit', timeZone:'America/New_York'})} ET`;
}

/* The note above a preview week's cards. Before the week's first kickoff
   it says the picks can still change and lock before that kickoff. After
   it -- a preview still showing then means no run locked the week -- it
   says so, instead of promising a lock that can no longer happen (Stage 30
   item 3). kickoffInstant is the My Picks lock's own reading of a kickoff. */
function previewNoteText(weekData, nowMs){
  if(!weekData || !weekData.preview) return '';
  const kicks = (weekData.games || []).map(kickoffInstant).filter(k => k !== null);
  const first = kicks.length ? Math.min(...kicks) : null;
  const when = previewWhen(weekData.previewed_utc);
  if(first !== null && nowMs >= first)
    return `Preview from ${when}: the week's first game has kicked off and these picks ` +
      `were never locked, so the lock run did not happen. None of them will be graded.`;
  return `Preview: these are the models' picks as of ${when}. ` +
    `They can still change. The picks lock before the week's first kickoff ` +
    `(usually Thursday), and only locked picks are graded.`;
}

/* ---------- Week stepper ----------
   The hidden <select> owns the selection; these only move it and then read it
   back. Two controls writing the same state independently is how they drift,
   and the arrows would be the ones to get it wrong.

   TAKES A PREFIX because two pages use it. The Week Board had this control and
   My Picks had a bare <select>, so the same job looked like two different
   things depending on which tab you were on -- and on a phone one of them was
   the iOS wheel. The fix is one implementation driven twice, not a second
   copy: a copied stepper is the `.game-card` story again, where one edit
   landed on one of two render paths and the diff looked complete.

   Element ids are `<prefix>-select`, `<prefix>-step-label`, `<prefix>-prev`
   and `<prefix>-next`. The Board's existing ids already fit that shape with
   prefix `week`, and My Picks' select was already `picks-week-select`, so
   nothing was renamed to make this work. */
function syncWeekStepper(prefix){
  const sel = document.getElementById(`${prefix}-select`);
  const label = document.getElementById(`${prefix}-step-label`);
  const prev = document.getElementById(`${prefix}-prev`);
  const next = document.getElementById(`${prefix}-next`);
  if(!sel || !label || !prev || !next) return;
  const i = weekKeysSorted.indexOf(sel.value);
  label.textContent = i === -1 ? '—' : weekLabel(sel.value);
  // Disabled rather than hidden at the ends: a control that vanishes moves the
  // one beside it under the pointer you were about to click.
  prev.disabled = i <= 0;
  next.disabled = i === -1 || i >= weekKeysSorted.length - 1;
}

function wireWeekStepper(prefix){
  const sel = document.getElementById(`${prefix}-select`);
  if(!sel) return;
  const step = d => {
    const i = weekKeysSorted.indexOf(sel.value);
    const j = i + d;
    if(j < 0 || j >= weekKeysSorted.length) return;
    sel.value = weekKeysSorted[j];
    // Drive the select's own change handler rather than duplicating what it
    // does, so the stepper can never take a path the dropdown does not.
    sel.dispatchEvent(new Event('change'));
  };
  const prev = document.getElementById(`${prefix}-prev`);
  const next = document.getElementById(`${prefix}-next`);
  if(prev) prev.addEventListener('click', ()=>step(-1));
  if(next) next.addEventListener('click', ()=>step(1));
  syncWeekStepper(prefix);
}

/* ---------- [ and ] step weeks (Stage 17) ----------
   On the Week Board and My Picks, the two pages with a week stepper. The key
   presses the stepper's own button, so it takes the path a click takes and
   does nothing at either end, where the button is disabled.

   Left alone: a key with Ctrl, Cmd or Alt (the browser's and the system's
   shortcuts), a key already handled, and a key typed into a field or an
   open list -- the sort list's type-ahead reads every character. The
   buttons carry aria-keyshortcuts so a screen reader can announce the keys. */
function weekKeyTarget(e, pageId){
  if(e.key !== '[' && e.key !== ']') return null;
  if(e.ctrlKey || e.metaKey || e.altKey || e.defaultPrevented) return null;
  const t = e.target;
  if(t && t.closest && t.closest('input, textarea, select, [contenteditable="true"], [role="listbox"]')) return null;
  const prefix = pageId === 'board' ? 'week' : pageId === 'picks' ? 'picks-week' : null;
  if(!prefix) return null;
  return `${prefix}-${e.key === '[' ? 'prev' : 'next'}`;
}

document.addEventListener('keydown', e => {
  const page = document.querySelector('.page.active');
  const id = weekKeyTarget(e, page ? page.id.replace(/^page-/, '') : null);
  const btn = id && document.getElementById(id);
  if(!btn) return;
  e.preventDefault();
  btn.click();
});

/* ---------- Listbox ----------

   Which edge an open list hangs from, as a plain function over numbers,
   because after this change NOTHING ON THE PAGE REACHES THE FLIP. Shortening
   the sort labels narrowed the button by 30px and the list with it; measured
   across 21 viewport widths from 320 to 520, on both listboxes, the flip
   never engages and no list leaves the viewport. That is the "deleting the
   only input that reaches a branch silently untests that branch" shape -- the
   rule still has to be right for the next control or the next long option,
   and a test over today's markup can no longer prove it.

   So it is stated once, here, and checked twice, which is what that trap
   entry prescribes: tests/test_listbox_edge_flip.py runs this function over a
   table of synthetic geometries that keeps every branch alive, and the
   rendered check asserts the property it exists to protect -- no list past
   the viewport -- over whatever the page actually contains today.

   It returns a word rather than a boolean so the two reasons NOT to flip --
   it already fits, and flipping would push it off the other edge -- cannot be
   read as the same answer by accident. */
function lbxFlipDecision(listLeft, listWidth, anchorRight, viewportWidth){
  if(listLeft + listWidth <= viewportWidth) return 'as-is';
  if(anchorRight - listWidth < 0) return 'as-is';
  return 'flip';
}

/* Replaces a native <select> as the VISIBLE control, for the reason recorded
   on .lbx in the stylesheet: `appearance:none` restyles the closed box and
   leaves the iOS system wheel exactly where it was.

   Same contract as the week stepper above, deliberately: THE SELECT STILL OWNS
   THE VALUE. This reads it, renders it, and writes back through
   sel.value + dispatchEvent('change') -- so every consumer keeps listening to
   the one element it already listened to, and the listbox cannot reach a state
   the select could not. Nothing downstream of this knows it exists.

   TAKES AN ELEMENT, never an id. #teamdive-select is next and is populated at
   runtime, so the second consumer must be this same function rather than a
   copy -- the .game-card lesson, where two render paths drifted because one
   edit landed on one of them and the diff looked complete. refresh() exists
   for exactly that case: a select whose options arrive after enhancement.

   PROGRESSIVE ENHANCEMENT, and this is where it departs from the week
   stepper. That control hardcodes `visually-hidden` in the markup; this list
   is built entirely by script, so the class is applied HERE, after the list
   is successfully built, and the select ships visible.

   What that buys is ORDERING, not reach. The select cannot be hidden unless
   the control replacing it already exists, so a script that dies between
   rendering the page and reaching this call leaves a working native select
   rather than nothing at all.

   It is NOT, as this comment said until 2026-09-21, that a no-script reader
   would otherwise have no control. With scripts off only #page-board is
   active (since Stage 13), every nav control is an inert <button>, and there
   is no :target rule and no anchor reaching another page. So #sort-select,
   on the board, is seen by that reader but sorts nothing (the cards are
   script-built as well), and #teamdive-select sits on a page nobody can
   reach. The <noscript> note explains the page to them; it does not make
   either select work, so do not read it as having changed this. The guard is kept
   anyway -- hidden by script rather than by markup is still the right
   default -- with the honest reason attached. */
function enhanceSelect(sel){
  if(!sel || sel.dataset.lbx === 'on') return null;

  const wrap = document.createElement('div');
  wrap.className = 'lbx';
  const btn = document.createElement('button');
  btn.type = 'button';
  btn.className = 'lbx-btn';
  btn.id = `${sel.id}-lbx-btn`;
  btn.setAttribute('aria-haspopup', 'listbox');
  btn.setAttribute('aria-expanded', 'false');
  const lbl = sel.getAttribute('aria-label');
  if(lbl) btn.setAttribute('aria-label', lbl);
  btn.innerHTML = `<span class="lbx-value"></span>`
    + `<svg class="lbx-chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor"`
    + ` stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">`
    + `<path d="M6 9l6 6 6-6"/></svg>`;
  const list = document.createElement('ul');
  list.className = 'lbx-list';
  list.id = `${sel.id}-lbx-list`;
  list.setAttribute('role', 'listbox');
  list.tabIndex = -1;
  list.hidden = true;
  if(lbl) list.setAttribute('aria-label', lbl);

  sel.parentNode.insertBefore(wrap, sel);
  wrap.appendChild(btn);
  wrap.appendChild(list);
  wrap.appendChild(sel);
  sel.classList.add('visually-hidden');
  sel.dataset.lbx = 'on';
  sel.setAttribute('tabindex', '-1');

  let open = false, active = -1, typed = '', typedAt = 0;
  const opts = () => [...list.children];

  function build(){
    list.innerHTML = '';
    [...sel.options].forEach((o, i) => {
      const li = document.createElement('li');
      li.className = 'lbx-opt';
      li.id = `${sel.id}-lbx-opt-${i}`;
      li.setAttribute('role', 'option');
      li.dataset.value = o.value;
      li.textContent = o.textContent;
      list.appendChild(li);
    });
    sync();
  }

  /* One place decides what is selected, and it reads the select. Writing the
     label from the click handler instead would let the button disagree with
     the value whenever anything else moved it. */
  function sync(){
    const i = sel.selectedIndex;
    btn.querySelector('.lbx-value').textContent = i === -1 ? '' : sel.options[i].textContent;
    opts().forEach((li, j) => li.setAttribute('aria-selected', j === i ? 'true' : 'false'));
    btn.disabled = sel.disabled || sel.options.length === 0;
  }

  function setActive(i){
    const items = opts();
    if(!items.length) return;
    active = Math.max(0, Math.min(i, items.length - 1));
    items.forEach((li, j) => li.classList.toggle('is-active', j === active));
    const li = items[active];
    list.setAttribute('aria-activedescendant', li.id);
    // block:'nearest' so opening on a mid-list selection does not jump the
    // page; the list is the scroll container, not the document.
    li.scrollIntoView({block: 'nearest'});
  }

  /* Freeze the button at the width of its longest label, for a control that
     asks for it with data-lbx-fit="widest".

     It measures a detached clone rather than wearing each label in turn,
     because changing sel.selectedIndex dispatches change, and the Week Board's
     change listener re-renders every game card -- six full re-renders on load
     to answer a question about text width.

     It runs TWICE, and the second run is the one that matters. The first
     happens before the webfont has arrived, so it measures the fallback face;
     everything about this defect is a sum of text widths, and a width frozen
     in the wrong typeface is the same class of wrong as the figure that
     started this. Measured here in Chromium: the widest label is 218px with
     Plus Jakarta Sans loaded and does not agree with the fallback. */
  function fitWidest(){
    if(sel.dataset.lbxFit !== 'widest') return;
    const probe = btn.cloneNode(true);
    probe.removeAttribute('id');
    probe.setAttribute('aria-hidden', 'true');
    probe.style.cssText = 'position:absolute; left:-9999px; top:0;'
                        + ' visibility:hidden; min-width:0; width:max-content;';
    document.body.appendChild(probe);
    const slot = probe.querySelector('.lbx-value');
    let widest = 0;
    [...sel.options].forEach(o => {
      slot.textContent = o.textContent;
      widest = Math.max(widest, probe.getBoundingClientRect().width);
    });
    probe.remove();
    if(widest) wrap.style.setProperty('--lbx-fit', Math.ceil(widest) + 'px');
  }

  /* Which edge the open list hangs from. Called only while the list is
     visible, because a [hidden] element is display:none and every rectangle
     it reports is zero -- measuring before unhiding gives right===0, which is
     never greater than clientWidth, so the flip would silently never happen
     and the control would look exactly as it does today.

     It flips back if flipping is worse. A list wider than the room to the
     left of the button's right edge would leave the viewport on the other
     side, and "fixed one edge by breaking the other" is a shape this repo has
     met before. Reverting is correct rather than clever: the pre-existing
     overflow is the lesser defect, and it is the one already recorded. */
  function placeList(){
    list.classList.remove('lbx-list--flip');
    const r = list.getBoundingClientRect();
    const anchor = wrap.getBoundingClientRect();
    if(lbxFlipDecision(r.left, r.width, anchor.right,
                       document.documentElement.clientWidth) === 'flip'){
      list.classList.add('lbx-list--flip');
    }
  }

  function openList(){
    if(open || btn.disabled) return;
    build();
    open = true;
    list.hidden = false;
    btn.setAttribute('aria-expanded', 'true');
    placeList();
    setActive(sel.selectedIndex === -1 ? 0 : sel.selectedIndex);
    list.focus();
  }

  function closeList(focusBtn){
    if(!open) return;
    open = false;
    list.hidden = true;
    btn.setAttribute('aria-expanded', 'false');
    list.removeAttribute('aria-activedescendant');
    if(focusBtn) btn.focus();
  }

  /* The write-back, and the only one. Setting .value without dispatching is
     how a control goes silently out of sync with the page it drives. */
  function choose(i){
    const items = opts();
    if(i < 0 || i >= items.length) return;
    sel.value = items[i].dataset.value;
    sync();
    sel.dispatchEvent(new Event('change'));
    closeList(true);
  }

  btn.addEventListener('click', (e) => {
    e.stopPropagation();
    open ? closeList(true) : openList();
  });
  btn.addEventListener('keydown', (e) => {
    if(e.key === 'ArrowDown' || e.key === 'ArrowUp' || e.key === 'Enter' || e.key === ' '){
      e.preventDefault();
      openList();
    }
  });

  list.addEventListener('click', (e) => {
    const li = e.target.closest('.lbx-opt');
    if(li) choose(opts().indexOf(li));
  });
  list.addEventListener('mousemove', (e) => {
    const li = e.target.closest('.lbx-opt');
    if(li) setActive(opts().indexOf(li));
  });
  /* Type-ahead. The 700ms window is what makes "ch" find Chronological rather
     than jumping to C and then to H. */
  const TYPE_WINDOW = 700;
  const typing = () => typed && Date.now() - typedAt < TYPE_WINDOW;
  function typeAhead(ch){
    const now = Date.now();
    typed = (typing() ? typed : '') + ch.toLowerCase();
    typedAt = now;
    const j = opts().findIndex(li => li.textContent.toLowerCase().startsWith(typed));
    if(j !== -1) setActive(j);
  }

  list.addEventListener('keydown', (e) => {
    const n = opts().length;
    switch(e.key){
      case 'ArrowDown': e.preventDefault(); setActive(active + 1); break;
      case 'ArrowUp':   e.preventDefault(); setActive(active - 1); break;
      case 'Home':      e.preventDefault(); setActive(0); break;
      case 'End':       e.preventDefault(); setActive(n - 1); break;
      case 'Enter':     e.preventDefault(); choose(active); break;
      /* Space is BOTH "select" and a character, and which one it is depends on
         whether a search is in flight. Two options share a first word --
         "Biggest Model Disagreement" and "Biggest Spread First" -- so the
         space is the keystroke that tells them apart and type-ahead cannot
         reach the second without it. Measured on the built page: typing
         "biggest s" walks the active option to "Biggest Spread First" with
         the list still open and nothing chosen; with the Space arm made
         unconditional, the space instead chose "Biggest Model Disagreement"
         and closed the list. Inside the window it extends the search; outside
         it, it selects.

         This example was re-measured when the "Sort: " prefix was dropped. It
         previously read "typing 'sort: b' chose option 0", which described a
         shared prefix that no longer exists -- and the behaviour it defends
         survives the copy change, which is why the arm is unchanged and only
         the sentence moved. */
      case ' ':
        e.preventDefault();
        if(typing()) typeAhead(' '); else choose(active);
        break;
      case 'Escape':    e.preventDefault(); closeList(true); break;
      case 'Tab':       closeList(false); break;
      default:
        if(e.key.length === 1 && !e.ctrlKey && !e.metaKey && !e.altKey){
          typeAhead(e.key);
        }
    }
  });
  list.addEventListener('focusout', (e) => {
    if(!wrap.contains(e.relatedTarget)) closeList(false);
  });
  document.addEventListener('click', (e) => {
    if(open && !wrap.contains(e.target)) closeList(false);
  });

  // Anything that moves the select -- the stepper, a share link, a filter
  // reset -- redraws the button through the same path a click takes.
  sel.addEventListener('change', sync);

  build();
  fitWidest();
  /* The second pass. document.fonts.ready settles after the webfont swaps in,
     and refresh() re-runs it too, because a control whose options arrive at
     runtime has a different longest label than the one it was built with. */
  if(document.fonts && document.fonts.ready) document.fonts.ready.then(fitWidest);
  return {refresh: () => { build(); fitWidest(); }};
}

/* The pages in the phone's "More" sheet, so the More button lights up on
   them. It listed four pages Stage 7.5 folded away and missed What's
   Changed (the 2026-09-28 audit); tests/test_more_button_pages.py holds it
   equal to the sheet's own buttons. */
const OVERFLOW_PAGES = ['teamdive','method','changelog','modellab','reliability'];
/* A page change says so three ways (Stage 26 item 2, from the 2026-09-28
   audit). Until then only the look changed: the tab kept the product name as
   its title on every page, focus stayed on the nav button, so a screen
   reader heard nothing of the new page, and the chosen nav button was
   marked only by .active. Now the nav buttons for the page carry
   aria-current="page", the document title names the page by its heading,
   and a change the reader asked for (a nav click, Back or Forward) moves
   focus to that heading. The first paint moves no focus: a page opened
   from a link starts where a page normally starts. */
const BASE_TITLE = document.title;
function pageHeading(pageId){
  const page = document.getElementById('page-' + pageId);
  return page && (page.querySelector('.page-head h2') || page.querySelector('h2'));
}
function setActivePage(pageId, opts){
  document.querySelectorAll('[data-page]').forEach(b=>{
    const on = b.dataset.page === pageId;
    b.classList.toggle('active', on);
    if(on) b.setAttribute('aria-current', 'page'); else b.removeAttribute('aria-current');
  });
  document.querySelectorAll('.page').forEach(p=>p.classList.toggle('active', p.id==='page-'+pageId));
  const moreBtn = document.getElementById('bnav-more-btn');
  if(moreBtn) moreBtn.classList.toggle('active', OVERFLOW_PAGES.includes(pageId));
  closeMoreSheet();
  window.scrollTo({top:0, behavior:'auto'});
  const heading = pageHeading(pageId);
  document.title = (pageId === 'board' || !heading) ? BASE_TITLE
    : `NFL ${heading.textContent.trim()} — Sportalytics`;
  if(opts && opts.focus && heading){
    heading.setAttribute('tabindex', '-1');
    heading.focus({preventScroll:true});
  }
}
document.querySelectorAll('[data-page]').forEach(btn=>{
  // goToPage (Hash routes, at the end of this script) switches the page AND
  // records it in the address, so the back button and a copied link work.
  btn.addEventListener('click', ()=> goToPage(btn.dataset.page));
});

/* The More sheet is always in the page: closed, it is only moved below the
   screen with a transform. Without `inert` its five buttons stayed in the
   Tab order and in the accessibility tree -- at 1440x900 the 19th Tab press
   focused "Team Deep-Dive" at top 917, on a sheet that never opens at that
   width (Stage 11; measured in docs/design/UX-REVIEW-2026-09-26.md). The
   markup starts inert, and this is the ONE place that opens or closes the
   sheet, so the class and the attribute cannot disagree. */
function setMoreSheetOpen(open){
  const sheet = document.getElementById('bnav-more-sheet');
  if(!sheet) return;
  sheet.classList.toggle('open', open);
  sheet.inert = !open;
}
function closeMoreSheet(){
  setMoreSheetOpen(false);
}
const moreBtn = document.getElementById('bnav-more-btn');
/* Stage 78 item 43: the sheet's own close button. */
const moreClose = document.querySelector('#bnav-more-sheet .bnav-more-close');
if(moreClose) moreClose.addEventListener('click', () => { closeMoreSheet(); if(moreBtn) moreBtn.focus(); });
if(moreBtn){
  moreBtn.addEventListener('click', (e)=>{
    e.stopPropagation();
    setMoreSheetOpen(!document.getElementById('bnav-more-sheet').classList.contains('open'));
  });
}
document.addEventListener('click', (e)=>{
  const sheet = document.getElementById('bnav-more-sheet');
  if(sheet && sheet.classList.contains('open') && !sheet.contains(e.target) && e.target.id!=='bnav-more-btn' && !e.target.closest('#bnav-more-btn')){
    closeMoreSheet();
  }
});

