/* The Settings sheet and the keyboard shortcuts (Stage 80 item 57, the
   2026-10-13 UI/UX audit's F10 and F11; Mark chose both as mocked on
   2026-10-14). Settings: the theme (light, dark or the device's), times in
   Eastern or the visitor's own zone (src/core/prefs.js), full or compact
   cards, the page the site opens on, and the tips dismissed, shown again.
   Each choice is kept in this browser under a site: key every page reads.
   "?" shows the shortcuts; Esc closes either.

   The site build puts this script on every page with a [data-settings-open]
   button (src/site/build.py add_sheet); a page built on its own keeps the
   buttons hidden. Its globals are SHEET_SETTINGS, SHEET_TIPS, SHEET_TOUR and
   SHEET_OLD_THEMES,
   the keys it writes, which the suite reads; everything else is inside the function. */
const SHEET_SETTINGS = [
  {key: 'site:theme', label: 'Theme', note: '', reload: true,
   options: [['light', 'Light'], ['dark', 'Dark'], [null, 'Device']]},
  {key: 'site:tz', label: 'Times', note: 'Every kickoff, puck drop and tip-off', reload: true,
   options: [['local', 'Your time'], [null, 'Eastern']]},
  {key: 'site:cards', label: 'Cards', note: 'Compact shows the pick and the bar only', reload: false,
   options: [[null, 'Full'], ['compact', 'Compact']]},
  // Stage 80 item 64 (V4).
  {key: 'site:density', label: 'Spacing', note: 'Compact fits more on a screen', reload: false,
   options: [[null, 'Comfortable'], ['compact', 'Compact']]},
  {key: 'site:start', label: 'Open the site on', note: '', reload: false,
   options: [[null, 'Home'], ['nfl', 'NFL'], ['nhl', 'NHL'], ['nba', 'NBA']]},
];
/* What "Show them again" forgets: each tip's "dismissed" key; and it asks
   for the first-visit tour once more (site:tour, src/dashboard/app.js). */
const SHEET_TIPS = ['nfl_pickem_onboarding_dismissed'];
const SHEET_TOUR = 'site:tour';
/* The theme's keys from before it was shared (Stage 59): the device's choice
   clears them too, or a page would fall back on one. */
const SHEET_OLD_THEMES = ['nfl_pickem_theme', 'nhl:theme', 'nba:theme'];
(function(){
  const openers = [...document.querySelectorAll('[data-settings-open]')];
  if(!openers.length) return;
  const get = k => { try{ return localStorage.getItem(k); }catch(e){ return null; } };
  const put = (k, v) => { try{ if(v === null) localStorage.removeItem(k); else localStorage.setItem(k, v); }catch(e){} };
  const esc = s => String(s).replace(/[&<>"]/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]));

  function settingsHtml(){
    return SHEET_SETTINGS.map((s, i) => {
      const now = get(s.key);
      const on = s.options.some(([v]) => v === now) ? now : null;
      return `<div class="sheet-row"><span id="sheet-l-${i}">${esc(s.label)}${s.note ? `<small>${esc(s.note)}</small>` : ''}</span>`
        + `<span class="sheet-seg" role="group" aria-labelledby="sheet-l-${i}">`
        + s.options.map(([v, label]) => `<button type="button" data-set="${i}" data-value="${v === null ? '' : esc(v)}" aria-pressed="${v === on}">${esc(label)}</button>`).join('')
        + '</span></div>';
    }).join('')
      + '<div class="sheet-row"><span id="sheet-l-tips">Tips you dismissed<small>The "New here?" note and the guides</small></span>'
      + '<button type="button" class="btn" data-tips aria-describedby="sheet-l-tips">Show them again</button></div>'
      + '<p class="sheet-status" role="status"></p>'
      + '<div class="sheet-foot"><button type="button" class="btn btn-link" data-keys>Keyboard shortcuts</button></div>';
  }
  const KEYS = [['<kbd>/</kbd> or <kbd>Ctrl</kbd> <kbd>K</kbd>', 'Search teams, games and pages'],
                ['<kbd>[</kbd> <kbd>]</kbd>', 'Previous and next week (NFL), day (NHL, NBA)'],
                ['<kbd>Shift</kbd> <kbd>[</kbd> <kbd>]</kbd>', 'Previous and next week on a day board'],
                ['<kbd>?</kbd>', 'This list'],
                ['<kbd>Esc</kbd>', 'Close a sheet or a card']];
  function keysHtml(){
    return `<dl class="sheet-keys">${KEYS.map(([k, what]) => `<dt>${k}</dt><dd>${what}</dd>`).join('')}</dl>`;
  }

  const shell = document.createElement('div');
  shell.className = 'sheet-shell';
  shell.hidden = true;
  shell.innerHTML = '<div class="sheet-scrim" data-sheet-close></div>'
    + '<div class="sheet-dialog" role="dialog" aria-modal="true" aria-labelledby="sheet-title">'
    + '<div class="sheet-head"><h2 id="sheet-title"></h2><button type="button" class="sheet-x" data-sheet-close aria-label="Close">'
    + '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18"/></svg></button></div>'
    + '<div class="sheet-body"></div></div>';
  document.body.appendChild(shell);
  const title = shell.querySelector('#sheet-title'), body = shell.querySelector('.sheet-body');
  let back = null;

  function open(which){
    if(shell.hidden) back = document.activeElement;
    title.textContent = which === 'keys' ? 'Keyboard shortcuts' : 'Settings';
    body.innerHTML = which === 'keys' ? keysHtml() : settingsHtml();
    shell.hidden = false;
    document.documentElement.classList.add('sheet-open');
    const first = body.querySelector('[aria-pressed="true"], button') || shell.querySelector('.sheet-x');
    first.focus();
  }
  function close(){
    if(shell.hidden) return;
    shell.hidden = true;
    document.documentElement.classList.remove('sheet-open');
    if(back && back.focus) back.focus();
  }
  shell.addEventListener('click', e => {
    if(e.target.closest('[data-sheet-close]')){ close(); return; }
    if(e.target.closest('[data-keys]')){ open('keys'); return; }
    if(e.target.closest('[data-tips]')){
      SHEET_TIPS.forEach(k => put(k, null));
      put(SHEET_TOUR, 'show');
      shell.querySelector('.sheet-status').textContent = 'Done: they show again on each page.';
      return;
    }
    const b = e.target.closest('[data-set]');
    if(!b) return;
    const s = SHEET_SETTINGS[Number(b.dataset.set)];
    const value = b.dataset.value === '' ? null : b.dataset.value;
    put(s.key, value);
    if(s.key === 'site:theme') SHEET_OLD_THEMES.forEach(k => put(k, null));
    if(s.key === 'site:cards'){
      if(value) document.documentElement.setAttribute('data-cards', value);
      else document.documentElement.removeAttribute('data-cards');
    }
    if(s.key === 'site:density'){
      if(value) document.documentElement.setAttribute('data-density', value);
      else document.documentElement.removeAttribute('data-density');
    }
    if(s.reload){ location.reload(); return; }
    b.parentNode.querySelectorAll('[data-set]').forEach(x => x.setAttribute('aria-pressed', String(x === b)));
  });
  /* The sheet is the one place Tab goes while it is open. */
  shell.addEventListener('keydown', e => {
    if(e.key === 'Escape'){ e.preventDefault(); close(); return; }
    if(e.key !== 'Tab') return;
    const stops = [...shell.querySelectorAll('button')].filter(x => !x.hidden && x.offsetParent !== null);
    if(!stops.length) return;
    const i = stops.indexOf(document.activeElement);
    if(e.shiftKey && i <= 0){ e.preventDefault(); stops[stops.length - 1].focus(); }
    else if(!e.shiftKey && i === stops.length - 1){ e.preventDefault(); stops[0].focus(); }
  });
  openers.forEach(b => { b.hidden = false; b.addEventListener('click', () => open('settings')); });
  document.addEventListener('keydown', e => {
    const typing = e.target.closest && e.target.closest('input, textarea, select, [contenteditable="true"]');
    if(e.key === '?' && !typing && !e.ctrlKey && !e.metaKey && !e.altKey && shell.hidden){
      e.preventDefault();
      open('keys');
    }
  });
})();
