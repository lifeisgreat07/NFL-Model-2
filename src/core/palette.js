/* The search box (Stage 80 item 56, the 2026-10-13 UI/UX audit's F6; Mark
   chose it as mocked on 2026-10-14). "/" or Ctrl K (Cmd K on a Mac), or the
   Search button, opens one box on every page that finds teams, the next
   games, pages and the NFL's experiments across the three sports, each a
   link to where it lives. Arrow keys move, Enter follows, Esc closes and
   gives the focus back.

   The site build puts this script and its index (src/site/search.py) on
   every page with a [data-palette-open] button, beside the Next games
   strip's slate, which it reads for the games. A page built on its own
   keeps its Search buttons hidden. What it finds and how it ranks them are
   two functions named pal*, so the suite can run them; nothing else it
   names reaches a page's own script. */
const PAL_GROUPS = ['Teams', 'Games', 'Pages', 'Experiments'];
const PAL_SPORT = {nfl: 'NFL', nhl: 'NHL', nba: 'NBA'};
/* Every thing the box can find: what it is called, the words it is found
   by, where it leads and what is said beside it. `base` leads from this
   page to the site's root ('' on the home, '../' on a sport's page). */
function palItems(index, games, base, now){
  const NAME = PAL_SPORT;
  const pageName = Object.fromEntries((index.pages || []).map(([s, p, label]) => [s + ':' + p, label]));
  const href = (s, hash) => `${base}${s}/${hash}`;
  const clock = t => new Date(t).toLocaleString([], {weekday: 'short', hour: 'numeric', minute: '2-digit'});
  const items = [];
  (index.teams || []).forEach(([s, abbr, name]) => items.push({group: 'Teams', label: name, words: `${abbr} ${name}`,
    href: href(s, s === 'nba' ? '' : `#team/${encodeURIComponent(abbr)}`),
    note: `${NAME[s]} · ${s === 'nba' ? pageName['nba:board'] || 'Day Board' : pageName[s + (s === 'nfl' ? ':teamdive' : ':teams')] || 'Teams'}`}));
  (Array.isArray(games) ? games : []).filter(g => Date.parse(g.t) > now - 3 * 3600 * 1000 && NAME[g.s]).forEach(g => {
    const pick = g.k === 'pick' ? ` · ${g.p} ${g.c}%` : g.k === 'lean' ? ` · Leans ${g.p} ${g.c}%` : '';
    items.push({group: 'Games', label: `${g.a} @ ${g.h}`, words: `${g.a} ${g.h} ${g.a}@${g.h}`,
      href: href(g.s, g.g ? `#game/${encodeURIComponent(g.g)}` : ''), note: `${NAME[g.s]} · ${clock(g.t)}${pick}`});
  });
  (index.pages || []).forEach(([s, page, label]) => items.push({group: 'Pages', label, words: `${label} ${NAME[s]}`,
    href: href(s, page === 'board' ? '' : `#${page}`), note: NAME[s], sport: s}));
  (index.experiments || []).forEach(([s, slug, name]) => items.push({group: 'Experiments', label: name, words: name,
    href: href(s, `#modellab/${encodeURIComponent(slug)}`), note: `${NAME[s]} · Model Lab`}));
  return items;
}
/* Each word typed must start a word of the item's: "sea" finds Seattle and
   SEA @ DEN, "acc" Season Accuracy. Within a group the items whose name
   starts with the query come first; five a group. With nothing typed, this
   sport's pages (`here` is "NFL", "NHL" or "NBA"; the home has none). */
function palSearch(items, q, here){
  const terms = q.toLowerCase().split(/\s+/).filter(Boolean);
  if(!terms.length) return items.filter(it => it.group === 'Pages' && PAL_SPORT[it.sport] === here);
  const hits = items.filter(it => {
    const words = it.words.toLowerCase().split(/[^a-z0-9@]+/);
    return terms.every(t => words.some(w => w.startsWith(t)));
  });
  const first = terms.join(' ');
  return PAL_GROUPS.flatMap(gr => hits.filter(it => it.group === gr)
    .map((it, i) => [it, it.label.toLowerCase().startsWith(first) ? 0 : 1, i])
    .sort((a, b) => a[1] - b[1] || a[2] - b[2]).slice(0, 5).map(x => x[0]));
}
(function(){
  const src = document.getElementById('site-search-data');
  const openers = [...document.querySelectorAll('[data-palette-open]')];
  if(!src || !openers.length) return;
  let INDEX;
  try{ INDEX = JSON.parse(src.textContent); }catch(e){ return; }
  let GAMES = [];
  try{ GAMES = JSON.parse((document.getElementById('site-strip-data') || {}).textContent || '[]'); }catch(e){}
  const home = document.documentElement.hasAttribute('data-site-home');
  const base = home ? '' : '../';
  const here = (document.querySelector('.sport-switch [aria-current="page"]') || {}).textContent || '';
  const items = palItems(INDEX, GAMES, base, Date.now());
  const GROUPS = PAL_GROUPS;
  const search = q => palSearch(items, q, here);
  const esc = s => String(s).replace(/[&<>"]/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]));

  const shell = document.createElement('div');
  shell.className = 'pal-shell';
  shell.hidden = true;
  shell.innerHTML = '<div class="pal-scrim" data-pal-close></div>'
    + '<div class="pal-dialog" role="dialog" aria-modal="true" aria-label="Search">'
    + '<div class="pal-in"><svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/></svg>'
    + '<input type="text" class="pal-input" role="combobox" aria-expanded="true" aria-controls="pal-list" aria-autocomplete="list" '
    + 'aria-label="Search teams, games, pages and experiments" placeholder="Search teams, games, pages" autocomplete="off" spellcheck="false">'
    + '<button type="button" class="pal-esc" data-pal-close aria-label="Close search">Esc</button></div>'
    + '<div class="pal-list" id="pal-list" role="listbox" aria-label="Results"></div></div>';
  document.body.appendChild(shell);
  const input = shell.querySelector('.pal-input'), list = shell.querySelector('.pal-list');
  let shown = [], active = 0, back = null;

  function draw(){
    shown = search(input.value);
    active = Math.min(active, Math.max(shown.length - 1, 0));
    if(!shown.length){
      const q = input.value.trim();
      list.innerHTML = `<p class="pal-none">${q ? `Nothing found for “${esc(q)}”.` : 'Type a team, a game or a page.'}</p>`;
      input.removeAttribute('aria-activedescendant');
      return;
    }
    let html = '', at = 0;
    GROUPS.forEach(gr => {
      const mine = shown.filter(it => it.group === gr);
      if(!mine.length) return;
      const head = 'pal-g-' + gr.toLowerCase();
      html += `<div role="group" aria-labelledby="${head}"><div class="pal-head" id="${head}" role="presentation">${gr}</div>`;
      mine.forEach(it => {
        const n = at++;
        html += `<a class="pal-item${n === active ? ' is-active' : ''}" id="pal-opt-${n}" role="option" aria-selected="${n === active}" `
          + `tabindex="-1" href="${esc(it.href)}"><span>${esc(it.label)}</span><small>${esc(it.note)}</small></a>`;
      });
      html += '</div>';
    });
    list.innerHTML = html;
    input.setAttribute('aria-activedescendant', 'pal-opt-' + active);
    const el = document.getElementById('pal-opt-' + active);
    if(el && el.scrollIntoView) el.scrollIntoView({block: 'nearest'});
  }
  function open(){
    if(!shell.hidden) return;
    back = document.activeElement;
    shell.hidden = false;
    document.documentElement.classList.add('pal-open');
    input.value = '';
    active = 0;
    draw();
    input.focus();
  }
  function close(){
    if(shell.hidden) return;
    shell.hidden = true;
    document.documentElement.classList.remove('pal-open');
    if(back && back.focus) back.focus();
  }
  function follow(it){
    if(!it) return;
    close();
    location.href = it.href;
  }
  input.addEventListener('input', () => { active = 0; draw(); });
  input.addEventListener('keydown', e => {
    if(e.key === 'ArrowDown' || e.key === 'ArrowUp'){
      e.preventDefault();
      if(shown.length) active = (active + (e.key === 'ArrowDown' ? 1 : -1) + shown.length) % shown.length;
      draw();
    } else if(e.key === 'Enter'){
      e.preventDefault();
      follow(shown[active]);
    } else if(e.key === 'Escape'){
      e.preventDefault();
      close();
    } else if(e.key === 'Tab'){
      e.preventDefault();  // the box is the one stop while it is open
    }
  });
  shell.addEventListener('click', e => {
    if(e.target.closest('[data-pal-close]')){ close(); return; }
    const a = e.target.closest('.pal-item');
    if(a){ e.preventDefault(); follow(shown[Number(a.id.replace('pal-opt-', ''))]); }
  });
  openers.forEach(b => { b.hidden = false; b.addEventListener('click', open); });
  /* "/" anywhere but in a field, and Ctrl K or Cmd K anywhere. */
  document.addEventListener('keydown', e => {
    const typing = e.target.closest && e.target.closest('input, textarea, select, [contenteditable="true"]');
    if((e.key === 'k' || e.key === 'K') && (e.ctrlKey || e.metaKey) && !e.altKey){
      e.preventDefault();
      shell.hidden ? open() : close();
    } else if(e.key === '/' && !typing && !e.ctrlKey && !e.metaKey && !e.altKey && shell.hidden){
      e.preventDefault();
      open();
    }
  });
})();
