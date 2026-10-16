/* The "Next games" strip (Stage 80 item 52, the 2026-10-13 UI/UX audit's
   F1; Mark chose the small cards, option B, on 2026-10-14). The next six
   games across the three sports, on the home and on each sport's board:
   each a card with the sport's mark, the start in the visitor's time zone,
   the game, and its saved pick and chance, the NFL preview's lean, or when
   its pick will be saved. Each card opens its sport's board.

   The site build puts this script and the slate it reads (src/site/home.py
   slate()) on every page that has an empty #site-strip, after all four are
   built (src/site/build.py inject_strip), so a sport's page can name the
   others' games without its own build reading their files. Everything is
   inside this function: nothing it names can meet a page's own script. */
(function(){
  const box = document.getElementById('site-strip');
  const src = document.getElementById('site-strip-data');
  if(!box || !src) return;
  let rows;
  try{ rows = JSON.parse(src.textContent); }catch(e){ return; }
  const NOW = Date.now(), SHOWN = 6;
  const home = document.documentElement.hasAttribute('data-site-home');
  const base = home ? '' : '../';
  const NAME = {nfl: 'NFL', nhl: 'NHL', nba: 'NBA'};
  // Each sport's mark, as the home page draws it (home.js ICON_PARTS;
  // tests/test_tonight_strip.py holds the two equal).
  const ICON_PARTS = {
    nfl: '<g transform="rotate(-28 10 10)"><ellipse cx="10" cy="10" rx="8.6" ry="5.2"/>'
       + '<path stroke-width="1.2" d="M5.6 10h8.8M7 8.1v3.8M9 8.1v3.8M11 8.1v3.8M13 8.1v3.8"/></g>',
    nhl: '<g transform="rotate(-28 10 10)"><ellipse cx="10" cy="8.4" rx="8.4" ry="3.2"/>'
       + '<path d="M1.6 8.4v3.2a8.4 3.2 0 0 0 16.8 0V8.4"/></g>',
    nba: '<g transform="rotate(-28 10 10)"><circle cx="10" cy="10" r="8.4"/>'
       + '<path stroke-width="1.2" d="M10 1.6v16.8M1.6 10h16.8M4.1 4c2.5 2.3 3 9.2 0 12M15.9 4c-2.5 2.3-3 9.2 0 12"/></g>',
  };
  const mark = s => `<svg class="ts-mark" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.4" `
    + `stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICON_PARTS[s] || ''}</svg>`;
  const day = t => { const d = new Date(t); return d.getFullYear() + '-' + d.getMonth() + '-' + d.getDate(); };
  const clock = t => new Date(t).toLocaleTimeString([], {hour: 'numeric', minute: '2-digit'});
  // The NBA files a tip-off it has not set at a placeholder hour: a weekday
  // tip before 5 PM Eastern is not a time (home.js tipSet, Stage 77 item 33).
  const ET = new Intl.DateTimeFormat('en-US', {weekday: 'short', hour: 'numeric', hourCycle: 'h23', timeZone: 'America/New_York'});
  const tipSet = t => {
    const p = Object.fromEntries(ET.formatToParts(new Date(t)).map(x => [x.type, x.value]));
    return p.weekday === 'Sat' || p.weekday === 'Sun' || Number(p.hour) >= 17;
  };
  function when(r){
    const t = Date.parse(r.t);
    const today = day(t) === day(NOW);
    const at = r.s === 'nba' && !tipSet(t) ? 'time TBD' : clock(t);
    return today ? at : `${new Date(t).toLocaleDateString([], {weekday: 'short'})} ${at}`;
  }
  /* What the card says of the pick: the saved side and its chance ("COL
     57%", "WSH 51% · even", as the boards print it), the preview's lean, or
     when the pick is saved. */
  function pickLine(r){
    if(r.k === 'pick') return `${r.p} ${r.c}%${r.e ? ' · even' : ''}`;
    if(r.k === 'lean') return `Leans ${r.p} ${r.c}%`;
    const lock = r.l ? Date.parse(r.l) : NaN;
    return lock > NOW ? `Pick at ${clock(lock).replace(':00', '')}` : 'Pick before the start';
  }
  const esc = s => String(s).replace(/[&<>"]/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]));
  function card(r){
    const line = pickLine(r), w = when(r);
    const label = `${NAME[r.s]}: ${r.a} at ${r.h}, ${w}. ${line}.`;
    const bar = r.k === 'pick' ? `<span class="ts-bar" aria-hidden="true"><i style="width:${r.c}%"></i></span>` : '';
    return `<a class="ts-item" href="${base}${r.s}/" aria-label="${esc(label)}">`
      + `<span class="ts-top">${mark(r.s)}<span>${esc(w)}</span></span>`
      + `<span class="ts-teams">${esc(r.a)} @ ${esc(r.h)}</span>`
      + `<span class="ts-pick${r.k === 'pick' ? ' is-pick' : ''}">${esc(line)}</span>${bar}</a>`;
  }
  const next = (Array.isArray(rows) ? rows : []).filter(r => Date.parse(r.t) > NOW && NAME[r.s]).slice(0, SHOWN);
  if(!next.length) return;
  const tag = home ? 'h2' : 'h3';
  box.innerHTML = `<div class="ts-head"><${tag} id="ts-title">Next games</${tag}>`
    + `<span>across the three sports, in your time zone</span></div>`
    + `<div class="ts-row">${next.map(card).join('')}</div>`;
  box.hidden = false;
})();
