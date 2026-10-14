/* Hash routes for the NHL's and NBA's pages (Stage 68 item 23, the
   2026-10-09 audit's E17 and U23). Each page of a sport's site is a
   section, #page-<name>; until now the address never changed, so a link
   could not open the Methodology and the back button left the site.
   installRoutes(show) is called once by the sport's script with its own
   showPage: a tap on a [data-page] or [data-route] button pushes #<name> (the board is the bare address), the back
   and forward buttons and a typed link follow, and a link that names no
   page opens the board. Included ahead of each sport's script.

   Stage 76 item 7 (the 2026-10-13 audit's X6, F3): a route learns one
   argument, as the NFL's parseRoute does. #board/<day> opens that day of
   that week, and on the NHL #team/<club> opens the Teams page on that club.
   A day chip, a week step or the club select replaces the current entry
   (history.replaceState), so stepping through a week does not cost seven
   presses of Back; a page change still pushes one. A day or club that does
   not exist opens the page without it. The sport passes `arg`:
     arg.known()      -> {days: [...], teams: [...]}, what a route may name
     arg.current(page) -> the page's argument now, or undefined for its default
     arg.apply(page, value) -> draw the page for value (undefined: its default)
   installRoutes returns replace(page), which the sport calls after a chip,
   a week step or a club change. parseHash and routeHash are pure, so the
   suite runs them under node. */
function parseHash(hash, known){
  let raw = '';
  try{ raw = decodeURIComponent(String(hash || '').replace(/^#/, '')); }catch(e){ raw = ''; }
  if(raw === '') return {page: 'board'};
  const slash = raw.indexOf('/');
  const head = slash === -1 ? raw : raw.slice(0, slash);
  const arg = slash === -1 ? '' : raw.slice(slash + 1);
  if(head === 'team'){
    if(!known.pages.includes('teams')) return null;
    return (known.teams || []).includes(arg) ? {page: 'teams', arg} : {page: 'teams'};
  }
  if(!known.pages.includes(head)) return null;
  if(head === 'board' && (known.days || []).includes(arg)) return {page: 'board', arg};
  return {page: head};
}
function routeHash(r){
  if(r.page === 'teams' && r.arg) return '#team/' + encodeURIComponent(r.arg);
  if(r.page === 'board') return r.arg ? '#board/' + encodeURIComponent(r.arg) : '';
  return '#' + r.page;
}
function installRoutes(show, arg){
  const pages = [...document.querySelectorAll('.page')].map(p => p.id.replace(/^page-/, ''));
  const route = arg || {};
  const known = () => Object.assign({pages}, route.known ? route.known() : {});
  const current = page => (route.current ? route.current(page) : undefined);
  const url = page => routeHash({page, arg: current(page)}) || location.pathname + location.search;
  const same = want => (want.startsWith('#') ? location.hash === want : location.hash === '');
  // Stage 76 item 8 (X5): one listener on the document, not one per button
  // bound at load. The NHL's side column is drawn again with the board, so
  // its "All 32 clubs" lost the route after a day chip, and the NBA's "See
  // the backtest" is not a nav button (data-route): both opened their page
  // without an entry, and Back left the site.
  document.addEventListener('click', e => {
    const b = e.target && e.target.closest ? e.target.closest('[data-page], [data-route]') : null;
    if(!b) return;
    const want = url(b.dataset.page || b.dataset.route);
    if(!same(want)) history.pushState(null, '', want);
  });
  const follow = () => {
    const r = parseHash(location.hash, known()) || {page: 'board'};
    if(route.apply) route.apply(r.page, r.arg);
    show(r.page);
  };
  window.addEventListener('popstate', follow);
  window.addEventListener('hashchange', follow);
  const first = location.hash ? parseHash(location.hash, known()) : null;
  if(first){
    if(route.apply && first.arg !== undefined) route.apply(first.page, first.arg);
    if(first.page !== 'board' || first.arg !== undefined) show(first.page);
  }
  return function replace(page){
    const active = document.querySelector('.page.active');
    if(active && active.id !== 'page-' + page) return;
    const want = url(page);
    if(!same(want)) history.replaceState(null, '', want);
  };
}
