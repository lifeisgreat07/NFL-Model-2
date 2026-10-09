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
const STATE_KINDS = ['waiting', 'filtered', 'missing', 'note'];
function stateHtml(kind, title, paras, action, extra){
  if(!STATE_KINDS.includes(kind)) throw new Error('unknown page state: ' + kind);
  if(kind === 'filtered' && !action) throw new Error('a filtered state needs its undo action');
  const body = (Array.isArray(paras) ? paras : [paras]).filter(Boolean)
    .map(t => kind === 'note' ? ' ' + t : `<p>${t}</p>`).join('');
  const titleEl = kind === 'note' ? `<b class="state-title">${title}</b>` : `<span class="state-title">${title}</span>`;
  const btn = action ? `<button class="btn" onclick="${action.onclick}">${action.label}</button>` : '';
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
  return `${w.season} · Week ${w.week}${w.preview ? ' (preview)' : ''}`;
}

// "Tue Sep 29, 16:41 UTC" from a preview's ISO stamp. UTC, like the page's
// "Updated" line, so the two can be compared at a glance.
function previewWhen(iso){
  const d = iso ? new Date(iso) : null;
  if(!d || isNaN(d)) return 'the last run';
  const day = d.toLocaleDateString('en-US', {weekday:'short', month:'short', day:'numeric', timeZone:'UTC'});
  const hm = d.toISOString().slice(11, 16);
  return `${day.replace(',', '')}, ${hm} UTC`;
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
    : `${heading.textContent.trim()} — Pick'em Model`;
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

/* ---------- Power Ratings ---------- */
/* Places a team moved since the previous weekly update (Stage 19). The arrow
   follows RANK, not rating (Mark, 2026-09-28): a team can gain rating and
   still lose places when others gain more, and an arrow disagreeing with the
   number beside it is exactly what a reader would notice. null (no previous
   ranking) prints nothing; 0 (did not move) prints only a hidden "no change"
   so a screen reader is not left guessing. */
function rankMoveHtml(change){
  if(change === null || change === undefined) return '';
  if(change === 0) return '<span class="visually-hidden">, no change in rank</span>';
  const up = change > 0, n = Math.abs(change);
  const words = `${up ? 'up' : 'down'} ${n} place${n === 1 ? '' : 's'} since the last update`;
  return `<span class="trend-arrow ${up?'up':'down'}" title="${words[0].toUpperCase() + words.slice(1)}"><span aria-hidden="true">${up?'&#9650;':'&#9660;'}${n}</span><span class="visually-hidden">, ${words}</span></span>`;
}
/* The one line above the table naming the biggest rise and the biggest fall
   (Stage 19). League-wide, not the searched view. Ties are named together,
   two at most and then counted, so a week where five teams rose three places
   does not print a paragraph. */
function moversSentence(teams){
  const moved = teams.filter(t => typeof t.rank_change === 'number');
  if(!moved.length) return '';
  const changes = moved.map(t => t.rank_change);
  const most = Math.max(...changes), least = Math.min(...changes);
  if(most <= 0 && least >= 0) return 'No team changed places since the last update.';
  const named = v => moved.filter(t => t.rank_change === v).map(t => t.name).sort();
  const list = a => a.length <= 2 ? a.join(' and ') : `${a.slice(0, 2).join(', ')} and ${a.length - 2} more`;
  const places = n => `${n} place${n === 1 ? '' : 's'}`;
  const parts = [];
  if(most > 0) parts.push(`${list(named(most))} up ${places(most)}`);
  if(least < 0) parts.push(`${list(named(least))} down ${places(-least)}`);
  return `Biggest moves since the last update: ${parts.join('; ')}.`;
}
let sortKey = 'net', sortDir = -1;
function renderRatings(){
  const movers = document.getElementById('ratings-movers');
  if(movers){
    const line = moversSentence(teams);
    movers.textContent = line;
    movers.hidden = !line;
  }
  const sorted = [...teams].sort((a,b)=>{
    if(sortKey==='team') return a.team.localeCompare(b.team)*sortDir;
    const av = (a[sortKey]===null||a[sortKey]===undefined) ? -Infinity : a[sortKey];
    const bv = (b[sortKey]===null||b[sortKey]===undefined) ? -Infinity : b[sortKey];
    return (av-bv)*sortDir;
  });
  // The # is the team's POWER RATING rank and it travels with the team. It is
  // NOT the row's position in the current sort: on a page titled Power
  // Ratings, sorting by Playoff Odds and relabelling the 9th-rated team "#1"
  // asserts something the model never said, and "#1" is exactly the part a
  // casual reader takes away. The rank is computed once in Python from the
  // net-rating order (`build_teams_js`) so every view agrees on it -- which
  // also means it survives filtering, and a searched team keeps its league
  // position instead of becoming "1" for being the only match on screen.
  const ranked = sorted.map(t=>({...t, _rank: t.rank}));
  const searchEl = document.getElementById('ratings-search');
  const q = searchEl ? searchEl.value.trim().toLowerCase() : '';
  const visible = q ? ranked.filter(t=>
    t.team.toLowerCase().includes(q) || (t.name && t.name.toLowerCase().includes(q))
  ) : ranked;

  /* The simulation count, printed into the Playoff Odds glossary entry.

     It used to live in a card above this table and was shown only while some
     team actually had odds -- a caveat about data that is not on screen being
     just more words. The card is gone; the sentence is on Methodology now,
     where it is a definition rather than a caveat and is therefore true
     whether or not this table has odds in it today. So there is no longer a
     condition, only the number.

     Still filled from playoffMeta rather than written into the prose: the
     count is a property of the run that produced the odds, and a figure typed
     into a sentence is a figure nothing recomputes. */
  const sims = document.getElementById('playoff-sims');
  if(sims && playoffMeta && playoffMeta.n_simulations){
    sims.textContent = playoffMeta.n_simulations.toLocaleString();
  } else if(sims){
    sims.textContent = 'many thousands of';
  }

  const sosNote = document.getElementById('sos-empty-note');
  if(sosNote){
    const anySos = teams.some(t=>t.sos!==null && t.sos!==undefined);
    sosNote.style.display = anySos ? 'none' : 'block';
  }

  const maxAbs = Math.max(...teams.map(t=>Math.abs(t.net)), 0.0001);

  // Print the domain the bars are drawn against. Computed from the whole
  // league, not the filtered view -- searching for one team must not silently
  // rescale the axis under the reader.
  const axMin = document.querySelector('#ratings-table .ax-min');
  const axMax = document.querySelector('#ratings-table .ax-max');
  if(axMin && axMax){
    axMin.textContent = '−' + fmtRatingScale(maxAbs);
    axMax.textContent = '+' + fmtRatingScale(maxAbs);
  }

  const body = document.getElementById('ratings-body');
  if(visible.length === 0){
    body.innerHTML = ratingsNoMatchRow(q);
    return;
  }
  body.innerHTML = visible.map((t)=>{
    const i = t._rank - 1;
    const width = (Math.abs(t.net)/maxAbs)*100;
    // Places moved since the previous weekly update, computed in Python
    // (previous_ranks) so it agrees with the # column. Stage 19 replaced a
    // rating-delta arrow here: the arrow now follows RANK.
    const trendHtml = rankMoveHtml(t.rank_change);
    return `<tr>
      <td class="rank">${i+1}</td>
      <td><div class="team-cell"><a class="row-link" href="${routeHash({page:'teamdive', team:t.team})}"><img class="team-logo" src="${teamLogo(t.team)}" alt="" loading="lazy" referrerpolicy="no-referrer" onerror="this.style.display='none'"><span class="team-abbr">${t.team}</span><span class="team-full">${t.name}</span></a>${trendHtml}</div></td>
      <td class="num"><div class="net-cell-inner">
        <div class="srs-bar-track diverging" title="${fmtRating(t.net)} per 100 plays; league scale ±${fmtRatingScale(maxAbs)}, centre line is zero"><div class="srs-bar-fill" style="left:${t.net>=0?50:50-width/2}%; width:${width/2}%;"></div></div>
        <span class="net-value">${fmtRating(t.net)}</span>
      </div></td>
      <td class="num">${fmtRating(t.off)}</td>
      <td class="num">${fmtRating(t.def)}</td>
      <td class="num">${(t.sos===null||t.sos===undefined)
        ? '<span title="No games played yet, so there are no opponents to average.">—</span>'
        : fmtRating(t.sos)}</td>
      <td class="num">${(t.playoff===null||t.playoff===undefined)
        ? '<span title="This team was not in the simulation.">—</span>'
        : t.playoff.toFixed(1)+'%'}</td>
    </tr>`;
  }).join('');
}
document.querySelectorAll('#ratings-table th[data-key]').forEach(th=>{
  const sortBy = ()=>{
    const key = th.dataset.key;
    if(key==='rank') return;
    if(sortKey===key){sortDir*=-1;} else {sortKey=key; sortDir=-1;}
    document.querySelectorAll('#ratings-table th').forEach(h=>{
      h.classList.remove('sorted');
      if(h.hasAttribute('aria-sort')) h.setAttribute('aria-sort', 'none');
    });
    th.classList.add('sorted');
    th.setAttribute('aria-sort', sortDir === -1 ? 'descending' : 'ascending');
    renderRatings();
  };
  th.addEventListener('click', sortBy);
  // A header that sorts is a control, so a keyboard has to reach it: it
  // carries tabindex="0" in the markup, and Enter or Space sorts.
  th.addEventListener('keydown', e=>{
    if(e.key === 'Enter' || e.key === ' '){ e.preventDefault(); sortBy(); }
  });
});
renderRatings();

const ratingsSearchEl = document.getElementById('ratings-search');
if(ratingsSearchEl){
  ratingsSearchEl.addEventListener('input', ()=> renderRatings());
}

/* Proof of lock (Stage 46 item 5): which commit last changed a week's
   picks before its first kickoff, and any commit after it, each linked to
   GitHub, where its time cannot be edited. commits are oldest first, from
   src/sports/nfl/lock_proof.py. Empty when there is nothing to say. */
function lockUtc(ms){
  const d = new Date(ms);
  return d.toLocaleDateString('en-US', {weekday: 'short', month: 'short', day: 'numeric', timeZone: 'UTC'})
    + ', ' + d.toLocaleTimeString('en-GB', {hour: '2-digit', minute: '2-digit', timeZone: 'UTC'}) + ' UTC';
}
function lockCommitLink(c){
  return `<a href="${escapeHtml(c.url)}" target="_blank" rel="noopener">${escapeHtml(c.short)}</a>`;
}
function lockProofHtml(commits, games){
  if(!commits || !commits.length || !games || !games.length) return '';
  const kicks = games.map(kickoffInstant).filter(k => k !== null);
  if(!kicks.length) return '';
  const first = Math.min(...kicks);
  const at = c => Date.parse(c.committed_utc);
  const before = commits.filter(c => at(c) < first), after = commits.filter(c => at(c) >= first);
  const parts = [];
  if(before.length){
    const last = before[before.length - 1];
    const hours = Math.floor((first - at(last)) / 3600000);
    const lead = hours >= 48 ? `${Math.floor(hours / 24)} days` : `${hours} hour${hours === 1 ? '' : 's'}`;
    parts.push(`These picks were last changed in commit ${lockCommitLink(last)} on ${lockUtc(at(last))}, ${lead} before the week's first kickoff.`);
    if(before.length > 1) parts.push(`First saved in ${lockCommitLink(before[0])} on ${lockUtc(at(before[0]))}.`);
  } else {
    parts.push('No commit of these picks is dated before the first kickoff.');
  }
  if(after.length){
    parts.push(`Changed after kickoff: ${after.map(c => `${lockCommitLink(c)} (${escapeHtml(c.subject)})`).join('; ')}.`);
  }
  return parts.join(' ');
}
function renderLockProof(weekKey, weekData){
  const el = document.getElementById('board-lock-note');
  if(!el) return;
  const commits = (lockProof && lockProof.weeks) ? lockProof.weeks[weekKey] : null;
  const html = (weekData && !weekData.preview) ? lockProofHtml(commits, weekData.games) : '';
  el.innerHTML = html;
  el.hidden = !html;
}
/* ---------- Week Board ---------- */
let currentBoardWeek = latestWeekKey;
let currentFilter = 'all';
/* Kickoff order, not confidence. A week is a sequence of games before it is a
   ranking of them: the reader's first question is what is on next, and the
   board answering with "most confident" made them re-sort every visit to find
   out. Confidence is still one click away, and is still the secondary sort
   inside a single kickoff slot, which is where it earns its place -- thirteen
   of week 1's sixteen games start at the same minute. */
let currentSort = 'chronological';

function populateWeekSelect(selectEl, onChange, initial){
  if(weekKeysSorted.length===0){
    selectEl.innerHTML = `<option>No weeks saved yet</option>`;
    selectEl.disabled = true;
    return;
  }
  selectEl.innerHTML = weekKeysSorted.map(k=>`<option value="${k}">${weekLabel(k)}</option>`).join('');
  selectEl.value = initial || weekKeysSorted[weekKeysSorted.length-1];
  selectEl.addEventListener('change', ()=> onChange(selectEl.value));
}

/* Marks the side a model picked, and - once the game is played - whether that
   pick was right.

   Three states, and the colour is what separates them:

     picked, not graded  tick in --accent    "this is the model's pick"
     picked, correct     tick in --good      "the pick was right"
     picked, wrong       cross in --warn     "the pick was wrong"
     not picked          dashed outline      the other side, or a toss-up

   The pre-game tick is deliberately NOT green. The version before this drew a
   green tick on unplayed games, which said a model had been proved right about
   a game nobody had played; that was one of six graded-colour violations fixed
   in PR #52, and the onboarding copy had to be rewritten because it described
   the tick as showing "which team each model actually favors" - which is the
   job being restored here, minus the false verdict.

   --accent is the right token for it: Job 2 is the model's lean and the active
   thing. --good and --warn stay Job 3, graded outcomes only, and still cannot
   appear on a game that has not happened. Bold weight beside the badge carries
   the same information for anyone who cannot separate the two hues. */
function pickBadge(picked, graded, correct){
  // A graded game with no verdict is a tie (Stage 30 item 1): no badge, since
  // a tick or a cross would each claim a result the game did not have.
  if(!picked || (graded && (correct === null || correct === undefined)))
    return `<span class="pick-badge placeholder"></span>`;
  const tick = '<path d="M20 6L9 17l-5-5"/>';
  const cross = '<path d="M6 6l12 12M18 6L6 18"/>';
  const state = !graded ? 'picked' : (correct ? 'correct' : 'incorrect');
  const label = !graded ? "this model's pick"
    : (correct ? 'this model was right' : 'this model was wrong');
  return `<span class="pick-badge ${state}" title="${label}">`
    + `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round">${state === 'incorrect' ? cross : tick}</svg></span>`;
}

/* The graded tag on a card: Model B's verdict (Model A's when B had no
   pick), or "Tie" for a graded game with no winner. Until Stage 30 item 1 a
   tie fell through `?? ... ? 'correct' : 'incorrect'` to "Missed" with the
   warn colour, because null is falsy. */
function gradedTagHtml(g){
  if(!g.graded) return '';
  const verdict = g.model_b_correct ?? g.model_a_correct;
  if(g.result === 'tie' || verdict === null || verdict === undefined)
    return `<span class="graded-tag tie">Tie</span>`;
  return `<span class="graded-tag ${verdict ? 'correct' : 'incorrect'}">${verdict ? 'Correct' : 'Missed'}</span>`;
}

/* Turns the model's own numbers into a football sentence.

   g.why holds what the football-only model actually used: each feature's
   contribution, signed toward the HOME team. Those are the real quantities the
   model added up, not a story told afterwards -- which is the only reason it is
   honest to narrate them at all.

   Three rules, so the wording is derived rather than chosen:
     - the favourite is whichever side the football-only model gives over 50%;
     - each contribution is flipped, if needed, to point toward that favourite,
       so "helps" and "hurts" mean the same thing in every card;
     - how much one reason dominates is its share of the total movement on the
       card, and that share picks the phrase. A reason carrying most of the
       card gets "almost entirely"; a near-tie gets neither name promoted.

   Deliberately returns markup so tests/test_plain_language.py scans this copy.
   A helper returning bare text would escape the jargon guard entirely, which
   is the sort of gap that only shows up months later. */
const WHY_IN_WORDS = {
  off_matchup: {
    toward: (fav, dog) => `${fav}'s offense against ${dog}'s defense`,
    neutral: 'the offense-versus-defense matchup',
  },
  def_matchup: {
    toward: (fav, dog) => `${fav}'s defense against ${dog}'s offense`,
    neutral: 'the defense-versus-offense matchup',
  },
  qb_matchup: {toward: () => 'the quarterback matchup', neutral: 'the quarterback matchup'},
  qb_change:  {toward: () => 'a change at quarterback', neutral: 'the change at quarterback'},
};

function whyParts(g){
  if(!g.why) return null;
  const homeFav = g.fbA_home >= 50;
  const fav = homeFav ? g.home : g.away;
  const dog = homeFav ? g.away : g.home;
  const sign = homeFav ? 1 : -1;
  const parts = Object.keys(WHY_IN_WORDS)
    .filter(k => typeof g.why[k] === 'number' && g.why[k] !== 0)
    .map(k => ({key:k, toward: g.why[k] * sign,
                text: WHY_IN_WORDS[k].toward(fav, dog),
                neutral: WHY_IN_WORDS[k].neutral}))
    .sort((a,b) => Math.abs(b.toward) - Math.abs(a.toward));
  if(!parts.length) return null;
  const total = parts.reduce((s,p) => s + Math.abs(p.toward), 0);
  return {fav, dog, parts, total, helps: parts.filter(p=>p.toward>0), hurts: parts.filter(p=>p.toward<0)};
}

function whySentence(g){
  const w = whyParts(g);
  if(!w) return '';
  const top = w.parts[0];
  const share = w.total > 0 ? Math.abs(top.toward)/w.total : 0;

  // Nothing is really driving this one. Saying so is more useful than naming
  // the largest of several tiny numbers as though it were a reason.
  if(w.total < 0.10){
    return `<p class="why-words">Nothing much separates these two. ${w.fav} come out
      barely ahead, and a game this close is one the model expects to get wrong
      about as often as it gets it right.</p>`;
  }

  let lead;
  if(top.toward > 0 && share >= 0.6){
    lead = `${w.fav} are ahead here almost entirely on ${top.text}.`;
  } else if(top.toward > 0 && w.helps.length > 1){
    // Second factor named neutrally. Spelling both out in full gives
    // "mainly on KC's offense against DEN's defense, with KC's defense
    // against DEN's offense adding to it" -- correct, and nobody finishes it.
    lead = `${w.fav} are ahead here mainly on ${top.text}, with ${w.helps[1].neutral} adding to it.`;
  } else if(top.toward > 0){
    lead = `${w.fav} are ahead here on ${top.text}.`;
  } else {
    // The biggest single factor points at the underdog and the favourite still
    // wins on the rest. Worth saying plainly -- it is the most interesting
    // thing on such a card, and hiding it would flatter the pick.
    lead = `${w.fav} come out ahead despite ${top.text}, which favours ${w.dog}.`;
  }

  // Named by which side it favours, not as "X pulls the other way". The first
  // version read "DEN's offense against KC's defense pulls the other way",
  // which states a fact about Denver's offense and then contradicts it in the
  // same breath. Whose side a factor is on is the thing a reader wants.
  const against = top.toward > 0 && w.hurts.length
    ? ` ${w.hurts[0].neutral.charAt(0).toUpperCase() + w.hurts[0].neutral.slice(1)} favours ${w.dog}.`
    : '';

  return `<p class="why-words">${lead}${against}</p>`;
}

function whyMarketSentence(g){
  if(g.spread === null || g.spread === undefined) return '';
  const modelFav = g.fbA_home >= 50 ? g.home : g.away;
  // spread_line is POSITIVE when the home team is favoured. Verified against
  // the saved predictions rather than assumed: SEA home vs NE, spread_line
  // +3.5, market_prob_home 0.6539 -- the market has the home side at 65%, so
  // positive is home. The card's "Vegas line: LAC -10.5" display negates it,
  // which is the football convention and the reason this is easy to get
  // backwards. The first version of this line did, and said "the betting line
  // agrees" on a game where Model A had ARI at 80.5% and the line had LAC by
  // 10.5 -- confidently wrong, on every card, and invisible in the diff.
  const lineFav = g.spread > 0 ? g.home : g.away;
  const by = fmtPoints(Math.abs(g.spread));
  return lineFav === modelFav
    ? `<p class="why-words dim">The betting line agrees, making ${lineFav} favourites by ${by}.</p>`
    : `<p class="why-words dim">The betting line disagrees, making ${lineFav} favourites by ${by}.</p>`;
}

/* The sentence under a label saying whose it is (Stage 17). whySentence() is
   Model A's reasoning -- it reads g.why, which holds the football-only
   model's contributions, and names Model A's favourite -- while the card's
   headline is Model B's. Where they disagree (KC@MIA, week 3: Model B KC 86%,
   Model A MIA 57%) an unlabelled "MIA are ahead here..." sits under "KC 86%
   to win" and reads as a contradiction. The label goes only where there is a
   sentence to label. */
function whyLabelled(g){
  const words = whySentence(g);
  return words ? `<div class="why-by">Model A&#39;s reasoning</div>${words}` : '';
}

/* ---------- Units (Stage 14: one meaning per number) ----------
   "Points" on this page means football points and nothing else: a spread,
   a margin, a pick'em value. A gap between two percentages is "pp"
   (percentage points), never "pt" -- before Stage 14 the Model Lab and
   Methodology tables wrote accuracy gaps as "+0.83pt", one character from
   a point spread. tests/test_units.py bans a bare "pt"/"pts" anywhere a
   reader can see it.

   fmtPoints writes a spread in words with its unit. Lines move in half
   points, so a whole number drops its ".0" ("6 points", "6.5 points"), and
   one point is singular. The card said "favourites by 6.0" with no unit. */
function fmtPoints(n){
  const v = Math.round(Math.abs(n) * 10) / 10;
  const text = Number.isInteger(v) ? String(v) : v.toFixed(1);
  return `${text} point${v === 1 ? '' : 's'}`;
}

/* A rating, shown per 100 plays (Stage 14; Mark chose it from a rendered
   side-by-side on 2026-09-26). The model and the data stay in EPA per play
   -- BUF +0.149 -- and only the display is rescaled: +14.9 expected points
   better than an average team over 100 plays. One decimal, a sign on
   anything that is not zero, and a rating that rounds to zero shows as 0.0
   rather than -0.0. ratingScale() is the one place the factor lives -- a
   function, not a const, because renderRatings() runs at load from higher
   up this script, where a const declared here would still be in its
   temporal dead zone. tests/test_per_100_plays.py holds the display to the
   data. */
function ratingScale(){ return 100; }
function fmtRating(epaPerPlay){
  const v = Math.round(epaPerPlay * ratingScale() * 10) / 10;
  // No branch for zero: Math.round gives -0 for a small negative, and
  // (-0).toFixed(1) is "0.0", so a rating that rounds to zero is unsigned.
  return v > 0 ? '+' + v.toFixed(1) : v.toFixed(1);
}
/* A bar's scale, in the same units, to the nearest whole number. */
function fmtRatingScale(epaPerPlay){
  return String(Math.round(Math.abs(epaPerPlay) * ratingScale()));
}

function whyRow(label, val){
  const pct = Math.min(50, Math.abs(val)*300); // scaled for visual width, not a real unit
  const cls = val >= 0 ? 'pos' : 'neg';
  return `<div class="why-row">
    <span class="why-label">${label}</span>
    <div class="why-bar-track"><div class="why-bar-fill ${cls}" style="width:${pct}%;"></div></div>
    <span class="why-val">${val>=0?'+':''}${val.toFixed(3)}</span>
  </div>`;
}

/* The Week Board's summary strip is gone: Games / Most confident / Biggest
   model gap. The owner asked for it removed twice -- "I do not need this at
   all" -- and each tile earns that independently. Games duplicated the "16
   games" badge already in the page head. Biggest model gap is the A-vs-market
   gap he separately called unnecessary on the cards, stated in a unit
   ("59pt") nobody has a scale for. Most confident restated what the first
   card in the default sort already showed, because the board sorted by
   confidence at the time. It no longer does -- the default is now kickoff
   order -- so that particular argument has expired even though the decision
   it supported has not. Recorded rather than quietly reworded: the tile is
   still not coming back, but the next person should not find a reason here
   that stopped being true and assume the rest of the paragraph is current.

   Kept as an empty function rather than deleted outright because renderGames
   calls it and the #week-glance node is a stable hook: the strip may come
   back as something that earns its space, and an empty seam is easier to fill
   than a removed one is to rebuild. */
function renderWeekGlance(gamesList){
  const el = document.getElementById('week-glance');
  if(el) el.innerHTML = '';
}

/* ---------- The matchup title, built in ONE place ----------
   Two functions render a .game-card: renderGames() for the Week Board and
   renderPicksGrid() for My Picks. Both used to hand-build this title, and
   that is not a tidiness complaint -- it is why the `@` separator survived
   on My Picks after being changed everywhere else. One edit, two sites, one
   of them missed, and nothing could tell: the diff looked complete.

   Appearance is deliberately NOT unified here. On My Picks the two pick
   buttons already carry both team abbreviations, so the title is a quiet
   label rather than a heading, and it is measured at 11px / weight 400 /
   --text-2 on the rendered page. Whether that is right is a Stage 9/10
   question about the card, not something a refactor should decide on its
   way past. The variant keeps the CSS free to differ while the MARKUP can
   only be written once.

   The note that used to sit here warned that `.game-kickoff` held a
   confidence rank and would collide with a real kickoff. That happened, and
   the class is now `.game-confidence`; the kickoff line on both cards is
   `.card-kickoff`. Left as a record rather than deleted: the warning was
   written a fortnight before the collision, which is the argument for
   writing them down at all. */
/* ---------- The pick button ----------
   A team tile rather than a word: a logo above the abbreviation, so the thing
   you tap is recognisable at a glance instead of three capital letters.

   The logo is decorative and carries alt="" deliberately. The abbreviation is
   real text beside it, so a screen reader that announced both would read the
   team twice; and the button's accessible name has to stay the abbreviation
   because that is what the pick is recorded as. onerror hides the image
   rather than leaving a broken-image glyph -- the logos come from a third
   party and the tile has to survive that host being unreachable, which is why
   the abbreviation is the text and not the picture. */
function pickButton(team, pick, locked){
  // `locked` is emitted here so the first frame is right; paintPickCard
  // re-derives it on every path, the same way it re-derives `selected`.
  return `<button class="pick-btn ${pick===team?'selected':''}" data-team="${team}"`
    + (locked ? ` disabled aria-label="${team}, locked at kickoff"` : '') + `>`
    + `<img class="pick-logo" src="${teamLogo(team)}" alt="" loading="lazy" referrerpolicy="no-referrer" onerror="this.style.display='none'">`
    + `<span class="pick-abbr">${team}</span>`
    + `</button>`;
}

/* ---------- The card's probability line (Stage 17, card v2) ----------
   Mark chose "B refined" on 2026-09-27 from rendered side-by-sides (dark,
   light, deutan): the team-colour bar is kept and shows Model B's split; the
   three probabilities sit on ONE line beneath it, on the same scale, with the
   shapes Season Accuracy uses (Model A circle, Model B square, Market
   triangle). Model B is the headline because it is the better model on
   proper scoring rules (Model Lab); the market is shown as a probability,
   not only as a spread.

   Everything is stored as the HOME side's percentage; a side is named by
   which half of the line it falls in. Within CARD_EVEN_BAND points of 50 a
   series has picked nobody, and the card says so rather than bolding a team
   on a 50.4 / 49.6 split. */
const CARD_EVEN_BAND = 2;

function cardSide(pHome, g){
  if(pHome === null || pHome === undefined) return null;
  if(Math.abs(pHome - 50) < CARD_EVEN_BAND) return {team: null, pct: Math.max(pHome, 100 - pHome)};
  return pHome >= 50 ? {team: g.home, pct: pHome} : {team: g.away, pct: 100 - pHome};
}

/* Markers closer than CARD_NEAR points would hide one another. 7 is measured,
   not picked: the narrowest line (176px, at a 360px screen) gives a 12px
   marker 6.8 points of the scale, so two markers 7 points apart on the same
   lane cannot touch at any supported width. (The first cut used 3 points and
   9px lanes; measured on the built page, markers overlapped by more than half
   a pixel on 12 of week 3's 16 cards at 1280px and 13 at 390px.) When they would, each takes a FIXED lane -- the Market above the line, Model B on it,
   Model A below -- so the same series always moves the same way and a reader
   learns it once. A marker with no neighbour stays on the line. */
/* The card's series, in the same colours and shapes as SERIES below. A copy
   rather than a reference: SERIES is declared further down the script than
   the Week Board's first render, and reading a const before its line throws
   (it did, in the first render of this card). tests/test_card_v2.py holds
   the two to each other. */
const CARD_SERIES = {
  a:      {label:'Model A', color:'var(--series-a)', shape:'circle'},
  b:      {label:'Model B', color:'var(--series-b)', shape:'square'},
  market: {label:'Market',  color:'var(--series-c)', shape:'triangle'},
};

const CARD_NEAR = 7;
const CARD_LANE = {market: -1, b: 0, a: 1};

function cardLanes(vals){
  const keys = Object.keys(vals).filter(k => vals[k] !== null && vals[k] !== undefined);
  const out = {};
  keys.forEach(k => {
    const crowded = keys.some(o => o !== k && Math.abs(vals[o] - vals[k]) < CARD_NEAR);
    out[k] = crowded ? CARD_LANE[k] : 0;
  });
  return out;
}

function cardSideText(s){
  return s.team ? `${s.team} ${Math.round(s.pct)}%` : `even (${Math.round(s.pct)}%)`;
}

/* The one sentence a screen reader hears for the whole visual. */
function cardAria(g){
  const b = cardSide(g.mktB_home, g), a = cardSide(g.fbA_home, g), m = cardSide(g.mkt_home, g);
  return [`Model B ${cardSideText(b)}`, m ? `Market ${cardSideText(m)}` : null,
          `Model A ${cardSideText(a)}`].filter(Boolean).join('. ') + '.';
}

/* Whether the two models pick different teams: the one test behind the
   card's "Models split" badge, its "Model A picks X; Model B picks Y" line
   and the Model Disagreement filter. The badge and the filter used to test
   a 12-point gap instead, so a card could say "Models agree" above a line
   saying the models picked different teams (TEN@NYG, 2026 week 3: Model A
   TEN 53%, Model B NYG 55%) -- and 12 points apart on the same team read
   as a split. A model within CARD_EVEN_BAND of 50 has picked nobody, which
   is not a disagreement about who wins. */
function modelsSplit(g){
  const a = cardSide(g.fbA_home, g), b = cardSide(g.mktB_home, g);
  return !!(a && b && a.team && b.team && a.team !== b.team);
}

/* Named only when Model A picks the OTHER team from Model B -- not when one
   of them calls it even, which is not a disagreement about who wins. */
function cardDisagreement(g){
  if(!modelsSplit(g)) return '';
  const a = cardSide(g.fbA_home, g), b = cardSide(g.mktB_home, g), m = cardSide(g.mkt_home, g);
  const withB = m && m.team === b.team ? 'Model B and the market pick' : 'Model B picks';
  return `Model A picks <b>${a.team}</b>; ${withB} <b>${b.team}</b>.`;
}

/* A game that is over but not graded yet (Stage 26 item 1, from the
   2026-09-28 audit). The card went on saying "GB 68% to win" after the final
   whistle. Now it says what Model B picked and who won, in the headline's
   own neutral grey: no right or wrong, which is the graded tag's to say once
   grading runs, and no word on when grading happens, which Mark removed on
   2026-09-28 as redundant. The score is the weekend refresh's, so it is
   stated as a result, not scored. Returns '' for any other state. */
function cardProvisional(g){
  if(g.status !== 'final' || g.graded || !gameHasScore(g)) return '';
  if(g.away_score === g.home_score) return 'a tie';
  return `${g.away_score > g.home_score ? g.away : g.home} won`;
}

function cardProbHtml(g, awayC, homeC){
  const b = cardSide(g.mktB_home, g), a = cardSide(g.fbA_home, g), m = cardSide(g.mkt_home, g);
  const vals = {b: g.mktB_home, a: g.fbA_home, market: g.mkt_home};
  const lanes = cardLanes(vals);
  const mark = k => {
    if(vals[k] === null || vals[k] === undefined) return '';
    const s = CARD_SERIES[k];
    // 12px markers on 12px lanes: a laned marker clears its neighbour.
    return `<svg class="card-mk" style="left:${vals[k]}%; top:calc(50% + ${lanes[k] * 12}px)" width="12" height="12" viewBox="0 0 12 12" aria-hidden="true">`
      + `${markerPath(s.shape, 6, 6, 4.5)} fill="${s.color}"/></svg>`;
  };
  const key = (k, side) => {
    const s = CARD_SERIES[k];
    return `<span class="card-key"><svg width="12" height="12" viewBox="0 0 14 14" aria-hidden="true">${markerPath(s.shape, 7, 7, 5)} fill="${s.color}"/></svg>`
      + `${s.label} <b>${cardSideText(side)}</b></span>`;
  };
  const bPicksAway = b.team === g.away, bPicksHome = b.team === g.home;
  const done = cardProvisional(g);
  const after = done ? `<span class="card-hl-to">&middot; ${done}</span>` : '<span class="card-hl-to">to win</span>';
  const headline = b.team
    ? `<span class="card-hl-label">Model B${done ? ' picked' : ''}</span> <b>${b.team} ${Math.round(b.pct)}%</b> ${after}`
    : `<span class="card-hl-label">Model B</span> <b>Too close to call</b>${done ? ` <span class="card-hl-to">&middot; ${done}</span>` : ''}`;
  const disagree = cardDisagreement(g);
  return `<div class="card-hl">${headline}</div>
      <div class="card-viz" role="img" aria-label="${cardAria(g)}">
        <span class="card-end">${pickBadge(bPicksAway, g.graded, g.model_b_correct)}${barTeam(g.away)}</span>
        <div class="card-scale">
          <div class="tele-bar">
            <div class="tele-bar-seg" style="width:${100-g.mktB_home}%; background:${awayC};"></div>
            <div class="tele-bar-seg" style="width:${g.mktB_home}%; background:${homeC};"></div>
          </div>
          <div class="card-line"><span class="card-mid"></span><span class="card-mid-label">50%</span>${mark('a')}${mark('market')}${mark('b')}</div>
        </div>
        <span class="card-end">${pickBadge(bPicksHome, g.graded, g.model_b_correct)}${barTeam(g.home)}</span>
      </div>
      <div class="card-keys">${key('b', b)}${m ? key('market', m) : ''}${key('a', a)}</div>
      ${disagree ? `<div class="card-disagree">${disagree}</div>` : ''}`;
}

function matchupHeader(g, variant){
  return `<div class="matchup-header${variant ? ' ' + variant : ''}">${g.away} <span class="at-symbol">at</span> ${g.home}</div>`;
}

/* The Week Board's logos sit at the two ends of Model B's bar, beside each
   team's abbreviation (Mark, 2026-09-28: he preferred them there to the
   header Stage 17 put them in). 20px, the size the Stage 8 restyle set for
   logos in the core UI. Decorative, alt="", because the abbreviation beside
   each logo is the name, and a screen reader would otherwise read every team
   twice. onerror hides a logo ESPN will not serve and leaves the
   abbreviation: the same fallback as every other logo here, and the reason
   the logos are hot-linked rather than copied into the repository (CLAUDE.md
   Stage 12). On a phone the logo stacks above the abbreviation, so the ends
   are no wider than the abbreviation alone and the probability line keeps
   the width CARD_NEAR was measured on. */
function barTeam(team){
  return `<span class="card-end-team"><img class="card-end-logo" src="${teamLogo(team)}" alt="" loading="lazy" referrerpolicy="no-referrer" onerror="this.style.display='none'">${team}</span>`;
}

/* ---------- Kickoff order ----------
   ISO date + 24-hour zero-padded time compares correctly as a string, which is
   why NO Date is constructed here. Parsing "2026-09-13" + "13:00" into a Date
   attaches the RUNTIME's timezone to a value that is Eastern, so the board
   would reorder itself depending on where the reader is sitting -- and the
   failure is silent, because a misplaced card still looks like a card.
   Verified against the real feed rather than assumed: every gameday is
   YYYY-MM-DD and every gametime_et is HH:MM zero-padded, including the 09:30
   London kickoffs, so lexical order IS chronological order.

   A game with no date sinks rather than sorting first. An unknown kickoff is
   unknown, not midnight. That branch is not hypothetical housekeeping: it is
   what every saved week looked like before these fields existed, and what a
   week looks like again if the schedule stops supplying them.

   At module scope so the suite can execute them -- the comparator they serve
   lives inside renderGames(), which needs a DOM and a week of real data, and
   a sort nobody can run is a sort nobody can check. */
/* ---------- Kickoff, in words ----------
   Built from the string parts, never from a Date, for the same reason
   kickoffKey below is a string compare: the stored time is EASTERN, and a
   Date is interpreted in the reader's zone, so "8:20 PM ET" would quietly
   become 5:20 PM for anyone on the west coast while still reading as a
   correct-looking kickoff. ET is stated in the output because a time whose
   zone is unstated is unfalsifiable by whoever reads it.

   Returns '' rather than a placeholder when there is no date. A week saved
   before these fields existed has none, and an empty string renders nothing
   at all -- which is honest -- where "TBD" would be a claim nobody made. */
const KICKOFF_MONTHS = ['Jan','Feb','Mar','Apr','May','Jun',
                        'Jul','Aug','Sep','Oct','Nov','Dec'];

function kickoffLabel(g){
  if(!g.gameday) return '';
  const parts = g.gameday.split('-');
  const date = `${KICKOFF_MONTHS[Number(parts[1]) - 1]} ${Number(parts[2])}`;
  const day = g.weekday ? `${g.weekday}, ` : '';
  if(!g.gametime_et) return `${day}${date}`;
  const hm = g.gametime_et.split(':');
  const hour24 = Number(hm[0]);
  const suffix = hour24 >= 12 ? 'PM' : 'AM';
  const hour12 = hour24 % 12 === 0 ? 12 : hour24 % 12;
  return `${day}${date} · ${hour12}:${hm[1]} ${suffix} ET`;
}

/* ---------- Where a game stands (Stage 15) ----------
   One line from the weekend refresh's snapshot, or '' for no line at all.
   "final" needs both scores; a snapshot can go stale after grading (Monday
   night's game is still "upcoming" in Monday morning's snapshot when
   Tuesday grades it), so a graded game says nothing here unless the
   snapshot has its final score -- the graded tag already says how the pick
   did, and "score not in yet" beside it would contradict it. */
/* Both scores are in. Compared with null, not by truth: 0 is a real score. */
function gameHasScore(g){
  return g.away_score !== null && g.away_score !== undefined
    && g.home_score !== null && g.home_score !== undefined;
}

/* A neutral site (Stage 37 item 6). The game still has a listed home team
   and both models still give it the home edge, which at Wembley is a
   modelling choice the reader should see, not find in the Methodology page.
   Whether a neutral game should lose the home term is a registration for
   Mark (Stage 38), not something this line decides. */
function cardSiteLine(g){
  if(!g.neutral) return '';
  const where = g.venue ? ` · ${escapeHtml(g.venue)}` : '';
  return `Neutral site${where}. The models still give ${escapeHtml(g.home)} the home edge.`;
}

function cardStatusLine(g){
  const hasScore = gameHasScore(g);
  // Just the score. Until 2026-09-28 an ungraded final also said when the
  // picks would be graded; Mark called that redundant, and the graded tag
  // says it once it happens.
  if(g.status === 'final' && hasScore) return `Final: ${g.away} ${g.away_score}, ${g.home} ${g.home_score}`;
  if(g.status === 'started' && !g.graded) return 'Kicked off · final score not in yet';
  // Mark's call (2026-10-05): the card stays and shows its pick, and the
  // game is graded for nobody and left out of every count.
  if(g.status === 'cancelled') return 'Cancelled · not played, so not graded';
  return '';
}

/* ---------- Where to watch, the quarterbacks, team news (Stage 17) ----------
   Three small facts, each from a file that was checked before it got here:
   the channel from src/sports/nfl/tv_channels.py (one network, only one that passed
   its checks), the quarterbacks from the saved pick itself (so the card
   cannot name a different one from the model's), and the news from
   src/sports/nfl/team_news.py. Each returns '' when it has nothing to say, and nothing
   is drawn -- a blank line or "no news" would be a claim nobody made.

   Once a game is final or graded, "where to watch" and "who is hurt" are
   history, so the channel and the news go; the quarterbacks stay, because
   they are part of the pick. */
/* The one HTML escaper. Until Stage 25 there were three identical
   copies: this one under another name, one for What's Changed and
   one local to renderTeamNews. */
function escapeHtml(s){
  return String(s).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
}

/* Two strings that reached innerHTML as written, until Stage 23 (the
   2026-09-28 audit): what a reader types into the Power Ratings search, and
   the context notes on a card, which come from sourced web reports. Each
   now goes through escapeHtml(), and each is a function of its own so
   tests/test_template_sinks.py can run it in node. */
function ratingsNoMatchRow(q){
  return `<tr><td colspan="7" style="text-align:center; padding:var(--s6); color:var(--text-2);">No teams match "${escapeHtml(q)}"</td></tr>`;
}

function contextNotesHtml(notes){
  return notes.map(n=>`<li style="margin-bottom:var(--s1);">${escapeHtml(n)}</li>`).join('');
}

function cardTvPill(g){
  if(!g.tv || g.graded || g.status === 'final' || g.status === 'cancelled') return '';
  // "regional" on the pill itself (Stage 37 item 2, Mark's observation in
  // the 2026-10-04 audit): nine cards reading "CBS" implied every viewer
  // gets all nine. Which games a viewer gets depends on their market, which
  // nfl.com does not say, so the pill says regional and nothing more.
  const regional = g.tv_regional ? '<span class="tv-regional"> · regional</span>' : '';
  return `<span class="tv-pill"><span class="visually-hidden">On TV: </span>${escapeHtml(g.tv)}${regional}</span>`;
}

/* One header per kickoff slot on the Week Board (Stage 37 item 2): a
   Sunday's 1:00 PM games read as one group under one time instead of the
   same time on every card. Only under the chronological sort -- under any
   other order a slot header would contradict the order the cards are in. */
function slotKey(g){
  return g.gameday ? `${g.gameday} ${g.gametime_et || ''}` : '';
}

function slotHeadBefore(sorted, i){
  if(currentSort !== 'chronological') return '';
  const key = slotKey(sorted[i]);
  if(!key || (i > 0 && slotKey(sorted[i - 1]) === key)) return '';
  const n = sorted.filter(g => slotKey(g) === key).length;
  return `<h3 class="slot-head">${escapeHtml(kickoffLabel(sorted[i]))}`
    + `<span class="slot-count"> · ${n} game${n === 1 ? '' : 's'}</span></h3>`;
}

/* Sunday-afternoon CBS and FOX games are regional: nfl.com says so
   (territory REGIONAL) but not where, so one line on the page says so once,
   rather than every card implying every viewer gets that game. Only when a
   card on screen carries such a channel. */
function boardTvNote(games){
  return games.some(g => cardTvPill(g) !== '' && g.tv_regional);
}

function cardQbLine(g){
  if(!g.away_qb && !g.home_qb) return '';
  const side = (team, name, basis) => !name ? `${team} none on record`
    : `${team} <b>${escapeHtml(name)}</b>`
      + (basis === 'last_game' ? ' (assumed: last game&#39;s starter)' : '');
  return `Quarterbacks: ${side(g.away, g.away_qb, g.away_qb_basis)} · ${side(g.home, g.home_qb, g.home_qb_basis)}`;
}

// One team's news, or null. The pick's own quarterback on the injury report
// comes first, because it is the item that changes how far to trust the pick;
// then a new starter; then other starters out or doubtful, by name up to two
// and as a count beyond that, so the line stays one line. Questionable
// players are left to Team Deep-Dive.
function cardNewsTeam(team, entry){
  if(!entry) return null;
  const published = entry.injury_report === 'published';
  const out = published ? (entry.out || []) : [], doubtful = published ? (entry.doubtful || []) : [];
  const qb = entry.qb && entry.qb.name ? entry.qb : null;
  const bits = [];
  const qbListed = !qb ? null : out.some(p => p.name === qb.name) ? 'out'
    : doubtful.some(p => p.name === qb.name) ? 'doubtful' : null;
  if(qbListed) bits.push(`QB ${qb.name} ${qbListed}`);
  else if(qb && qb.changed_from) bits.push(`new QB`);
  const others = out.map(p => [p.name, 'out']).concat(doubtful.map(p => [p.name, 'doubtful']))
    .filter(([name]) => !qb || name !== qb.name);
  if(others.length > 2) bits.push(`${others.length} starters out or doubtful`);
  else others.forEach(([name, status]) => bits.push(`${name} ${status}`));
  return bits.length ? `${team}: ${bits.join(', ')}` : null;
}

function cardNewsLine(g, news){
  if(!news || !news.teams || g.graded || g.status === 'final' || g.status === 'cancelled') return '';
  const parts = [g.away, g.home].map(t => cardNewsTeam(t, news.teams[t])).filter(Boolean);
  return parts.length ? `<b>Team news</b> ${parts.map(escapeHtml).join(' · ')}` : '';
}

function kickoffKey(g){
  return g.gameday ? `${g.gameday}T${g.gametime_et || '00:00'}` : null;
}

function byConfidence(a, b){
  return (a.confidence_rank ?? 999) - (b.confidence_rank ?? 999);
}

function byKickoff(a, b){
  const ka = kickoffKey(a), kb = kickoffKey(b);
  if(ka === null && kb === null) return byConfidence(a, b);
  if(ka === null) return 1;
  if(kb === null) return -1;
  if(ka !== kb) return ka < kb ? -1 : 1;
  // Thirteen of week 1's sixteen games kick off at the same minute, so without
  // a tiebreak this sort would leave most of the board in file order and look
  // like it had done nothing.
  return byConfidence(a, b);
}

function renderGames(){
  const grid = document.getElementById('game-grid');
  const badge = document.getElementById('board-badge');
  const weekData = weeks[currentBoardWeek];
  const gamesList = weekData ? weekData.games : [];
  // The badge now speaks only when there is nothing to count. "16 games" above
  // sixteen visible cards told the reader what they could already see; "No
  // games" is the one state the grid cannot say for itself.
  badge.textContent = gamesList.length ? '' : 'No games';
  badge.hidden = gamesList.length > 0;
  renderWeekGlance(gamesList);
  renderLockProof(currentBoardWeek, weekData);
  const tvNote = document.getElementById('board-tv-note');
  if(tvNote) tvNote.hidden = true;
  // Tuesday's picks for a week Thursday has not locked yet. Said above the
  // cards, not only in the week label, because it changes how every number
  // below it reads: these can move, and none of them is ever graded.
  const previewNote = document.getElementById('board-preview-note');
  if(previewNote){
    const isPreview = !!(weekData && weekData.preview);
    previewNote.hidden = !isPreview;
    previewNote.textContent = previewNoteText(weekData, Date.now());
  }

  const pdfLink = document.getElementById('picks-pdf-link');
  if(pdfLink){
    const hasPdf = picksPdfs.indexOf(currentBoardWeek) !== -1;
    pdfLink.hidden = !hasPdf;
    if(hasPdf){
      pdfLink.href = 'dist/picks_' + currentBoardWeek + '.pdf';
      pdfLink.setAttribute('aria-label', 'Download printable PDF of picks for ' + currentBoardWeek.replace('_week', ' week '));
    }
  }

  if(!weekData || gamesList.length === 0){
    grid.innerHTML = stateHtml('waiting', 'No picks for this week yet',
      'The model saves its picks for a week before that week&#39;s first kickoff. They appear here as soon as they are saved.');
    return;
  }

  const filtered = gamesList.filter(g=>{
    if(currentFilter==='all') return true;
    if(currentFilter==='flagged') return !!g.flag;
    // The badge's own test, so the filter shows exactly the cards that say
    // "Models split" (see modelsSplit).
    if(currentFilter==='divergent') return modelsSplit(g);
    return true;
  });

  if(filtered.length === 0){
    grid.innerHTML = stateHtml('filtered', 'No games match this filter',
      'Every game this week is still here; this filter just hides all of them.',
      {label: 'Show all games', onclick: "document.querySelector('#filter-row [data-filter=all]').click()"});
    return;
  }

  const sorted = [...filtered].sort((a,b)=>{
    if(currentSort === 'chronological') return byKickoff(a,b);
    if(currentSort === 'confidence'){
      // lower confidence_rank = more confident; nulls (ungraded/old-format) sink to the bottom
      const ra = a.confidence_rank ?? 999, rb = b.confidence_rank ?? 999;
      return ra - rb;
    }
    if(currentSort === 'confidence_asc'){
      const ra = a.confidence_rank ?? -1, rb = b.confidence_rank ?? -1;
      return rb - ra;  // highest rank number = least confident = closest game, shown first
    }
    if(currentSort === 'disagreement'){
      const da = Math.abs(a.fbA_home - a.mktB_home), db = Math.abs(b.fbA_home - b.mktB_home);
      return db - da;
    }
    if(currentSort === 'spread'){
      const sa = a.spread === null || a.spread === undefined ? -1 : Math.abs(a.spread);
      const sb = b.spread === null || b.spread === undefined ? -1 : Math.abs(b.spread);
      return sb - sa;
    }
    if(currentSort === 'alpha'){
      return a.home.localeCompare(b.home);
    }
    return 0;
  });

  if(tvNote) tvNote.hidden = !boardTvNote(sorted);
  const news = weekData.news;

  const cards = sorted.map(g=>{
    // Within EVEN_BAND points of 50 the model has not picked anybody, and
    // bolding one side of a 50.4/49.6 split states a confidence it does not have.
    const EVEN_BAND = 2;
    const leanOf = p => Math.abs(p - 50) < EVEN_BAND ? 'even' : (p >= 50 ? 'home' : 'away');
    const aLean = leanOf(g.fbA_home), bLean = leanOf(g.mktB_home);
    // A game neither model will call. Distinct from "models agree", which on a
    // 50/50 game would claim consensus where there is only shared uncertainty.
    const tossUp = aLean === 'even' && bLean === 'even';
    const aHomeWin = aLean === 'home', aAwayWin = aLean === 'away';
    const bHomeWin = bLean === 'home', bAwayWin = bLean === 'away';
    const idSafe = (g.home+g.away).replace(/[^a-zA-Z]/g,'');
    const [awayC, homeC] = matchupColors(g.away, g.home);
    const spreadText = (g.spread===null || g.spread===undefined) ? "No line available"
      : g.spread === 0 ? "PK"
      : (g.spread>0 ? `${g.home} -${g.spread}` : `${g.away} -${Math.abs(g.spread)}`);
    const gradedTag = gradedTagHtml(g);
    // RETIRED in Stage 11: an "Illustrative margin" row ("KC by ~10.1")
    // used to sit in the panel below, a point margin back-solved from the
    // win probability. Margin modelling was tested as a predictor and
    // REJECTED (Model Lab), so the page was showing a number of the kind the
    // project had decided not to trust, and at card size its "~" read as a
    // minus. The Vegas line above is the real point margin on the card.
    // tests/test_no_illustrative_margin.py keeps it from coming back.

    // The sentence sits on the card, not behind the toggle. A reason nobody
    // expands is a reason nobody reads, and "why is this team favoured" was
    // the whole point of the item -- the numbers stay behind the toggle for
    // anyone who wants to check the sentence against them.
    const whyHtml = g.why ? `
      ${whyLabelled(g)}
      ${whyMarketSentence(g)}
      <button class="btn btn-link why-toggle" data-why="${idSafe}" aria-expanded="false" aria-controls="why-${idSafe}">+ the numbers behind this</button>
      <div class="why-panel" id="why-${idSafe}">
        ${whyRow('Offense edge', g.why.off_matchup)}
        ${whyRow('Defense edge', g.why.def_matchup)}
        ${whyRow('QB edge', g.why.qb_matchup)}
        ${(g.why.ol_continuity !== undefined) ? whyRow('O-line continuity', g.why.ol_continuity) : ''}
        ${trackRecordHtml(g.mktB_home, 'panel')}
      </div>` : '';
    const kickoff = kickoffLabel(g);
    const tvPill = cardTvPill(g);
    const statusLine = cardStatusLine(g);
    const siteLine = cardSiteLine(g);
    const qbLine = cardQbLine(g), newsLine = cardNewsLine(g, news);
    return `<div class="game-card ${g.flag?'has-flag':''}">
      ${matchupHeader(g)}
      ${kickoff || tvPill ? `<div class="card-kickoff">${kickoff}${tvPill}</div>` : ''}
      ${statusLine ? `<div class="card-status">${statusLine}</div>` : ''}
      ${siteLine ? `<div class="card-site">${siteLine}</div>` : ''}
      <div class="game-top">
        <div class="tag-row" style="display:flex; gap:var(--s2); align-items:center;">
          ${gradedTag}
          ${/* The badge says WHETHER the models disagree, not by how much. It
                read `gap 59pt` -- a number nobody has a scale for, and the
                A-vs-market gap the owner named as unnecessary on the card
                twice. Three states, matching the component study: a near-even
                call is worth flagging on its own, because "the models agree"
                on a 50/50 game means they agree they do not know. */''}
          <span class="conf-tag ${tossUp ? 'tag-neutral' : ''}">${
            tossUp ? 'Toss-up' : (modelsSplit(g) ? 'Models split' : 'Models agree')}</span>
        </div>
      </div>
      ${cardProbHtml(g, awayC, homeC)}
      <div class="market-ref">Vegas line: <b>${spreadText}</b></div>
      ${qbLine ? `<div class="card-qbs">${qbLine}</div>` : ''}
      ${newsLine ? `<div class="card-news">${newsLine}</div>` : ''}
      ${trackRecordHtml(g.mktB_home, 'card')}
      ${whyHtml}
      ${(g.notes && g.notes.length) ? `<button class="btn btn-link toggle-flag" data-idx="${idSafe}" aria-expanded="false" aria-controls="flag-${idSafe}">+ view context (${g.notes.length})</button>
      <div class="flag-note" id="flag-${idSafe}">
        <b>Context:</b>
        <ul style="margin:var(--s2) 0 0 var(--s5); padding:0;">
          ${contextNotesHtml(g.notes)}
        </ul>
      </div>` : ''}
    </div>`;
  });
  grid.innerHTML = cards.map((card, i) => slotHeadBefore(sorted, i) + card).join('');

  document.querySelectorAll('.toggle-flag').forEach(btn=>{
    const originalLabel = btn.textContent;
    btn.addEventListener('click', ()=>{
      const note = document.getElementById('flag-'+btn.dataset.idx);
      // aria-expanded follows the panel, as .dive-game-head's does (Stage 26):
      // the + / − in the label is not announced as a state.
      btn.setAttribute('aria-expanded', note.classList.toggle('open') ? 'true' : 'false');
      btn.textContent = note.classList.contains('open')
        ? originalLabel.replace('+ view', '− hide')
        : originalLabel;
    });
  });
  document.querySelectorAll('.why-toggle').forEach(btn=>{
    btn.addEventListener('click', ()=>{
      const panel = document.getElementById('why-'+btn.dataset.why);
      btn.setAttribute('aria-expanded', panel.classList.toggle('open') ? 'true' : 'false');
      btn.textContent = panel.classList.contains('open') ? '− hide the numbers' : '+ the numbers behind this';
    });
  });
}
/* SCOPED TO #filter-row, deliberately. `.filter-btn` is a shared pill style,
   not a Week Board filter: nine elements wear it and only three are filters.
   The other six are "Got it" on the onboarding banner and, on My Picks, "Copy
   these into my log", "Back to my picks", "Copy Share Link", "Export My Picks"
   and "Import My Picks". An unscoped querySelectorAll gave all nine this
   handler, so tapping Export My Picks stripped .active from All Games, painted
   Export in the accent, and set currentFilter to undefined -- which falls
   through the filter's final `return true`, so the board still showed every
   game with no pill marked and nothing errored. Measured in headless Chromium
   before the fix: .active went from ["All Games"] to ["Export My Picks"].
   Select the buttons that have the attribute this handler reads. */
document.querySelectorAll('#filter-row .filter-btn[data-filter]').forEach(btn=>{
  btn.addEventListener('click', ()=>{
    // .active is the look; aria-pressed is the state a screen reader hears
    // (Stage 26: every chip on the page says which one is on the same way).
    document.querySelectorAll('#filter-row .filter-btn[data-filter]').forEach(b=>{
      b.classList.toggle('active', b === btn);
      b.setAttribute('aria-pressed', b === btn ? 'true' : 'false');
    });
    currentFilter = btn.dataset.filter;
    renderGames();
  });
});
populateWeekSelect(document.getElementById('week-select'), (val)=>{
  currentBoardWeek = val;
  // The football tumbles while the week swaps. The work is synchronous, so
  // stop() is called immediately -- it waits for the current revolution to
  // finish, which is what makes a fast swap read as one deliberate turn rather
  // than a flicker. A slow machine gets more turns, not a stutter.
  brandMark.start();
  renderGames();
  syncWeekStepper('week');
  brandMark.stop();
}, latestWeekKey);
wireWeekStepper('week');
document.getElementById('sort-select').addEventListener('change', (e)=>{ currentSort = e.target.value; renderGames(); });
/* After the change listener, not before. enhanceSelect() writes back through
   dispatchEvent('change'), so wiring it first would build a control whose
   clicks reached nothing -- the written-tested-never-called shape, in the one
   ordering where it still looks correct on screen. */
enhanceSelect(document.getElementById('sort-select'));
renderGames();

/* ---------- Onboarding banner (first-visit only) ---------- */
const ONBOARDING_KEY = 'nfl_pickem_onboarding_dismissed';

/* ---------- Theme toggle ---------- */
const THEME_KEY = 'nfl_pickem_theme';
function currentTheme(){
  return document.documentElement.getAttribute('data-theme') === 'light' ? 'light' : 'dark';
}
function updateThemeLabel(){
  const label = document.getElementById('theme-toggle-label');
  if(label) label.textContent = currentTheme() === 'light' ? 'Dark mode' : 'Light mode';
}
/* Stage 47 item 11: paper is white, so a page in the dark theme prints in
   the light one, and goes back to the reader's theme afterwards. */
(function printInLight(){
  let before = null;
  window.addEventListener('beforeprint', () => {
    before = document.documentElement.getAttribute('data-theme');
    document.documentElement.setAttribute('data-theme', 'light');
  });
  window.addEventListener('afterprint', () => {
    if(before === null) document.documentElement.removeAttribute('data-theme');
    else document.documentElement.setAttribute('data-theme', before);
  });
})();
(function initTheme(){
  updateThemeLabel();
  // The sidebar's button, and the top bar's below 1080px (Stage 26 item 3).
  document.querySelectorAll('#theme-toggle, .topbar-theme').forEach(btn => btn.addEventListener('click', ()=>{
    const next = currentTheme() === 'light' ? 'dark' : 'light';
    if(next === 'light'){
      document.documentElement.setAttribute('data-theme','light');
    } else {
      document.documentElement.removeAttribute('data-theme');
    }
    try{ localStorage.setItem(THEME_KEY, next); }catch(e){}
    updateThemeLabel();
  }));
})();
// The top bar's height, for the sticky table headers that stick below it
// under 1080px (Stage 30 item 2). Measured, not assumed: the bar grows with
// the safe area and when its title wraps. 0 when the bar is not shown.
// offsetHeight is the BORDER box, so the observer watches the border box:
// the default content box does not fire when only the padding changes, and
// the safe area reaches the bar as padding (--safe-top). Stage 35.
(function initTopbarHeight(){
  const bar = document.querySelector('.topbar');
  if(!bar) return;
  const write = () => document.documentElement.style.setProperty('--topbar-h', bar.offsetHeight + 'px');
  write();
  if(typeof ResizeObserver === 'function') new ResizeObserver(write).observe(bar, {box: 'border-box'});
  window.addEventListener('resize', write);
})();
function dismissOnboarding(){
  try{ localStorage.setItem(ONBOARDING_KEY, '1'); }catch(e){}
  const el = document.getElementById('onboarding-banner');
  if(el) el.style.display = 'none';
}
(function initOnboarding(){
  let dismissed = false;
  try{ dismissed = localStorage.getItem(ONBOARDING_KEY) === '1'; }catch(e){}
  const el = document.getElementById('onboarding-banner');
  if(el && !dismissed) el.style.display = 'block';
})();

/* Where the orientation banner sits (Stage 13). On a phone it goes in among
   the cards, after the first ORIENTATION_AFTER of them, so the first screen
   shows games rather than instructions (before this, at 390x844 the banner
   was 610px tall and the first card started at 914px, below the fold).
   Wider than that it stays in its markup home, above the week summary, where
   the cards beside it are already on screen.

   renderGames() rewrites #game-grid with innerHTML, which would drop the
   banner if it were inside, so the node is held here, not looked up, and
   every rewrite of the grid re-places it. The observer only moves it when
   it is somewhere else, so its own move cannot set it off again. */
const ORIENTATION_AFTER = 2;
const ORIENTATION_PHONE = '(max-width:640px)';
function orientationSlot(cardCount, isPhone){
  return isPhone && cardCount >= ORIENTATION_AFTER ? ORIENTATION_AFTER : null;
}
(function placeOrientationWiring(){
  const banner = document.getElementById('onboarding-banner');
  const grid = document.getElementById('game-grid');
  const home = document.getElementById('week-glance');
  if(!banner || !grid || !home || !window.matchMedia) return;
  const phone = window.matchMedia(ORIENTATION_PHONE);
  function placeOrientation(){
    const cards = [...grid.children].filter(c => c.classList.contains('game-card'));
    const slot = orientationSlot(cards.length, phone.matches);
    if(slot === null){
      if(banner.nextElementSibling !== home) home.parentNode.insertBefore(banner, home);
      return;
    }
    const after = cards[slot - 1];
    if(after.nextElementSibling !== banner) after.after(banner);
  }
  new MutationObserver(placeOrientation).observe(grid, {childList:true});
  if(phone.addEventListener) phone.addEventListener('change', placeOrientation);
  placeOrientation();
})();

/* ---------- Picks lock at kickoff (Stage 11) ----------
   Before this, a pick could be made after the result was known and the
   Season Accuracy race counted it: writing every graded winner into storage
   put "My picks 100.0%, 32 of 32" on the page (measured 2026-09-26). On a
   dashboard whose whole claim is that its numbers are true, that was the one
   number a visitor could make false by clicking.

   Three rules, all here as plain functions so the suite can execute them:
     1. A game's buttons lock at its kickoff, or once it is graded.
     2. Every pick is stored with the time it was made (PICK_TIMES_KEY).
     3. A graded pick is COUNTED only if its time is before kickoff. A pick
        with no time -- everything saved before this existed, and anything
        arriving through a share link, which carries no times -- is kept and
        shown, but not counted, and the page says how many it left out.

   This is honesty on a static site, not security: the times live in the
   visitor's own browser and a determined person can edit them. What it
   removes is the accidental and the casual case, and the page no longer
   counts a pick it knows was made late.

   The kickoff is an INSTANT here, unlike kickoffKey above, because it is
   compared with the visitor's clock. It is built with Date.UTC from the
   Eastern wall-clock fields plus the US daylight-saving rule, never with
   `new Date("2026-09-13T13:00")`, which would read an Eastern time in the
   visitor's zone and lock a Los Angeles visitor three hours late. */
function easternOffsetHours(y, m, d, hh){
  // US rule since 2007: daylight time (UTC-4) from 02:00 on the second
  // Sunday of March to 02:00 on the first Sunday of November, else UTC-5.
  const firstSunday = mon => 1 + (7 - new Date(Date.UTC(y, mon - 1, 1)).getUTCDay()) % 7;
  const key = m * 10000 + d * 100 + hh;
  const start = 3 * 10000 + (firstSunday(3) + 7) * 100 + 2;
  const end = 11 * 10000 + firstSunday(11) * 100 + 2;
  return (key >= start && key < end) ? 4 : 5;
}

function kickoffInstant(g){
  // null means "kickoff unknown", which never locks on time alone. A day
  // with no time locks from the start of that day: early rather than late.
  if(!g || !g.gameday) return null;
  const p = g.gameday.split('-').map(Number);
  const t = (g.gametime_et || '00:00').split(':').map(Number);
  if(p.length !== 3 || p.some(isNaN) || t.some(isNaN)) return null;
  const off = easternOffsetHours(p[0], p[1], p[2], t[0]);
  return Date.UTC(p[0], p[1] - 1, p[2], t[0] + off, t[1] || 0);
}

function isPickLocked(g, nowMs){
  if(g && g.graded) return true;
  const k = kickoffInstant(g);
  return k !== null && nowMs >= k;
}

// 'counted', 'late' (made at or after kickoff) or 'untimed' (no time, or a
// game whose kickoff is unknown, so the time cannot be checked against it).
function pickVerdict(pickedAt, g){
  const t = pickedAt ? Date.parse(pickedAt) : NaN;
  const k = kickoffInstant(g);
  if(isNaN(t) || k === null) return 'untimed';
  return t < k ? 'counted' : 'late';
}

// The one tally behind every record on the page: the My Picks badge, the
// streak strip, the trend line and the scoreboard race. Four hand-written
// loops did this before, which is four places to forget the lock.
function tallyMyPicks(picks, times, keys, weekMap){
  const r = {wins: 0, losses: 0, late: 0, untimed: 0};
  keys.forEach(k => {
    ((weekMap[k] && weekMap[k].games) || []).forEach(g => {
      const pid = k + '|' + g.home + '|' + g.away;
      const pick = picks[pid];
      if(!pick || !g.graded || g.actual_home_win === null || g.actual_home_win === undefined) return;
      const v = pickVerdict(times[pid], g);
      if(v !== 'counted'){ r[v]++; return; }
      if(pick === (g.actual_home_win ? g.home : g.away)) r.wins++; else r.losses++;
    });
  });
  return r;
}

// Picks are kept in this browser only (a static site has no accounts), so a
// visitor on a new device sees none, and picks copied in from a share link
// carry no time. Said wherever the page reports picks it cannot count.
const PICKS_LIVE_HERE = 'Your picks live in this browser: Export and Import on My Picks move them to another device.';

function leftOutSentence(t){
  const n = t.late + t.untimed;
  if(!n) return '';
  const parts = [];
  if(t.late) parts.push(`${t.late} made after kickoff`);
  if(t.untimed) parts.push(`${t.untimed} with no record of when ${t.untimed === 1 ? 'it was' : 'they were'} made`);
  return `${n} of your graded picks ${n === 1 ? 'is' : 'are'} not counted: ${parts.join(', ')}.`;
}

// The My Picks record badge. Graded picks that were all late or untimed
// say "0 counted" and why, not "No graded picks yet" -- they are graded,
// and the visitor can see them (Stage 37 item 1).
function recordBadgeText(t){
  const left = t.late + t.untimed;
  if(t.wins + t.losses > 0) return `${t.wins}-${t.losses} on graded picks` + (left ? ` (${left} not counted)` : '');
  if(left) return `0 counted: ${left} graded pick${left === 1 ? '' : 's'} made after kickoff or with no time`;
  return 'No graded picks yet';
}

// A stored time means "made no later than this". A pick with no time whose
// game has NOT kicked off can be stamped with now truthfully: it is sitting
// in storage now, so it was made by now, and now is before kickoff. That is
// what keeps a pick saved before this change, or copied in from a share link
// for a game still to come, from being thrown out. A game already locked is
// never stamped -- there, now proves nothing about before kickoff.
function stampUnlockedPicks(picks, times, gameOf, nowMs){
  let stamped = 0;
  Object.keys(picks).forEach(pid => {
    if(times[pid]) return;
    const g = gameOf(pid);
    if(!g || kickoffInstant(g) === null || isPickLocked(g, nowMs)) return;
    times[pid] = new Date(nowMs).toISOString();
    stamped++;
  });
  return stamped;
}
/* ---------- end of the picks lock ---------- */

/* ---------- My Picks Log (localStorage, this device only) ---------- */
let currentPicksWeek = latestWeekKey;
const PICKS_STORAGE_KEY = 'nfl_pickem_my_picks';
const PICK_TIMES_KEY = 'nfl_pickem_pick_times';

function loadPickTimes(){
  try{ return JSON.parse(localStorage.getItem(PICK_TIMES_KEY) || '{}'); }
  catch(e){ return {}; }
}
function savePickTimes(times){
  try{ localStorage.setItem(PICK_TIMES_KEY, JSON.stringify(times)); }
  catch(e){ console.warn('Could not save pick times locally', e); }
}

// Find the game a pick id names, so a handler can ask whether it is locked.
function gameForPid(pid){
  const [k, home, away] = pid.split('|');
  return ((weeks[k] && weeks[k].games) || []).find(g => g.home === home && g.away === away) || null;
}

function loadMyPicks(){
  try{ return JSON.parse(localStorage.getItem(PICKS_STORAGE_KEY) || '{}'); }
  catch(e){ return {}; }
}
function saveMyPicks(picks){
  try{ localStorage.setItem(PICKS_STORAGE_KEY, JSON.stringify(picks)); }
  catch(e){ console.warn('Could not save picks locally', e); }
}

/* ---------- Shareable picks link ----------
   A static site with no backend, so the picks have to travel inside the URL
   itself. Three decisions worth stating:

   1. One week per link, not the whole log. A week is ~16 games; a season is
      272, and a URL carrying all of them would be long enough that mail
      clients and chat apps start wrapping and truncating it. Truncation on a
      link is the bad case, because a half-decoded pick set still looks like a
      pick set.

   2. The fragment (#), never the query string. Fragments are not sent to the
      server, so someone's picks do not end up in GitHub Pages' request logs
      just because they shared them.

   3. One character per game, positional -- which is compact but only correct
      if both ends agree on the game order. So the link carries a fingerprint
      of the exact schedule the sender saw. If the receiver's copy of that
      week differs at all, the link is REFUSED rather than decoded against the
      wrong games. Silently attaching someone's picks to the wrong fixtures is
      worse than not opening the link. */
const SHARE_VERSION = '1';

// FNV-1a. Not a security hash -- it exists to notice that two schedules
// differ, and it only has to survive being pasted through a chat window.
function scheduleFingerprint(games){
  const s = games.map(g => g.away + '@' + g.home).join(',');
  let h = 0x811c9dc5;
  for(let i = 0; i < s.length; i++){
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 0x01000193) >>> 0;
  }
  return h.toString(36);
}

function encodeSharedPicks(weekKey){
  const weekData = weeks[weekKey];
  if(!weekData || !(weekData.games||[]).length) return null;
  const myPicks = loadMyPicks();
  const games = weekData.games;

  // h = home, a = away, - = no pick. Fixed length, one char per game, in the
  // week's own order.
  let bits = '', picked = 0;
  games.forEach(g => {
    const pick = myPicks[weekKey + '|' + g.home + '|' + g.away];
    if(pick === g.home){ bits += 'h'; picked++; }
    else if(pick === g.away){ bits += 'a'; picked++; }
    else bits += '-';
  });
  if(picked === 0) return null;
  return { token: [SHARE_VERSION, weekKey, bits, scheduleFingerprint(games)].join('~'),
           picked };
}

function decodeSharedPicks(token){
  const parts = String(token).split('~');
  if(parts.length !== 4) return {error: 'That link is not in a format this page recognises.'};
  const [version, weekKey, bits, fingerprint] = parts;

  if(version !== SHARE_VERSION){
    return {error: `That link was made by a different version of this page (v${version}).`};
  }
  const weekData = weeks[weekKey];
  if(!weekData || !(weekData.games||[]).length){
    return {error: `This site has no data for ${weekKey.replace('_',' ')}, so those picks cannot be shown.`};
  }
  const games = weekData.games;
  if(bits.length !== games.length){
    return {error: `That link covers ${bits.length} games but this site has ${games.length} for that week, so the picks cannot be lined up. Nothing was imported.`};
  }
  if(fingerprint !== scheduleFingerprint(games)){
    // The dangerous case, and the reason the fingerprint exists at all.
    return {error: 'That link was made from a different version of this week\'s schedule. Lining the picks up by position would attach them to the wrong games, so nothing was imported.'};
  }

  const picks = {};
  let picked = 0;
  games.forEach((g, i) => {
    const c = bits[i];
    if(c === 'h'){ picks[weekKey + '|' + g.home + '|' + g.away] = g.home; picked++; }
    else if(c === 'a'){ picks[weekKey + '|' + g.home + '|' + g.away] = g.away; picked++; }
    else if(c !== '-'){ /* tolerated: unknown char reads as no pick */ }
  });
  return {weekKey, picks, picked};
}

function copyShareLink(btn){
  const encoded = encodeSharedPicks(currentPicksWeek);
  const label = btn ? btn.textContent : '';
  const flash = (msg) => {
    if(!btn) return;
    btn.textContent = msg;
    setTimeout(()=>{ btn.textContent = label; }, 2600);
  };
  if(!encoded){
    flash('No picks this week');
    return;
  }
  const url = location.origin + location.pathname + '#picks=' + encoded.token;

  // Clipboard access needs a secure context; opened from a file:// path it
  // will not be there. Falling back to a prompt keeps the link reachable
  // rather than failing with nothing on screen.
  const fallback = () => {
    window.prompt('Copy this link to share your picks:', url);
    flash('Link ready');
  };
  if(navigator.clipboard && navigator.clipboard.writeText){
    navigator.clipboard.writeText(url)
      .then(()=> flash(`Copied (${encoded.picked} picks)`))
      .catch(fallback);
  } else {
    fallback();
  }
}

// Non-null only while a shared link is open. renderPicksGrid reads it, which
// is what keeps the shared view from touching localStorage at all.
let sharedPicksView = null;

function showSharedPicks(decoded){
  sharedPicksView = decoded;
  currentPicksWeek = decoded.weekKey;
  const sel = document.getElementById('picks-week-select');
  if(sel) sel.value = decoded.weekKey;
  // Deliberately NOT a change event: that handler ends the shared view, so
  // dispatching one here would close the thing it is opening. The select is
  // moved directly and the stepper is told about it, which is the one case
  // where the "let the select emit and everyone listens" rule cannot apply.
  // Without this the arrows and their label keep showing the previous week
  // while the grid shows the shared one -- two controls disagreeing about the
  // same state, which is the exact failure a shared stepper exists to prevent.
  syncWeekStepper('picks-week');

  const banner = document.getElementById('shared-picks-banner');
  const note = document.getElementById('shared-picks-note');
  if(note){
    const mine = Object.keys(loadMyPicks()).length;
    note.textContent = `${decoded.picked} pick${decoded.picked===1?'':'s'} for `
      + `${decoded.weekKey.replace('_',' ')}, shared from someone else's device. `
      + `Nothing has been saved to this device. `
      + (mine ? 'Your own picks are untouched and will come back when you leave this view.'
              : 'You have no picks of your own logged yet.');
  }
  if(banner) banner.style.display = 'block';
  // Dismiss any pending undo. It refers to a pick made on THIS device a
  // moment ago, and leaving it up means shared view is showing a "Pick saved
  // -- Undo" button that still writes to local storage, which is exactly the
  // guarantee this view is supposed to make. Seen in a screenshot of the
  // receive path; nothing in the logic would have surfaced it.
  const toast = document.getElementById('undo-toast');
  if(toast) toast.classList.remove('visible');
  lastPickChange = null;

  setActivePage('picks');
  renderPicksGrid();
}

function exitSharedPicks(){
  sharedPicksView = null;
  const banner = document.getElementById('shared-picks-banner');
  if(banner) banner.style.display = 'none';
  if(location.hash.indexOf('picks=') !== -1){
    history.replaceState(null, '', location.pathname + location.search);
  }
  renderPicksGrid();
}

function importSharedPicks(){
  if(!sharedPicksView) return;
  const incoming = sharedPicksView.picks;
  const existing = loadMyPicks();
  const clashes = Object.keys(incoming).filter(k => existing[k] && existing[k] !== incoming[k]);

  // Asked, not assumed. These picks belong to someone else, and overwriting
  // a real logged pick would corrupt the record the Season Accuracy page is
  // scored from.
  let overwrite = false;
  if(clashes.length){
    overwrite = window.confirm(
      `${clashes.length} of these games already have a different pick logged on this device.\n\n`
      + `OK = replace yours with the shared pick.\n`
      + `Cancel = keep your own and only fill in the games you have not picked.`);
  }
  const merged = overwrite ? {...existing, ...incoming} : {...incoming, ...existing};
  // A link carries no pick times. Wherever a pick CHANGED, the old time
  // belongs to the old pick and goes with it; games still to come are
  // re-stamped on the next render, locked ones stay uncounted.
  const times = loadPickTimes();
  Object.keys(merged).forEach(k => { if(existing[k] !== merged[k]) delete times[k]; });
  saveMyPicks(merged);
  savePickTimes(times);
  exitSharedPicks();
  alert('Shared picks copied into your log.');
}

function readSharedPicksFromUrl(){
  const m = /[#&]picks=([^&]+)/.exec(location.hash || '');
  if(!m) return;
  const decoded = decodeSharedPicks(decodeURIComponent(m[1]));
  if(decoded.error){
    // Say what went wrong and drop the bad fragment, rather than leaving a
    // link that fails again on every refresh.
    alert(decoded.error);
    history.replaceState(null, '', location.pathname + location.search);
    return;
  }
  showSharedPicks(decoded);
}

function exportMyPicks(){
  const picks = loadMyPicks();
  const payload = { exported: new Date().toISOString(), picks, pick_times: loadPickTimes() };
  const blob = new Blob([JSON.stringify(payload, null, 2)], {type: 'application/json'});
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = 'my_picks_export.json';
  document.body.appendChild(a); a.click(); document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

function importMyPicks(file){
  const reader = new FileReader();
  reader.onload = (e) => {
    try{
      const payload = JSON.parse(e.target.result);
      const incoming = payload.picks || payload; // tolerate a bare picks object too
      if(typeof incoming !== 'object' || incoming === null) throw new Error('not an object');
      const existing = loadMyPicks();
      // Merge rather than overwrite -- imported picks fill in gaps, but don't
      // silently clobber picks already made on this device for the same game.
      const merged = {...incoming, ...existing};
      // Times travel with the picks they belong to: an imported pick keeps
      // the time in the file (older exports have none), a kept pick keeps
      // its own. A pick is never paired with another pick's time.
      const times = loadPickTimes();
      const incomingTimes = (payload && typeof payload.pick_times === 'object' && payload.pick_times) || {};
      Object.keys(merged).forEach(k => {
        if(existing[k] !== undefined) return;
        if(incomingTimes[k]) times[k] = incomingTimes[k]; else delete times[k];
      });
      saveMyPicks(merged);
      savePickTimes(times);
      alert(`Imported ${Object.keys(incoming).length} picks (existing picks on this device were kept where they overlap).`);
      renderPicksGrid();
    } catch(err){
      alert('Could not read that file -- make sure it\'s a picks export from this same site.');
    }
  };
  reader.readAsText(file);
}

/* ---------- One card, one pick ----------
   The single implementation of "what a card looks like given a pick". It is
   called for every card by renderPicksGrid, and for exactly one card by the
   tap handler and by Undo -- so the full render and the surgical update
   cannot drift, which is the .game-card failure this repo has already paid
   for once: two render paths, one edit, a diff that looked complete.

   Everything else on a picks card -- the matchup, the kickoff -- is
   independent of the pick and is never redrawn. */
function paintPickCard(group, pick){
  if(!group) return;
  const modelBPick = group.dataset.modelB;
  // The lock is re-read from the clock on every paint, so a page left open
  // across a kickoff locks the card the next time anything touches it.
  const game = gameForPid(group.dataset.pid);
  const locked = !sharedPicksView && isPickLocked(game, Date.now());
  group.querySelectorAll('.pick-btn').forEach(btn=>{
    btn.classList.toggle('selected', btn.dataset.team === pick);
    // The button is a control with a persistent on/off state, so it says so
    // rather than relying on a colour a screen reader cannot see.
    btn.setAttribute('aria-pressed', btn.dataset.team === pick ? 'true' : 'false');
    btn.disabled = locked;
    if(locked) btn.setAttribute('aria-label', `${btn.dataset.team}, locked at kickoff`);
    else btn.removeAttribute('aria-label');
  });
  const agrees = group.parentElement && group.parentElement.querySelector('.pick-agrees');
  if(agrees) agrees.textContent = pickAgreesText(pick, modelBPick);
  const status = group.parentElement && group.parentElement.querySelector('.pick-lock');
  if(status) status.innerHTML = locked ? pickLockHtml(pick, pickVerdict(loadPickTimes()[group.dataset.pid], game)) : '';
}

/* What a locked card says under its buttons. Only a pick that will NOT be
   counted gets more than the lock itself, and it says why in plain words. */
const LOCK_ICON = '<svg class="lock-icon" viewBox="0 0 16 16" width="12" height="12" aria-hidden="true" focusable="false"><path d="M4.5 7V5a3.5 3.5 0 0 1 7 0v2" fill="none" stroke="currentColor" stroke-width="1.6"/><rect x="3" y="7" width="10" height="7" rx="1.5" fill="currentColor"/></svg>';
function pickLockHtml(pick, verdict){
  let why = '';
  if(pick && verdict === 'late') why = ' This pick was made after kickoff, so it is not counted.';
  else if(pick && verdict === 'untimed') why = ' There is no record of when this pick was made, so it is not counted.';
  return `${LOCK_ICON}<span>Locked at kickoff.${why}</span>`;
}

/* Whose picks are being described changes the pronoun, and that is the only
   thing sharedPicksView changes here. Extracted so the sentence exists once. */
function pickAgreesText(pick, modelBPick){
  if(!pick) return `Model B picks: ${modelBPick}`;
  const agree = pick === modelBPick;
  const suffix = sharedPicksView
    ? (agree ? ' (they agree)' : ' (they differ)')
    : (agree ? ' (you agree)' : ' (you differ)');
  return `Model B picks: ${modelBPick}${suffix}`;
}

/* The record badge and the streak strip are the only things outside a card
   that a single pick can change. They sit above the grid, not under the
   finger, so redrawing them costs nothing the user can feel. */
function refreshPickTotals(myPicks){
  const badge = document.getElementById('picks-record-badge');
  // A share link carries no pick times, so a shared week is never scored:
  // anyone can build a link after the results are in.
  const times = sharedPicksView ? {} : loadPickTimes();
  const t = tallyMyPicks(myPicks, times, weekKeysSorted, weeks);
  if(badge) badge.textContent = sharedPicksView
    ? 'Shared picks are not scored'
    : recordBadgeText(t);

  renderPicksStreak(myPicks, times);
}

function renderPicksStreak(myPicks, times){
  const container = document.getElementById('picks-streak-strip');
  const weekRecords = []; // {label, wins, losses, status}
  weekKeysSorted.forEach(k=>{
    // Counted picks only, through the same tally as the badge above it.
    const {wins, losses} = tallyMyPicks(myPicks, times, [k], weeks);
    const total = wins+losses;
    let status = 'none';
    if(total>0) status = wins>losses ? 'win' : (losses>wins ? 'loss' : 'even');
    weekRecords.push({label:k, wins, losses, status});
  });

  const graded = weekRecords.filter(w=>w.status!=='none');
  if(graded.length === 0){
    container.innerHTML = '';
    return;
  }

  // Current streak: consecutive most-recent graded weeks with the SAME
  // win/loss direction, counting backward from the latest graded week.
  let streak = 0, streakType = null;
  for(let i=graded.length-1; i>=0; i--){
    const w = graded[i];
    if(w.status==='even') break;
    if(streakType===null){ streakType = w.status; streak = 1; }
    else if(w.status===streakType){ streak++; }
    else break;
  }
  const streakLabel = streak>0 ? `${streak}-week ${streakType==='win'?'winning':'losing'} streak` : '';

  container.innerHTML = `
    <div class="streak-row">
      <div class="streak-cells">
        ${weekRecords.map(w=>`<span class="streak-cell ${w.status}" title="${w.label}: ${w.wins}-${w.losses}"></span>`).join('')}
      </div>
      ${streakLabel ? `<span class="streak-label ${streakType}">${streakLabel}</span>` : ''}
    </div>`;
}

let lastPickChange = null;

function renderPicksGrid(){
  const grid = document.getElementById('picks-grid');
  const badge = document.getElementById('picks-record-badge');
  const weekData = weeks[currentPicksWeek];
  const gamesList = weekData ? weekData.games : [];
  // While a share link is open the grid renders THEIR picks and never reads
  // this device's storage, so viewing someone else's week cannot be mistaken
  // for -- or quietly become -- your own log.
  const myPicks = sharedPicksView ? sharedPicksView.picks : loadMyPicks();
  grid.classList.toggle('picks-readonly', !!sharedPicksView);

  if(!weekData || gamesList.length === 0){
    grid.innerHTML = stateHtml('waiting', 'No games to pick for this week yet',
      'Games appear here once the model has saved its picks for the week.');
    badge.textContent = '—';
    return;
  }

  if(!sharedPicksView){
    const times = loadPickTimes();
    if(stampUnlockedPicks(myPicks, times, gameForPid, Date.now())) savePickTimes(times);
  }
  refreshPickTotals(myPicks);

  const now = Date.now();
  grid.innerHTML = gamesList.map(g=>{
    const pid = currentPicksWeek+'|'+g.home+'|'+g.away;
    const pick = myPicks[pid];
    const modelBPick = g.mktB_home >= 50 ? g.home : g.away;
    const kickoff = kickoffLabel(g);
    const locked = !sharedPicksView && isPickLocked(g, now);
    return `<div class="game-card">
      ${matchupHeader(g, 'quiet')}
      ${kickoff ? `<div class="card-kickoff">${kickoff}</div>` : ''}
      <div class="pick-buttons" data-pid="${pid}" data-model-b="${modelBPick}">
        ${pickButton(g.away, pick, locked)}
        ${pickButton(g.home, pick, locked)}
      </div>
      <div class="pick-lock"></div>
      <div class="pick-agrees"></div>
    </div>`;
  }).join('');

  // paintPickCard is the LAST writer on every path, including this one. The
  // markup above still emits `selected` so the first frame is never wrong,
  // but the class it wrote is immediately re-derived here -- so if the two
  // ever disagree, the single authority wins rather than the string template.
  // `.pick-agrees` is emitted empty for the same reason: one implementation
  // of that sentence, not two that drift.
  grid.querySelectorAll('.pick-buttons').forEach(group=>{
    paintPickCard(group, myPicks[group.dataset.pid]);
  });

  // No handlers at all in shared view. Disabling them here rather than
  // ignoring the click inside the handler means there is no path from a tap
  // on someone else's picks to a write against this device's storage.
  if(sharedPicksView) return;

  grid.querySelectorAll('.pick-buttons').forEach(group=>{
    const pid = group.dataset.pid;
    group.querySelectorAll('.pick-btn').forEach(btn=>{
      btn.addEventListener('click', ()=>{
        // Checked here as well as by `disabled`: a page left open across a
        // kickoff still has live buttons until something repaints the card.
        if(isPickLocked(gameForPid(pid), Date.now())){
          paintPickCard(group, loadMyPicks()[pid]);
          return;
        }
        const picks = loadMyPicks(), times = loadPickTimes();
        const previous = picks[pid], previousAt = times[pid];
        const clicked = btn.dataset.team;
        // Clicking your already-selected pick clears it, rather than being
        // a no-op -- otherwise there's no way to un-pick a game at all.
        if(previous === clicked){
          delete picks[pid]; delete times[pid];
        } else {
          picks[pid] = clicked; times[pid] = new Date().toISOString();
        }
        lastPickChange = {pid, previous, previousAt};
        saveMyPicks(picks); savePickTimes(times);
        // NOT renderPicksGrid(). That replaces the whole grid through
        // innerHTML, which destroys the button being tapped along with every
        // other card -- and on iOS the page jumps to the top when the element
        // under your finger is removed mid-tap. Reported from a phone:
        // "changing my pick on cards below the first two scrolls to the top".
        // It does not reproduce in headless Chromium, which has scroll
        // anchoring on by default and absorbs it; that is a difference in
        // engines, not evidence there was nothing to fix.
        //
        // It is also the rule this repo already wrote down after an open
        // breakdown vanished on a filter change: a wholesale innerHTML
        // re-render silently destroys interaction state. Focus, the active
        // touch and the scroll position are all interaction state.
        //
        // Nothing else on the card depends on the pick, so nothing else needs
        // redrawing. The totals above the grid do, and they are not under the
        // finger.
        paintPickCard(group, picks[pid]);
        refreshPickTotals(picks);
        showUndoToast();
      });
    });
  });
}

function showUndoToast(){
  let toast = document.getElementById('undo-toast');
  if(!toast){
    toast = document.createElement('div');
    toast.id = 'undo-toast';
    toast.className = 'undo-toast';
    document.body.appendChild(toast);
  }
  toast.innerHTML = `<span>Pick saved</span><button class="btn btn-link undo-btn" id="undo-action">Undo</button>`;
  toast.classList.add('visible');
  document.getElementById('undo-action').onclick = ()=>{
    if(!lastPickChange) return;
    // Undo is a pick too: after kickoff it would be a late change.
    if(isPickLocked(gameForPid(lastPickChange.pid), Date.now())){
      lastPickChange = null;
      toast.classList.remove('visible');
      return;
    }
    const picks = loadMyPicks(), times = loadPickTimes();
    if(lastPickChange.previous === undefined){
      delete picks[lastPickChange.pid];
    } else {
      picks[lastPickChange.pid] = lastPickChange.previous;
    }
    if(lastPickChange.previousAt === undefined) delete times[lastPickChange.pid];
    else times[lastPickChange.pid] = lastPickChange.previousAt;
    saveMyPicks(picks); savePickTimes(times);
    const pid = lastPickChange.pid;
    lastPickChange = null;
    toast.classList.remove('visible');
    // Same surgical path as the tap that created this toast. Undo is not
    // under the finger, but routing it through renderPicksGrid would leave
    // two ways for a card to reach its painted state, and the one nobody
    // looks at is the one that drifts.
    const group = document.querySelector(`#picks-grid .pick-buttons[data-pid="${CSS.escape(pid)}"]`);
    paintPickCard(group, picks[pid]);
    refreshPickTotals(picks);
  };
  clearTimeout(showUndoToast._timer);
  showUndoToast._timer = setTimeout(()=>{ toast.classList.remove('visible'); }, 5000);
}
populateWeekSelect(document.getElementById('picks-week-select'), (val)=>{
  // A share link covers exactly one week, so navigating away from that week
  // ends the shared view rather than showing an empty grid attributed to
  // someone else.
  if(sharedPicksView && val !== sharedPicksView.weekKey) exitSharedPicks();
  currentPicksWeek = val;
  renderPicksGrid();
  syncWeekStepper('picks-week');
}, latestWeekKey);
wireWeekStepper('picks-week');
renderPicksGrid();
// Last, so every function and the week selector it touches already exist.
readSharedPicksFromUrl();

// Pasting a share link into a tab that already has the dashboard open changes
// only the fragment, so the browser does not reload and none of the above runs
// again -- the link would appear to do nothing at all. Found by testing the
// receive path as a real second visit rather than as a fresh page load.
// The same listener handles the back button out of a shared view.
window.addEventListener('hashchange', ()=>{
  if(/[#&]picks=/.test(location.hash || '')) readSharedPicksFromUrl();
  else if(sharedPicksView) exitSharedPicks();
});

/* ---------- What actually happened at this confidence level ----------

   The reliability diagram on Model Lab answers "are the probabilities honest?"
   for someone reading the research. This puts the same answer on the pick
   itself, where a person is actually deciding something.

   Given a stated probability, it finds the backtest bin that probability falls
   in and reports what really happened in that bin across ~1087 games, with the
   Wilson interval. Motivated by a confirmed finding, re-derived 2026-09-06 by
   src/sports/nfl/research/verify_low_confidence_finding.py: across the 343 games where Model A's
   own probability sits within 0.05 of a coin flip it hits 52.48%, while the
   market hits 64.14% on those same games -- a -11.66pt gap, CI [-18.37,
   -5.25]. A number like 52% on a pick card reads as "slightly favoured"
   unless the track record behind it is shown too.

   Two details that are easy to get wrong:

     1. The bins are over the probability of a HOME win across [0,1], not over
        "probability of whichever side we picked" -- calibration.py bins that
        way deliberately, so the direction of any miscalibration survives. That
        means an AWAY pick has to be read as the complement: a 65% away pick is
        a 35% home probability, so it belongs in the 30-40% bin, and that bin's
        historical rate has to be flipped before it means anything about the
        away side. Getting this backwards would show a confident pick as though
        it historically lost.
     2. A bin whose interval spans 50% has a track record that cannot be
        distinguished from a coin flip. That is worth saying out loud rather
        than leaving the reader to compare three numbers themselves. */
/* "2022-2025", not "2022-2023-2024-2025". Falls back to listing them when the
   seasons aren't contiguous, since collapsing a gap would misstate the span. */
function seasonRange(seasons){
  if(!seasons || !seasons.length) return 'the backtest window';
  const first = seasons[0], last = seasons[seasons.length - 1];
  const contiguous = seasons.every((s, i) => s === first + i);
  return contiguous ? `${first}&ndash;${last}` : seasons.join(', ');
}

function pickTrackRecord(homeProbPct, modelKey){
  if(!calibration || !calibration.models || !calibration.models[modelKey]) return null;
  if(homeProbPct === null || homeProbPct === undefined) return null;

  const p = homeProbPct / 100;
  const bin = calibration.models[modelKey].bins.find(
    b => p >= b.lo && (b.hi < 1 ? p < b.hi : p <= b.hi));
  if(!bin) return null;

  // Which side the card is actually picking, and therefore which direction the
  // bin's home-win rate has to be read in.
  const pickedHome = homeProbPct >= 50;
  const rate  = pickedHome ? bin.observed : 100 - bin.observed;
  // Flipping an interval reverses its ends: the complement of [lo, hi] is
  // [100-hi, 100-lo]. Writing it the other way round yields lo > hi, which
  // renders as a backwards range rather than failing loudly.
  const lo    = pickedHome ? bin.ci_lo : 100 - bin.ci_hi;
  const hi    = pickedHome ? bin.ci_hi : 100 - bin.ci_lo;

  return {
    label: bin.label, n: bin.n, rate, lo, hi,
    underpowered: bin.underpowered,
    coinFlip: lo <= 50 && hi >= 50,
  };
}

/* `where` decides whether the ordinary case is drawn on the card or tucked
   into the breakdown the card already has a toggle for.

   The reason is that this block is not per-game -- it is per confidence BAND,
   so most of a week's cards carry a byte-identical paragraph. Rendered inline
   on all sixteen it was ~140px of repeated text per card, which is what stopped
   the cards being the near-square shape the component study measured, and it
   is also the thing a reader stops seeing by the third card.

   What stays on the card is the band with too few games to report a rate at
   all. That is a statement about missing evidence, it differs between games,
   and nothing else on the card implies it.

   The coin-flip case USED to stay here too, and it was removed on the owner's
   call: "I don't need the week board essentially telling me over and over that
   a split decision is not much better than a coinflip." He is right that it
   repeats -- seven of sixteen cards carried it in Week 1, every one of them
   saying the same thing about a band around 58-59% -- and the card already
   says MODELS SPLIT and prints two probabilities either side of 50%. It is a
   different claim (calibration of the band, not disagreement between models),
   but it is not a claim a reader needs seven times on one screen.

   It is not deleted: the routine path below still renders it inside the
   breakdown, so it is one click away on every card it applies to.

   This also happens to be what makes the cards uniform. That block was 129px
   and appeared on some cards and not others, which alone accounted for a
   205px spread in card height; without it the spread is 20px.

   'any' keeps the old always-inline behaviour for other callers. */
function trackRecordHtml(homeProbPct, where='any'){
  const t = pickTrackRecord(homeProbPct, 'model_b');
  if(!t) return '';
  const notable = t.underpowered;
  if(where === 'card' && !notable) return '';
  if(where === 'panel' && notable) return '';
  if(t.underpowered){
    return `<div class="track-record thin">Only ${t.n} past game${t.n===1?'':'s'}
      landed at this confidence &mdash; too few to report a track record.</div>`;
  }
  const coin = t.coinFlip
    ? ` <span class="track-coin">That range includes 50%, so this band has not
        been shown to beat a coin flip.</span>`
    : '';
  // Was three lines carrying "95% CI 67.2-81.4%" on every card. The number was
  // honest and the phrasing was not for this reader -- and "CI" slipped past
  // the jargon guard, which bans "confidence interval" spelled out. Same
  // information, said the way you would say it out loud.
  return `<div class="track-record${t.coinFlip?' warn':''}">
    <b>When picks looked this sure before,</b> they were right
    <b>${t.rate.toFixed(1)}%</b> of the time &mdash; ${t.n} past games, and the
    real rate is somewhere around ${t.lo.toFixed(0)}&ndash;${t.hi.toFixed(0)}%.${coin}
    <span class="track-note">A record for this band of picks over
    ${seasonRange(calibration.backtest_seasons)}, not a second guess at this game.</span>
  </div>`;
}

/* ---------- Chart series identity ----------
   One definition of what each series looks like, shared by every chart on
   the page. Colour follows the ENTITY, not its position in whatever subset
   is currently drawn, so hiding Model A on the reliability diagram never
   repaints the market. `shape` and `dash` are the secondary encoding: on a
   greyscale print, in forced-colours mode, or for a reader whose vision the
   OKLab checks can only approximate, identity survives without colour. */
const SERIES = {
  a:      {label:'Model A',  color:'var(--series-a)', shape:'circle',   dash:''},
  b:      {label:'Model B',  color:'var(--series-b)', shape:'square',   dash:''},
  market: {label:'Market',   color:'var(--series-c)', shape:'triangle', dash:''},
  picks:  {label:'My Picks', color:'var(--series-d)', shape:'diamond',  dash:'6,4'},
};

/* Marker path for a series shape, centred on (cx,cy). Sized by `r` as a
   radius so every shape reads at roughly the same visual weight; the skill's
   floor is an 8px marker, so r stays >= 4.5 wherever these are hit targets. */
function markerPath(shape, cx, cy, r){
  const s = r * 0.92;
  switch(shape){
    case 'square':   return `<rect x="${(cx-s).toFixed(1)}" y="${(cy-s).toFixed(1)}" width="${(2*s).toFixed(1)}" height="${(2*s).toFixed(1)}" rx="1"`;
    case 'triangle': return `<polygon points="${cx.toFixed(1)},${(cy-r*1.15).toFixed(1)} ${(cx+r).toFixed(1)},${(cy+r*0.75).toFixed(1)} ${(cx-r).toFixed(1)},${(cy+r*0.75).toFixed(1)}"`;
    case 'diamond':  return `<polygon points="${cx.toFixed(1)},${(cy-r*1.2).toFixed(1)} ${(cx+r*1.2).toFixed(1)},${cy.toFixed(1)} ${cx.toFixed(1)},${(cy+r*1.2).toFixed(1)} ${(cx-r*1.2).toFixed(1)},${cy.toFixed(1)}"`;
    default:         return `<circle cx="${cx.toFixed(1)}" cy="${cy.toFixed(1)}" r="${r.toFixed(1)}"`;
  }
}

/* Legend swatches carry the shape as well as the colour, so the legend is a
   real key to the marks rather than four coloured squares. */
function seriesLegend(keys){
  return keys.map(k=>{
    const s = SERIES[k];
    return `<span style="display:inline-flex; align-items:center; gap:var(--s2); margin-right:var(--s4); white-space:nowrap;">
      <svg width="14" height="14" viewBox="0 0 14 14" aria-hidden="true" style="flex-shrink:0;">
        ${markerPath(s.shape, 7, 7, 5)} fill="${s.color}"/>
      </svg>${s.label}</span>`;
  }).join('');
}

/* ---------- Season Accuracy ---------- */
/* End-labels for a line chart (Stage 19): given where each line ends, where
   to put its label so no two are closer than `gap` and the block stays within
   [lo, hi]. Labels keep their lines' order; a label moves only as far as it
   has to. Returns the positions in the input's order. */
const TREND_LABEL_GAP = 14;
function spreadLabels(ys, gap, lo, hi){
  const order = ys.map((v, i) => ({v, i})).sort((a, b) => a.v - b.v || a.i - b.i);
  const out = order.map(o => Math.min(Math.max(o.v, lo), hi));
  for(let k = 1; k < out.length; k++) out[k] = Math.max(out[k], out[k-1] + gap);
  const over = out.length ? out[out.length-1] - hi : 0;
  if(over > 0){
    for(let k = 0; k < out.length; k++) out[k] -= over;
    for(let k = out.length - 2; k >= 0; k--) out[k] = Math.min(out[k], out[k+1] - gap);
  }
  const res = new Array(ys.length);
  order.forEach((o, k) => { res[o.i] = out[k]; });
  return res;
}

/* Charts drawn for a phone (Stage 26 item 4, from the 2026-09-28 audit).
   The trend and reliability charts were drawn 680 and 470 units wide and
   shrunk to fit, so on a 375px phone their text came out 4px and 6px tall.
   Below 640px (the page's phone width, as ORIENTATION_PHONE) each is drawn
   at about the width it will have, with its text sized for that width, so it
   renders at 11-12px. Mark chose this from rendered side-by-sides on
   2026-09-28, with the trend chart's names at the line ends dropped on a
   phone: the legend above it names every line, by colour and by the marker
   shape each line ends in. Decided once, when the chart is built; a phone
   turned sideways keeps the chart it loaded with, which still scales. */
const CHART_PHONE = '(max-width:640px)';
function chartIsPhone(){
  return !!(window.matchMedia && window.matchMedia(CHART_PHONE).matches);
}

function buildCumulativeTrendChart(){
  // Two points, not one. A trend needs somewhere to go, and a single graded
  // week drew either nothing (every series short-circuits at valid.length < 2)
  // or, when an empty week was still being emitted as a data point, three flat
  // horizontal lines that looked like a considered finding and were an artifact
  // of charting a week with no games in it.
  //
  // Says so rather than rendering nothing, following the calibration section
  // further down this same page, which already handles its own not-enough-data
  // case in words. An absent chart invites "is it broken?"; a sentence does not.
  if(!accuracy.weeks || accuracy.weeks.length < 2){
    const n = (accuracy.weeks || []).length;
    return `<div class="method-block">
      <h3>Accuracy over the season</h3>
      <p>${n === 0
          ? 'No weeks have been graded yet, so there is no trend to show. This fills in after the first week’s games are played and graded.'
          : 'Only one week has been graded so far. A trend line needs at least two, so this chart appears once the second week is in — a single point drawn as a line would suggest a direction that has not been measured.'}</p>
    </div>`;
  }
  const myPicks = loadMyPicks(), pickTimes = loadPickTimes();

  let cA=0, nA=0, cB=0, nB=0, cM=0, nM=0, cP=0, nP=0;
  const points = accuracy.weeks.map(w=>{
    cA += w.model_a_correct; nA += w.model_a_n;
    cB += w.model_b_correct; nB += w.model_b_n;
    cM += w.market_correct; nM += w.market_n;
    const weekKey = Object.keys(weeks).find(k=>weeks[k].season===w.season && weeks[k].week===w.week);
    if(weekKey){
      // Counted picks only -- the same tally as the scoreboard above it.
      const t = tallyMyPicks(myPicks, pickTimes, [weekKey], weeks);
      cP += t.wins; nP += t.wins + t.losses;
    }
    return {
      label: `${w.season} Wk${w.week}`,
      a: nA>0 ? (cA/nA*100) : null, b: nB>0 ? (cB/nB*100) : null,
      m: nM>0 ? (cM/nM*100) : null, p: nP>0 ? (cP/nP*100) : null,
    };
  });

  // padR leaves room for the direct end-labels: four series is inside the
  // "<= 4 series are also direct-labeled" rule, so identity never rests on
  // colour alone even for a reader who skips the legend.
  const phone = chartIsPhone();
  const W = phone ? 300 : 680, H = phone ? 230 : 220, padL = phone ? 34 : 36, padR = phone ? 20 : 74;
  const padT=14, padB=28;
  const fsTick = phone ? 11 : 9, fsName = phone ? 12 : 10;
  const n = points.length;
  const x = i => n<=1 ? padL : padL + (i/(n-1))*(W-padL-padR);
  const allVals = points.flatMap(p=>[p.a,p.b,p.m,p.p]).filter(v=>v!==null);
  const yMin = Math.max(0, Math.min(...allVals, 40) - 5);
  const yMax = Math.min(100, Math.max(...allVals, 60) + 5);
  const y = v => padT + (1-(v-yMin)/(yMax-yMin))*(H-padT-padB);

  // Series drawn in fixed order, each with a direct end-label. The labels
  // are placed together once every line is known (Stage 19): sorted by where
  // their lines end and spread to a minimum gap, the block moved back inside
  // the plot if spreading pushed it out. Nudging one label at a time, in draw
  // order and always downwards, left two labels overprinting whenever two
  // lines ended together.
  const ends = [];
  function lineFor(key, seriesKey){
    const s = SERIES[seriesKey];
    const valid = points.map((p,i)=>({i, v:p[key]})).filter(d=>d.v!==null);
    if(valid.length < 2) return '';
    const d = valid.map((d,idx)=>`${idx===0?'M':'L'}${x(d.i).toFixed(1)},${y(d.v).toFixed(1)}`).join(' ');
    const last = valid[valid.length-1];
    ends.push({x: x(last.i), y: y(last.v), label: s.label});
    const dash = s.dash ? ` stroke-dasharray="${s.dash}"` : '';
    return `<path d="${d}" fill="none" stroke="${s.color}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"${dash}/>
      ${markerPath(s.shape, x(last.i), y(last.v), 4.5)} fill="${s.color}" stroke="var(--surface)" stroke-width="2"/>`;
  }
  function endLabels(){
    if(phone) return '';   // the legend names the lines on a phone
    const placed = spreadLabels(ends.map(e => e.y), TREND_LABEL_GAP, padT + 4, H - padB);
    return ends.map((e, k) =>
      `<text x="${(e.x+9).toFixed(1)}" y="${(placed[k]+3.5).toFixed(1)}" font-size="${fsName}" font-weight="600" fill="var(--text-2)">${e.label}</text>`).join('');
  }

  // The weeks under the x-axis. A season's weeks as "Wk 1"; the season
  // itself only when the points span more than one.
  const oneSeason = new Set(accuracy.weeks.map(w => w.season)).size === 1;
  const weekTicks = accuracy.weeks.map((w, i) =>
    `<text x="${x(i).toFixed(1)}" y="${(H - padB + 16).toFixed(1)}" text-anchor="middle" font-size="${fsTick}" fill="var(--text-2)">${oneSeason ? '' : w.season + ' '}Wk ${w.week}</text>`).join('');

  const gridLines = [];
  for(let gv = Math.ceil(yMin/10)*10; gv <= yMax; gv += 10){
    gridLines.push(`<line x1="${padL}" y1="${y(gv).toFixed(1)}" x2="${W-padR}" y2="${y(gv).toFixed(1)}" stroke="var(--border)" stroke-width="1"/>
      <text x="${padL-6}" y="${(y(gv)+3).toFixed(1)}" text-anchor="end" font-size="${fsTick}" fill="var(--text-2)">${gv}%</text>`);
  }

  // My picks are in the legend only when they have a line to name. When
  // every graded pick was late or untimed there is none, and the chart says
  // why instead (Stage 37 item 1).
  const picksDrawn = points.filter(p => p.p !== null).length >= 2;
  const legend = seriesLegend(picksDrawn ? ['a','b','market','picks'] : ['a','b','market']);
  const allMine = tallyMyPicks(myPicks, pickTimes, weekKeysSorted, weeks);
  const picksNote = !picksDrawn && nP === 0 && (allMine.late + allMine.untimed) > 0
    ? `<p class="score-foot">My picks has no line yet. ${leftOutSentence(allMine)} ${PICKS_LIVE_HERE}</p>` : '';

  return `<div class="method-block">
    <h3>Cumulative Accuracy Trend</h3>
    <p style="margin-bottom:var(--s3);">Running accuracy as the season progresses -- not week-by-week noise, but how each approach has performed overall up to that point.</p>
    <div style="font-size:var(--fs-11); color:var(--text-2); margin-bottom:var(--s2);">${legend}</div>
    <svg viewBox="0 0 ${W} ${H}" style="width:100%; height:auto; max-width:${W}px;" role="img" aria-label="Line chart of running accuracy by week for Model A, Model B, the market and, once you have made picks, yours. Each week's own figures are in the Week by week table below.">
      ${gridLines.join('')}
      ${lineFor('a','a')}
      ${lineFor('b','b')}
      ${lineFor('m','market')}
      ${lineFor('p','picks')}
      ${endLabels()}
      ${weekTicks}
    </svg>
    ${picksNote}
  </div>`;
}

function buildCalibrationChart(){
  if(!accuracy.calibration || accuracy.calibration.length === 0) return '';

  // Refuse to draw a calibration chart that has no power behind it. Plotting
  // a bucket of n=1 against a perfect-calibration line renders a coin flip
  // as though it were a measurement -- the chart looks authoritative and
  // says nothing. Live calibration needs many graded weeks; until then this
  // states the sample size plainly instead.
  if(accuracy.calibration_underpowered){
    return `<div class="method-block">
      <h3>Not enough games yet to check</h3>
      <p style="margin-bottom:0;">Not enough graded games yet to say whether these percentages are honest.
      Only <b style="color:var(--text)">${accuracy.n_graded}</b> game${accuracy.n_graded===1?'':'s'}
      ${accuracy.n_graded===1?'has':'have'} been graded so far, spread across
      ${accuracy.calibration.length} confidence buckets &mdash; every one of them below the
      ${accuracy.min_bucket_n}-game floor this dashboard requires before reporting a hit rate.
      A bucket of one game reporting &ldquo;0% actual&rdquo; is a coin flip, not a finding, so it
      isn't charted. The counts are still shown in the table below.
      The same check across every past season is on <b style="color:var(--text)">Model Lab</b>.</p>
    </div>`;
  }

  const S = 260, pad = 30;
  const scale = v => pad + (v/100)*(S-2*pad);

  const points = accuracy.calibration.map(c => ({x: c.avg_predicted, y: c.actual_rate, n: c.n, bucket: c.bucket}));
  const maxN = Math.max(...points.map(p=>p.n), 1);

  const dots = points.map(p => {
    const r = 4 + (p.n/maxN)*8; // dot size reflects sample size in that bucket
    return `<circle cx="${scale(p.x).toFixed(1)}" cy="${(S-scale(p.y)).toFixed(1)}" r="${r.toFixed(1)}" fill="var(--series-b)" fill-opacity="0.85" stroke="var(--surface)" stroke-width="2">
      <title>${p.bucket}: predicted ${p.x}%, actual ${p.y}% (n=${p.n})</title>
    </circle>`;
  }).join('');

  return `
    <div style="display:flex; align-items:flex-start; gap:var(--s5); flex-wrap:wrap; margin-bottom:var(--s4);">
      <svg viewBox="0 0 ${S} ${S}" style="width:260px; height:260px; flex-shrink:0;" role="img" aria-label="Calibration chart: each confidence bucket's average predicted chance against how often those picks were right. The same buckets are in the table below.">
        <line x1="${pad}" y1="${S-pad}" x2="${S-pad}" y2="${pad}" stroke="var(--border-strong)" stroke-width="1.5" stroke-dasharray="4,3"/>
        <line x1="${pad}" y1="${S-pad}" x2="${pad}" y2="${pad}" stroke="var(--border)" stroke-width="1"/>
        <line x1="${pad}" y1="${S-pad}" x2="${S-pad}" y2="${S-pad}" stroke="var(--border)" stroke-width="1"/>
        <text x="${pad}" y="${S-pad+14}" font-size="9" fill="var(--text-2)">0%</text>
        <text x="${S-pad}" y="${S-pad+14}" font-size="9" fill="var(--text-2)" text-anchor="end">100%</text>
        <text x="${pad-6}" y="${S-pad+4}" font-size="9" fill="var(--text-2)" text-anchor="end">0%</text>
        <text x="${pad-6}" y="${pad+4}" font-size="9" fill="var(--text-2)" text-anchor="end">100%</text>
        ${dots}
      </svg>
      <div style="font-size:var(--fs-12); color:var(--text-2); max-width:280px; padding-top:var(--s2);">
        <div style="margin-bottom:var(--s2);"><span style="display:inline-block; width:8px; height:1.5px; background:var(--border-strong); margin-right:var(--s1); vertical-align:middle;"></span>Dashed line = perfectly honest</div>
        <div><span style="display:inline-block; width:8px; height:8px; border-radius:50%; background:var(--series-b); margin-right:var(--s1); vertical-align:middle;"></span>Each dot = one confidence bucket (bigger dot = more games)</div>
        <div style="margin-top:var(--s2);">Dots above the line mean we're underconfident in that bucket; below means overconfident.</div>
      </div>
    </div>`;
}

/* ---------- Reliability diagram (backtest calibration) ----------

   What this chart answers: when a model says 70%, does that side actually win
   about 70% of the time? Every point is one probability bin; x is the average
   probability the model stated inside that bin, y is how often the home team
   really won. Perfect calibration is the diagonal.

   Two decisions worth naming, because they are what separate this from the
   live calibration panel on Season Accuracy:

   1. It is drawn from the BACKTEST (~1087 games), not from the handful of
      graded games this season. The live panel refuses to draw itself until it
      has the sample to justify a claim; this one has it.
   2. Every point carries a Wilson interval. A reliability diagram of bare
      dots invites the reader to treat every off-diagonal point as a defect.
      Most of these intervals cross the diagonal, which means "consistent with
      perfect calibration" -- and the chart has to be able to say so.

   Bins under the min-n floor are drawn hollow rather than tinted, so the
   "don't lean on this one" signal survives greyscale and colour-blindness. */
const RELIABILITY_SERIES = [['model_a','a'], ['model_b','b'], ['market','market']];
let relVisible = {model_a:true, model_b:true, market:true};

/* ---------- Reliability points: a 24px target at every width (Stage 12) ----------
   Each point's transparent halo is its hit target. It was r=11, 22 units in
   the chart's 470-unit viewBox, and the chart scales with its container, so
   the target was 22 CSS px only when the chart rendered at exactly 470px:
   the browser checker measured 21-22px at 360, 390, 1024 and 1280 wide,
   under WCAG 2.5.8's 24. The radius is now worked out from the rendered
   width so the halo is never under 24 CSS px across, and never smaller than
   it was. Pure, so the suite can execute it; applied by sizeRelHalos(). */
const REL_HALO_BASE_R = 11;
function relHaloRadius(renderedWidth, viewBoxWidth, minPx){
  if(!(renderedWidth > 0) || !(viewBoxWidth > 0)) return REL_HALO_BASE_R;  // hidden page: nothing to size yet
  return Math.max(REL_HALO_BASE_R, (minPx / 2) * (viewBoxWidth / renderedWidth));
}

function buildReliabilityDiagram(){
  if(!calibration || !calibration.models) return '';

  const phone = chartIsPhone();
  const W = phone ? 300 : 470, padL = phone ? 52 : 48, padR = phone ? 18 : 16, padT = 14;
  // The desktop plot stays 390, as it was before the phone drawing (it leaves
  // 16 spare units at the right); only the phone plot fills its width.
  const PLOT = phone ? W - padL - padR : 390;
  const H = padT + PLOT + (phone ? 44 : 40);
  const fs = phone ? {tick: 11, note: 11, axis: 12} : {tick: 10, note: 9.5, axis: 10.5};
  const x = v => padL + (v/100)*PLOT;
  const y = v => padT + (1 - v/100)*PLOT;

  const grid = [0,25,50,75,100].map(g=>`
    <line x1="${x(g).toFixed(1)}" y1="${padT}" x2="${x(g).toFixed(1)}" y2="${(padT+PLOT).toFixed(1)}" stroke="var(--border)" stroke-width="1"/>
    <line x1="${padL}" y1="${y(g).toFixed(1)}" x2="${(padL+PLOT).toFixed(1)}" y2="${y(g).toFixed(1)}" stroke="var(--border)" stroke-width="1"/>
    <text x="${x(g).toFixed(1)}" y="${(padT+PLOT+16).toFixed(1)}" font-size="${fs.tick}" fill="var(--text-2)" text-anchor="middle">${g}%</text>
    <text x="${(padL-8).toFixed(1)}" y="${(y(g)+3.5).toFixed(1)}" font-size="${fs.tick}" fill="var(--text-2)" text-anchor="end">${g}%</text>`).join('');

  // Marks are drawn series by series in fixed order so overlaps stack the same
  // way on every render -- a chart whose z-order shuffles between loads is a
  // chart nobody can point at in a screenshot.
  const marks = RELIABILITY_SERIES.map(([modelKey, seriesKey])=>{
    const m = calibration.models[modelKey];
    if(!m) return '';
    const s = SERIES[seriesKey];
    const pts = m.bins.map(b=>{
      const cx = x(b.mean_predicted), cy = y(b.observed);
      const barTop = y(b.ci_hi), barBot = y(b.ci_lo);
      // Wilson interval. Drawn under the marker so the marker's surface ring
      // still separates it from whatever it overlaps.
      const bar = `<line x1="${cx.toFixed(1)}" y1="${barTop.toFixed(1)}" x2="${cx.toFixed(1)}" y2="${barBot.toFixed(1)}" stroke="${s.color}" stroke-width="2" stroke-opacity="0.5" stroke-linecap="round"/>
        <line x1="${(cx-3.5).toFixed(1)}" y1="${barTop.toFixed(1)}" x2="${(cx+3.5).toFixed(1)}" y2="${barTop.toFixed(1)}" stroke="${s.color}" stroke-width="2" stroke-opacity="0.5"/>
        <line x1="${(cx-3.5).toFixed(1)}" y1="${barBot.toFixed(1)}" x2="${(cx+3.5).toFixed(1)}" y2="${barBot.toFixed(1)}" stroke="${s.color}" stroke-width="2" stroke-opacity="0.5"/>`;
      const fill = b.underpowered ? 'var(--surface)' : s.color;
      const marker = `${markerPath(s.shape, cx, cy, 5)} fill="${fill}" stroke="${b.underpowered ? s.color : 'var(--surface)'}" stroke-width="2"/>`;
      const tip = [
        `<b>${s.label} &middot; ${b.label} bin</b>`,
        `Stated ${b.mean_predicted}% &rarr; actually won <b>${b.observed}%</b>`,
        `95% interval ${b.ci_lo}%&ndash;${b.ci_hi}% over ${b.n} game${b.n===1?'':'s'}`,
        b.underpowered
          ? `Under the ${calibration.min_bin_n}-game floor &mdash; too thin to lean on`
          : (b.consistent_with_perfect
              ? 'Interval covers the stated rate: consistent with perfect calibration'
              : 'Interval excludes the stated rate: a real miss in this bin'),
      ].join('<br>');
      // A transparent halo makes the hit target larger than the mark, which
      // matters most for the thin bins nobody can click precisely.
      // tabindex -1 on every point: initReliabilityDiagram hands the one Tab
      // stop to a single point (roving tabindex, Stage 26).
      return `<g class="rel-point" tabindex="-1" role="img"
                 aria-label="${s.label}, ${b.label} bin: stated ${b.mean_predicted} percent, observed ${b.observed} percent, ${b.n} games"
                 data-tip="${tip.replace(/"/g,'&quot;')}" data-cx="${cx.toFixed(1)}" data-cy="${cy.toFixed(1)}">
        ${bar}
        <circle class="rel-halo" cx="${cx.toFixed(1)}" cy="${cy.toFixed(1)}" r="${REL_HALO_BASE_R}" fill="transparent" stroke="none" opacity="0"/>
        ${marker}
      </g>`;
    }).join('');
    return `<g class="rel-series" data-model="${modelKey}">${pts}</g>`;
  }).join('');

  // The toggle row doubles as the legend: each control carries the series'
  // own marker shape and colour next to its name, sits directly above the
  // plot, and is always visible. Per-series direct labels inside the plot
  // were tried and dropped -- Model B and the market finish 0.3 points apart
  // in the top bin, so their labels collide exactly where the chart is most
  // crowded. The rule those labels serve is that identity must never rest on
  // colour alone; here the marker SHAPE carries it, which survives greyscale
  // and colour-blindness at every one of the 30 points rather than at three.
  const filters = RELIABILITY_SERIES.map(([modelKey, seriesKey])=>{
    const s = SERIES[seriesKey];
    return `<button class="btn btn-chip btn-toggle rel-toggle" data-model="${modelKey}" aria-pressed="true">
      <svg width="12" height="12" viewBox="0 0 12 12" aria-hidden="true">${markerPath(s.shape, 6, 6, 4.5)} fill="${s.color}"/></svg>${s.label}</button>`;
  }).join('');

  // The three decomposition scalars are single numbers, not shapes -- a bar
  // chart of three values that differ in the third decimal place would be a
  // worse read than the numbers themselves. Uncertainty is shown once,
  // outside the per-model rows, because it is a property of the games and is
  // identical for all three by construction.
  const statRows = RELIABILITY_SERIES.map(([modelKey, seriesKey])=>{
    const m = calibration.models[modelKey];
    if(!m) return '';
    const s = SERIES[seriesKey], d = m.decomposition;
    return `<div class="rel-stat">
      <span class="nm"><svg width="11" height="11" viewBox="0 0 11 11" aria-hidden="true">${markerPath(s.shape, 5.5, 5.5, 4.2)} fill="${s.color}"/></svg>${s.label}</span>
      <span class="v">${d.reliability.toFixed(6)}</span>
      <span class="v">${d.resolution.toFixed(6)}</span>
    </div>`;
  }).join('');

  const tableRows = RELIABILITY_SERIES.map(([modelKey, seriesKey])=>{
    const m = calibration.models[modelKey];
    if(!m) return '';
    return m.bins.map(b=>`<tr>
      <td>${SERIES[seriesKey].label}</td><td>${b.label}</td>
      <td class="num">${b.n}</td><td class="num">${b.mean_predicted}%</td>
      <td class="num">${b.observed}%${b.underpowered?'&nbsp;*':''}</td>
      <td class="num">${b.ci_lo}&ndash;${b.ci_hi}%</td></tr>`).join('');
  }).join('');

  const p = calibration.provenance || {};
  const n = calibration.models.model_a ? calibration.models.model_a.metrics.n : 0;
  const base = calibration.models.model_a
    ? (calibration.models.model_a.decomposition.base_rate*100).toFixed(1) : '--';

  return `<div class="method-block">
    <h3>Reliability Diagram &mdash; Are the Probabilities Honest?</h3>
    <p style="margin-bottom:var(--s3);">When a model says <b style="color:var(--text)">70%</b>, does that side actually win about 70% of the time? Each mark is one probability bin across ${n} backtested games, with its 95% interval.</p>
    <details class="rel-how">
      <summary>How to read this</summary>
      <p style="margin:var(--s2) 0 var(--s4);">Accuracy only asks whether we picked the right side; this asks something harder. The vertical bar on each mark is its 95% Wilson interval. The dashed diagonal is perfect calibration &mdash; and a mark whose bar crosses that line is <i>consistent</i> with being perfectly calibrated, however far the mark itself sits from it.</p>
    </details>
    <div class="rel-filters">${filters}</div>
    <div class="rel-wrap">
      <div class="rel-plot">
        <svg viewBox="0 0 ${W} ${H}" style="width:100%; height:auto;" role="group" aria-label="Reliability diagram: stated probability against observed win rate. One Tab stop; arrow keys move between points, Home and End go to the first and last.">
          ${grid}
          <line x1="${x(0).toFixed(1)}" y1="${y(0).toFixed(1)}" x2="${x(100).toFixed(1)}" y2="${y(100).toFixed(1)}" stroke="var(--border-strong)" stroke-width="1.5" stroke-dasharray="5,4"/>
          <text x="${(x(100)-4).toFixed(1)}" y="${(y(100)+14).toFixed(1)}" font-size="${fs.note}" fill="var(--text-2)" text-anchor="end">perfect calibration</text>
          ${marks}
          <text x="${(padL+PLOT/2).toFixed(1)}" y="${(padT+PLOT+34).toFixed(1)}" font-size="${fs.axis}" fill="var(--text-2)" text-anchor="middle">Probability the model stated</text>
          <text x="12" y="${(padT+PLOT/2).toFixed(1)}" font-size="${fs.axis}" fill="var(--text-2)" text-anchor="middle" transform="rotate(-90 12 ${(padT+PLOT/2).toFixed(1)})">How often it actually happened</text>
        </svg>
        <div class="rel-tip" id="rel-tip"></div>
      </div>
      <div class="rel-side">
        <div class="rel-stat" style="border-bottom:1px solid var(--border-strong);">
          <span class="nm" style="color:var(--text-2); font-size:var(--fs-11); letter-spacing:.06em; text-transform:uppercase;">Brier decomposition</span>
          <span class="v" style="font-size:var(--fs-11); letter-spacing:.06em; text-transform:uppercase;" title="Mean squared gap between stated probability and observed rate. Lower is better; 0 is perfect calibration.">Reliab. &darr;</span>
          <span class="v" style="font-size:var(--fs-11); letter-spacing:.06em; text-transform:uppercase;" title="How far the bins sit from the base rate. Higher is better; 0 means the model says nothing.">Resol. &uarr;</span>
        </div>
        ${statRows}
        <details class="rel-how">
          <summary>What these numbers mean</summary>
          <p style="font-size:var(--fs-12); margin-top:var(--s3);">Brier = reliability &minus; resolution + uncertainty (Murphy, 1973). <b style="color:var(--text)">Reliability</b> is miscalibration: lower is better. <b style="color:var(--text)">Resolution</b> is how far the model dares to move away from the base rate: higher is better. A model that always predicts the ${base}% base rate scores a perfect 0 on reliability and a useless 0 on resolution &mdash; which is exactly why accuracy alone can't tell those two apart. Uncertainty (${calibration.models.model_a ? calibration.models.model_a.decomposition.uncertainty.toFixed(6) : '--'}) belongs to the games, not to any model.</p>
        </details>
        <p style="font-size:var(--fs-12); margin-top:var(--s3);">Model B's numbers look better than the market's on resolution and worse on reliability, and until 2026-09-05 this panel called that "a lead, not a claim" because nothing had tested it. It has now been tested, with a 5,000-resample paired bootstrap, and <b style="color:var(--text)">the lead did not survive</b>: every one of the four gaps against the market has a 95% interval that includes zero. Brier &minus;0.000622, CI [&minus;0.002395, +0.001141]. Resolution +0.001141, CI [&minus;0.002196, +0.004597]. At 1,087 games those differences are indistinguishable from noise, so the honest reading of this chart is that <b style="color:var(--text)">Model B and the market are calibrated about equally well</b> &mdash; not that one edges the other.</p>
        <p style="font-size:var(--fs-12); margin-top:var(--s3);">The same test did find two things that hold. Against <b style="color:var(--text)">Model A</b>, Model B is genuinely better &mdash; Brier &minus;0.019133, CI [&minus;0.025838, &minus;0.012687], and resolution +0.016814, CI [+0.008990, +0.024819] &mdash; which is the first version of "the spread helps" that rests on proper scoring rules rather than on accuracy, a metric this project has already shown moves by a whole game between platforms. And the market genuinely beats Model A: Brier +0.018511, CI [+0.011496, +0.025553]. See <b style="color:var(--text)">the experiment log above</b> for all three, and <code>src/sports/nfl/research/bootstrap_brier_gap.py</code> for the method.</p>
        <details class="rel-table" style="margin-top:var(--s3);">
          <summary>Show the numbers as a table</summary>
          <div class="table-wrap" style="margin-top:var(--s2);"><table class="metrics-table"><caption class="visually-hidden">Backtest calibration by probability bin, with 95% intervals</caption>
            <thead><tr><th scope="col">Series</th><th scope="col">Bin</th><th scope="col">Games</th><th scope="col">Stated</th><th scope="col">Observed</th><th scope="col">95% interval</th></tr></thead>
            <tbody>${tableRows}</tbody>
          </table></div>
          <p style="font-size:var(--fs-11); color:var(--text-2); margin-top:var(--s2);">* Fewer than ${calibration.min_bin_n} games in the bin &mdash; shown for completeness, drawn hollow on the chart, and not a measurement.</p>
        </details>
        <p class="rel-prov">Computed by <code>src/sports/nfl/research/calibration.py</code> over ${JSON.stringify(calibration.backtest_seasons)} &middot; model v${calibration.model_version} &middot; ${calibration.generated_at}<br>
        ${p.platform || 'unknown platform'} &middot; Python ${p.python || '?'} &middot; numpy ${p.numpy || '?'} &middot; pandas ${p.pandas || '?'} &middot; scikit-learn ${p['scikit-learn'] || '?'}<br>
        The machine is recorded because it has mattered before: see &ldquo;Backtest accuracy is not reproducible across platforms&rdquo; above.</p>
      </div>
    </div>
  </div>`;
}

/* Wires up the hover/focus readout and the series toggles. Runs after the
   markup is in the DOM, so the chart is a plain string everywhere else. */
function initReliabilityDiagram(){
  const tip = document.getElementById('rel-tip');
  if(!tip) return;
  const plot = tip.parentElement;

  function show(el){
    tip.innerHTML = el.dataset.tip;
    tip.classList.add('on');
    // Position in the plot's own pixel space, converting from the SVG's
    // viewBox units. Flips to the other side near an edge so the readout
    // never runs off the panel.
    const svg = plot.querySelector('svg');
    const box = svg.getBoundingClientRect();
    const vb = svg.viewBox.baseVal;
    const k = box.width / vb.width;
    let left = (+el.dataset.cx) * k + 16;
    let top  = (+el.dataset.cy) * k - 10;
    if(left + tip.offsetWidth > box.width) left = (+el.dataset.cx) * k - tip.offsetWidth - 16;
    // Clamp both axes to the plot box. Flipping to the left of a mark near the
    // right edge can still put the readout off the panel entirely, which is
    // how the first version of this hid its own y-axis label.
    left = Math.max(0, Math.min(left, Math.max(0, box.width - tip.offsetWidth)));
    top = Math.max(0, Math.min(top, box.height - tip.offsetHeight));
    tip.style.left = left + 'px';
    tip.style.top = top + 'px';
  }
  function hide(){ tip.classList.remove('on'); }

  // Size the halos now and whenever the chart's width changes -- including
  // the moment Model Lab opens, when the chart goes from 0 wide to its real
  // width. Without ResizeObserver, a window resize is the fallback.
  const svgEl = plot.querySelector('svg');
  function sizeRelHalos(){
    if(!svgEl) return;
    const r = relHaloRadius(svgEl.getBoundingClientRect().width, svgEl.viewBox.baseVal.width, 24);
    // Rounded UP: rounding to nearest could leave a halo at 23.99px.
    const rUp = (Math.ceil(r * 100) / 100).toFixed(2);
    svgEl.querySelectorAll('.rel-halo').forEach(c => c.setAttribute('r', rUp));
  }
  sizeRelHalos();
  if(window.ResizeObserver && svgEl) new ResizeObserver(sizeRelHalos).observe(svgEl);
  else window.addEventListener('resize', sizeRelHalos);

  // One Tab stop for the whole chart (Stage 26 item 10). Each of the thirty
  // points used to be its own Tab stop, so reaching the table below meant
  // thirty presses through marks a keyboard reader may not want. Roving
  // tabindex: exactly one visible point holds tabindex 0 and is the way in;
  // the arrow keys move through the visible points in drawing order (series
  // by series, bin by bin), Home and End jump to the ends, and a point in a
  // series switched off is skipped and never keeps the Tab stop.
  const points = [...plot.querySelectorAll('.rel-point')];
  const visiblePoints = () => points.filter(p => p.closest('.rel-series').style.display !== 'none');
  function setRoving(el){ points.forEach(p => p.setAttribute('tabindex', p === el ? '0' : '-1')); }
  if(points.length) setRoving(points[0]);

  points.forEach(el=>{
    el.addEventListener('mouseenter', ()=>show(el));
    el.addEventListener('focus', ()=>{ setRoving(el); show(el); });
    el.addEventListener('mouseleave', hide);
    el.addEventListener('blur', hide);
    el.addEventListener('keydown', e=>{
      const vis = visiblePoints(), i = vis.indexOf(el);
      let next = null;
      if(e.key === 'ArrowRight' || e.key === 'ArrowDown') next = vis[Math.min(i + 1, vis.length - 1)];
      else if(e.key === 'ArrowLeft' || e.key === 'ArrowUp') next = vis[Math.max(i - 1, 0)];
      else if(e.key === 'Home') next = vis[0];
      else if(e.key === 'End') next = vis[vis.length - 1];
      if(!next) return;
      e.preventDefault();
      next.focus();   // the focus handler moves the Tab stop with it
    });
  });

  document.querySelectorAll('.rel-toggle').forEach(btn=>{
    btn.addEventListener('click', ()=>{
      const key = btn.dataset.model;
      relVisible[key] = !relVisible[key];
      // Never let the reader turn everything off -- an empty plot reads as a
      // broken chart rather than a chosen filter.
      if(!Object.values(relVisible).some(Boolean)){ relVisible[key] = true; return; }
      btn.setAttribute('aria-pressed', String(relVisible[key]));
      const g = document.querySelector(`.rel-series[data-model="${key}"]`);
      if(g) g.style.display = relVisible[key] ? '' : 'none';
      // The Tab stop never stays on a hidden point, or the chart drops out
      // of the Tab order the moment its series is switched off.
      const holder = points.find(p => p.getAttribute('tabindex') === '0');
      if(!holder || !visiblePoints().includes(holder)) setRoving(visiblePoints()[0]);
      hide();
    });
  });
}

/* The scoreboard's sentence. A pure function of the three records, so the
   harness in tests/test_scoreboard.py can run it over ties, leads and
   unequal game counts without a page. Ranked by games right, not by the
   rounded percentage, because two records that differ by one game can
   print the same percentage. */
function scoreboardVerdict(rows){
  // Every graded game so far a tie: no record exists yet, and "level" would
  // read as three equal records rather than none (Stage 35).
  if(rows.every(r => r.n === 0)) return 'No graded game has a winner yet.';
  const sorted = [...rows].sort((a, b) => b.correct - a.correct);
  const top = sorted[0], gap = top.correct - sorted[1].correct;
  const sameGames = rows.every(r => r.n === rows[0].n);
  const lead = top.subject;
  if(!sameGames) return `${lead} has the best record so far.`;
  if(gap > 0) return `${lead} leads by ${gap} game${gap === 1 ? '' : 's'}.`;
  const level = sorted.filter(r => r.correct === top.correct);
  if(level.length === rows.length) return 'All three are level so far.';
  const names = level.map((r, i) => i === 0 ? r.subject : r.subject.replace(/^The /, 'the '));
  return `${names.join(' and ')} are level at the top.`;
}
/* nGraded is accuracy.n_graded: every game checked against a result, a tie
   included. The rule, since Stage 30 item 1 (tests/test_tie_rendering.py):
   a tie is GRADED -- it has a result -- but DECIDES nothing, so it counts in
   n_graded and in no row's record. Until Stage 35 the eyebrow printed the
   market row's n here, which leaves ties out (and any game saved without a
   market price), so a tie put it one below the calibration text's count of
   graded games. Each row's "N of M" is that row's own decided games.
   A row's pct is null when it has decided nothing yet -- every graded game
   a tie -- and then draws no bar and a dash, never r.pct.toFixed on null. */
function scoreboardHtml(o, mine, leftOut, nGraded){
  const rows = [
    {name: 'Market', subject: 'The betting market', series: 'var(--series-c)', shape: 'tri', ...o.market},
    {name: 'Model B', subject: 'Model B', series: 'var(--series-b)', shape: 'sq', ...o.model_b},
    {name: 'Model A', subject: 'Model A', series: 'var(--series-a)', shape: 'dot', ...o.model_a},
  ];
  const race = [...rows].sort((a, b) => b.correct - a.correct);
  // Graded picks that all came too late, or with no time, still join the
  // race as a row that says so (Stage 37 item 1, Mark's observation in the
  // 2026-10-04 audit): leaving the row out read as the picks being lost.
  if(mine) race.push({name: 'My picks', series: 'var(--series-d)', shape: 'diamond', ...mine});
  else if(leftOut) race.push({name: 'My picks', series: 'var(--series-d)', shape: 'diamond',
                              correct: 0, n: 0, pct: null, noneCounted: true});
  const row = r => `<div class="score-row">
      <div class="score-name"><span class="score-mark ${r.shape}" style="--series:${r.series}" aria-hidden="true"></span>${r.name}</div>
      <div class="score-track" aria-hidden="true"><div class="score-fill" style="--series:${r.series}; width:${r.pct ?? 0}%"></div><div class="score-coin"></div></div>
      <div class="score-figure"><span class="score-pct">${r.pct == null ? '&ndash;' : `${r.pct.toFixed(1)}%`}</span><span class="score-count">${r.noneCounted ? '0 counted' : `${r.correct} of ${r.n}`}</span></div>
    </div>`;
  return `<div class="scoreboard" role="region" aria-label="Season scoreboard">
    <div class="scoreboard-eyebrow">Picked the winner &middot; ${nGraded} game${nGraded === 1 ? '' : 's'} graded</div>
    <div class="scoreboard-verdict">${scoreboardVerdict(rows)}</div>
    ${race.map(row).join('')}
    <div class="score-axis" aria-hidden="true"><span></span><div class="score-axis-track"><span class="coin">50% &middot; a coin flip</span><span class="full">100%</span></div><span></span></div>
    ${mine || leftOut ? '' : '<div class="score-foot">Pick some games on the Week Board to join this race.</div>'}
    ${leftOut ? `<div class="score-foot">${leftOut} Only picks made before kickoff are counted.${mine ? '' : ` ${PICKS_LIVE_HERE}`}</div>` : ''}
  </div>`;
}
/* Season Accuracy's second score (Stage 19): how sure each forecast was, not
   only whether it picked the winner. The numbers are Python's average log
   loss over the games all three forecasts priced (build_forecast_score), and
   null below 50 graded games -- null renders nothing. The words stay plain on
   purpose (Mark, 2026-09-28); Methodology's glossary names the technical
   term. Lowest first, because lower is better. */
function forecastScoreHtml(s){
  if(!s) return '';
  // Shape before series, unlike scoreboardHtml's rows: mutation cases anchor
  // on that function's exact text, and a second copy of it here made one of
  // them match twice.
  const rows = [
    {name: 'Market', shape: 'tri', series: 'var(--series-c)', score: s.market},
    {name: 'Model B', shape: 'sq', series: 'var(--series-b)', score: s.model_b},
    {name: 'Model A', shape: 'dot', series: 'var(--series-a)', score: s.model_a},
  ].sort((a, b) => a.score - b.score);
  const body = rows.map(r => `<tr><td><span class="score-mark ${r.shape}" style="--series:${r.series}" aria-hidden="true"></span>${r.name}</td><td class="num">${r.score.toFixed(3)}</td></tr>`).join('');
  return `
    <div class="method-block forecast-score">
      <h3>How sure, and how right</h3>
      <p>Picking the winner is only half of it. This score also weighs how sure each forecast was: a pick made at 90% that loses costs far more than one made at 55%. <b style="color:var(--text)">Lower is better.</b> Calling every game 50&ndash;50 scores ${s.coin_flip.toFixed(3)}, whatever happens.</p>
      <div class="table-wrap"><table class="metrics-table"><caption class="visually-hidden">Forecast score for each forecast; lower is better</caption>
        <thead><tr><th scope="col">Forecast</th><th scope="col">Score</th></tr></thead>
        <tbody>${body}</tbody>
      </table></div>
      <p style="font-size:var(--fs-12); color:var(--text-2); margin-top:var(--s2);">Over the ${s.n} games all three had a number for. The Methodology page explains how it is worked out.</p>
    </div>`;
}
function renderAccuracy(){
  const el = document.getElementById('accuracy-content');
  if(!accuracy.overall){
    // This is the whole page until the first week of the season is played, so
    // it is written for a reader, not for whoever runs the scripts. The old
    // copy said "Run grade_predictions.py after a week's games finish", which
    // tells a visitor nothing except that something is missing.
    el.innerHTML = stateHtml('waiting', 'Nothing to score yet', [
      `Every pick on this site is saved before kickoff and checked against the
      real result afterwards. No games have been played and graded yet, so there
      is no record to show — and a record built from anything other than
      already-saved picks would not be worth showing.`,
      `This page fills in on its own the day after the first week's games
      finish: how often each model was right, how that changes week to week, and
      whether the confidence numbers turn out to be honest.`], null, 'state--readable');
    return;
  }
  const o = accuracy.overall;

  // My Picks record: only picks made before their game's kickoff are in the
  // race, and the page says how many it left out.
  const mineTally = tallyMyPicks(loadMyPicks(), loadPickTimes(), weekKeysSorted, weeks);
  const myWins = mineTally.wins, myTotal = mineTally.wins + mineTally.losses;
  const myPct = myTotal > 0 ? Math.round(1000*myWins/myTotal)/10 : null;

  const cardsHtml = scoreboardHtml(o, myTotal > 0 ? {correct: myWins, n: myTotal, pct: myPct} : null,
                                   leftOutSentence(mineTally), accuracy.n_graded);

  const cumulativeChartHtml = buildCumulativeTrendChart();

  // Each week names its own board when that week is saved (Stage 26 item 5);
  // a week the page has no board for stays plain text rather than a link to
  // a route that would open something else.
  const weekCell = w => {
    const key = `${w.season}_week${w.week}`, label = `${w.season} Wk ${w.week}`;
    return weekKeysSorted.includes(key)
      ? `<a class="row-link week-link" href="${routeHash({page:'board', week:key})}">${label}</a>` : label;
  };
  const weeklyRows = accuracy.weeks.map(w=>`
    <tr>
      <td>${weekCell(w)}</td>
      <td class="num">${w.model_a_correct}/${w.model_a_n}</td>
      <td class="num">${w.model_b_correct}/${w.model_b_n}</td>
      <td class="num">${w.market_correct}/${w.market_n}</td>
    </tr>`).join('');
  // An empty tbody renders as a header with nothing under it, which reads as a
  // broken table rather than an empty one. Every not-enough-data case on this
  // page now says what it is waiting for.
  const weeklyHtml = `
    <div class="method-block">
      <h3>Week by week</h3>
      ${weeklyRows
        ? `<div class="table-wrap"><table class="metrics-table"><caption class="visually-hidden">Correct picks by week for each model</caption>
        <thead><tr><th scope="col">Week</th><th scope="col">Model A</th><th scope="col">Model B</th><th scope="col">Market</th></tr></thead>
        <tbody>${weeklyRows}</tbody>
      </table></div>`
        : `<p>Nothing graded yet. Each week appears here the day after its games are played.</p>`}
    </div>`;

  const calibChartHtml = buildCalibrationChart();

  // Underpowered rows keep their real counts but the "actual rate" is dimmed
  // and marked, so the number is visible without reading as a result.
  const calibRows = accuracy.calibration.map(c=>{
    const rate = c.underpowered
      ? `<span style="color:var(--text-2);" title="n=${c.n}, below the ${accuracy.min_bucket_n}-game floor -- not a meaningful rate">${c.actual_rate}%&nbsp;*</span>`
      : `${c.actual_rate}%`;
    return `<tr><td>${c.bucket}</td><td class="num">${c.n}</td><td class="num">${c.avg_predicted}%</td><td class="num">${rate}</td></tr>`;
  }).join('');
  const anyUnderpowered = accuracy.calibration.some(c=>c.underpowered);
  const calibFootnote = anyUnderpowered
    ? `<p style="font-size:var(--fs-11); color:var(--text-2); margin-top:var(--s2);">* Fewer than ${accuracy.min_bucket_n} games in this bucket &mdash; the rate is shown for completeness but is not a meaningful measurement.</p>`
    : '';
  const calibHtml = `
    <div class="method-block">
      <h3>Are these percentages honest?</h3>
      <p>Does a game we picked at, say, 65% confidence actually win about 65% of the time? Compares the average predicted probability in each confidence bucket to how often the pick was actually right.</p>
      ${calibChartHtml}
      <div class="table-wrap"><table class="metrics-table"><caption class="visually-hidden">Stated confidence against how often the pick was right, by bucket</caption>
        <thead><tr><th scope="col">Confidence Bucket</th><th scope="col">Games</th><th scope="col">Avg Predicted</th><th scope="col">Actual Correct Rate</th></tr></thead>
        <tbody>${calibRows || '<tr><td colspan="4">Not enough graded games yet.</td></tr>'}</tbody>
      </table></div>
      ${calibFootnote}
    </div>`;

  el.innerHTML = cardsHtml + forecastScoreHtml(accuracy.forecast_score) + cumulativeChartHtml + weeklyHtml + calibHtml;
}
renderAccuracy();

(function mountReliabilityDiagram(){
  const el = document.getElementById('reliability-diagram');
  if(!el) return;
  const html = buildReliabilityDiagram();
  if(!html) return;          // no calibration.json in this build
  el.innerHTML = html;
  initReliabilityDiagram();
})();

/* ---------- Team Deep-Dive ----------

   The listbox handle, kept because this select is the case enhanceSelect's
   refresh() was written for. That function renders the options it can see at
   the moment it runs, and at that moment this select has none -- they are
   written below, from teamHistory, after the page has loaded. So every write
   to select.innerHTML is a moment the listbox is showing something the select
   no longer says, and has to come back through refresh().

   Null until the first render enhances it, which is why every use is guarded
   rather than assumed: the no-data branch runs BEFORE anything is enhanced. */
let teamDiveListbox = null;

/* The team Team Deep-Dive opens on when no #team/<code> link names one
   (Stage 19): the top of Power Ratings, by the rank Python computed for that
   table. It used to be the first option alphabetically -- Arizona, whatever
   Arizona's season. A link still wins: applyRoute() sets the select after
   this. With no rank 1, or a rank 1 the history file has no name for, it
   falls back to that first option, so the page never opens on nothing. */
function teamDiveDefault(names, ratedTeams){
  const top = (ratedTeams || []).find(t => t.rank === 1);
  if(top && Object.prototype.hasOwnProperty.call(names, top.team)) return top.team;
  return Object.keys(names).sort((a, b) => names[a].localeCompare(names[b]))[0];
}

function renderTeamDive(){
  const select = document.getElementById('teamdive-select');
  const content = document.getElementById('teamdive-content');
  const badge = document.getElementById('teamdive-badge');

  if(!teamHistory || !teamHistory.names || Object.keys(teamHistory.names).length === 0){
    content.innerHTML = stateHtml('missing', 'No team history in this build',
      'This page is drawn from a team history file, and the page was built without one. Nothing here is wrong with any team; the file is what is missing.');
    select.innerHTML = '';
    // Without this the button keeps naming whatever team it last rendered,
    // sitting directly above a message saying there is no data. sync() turns
    // an empty select into a disabled button, which is the honest state.
    if(teamDiveListbox) teamDiveListbox.refresh();
    badge.textContent = '—';
    return;
  }

  if(select.options.length === 0){
    const sortedTeams = Object.keys(teamHistory.names).sort((a,b)=>teamHistory.names[a].localeCompare(teamHistory.names[b]));
    select.innerHTML = sortedTeams.map(t=>`<option value="${t}">${teamHistory.names[t]} (${t})</option>`).join('');
    // Before the listbox is built, so its button names the same team.
    select.value = teamDiveDefault(teamHistory.names, teams);
    select.addEventListener('change', renderTeamDive);
    /* AFTER the change listener, never before -- the same ordering the Week
       Board's call site documents, and for the same reason. enhanceSelect
       writes back by dispatching change on the select, so a listbox built
       first would dispatch into a listener that does not exist yet: the
       button would update, the list would close, and the page below it would
       go on showing the previous team, with every source-reading test green.

       `|| teamDiveListbox` because enhanceSelect returns null for a select it
       has already enhanced. Nothing re-enters this branch today, since the
       sentinel above is the option count and teamHistory does not change
       after load -- but assigning that null would silently discard a working
       handle, and the symptom would be a listbox that stops refreshing. */
    teamDiveListbox = enhanceSelect(select) || teamDiveListbox;
  }

  const team = select.value || select.options[0]?.value;
  const points = (teamHistory.timeline[team] || []);
  badge.textContent = `${points.length} data point${points.length===1?'':'s'}`;

  if(points.length === 0){
    content.innerHTML = stateHtml('waiting', `No history for ${team} yet`,
      'This team has no rated seasons or weeks on record so far.');
    return;
  }

  const maxAbs = Math.max(...points.map(p=>Math.abs(p.net)), 0.0001);
  const rowsHtml = points.map(p=>{
    const width = (Math.abs(p.net)/maxAbs)*100;
    const isLive = p.label.includes('Wk');
    return `<div class="dive-row">
      <span class="dive-label ${isLive?'live':''}">${p.label}</span>
      <div class="srs-bar-track diverging" style="width:140px;" title="${fmtRating(p.net)} per 100 plays; scale ±${fmtRatingScale(maxAbs)} across this team's own history, centre line is zero"><div class="srs-bar-fill" style="left:${p.net>=0?50:50-width/2}%; width:${width/2}%;"></div></div>
      <span class="dive-value">${fmtRating(p.net)}</span>
      ${diveSplitHtml(p)}
    </div>`;
  }).join('');
  // Said once above the rows, not in every row: defense is the one number
  // on the page that runs backwards (Mark, 2026-09-28).
  const splitNote = points.some(p => diveSplitHtml(p))
    ? `<p class="dive-note">Net is offense minus defense. Defense counts expected points allowed, so for defense lower is better.</p>`
    : '';

  content.innerHTML = diveTeamHtml(team, teamHistory.names[team]) + renderTeamNews(team)
    + `<div class="table-wrap" style="padding:var(--s5) var(--s5);">${splitNote}${rowsHtml}</div>`
    + renderTeamGames(team);
  wireTeamGameToggles();
}

/* Which team the page is showing, as a logo and the full name above
   everything else (Mark, 2026-09-28: it re-establishes whose page this is).
   The logo is decorative, alt="", because the name beside it is the text; a
   logo ESPN will not serve hides and leaves the name, the fallback every
   logo here has. */
function diveTeamHtml(team, name){
  return `<div class="dive-team"><img class="dive-logo" src="${teamLogo(team)}" alt="" loading="lazy" referrerpolicy="no-referrer" onerror="this.style.display='none'">`
    + `<span class="dive-team-name">${name || team}</span></div>`;
}

/* Offense and defense beside a Team Deep-Dive row's net (Stage 19), in the
   same per-100-plays units through the same formatter. Nothing unless both
   are numbers -- a history point can carry net alone. On a phone the pair
   drops to a second small line under the row (CSS, below 768px). */
function diveSplitHtml(p){
  if(typeof p.off !== 'number' || typeof p.def !== 'number') return '';
  return `<span class="dive-split"><span>Offense ${fmtRating(p.off)}</span><span title="Expected points allowed: lower is better">Defense ${fmtRating(p.def)}</span></span>`;
}

/* ---------- Team Deep-Dive: this week's team news (Stage 16) ----------

   src/sports/nfl/team_news.py writes, per locked week not yet graded, each team's
   starters listed Out or Doubtful, a count of those Questionable, and the
   quarterback the saved pick was made with. generate_dashboard.py attaches
   that to weeks[k].news only while the week is still being played, so an item
   expires with its week without anything here checking dates.

   Short on purpose (CLAUDE.md Stage 16): one line per kind of news, never
   more than five, each with its source and date. ABSENT IS NOT HEALTHY: a
   report not yet out says so, and never renders as "nobody hurt". */
function newsWeekKey(){
  const keys = weekKeysSorted.filter(k => weeks[k].news && weeks[k].news.teams);
  return keys.length ? keys[keys.length - 1] : null;
}

function newsDate(iso){
  if(!iso) return null;
  const d = new Date(iso);
  if(isNaN(d)) return null;
  return d.toLocaleDateString('en-US', {timeZone:'America/New_York', weekday:'short', month:'short', day:'numeric'});
}

// [{text, source}] for one team's entry, most important first. Plain text;
// the renderer escapes it.
function teamNewsItems(entry, week, readAt){
  const items = [];
  const read = newsDate(readAt);
  const report = `Official injury report, via nflverse${read ? ` · read ${read}` : ''}`;
  const people = list => list.map(p => {
    const bits = [p.position, p.injury ? p.injury.toLowerCase() : null].filter(Boolean);
    return bits.length ? `${p.name} (${bits.join(', ')})` : p.name;
  }).join(', ');

  const qb = entry.qb;
  if(qb && qb.name){
    // The pick's quarterback on the injury report is the one line that
    // changes how far to trust the pick, so it replaces the usual QB line
    // rather than sitting two lines below it looking unrelated.
    const listed = (entry.out || []).some(p => p.name === qb.name) ? 'out'
      : (entry.doubtful || []).some(p => p.name === qb.name) ? 'doubtful' : null;
    items.push({
      text: listed
        ? `The model's pick was made with ${qb.name} at quarterback, and he is listed as ${listed}.`
        : qb.changed_from
        ? `New starting quarterback: ${qb.name}, in place of ${qb.changed_from}.`
        : `Quarterback: ${qb.name}, the same starter as last game.`,
      source: `The quarterback the model's week ${week} pick was made with`,
    });
  }

  if(entry.injury_report === 'not yet published'){
    items.push({text: `The week ${week} injury report is not out yet, so there is no injury news.`, source: report});
  } else if(entry.injury_report !== 'published'){
    items.push({text: `Starters could not be checked: there is no depth chart for this team.`,
                source: `nflverse depth charts${read ? ` · read ${read}` : ''}`});
  } else {
    const out = entry.out || [], doubtful = entry.doubtful || [];
    const q = entry.questionable_starters || 0;
    if(out.length) items.push({text: `Out: ${people(out)}.`, source: report});
    if(doubtful.length) items.push({text: `Doubtful: ${people(doubtful)}.`, source: report});
    if(q) items.push({text: `${q} starter${q === 1 ? '' : 's'} listed as questionable.`, source: report});
    if(!out.length && !doubtful.length && !q){
      items.push({text: 'No starters listed as out, doubtful or questionable.', source: report});
    }
  }
  return items;
}

function renderTeamNews(team){
  const key = newsWeekKey();
  const head = sub => `<div class="dive-news"><h3 class="dive-news-title">This week</h3>
    <div class="dive-news-sub">${sub}</div>`;
  if(!key){
    return head(`No team news right now. It appears once a week's picks are locked,
      and goes when that week has been graded.`) + `</div>`;
  }
  const w = weeks[key];
  const entry = w.news.teams[team];
  const game = (w.games || []).find(g => g.home === team || g.away === team);
  if(!entry || !game){
    return head(`${escapeHtml(team)} have no game in week ${w.week}.`) + `</div>`;
  }
  const where = game.home === team ? `vs ${escapeHtml(game.away)}` : `@ ${escapeHtml(game.home)}`;
  const rows = teamNewsItems(entry, w.week, w.news.read_at).map(it =>
    `<li class="dive-news-item"><span class="dive-news-text">${escapeHtml(it.text)}</span>
      <span class="dive-news-src">${escapeHtml(it.source)}</span></li>`).join('');
  return head(`Week ${w.week}, ${where}. Starters only; backups are left out to keep this short.`)
    + `<div class="table-wrap"><ul class="dive-news-list">${rows}</ul></div></div>`;
}

/* ---------- Team Deep-Dive: game drill-down ----------

   The net-rating history above answers "how good has this team been". This
   answers "what did the model actually say about their games, and was it
   right" -- which is the question the ratings are only a proxy for.

   Everything in `weeks` is stored from the HOME team's point of view: fbA_home
   and mktB_home are home win probabilities, spread_line is the home team's
   line (positive when home is favoured, asserted at runtime in
   ats_evaluation.py), and why{} holds contributions toward the home side. A
   page built around one selected team has to flip all of it, and getting a
   flip wrong is invisible: every number still looks like a plausible number.
   So the flip happens once, here, and tests/test_team_dive.py checks it
   against the away side of a real game rather than trusting it. */
// null/undefined stay null (not graded); everything else becomes a real
// boolean. Keeps "was the model right" a tri-state rather than collapsing
// "not graded yet" into "wrong".
function asBool(v){
  return (v === null || v === undefined) ? null : !!v;
}

function teamGamesFor(team){
  const out = [];
  weekKeysSorted.forEach(k=>{
    (weeks[k].games || []).forEach(g=>{
      if(g.home !== team && g.away !== team) return;
      const isHome = g.home === team;
      const flipPct = p => (p===null||p===undefined) ? null : (isHome ? p : 100 - p);
      out.push({
        weekKey: k,
        label: weekLabel(k),
        isHome,
        opponent: isHome ? g.away : g.home,
        probA: flipPct(g.fbA_home),
        probB: flipPct(g.mktB_home),
        line: (g.spread===null||g.spread===undefined) ? null : (isHome ? g.spread : -g.spread),
        graded: !!g.graded,
        // actual_home_win is the home side's result, so the selected team won
        // when it IS the home side and that is true, or when it is not and
        // that is false.
        won: (g.graded && g.actual_home_win !== null && g.actual_home_win !== undefined)
              ? (isHome ? !!g.actual_home_win : !g.actual_home_win) : null,
        // A graded game with no winner: Team Deep-Dive says "Tie", not "not
        // yet played" (Stage 30 item 1).
        tie: !!g.graded && g.result === 'tie',
        // Normalised to real booleans here, at the boundary, because the
        // graded files store 1/0 rather than true/false. A downstream
        // `=== true` against a 1 is quietly false, which showed up as
        // "Model A called 0 of 1" beside a game the model had plainly won,
        // and as the correct/wrong marks silently not rendering at all.
        modelACorrect: asBool(g.model_a_correct),
        modelBCorrect: asBool(g.model_b_correct),
        // Contributions point toward the HOME team, so they negate for an
        // away view -- a +0.10 edge for the home side is a -0.10 edge here.
        why: g.why ? Object.fromEntries(Object.entries(g.why)
              .map(([k2, v]) => [k2, isHome ? v : -v])) : null,
      });
    });
  });
  return out;
}

const WHY_LABELS = {off_matchup: 'Offense', def_matchup: 'Defense',
                    qb_matchup: 'QB', qb_change: 'QB change'};

/* One game's result on Team Deep-Dive: W, L, T for a tie, or "not yet
   played". A tie used to read as unplayed because its won is null. */
function diveResultHtml(g){
  if(g.tie) return `<span class="dive-result tie">T</span>`;
  if(g.won === null) return `<span class="dive-pending">not yet played</span>`;
  return `<span class="dive-result ${g.won?'won':'lost'}">${g.won?'W':'L'}</span>`;
}

/* The line above a team's games: its record over graded games, with ties
   as a third figure (W-L-T), and how many each model called. A tie has no
   winner, so it is in the record but not in either model's count. */
function diveSummaryHtml(team, games){
  const decided = games.filter(g => g.won !== null);
  const wins = decided.filter(g => g.won).length;
  const ties = games.filter(g => g.tie).length;
  const n = decided.length + ties;
  if(!n) return `<div class="dive-games-summary">None of these games have been graded yet,
       so there is no record to report.</div>`;
  const aRight = decided.filter(g => g.modelACorrect === true).length;
  const bRight = decided.filter(g => g.modelBCorrect === true).length;
  return `<div class="dive-games-summary">${team} are <b>${wins}-${decided.length-wins}${ties ? '-' + ties : ''}</b>
       across ${n} graded game${n===1?'':'s'} &middot;
       Model A called ${aRight} of ${decided.length} &middot;
       Model B called ${bRight} of ${decided.length}</div>`;
}

function renderTeamGames(team){
  const games = teamGamesFor(team);
  if(games.length === 0){
    // Distinct from "no history": the ratings chart above is backtested and
    // goes back to 2020, while saved per-game predictions only start when the
    // weekly routine does. An empty list here is normal, not broken.
    return stateHtml('note', `No saved predictions for ${team} yet.`,
      `The rating history above is replayed from past seasons; this list only covers weeks the
      live weekly run has actually saved predictions for, so it fills in from
      the first run of the season onward.`, null, 'state--after');
  }

  const summary = diveSummaryHtml(team, games);

  const rows = games.map((g, i) => {
    const pct = p => p===null ? '—' : `${p.toFixed(1)}%`;
    const lineText = g.line===null ? '—'
      : (g.line > 0 ? `-${g.line}` : (g.line < 0 ? `+${Math.abs(g.line)}` : 'PK'));
    const result = diveResultHtml(g);
    const mark = c => c === true ? '<span class="dive-tick">correct</span>'
      : c === false ? '<span class="dive-cross">wrong</span>' : '';

    const whyHtml = g.why
      ? Object.entries(g.why)
          .map(([k, v]) => whyRow(WHY_LABELS[k] || k, v)).join('')
      : `<div class="why-row"><span class="why-label">No breakdown</span></div>`;

    return `<div class="dive-game" data-i="${i}">
      <button class="dive-game-head" aria-expanded="false" data-toggle="${i}">
        <span class="dive-game-week">${g.label}</span>
        <span class="dive-game-opp">${g.isHome ? 'vs' : '@'} ${g.opponent}</span>
        <span class="dive-game-line"><span class="visually-hidden">Line </span>${lineText}</span>
        <span class="dive-game-prob" title="Model B win probability for ${team}"><span class="visually-hidden">Model B </span>${pct(g.probB)}</span>
        <span class="dive-game-res"><span class="visually-hidden">Result </span>${result}</span>
      </button>
      <div class="why-panel" id="dive-why-${i}">
        <div class="dive-why-head">
          Model A gave ${team} ${pct(g.probA)} ${mark(g.modelACorrect)} &middot;
          Model B gave ${team} ${pct(g.probB)} ${mark(g.modelBCorrect)}
        </div>
        <div class="dive-why-note">Contributions shown from ${team}'s side. Positive helps ${team}.</div>
        ${whyHtml}
      </div>
    </div>`;
  }).join('');

  return `<div class="dive-games">
    <h3 class="dive-games-title">Games</h3>
    ${summary}
    <div class="table-wrap">
      <div class="dive-games-head" aria-hidden="true">
        <span class="dgh-week">Week</span><span class="dgh-opp">Opponent</span>
        <span class="dgh-line">Line</span><span class="dgh-prob" title="Model B win probability for ${team}">Model B</span>
        <span class="dgh-res">Result</span>
      </div>
      ${rows}
    </div>
  </div>`;
}

function wireTeamGameToggles(){
  document.querySelectorAll('#teamdive-content .dive-game-head').forEach(btn=>{
    btn.addEventListener('click', ()=>{
      const panel = document.getElementById('dive-why-' + btn.dataset.toggle);
      if(!panel) return;
      const open = panel.classList.toggle('open');
      btn.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
  });
}
// Called here, below WHY_LABELS, and not up beside the function definition.
// WHY_LABELS is a const, so a call placed before it sits in the temporal dead
// zone and throws the moment a team has games to render. The first draft
// dropped this call entirely while moving code around, which was silent: the
// select simply stayed empty and nothing errored.
renderTeamDive();

/* ---------- Changelog ---------- */
// Escaped (escapeHtml) rather than interpolated raw: this text comes out of config.py,
// which is a source file people edit by hand, and an unescaped '<' in a
// release note would silently break the page it is describing.

/* ---------- Booth's audit log (Checking the AI's work) ---------- */
function renderAgentLog(){
  const el = document.getElementById('agent-log');
  if(!el) return;
  // null means the collector has never run. That is NOT the same as "audits
  // ran and found nothing", and the page must not let the reader read the
  // second from the first -- it is the more flattering of the two.
  if(!agentLog || !agentLog.summary){
    el.innerHTML = stateHtml('missing', 'The record has not been collected yet',
      `The audits below were written by hand. The automatic tally of every
      audit this project's verifier has run is produced by a workflow that has
      not been run yet, so rather than show an empty scoreboard this section
      says so.`);
    return;
  }
  const s = agentLog.summary;
  const stat = (n, label, note) => `<div class="agent-stat">
      <div class="agent-stat-n">${n}</div>
      <div class="agent-stat-l">${label}</div>
      ${note ? `<div class="agent-stat-note">${note}</div>` : ''}
    </div>`;
  el.innerHTML = `<div class="method-block">
    <h3>What the checking has actually caught</h3>
    <p>Every pull request in this project is reviewed a second time by a
    separate agent whose only job is to check whether what the first one
    claimed is true. These numbers are counted from those reviews, not
    written by hand.</p>
    <div class="agent-stats">
      ${stat(s.pull_requests_audited, 'changes reviewed')}
      ${stat(s.claims_checked, 'claims checked one by one')}
      ${stat(s.discrepancies_found, 'claims that turned out to be wrong',
             s.pull_requests_with_a_discrepancy + ' of the reviews found at least one')}
      ${stat(s.unverifiable, 'claims that could not be checked either way')}
    </div>
    <p style="margin-top:var(--s4);">${s.audits_without_a_verdict_block} review${s.audits_without_a_verdict_block===1?'':'s'}
    ${s.audits_without_a_verdict_block===1?'was':'were'} written before the checker started
    reporting in a fixed format, so ${s.audits_without_a_verdict_block===1?'it is':'they are'}
    counted here but ${s.audits_without_a_verdict_block===1?'its':'their'} findings are not.
    ${s.reports_disagreeing_with_themselves} review${s.reports_disagreeing_with_themselves===1?'':'s'}
    disagreed with ${s.reports_disagreeing_with_themselves===1?'itself':'themselves'} &mdash; the
    summary said one thing and the detail said another &mdash; which is recorded rather than
    quietly corrected.</p>
    <p class="rel-prov">${s.audits_total} review${s.audits_total===1?'':'s'} in total,
    ${s.audits_superseded} of them replaced by a later run of the same review and not counted.
    Collected ${agentLog.generated_utc || 'unknown'}.</p>
  </div>`;
}

/* ---------- The scheduled jobs, run by run (Stage 41 item 4) ---------- */
const RUN_RESULTS = {success: 'Finished', failure: 'Failed', cancelled: 'Cancelled',
  skipped: 'Skipped', timed_out: 'Timed out'};
function runResultText(r){
  return r.conclusion == null ? 'Running' : (RUN_RESULTS[r.conclusion] || r.conclusion);
}
function runTriggerText(r){
  if(r.event === 'schedule') return 'GitHub&#39;s timer';
  if(r.event === 'workflow_dispatch') return 'Requested';
  return escapeHtml(String(r.event || 'unknown'));
}
function runStartedText(iso){
  if(!iso) return 'unknown';
  return new Date(iso).toLocaleString('en-US', {timeZone: 'America/New_York',
    month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit'});
}
function renderRecentRuns(){
  const el = document.getElementById('recent-runs');
  if(!el) return;
  // null: this build did not read the history (any build but the deploy, or
  // a deploy whose read failed). Not the same as "nothing ran".
  if(!recentRuns || !Array.isArray(recentRuns.runs)){
    el.innerHTML = stateHtml('missing', 'The run history was not read for this build',
      `The list of recent scheduled runs is read from GitHub when the site is
      published. This copy of the page was built without it, so rather than
      show an empty table this section says so.`);
    return;
  }
  const runs = recentRuns.runs;
  const failed = runs.filter(r => r.conclusion === 'failure' || r.conclusion === 'timed_out').length;
  const body = runs.map(r => `<tr>
      <td>${escapeHtml(r.workflow)}<div style="font-size:var(--fs-12); color:var(--text-2);">${runTriggerText(r)}</div></td>
      <td>${runStartedText(r.started_utc)}</td>
      <td>${r.url ? `<a class="row-link" href="${escapeHtml(r.url)}" style="color:var(--accent); text-decoration:underline;">${runResultText(r)}</a>` : runResultText(r)}</td>
      <td class="num">${r.minutes == null ? '&ndash;' : r.minutes.toFixed(1)}</td>
    </tr>`).join('');
  el.innerHTML = `<div class="method-block">
    <h3>The scheduled jobs, run by run</h3>
    <p>The picks are locked, graded and checked by jobs that run on a timer with
    nobody watching. These are their last ${runs.length} runs, read from GitHub when
    this page was published: ${failed === 0 ? 'none failed' :
      failed + ' failed'}. GitHub&#39;s own timer has started jobs hours late, so
    since October 4 an outside service also asks for each run at its scheduled
    time; those show as &ldquo;Requested&rdquo;, as does a run started by hand.
    Times are Eastern.</p>
    ${runs.length ? `<div class="table-wrap" data-scroll-label="Recent scheduled runs"><table class="metrics-table">
      <caption class="visually-hidden">The last scheduled runs, newest first</caption>
      <thead><tr><th scope="col">Job</th><th scope="col">Started</th>
      <th scope="col">Result</th><th scope="col">Min</th></tr></thead>
      <tbody>${body}</tbody>
    </table></div>` : stateHtml('note', 'No runs yet.', 'GitHub returned no runs for these jobs.')}
    <p class="rel-prov">Read ${escapeHtml(recentRuns.read_utc || 'at an unknown time')} (UTC).
    Each result links to that run on GitHub.</p>
  </div>`;
}

function renderChangelog(){
  const content = document.getElementById('changelog-content');
  const badge = document.getElementById('changelog-badge');
  if(!content) return;

  if(!versionHistory || !versionHistory.length){
    content.innerHTML = stateHtml('missing', 'No version history in this build',
      'The list of model versions is read from the project&#39;s settings file when the page is built, and this build found none.');
    if(badge) badge.textContent = '—';
    return;
  }
  if(badge){
    badge.textContent = versionHistory.length + ' version' + (versionHistory.length===1?'':'s');
  }

  content.innerHTML = `<div class="method-block">` + versionHistory.map(v => {
    // The badge is derived, not stored: whichever entry matches the version
    // the model is actually running is the current one. Storing a flag would
    // let the page mark a release "current" that config.py disagrees with.
    const isCurrent = v.version === modelVersion;
    return `<div class="cl-entry">
      <div class="cl-meta">
        <span class="cl-version">v${escapeHtml(v.version)}</span>
        <span class="cl-date">${escapeHtml(v.date)}</span>
        ${isCurrent ? '<span class="cl-current">Running now</span>' : ''}
      </div>
      <div>
        <div class="cl-headline">${escapeHtml(v.headline)}</div>
        <div class="cl-detail">${escapeHtml(v.detail)}</div>
      </div>
    </div>`;
  }).join('') + `</div>`;
}
renderAgentLog();
renderRecentRuns();
renderChangelog();

/* ---------- Hash routes (Stage 13) ----------
   Every page, a Week Board week, a team and a Model Lab experiment have an
   address, so a link can point at one and the back button steps between
   pages:

     #board               the Week Board, latest week
     #board/2026_week2    the Week Board at that week
     #team/KC             Team Deep-Dive on that team
     #modellab/<slug>     Model Lab, scrolled to that experiment's row
     #ratings, #picks, #accuracy, #teamdive, #modellab, #method,
     #changelog, #reliability

   They coexist with share links: anything carrying `picks=` belongs to
   readSharedPicksFromUrl() and is never read as a route, and while a shared
   view is up the address is left alone. A hash that is not a route -- the
   Methodology page's own jump links (#part-method) are the live case -- is
   ignored rather than bounced to a page. A route naming a week, team or
   experiment that does not exist opens the page without it.

   A page change adds a history entry (pushState); a week or team change
   inside a page replaces the current one, so stepping through eight weeks
   does not cost eight presses of Back. Nothing writes a hash at load: an
   address with none still opens on the Week Board.

   parseRoute and routeHash are pure, so the suite runs them under node. */
const ROUTE_PAGES = ['board','ratings','teamdive','picks','accuracy','modellab','method','changelog','reliability'];
function parseRoute(hash, known){
  const raw = String(hash || '').replace(/^#/, '');
  if(/(^|&)picks=/.test(raw)) return null;
  if(raw === '') return {page:'board'};
  const slash = raw.indexOf('/');
  const head = slash === -1 ? raw : raw.slice(0, slash);
  let arg = slash === -1 ? '' : raw.slice(slash + 1);
  try{ arg = decodeURIComponent(arg); }catch(e){ arg = ''; }
  if(head === 'team') return known.teams.includes(arg) ? {page:'teamdive', team:arg} : {page:'teamdive'};
  if(!ROUTE_PAGES.includes(head)) return null;
  if(head === 'board' && known.weeks.includes(arg)) return {page:'board', week:arg};
  if(head === 'modellab' && known.experiments.includes(arg)) return {page:'modellab', experiment:arg};
  return {page:head};
}
function routeHash(r){
  if(r.page === 'teamdive' && r.team) return '#team/' + encodeURIComponent(r.team);
  if(r.page === 'board' && r.week) return '#board/' + encodeURIComponent(r.week);
  if(r.page === 'modellab' && r.experiment) return '#modellab/' + encodeURIComponent(r.experiment);
  return '#' + r.page;
}
function experimentSlug(text){
  return String(text).toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '')
    .slice(0, 48).replace(/-+$/, '');
}

/* ---------- Model Lab: filter by decision (Stage 18) ----------
   One chip per decision the table actually holds, in a fixed order, each
   with its count, plus All and the leakage flag. Counted from the rendered
   rows rather than carried separately, so a chip can never promise rows the
   table does not have. A row's decision is its first tag; the leakage flag
   is a second tag reading LEAKAGE. */
const LAB_DECISIONS = ['ACCEPT', 'CONFIRMED FINDING', 'INCONCLUSIVE', 'REJECT', 'DEFERRED'];

function labChips(rows){
  const chips = [{key:'all', label:'All', n: rows.length}];
  LAB_DECISIONS.forEach(d => {
    const n = rows.filter(r => r.decision === d).length;
    if(n) chips.push({key: d, label: d.charAt(0) + d.slice(1).toLowerCase(), n});
  });
  const leak = rows.filter(r => r.leakage).length;
  if(leak) chips.push({key:'leakage', label:'Leakage', n: leak});
  return chips;
}

function labRowMatches(row, key){
  return key === 'all' || (key === 'leakage' ? row.leakage : row.decision === key);
}

let labShowAll = null;

(function wireLabFilters(){
  const bar = document.getElementById('lab-filter-row');
  const status = document.getElementById('lab-filter-status');
  const trs = Array.from(document.querySelectorAll(
    '#page-modellab .table-wrap[data-scroll-label="Experiment log"] tbody tr'));
  if(!bar || !trs.length) return;
  const rows = trs.map(tr => {
    const tags = Array.from(tr.querySelectorAll('td:last-child .conf-tag')).map(s => s.textContent.trim());
    return {tr, decision: tags[0], leakage: tags.includes('LEAKAGE')};
  });
  const chips = labChips(rows);
  bar.innerHTML = chips.map(c =>
    `<button type="button" class="btn btn-chip lab-filter${c.key === 'all' ? ' active' : ''}" data-decision="${c.key}"` +
    ` aria-pressed="${c.key === 'all' ? 'true' : 'false'}">${c.label}<span class="chip-n">${c.n}</span></button>`).join('');
  bar.hidden = false;
  function show(key){
    let shown = 0;
    rows.forEach(r => { const on = labRowMatches(r, key); r.tr.hidden = !on; if(on) shown++; });
    bar.querySelectorAll('.lab-filter').forEach(b => {
      const on = b.dataset.decision === key;
      b.classList.toggle('active', on);
      b.setAttribute('aria-pressed', on ? 'true' : 'false');
    });
    if(status) status.textContent = `Showing ${shown} of ${rows.length} experiments.`;
  }
  bar.addEventListener('click', e => {
    const b = e.target.closest('.lab-filter');
    if(b) show(b.dataset.decision);
  });
  labShowAll = () => show('all');
})();

/* Model Lab's experiment rows are static markup with no ids; each gets one
   from its first cell, made unique if two names slug alike. */
const routeKnown = (function(){
  const experiments = [];
  document.querySelectorAll('#page-modellab .table-wrap[data-scroll-label="Experiment log"] tbody tr').forEach(tr=>{
    const first = tr.querySelector('td');
    if(!first) return;
    let slug = experimentSlug(first.textContent), n = 2;
    while(experiments.includes(slug)) slug = experimentSlug(first.textContent) + '-' + n++;
    experiments.push(slug);
    tr.id = 'exp-' + slug;
  });
  const teams = (teamHistory && teamHistory.names) ? Object.keys(teamHistory.names) : [];
  return {weeks: weekKeysSorted.slice(), teams, experiments};
})();

function currentRoute(page){
  if(page === 'board') return {page, week: currentBoardWeek !== latestWeekKey ? currentBoardWeek : undefined};
  if(page === 'teamdive'){
    const s = document.getElementById('teamdive-select');
    return {page, team: (s && s.value) || undefined};
  }
  return {page};
}
function inSharedView(){ return /[#&]picks=/.test(location.hash || ''); }
function routeUrl(r){ return location.pathname + location.search + routeHash(r); }

function goToPage(page){
  setActivePage(page, {focus:true});
  if(inSharedView()) return;
  const url = routeUrl(currentRoute(page));
  if(location.pathname + location.search + location.hash !== url) history.pushState(null, '', url);
}
function replaceRoute(page){
  const active = document.querySelector('.page.active');
  if(inSharedView() || !active || active.id !== 'page-' + page) return;
  history.replaceState(null, '', routeUrl(currentRoute(page)));
}

function applyRoute(r, opts){
  if(!r || !document.getElementById('page-' + r.page)) return;
  const active = document.querySelector('.page.active');
  if(!active || active.id !== 'page-' + r.page) setActivePage(r.page, opts);
  if(r.page === 'board'){
    const s = document.getElementById('week-select');
    const want = r.week || latestWeekKey;
    if(s && want && s.value !== want){ s.value = want; s.dispatchEvent(new Event('change')); }
  }
  if(r.team){
    const s = document.getElementById('teamdive-select');
    if(s && s.value !== r.team){ s.value = r.team; s.dispatchEvent(new Event('change')); }
  }
  document.querySelectorAll('tr.route-target').forEach(tr => tr.classList.remove('route-target'));
  if(r.experiment){
    const row = document.getElementById('exp-' + r.experiment);
    // A link to a row the decision filter is hiding clears the filter
    // first, or it would scroll to nothing.
    if(row && row.hidden && labShowAll) labShowAll();
    if(row){
      row.classList.add('route-target');
      row.setAttribute('tabindex', '-1');
      row.scrollIntoView({block:'center'});
      row.focus({preventScroll:true});
    }
  }
}

(function wireRoutes(){
  const week = document.getElementById('week-select');
  if(week) week.addEventListener('change', ()=> replaceRoute('board'));
  const team = document.getElementById('teamdive-select');
  if(team) team.addEventListener('change', ()=> replaceRoute('teamdive'));
  // popstate covers Back and Forward, and a fragment typed or pasted into the
  // address bar of an open tab.
  window.addEventListener('popstate', ()=> applyRoute(parseRoute(location.hash, routeKnown), {focus:true}));
  if(location.hash) applyRoute(parseRoute(location.hash, routeKnown));
})();
