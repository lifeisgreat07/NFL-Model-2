/* Hash routes for the NHL's and NBA's pages (Stage 68 item 23, the
   2026-10-09 audit's E17 and U23). Each page of a sport's site is a
   section, #page-<name>; until now the address never changed, so a link
   could not open the Methodology and the back button left the site.
   installRoutes(show) is called once by the sport's script with its own
   showPage: a tap pushes #<name> (the board is the bare address), the back
   and forward buttons and a typed link follow, and a link that names no
   page opens the board. Included ahead of each sport's script. */
function installRoutes(show){
  const known = new Set([...document.querySelectorAll('.page')].map(p => p.id.replace(/^page-/, '')));
  const fromHash = () => {
    let h = '';
    try{ h = decodeURIComponent(location.hash.slice(1)); }catch(e){ h = ''; }
    return known.has(h) ? h : null;
  };
  document.querySelectorAll('[data-page]').forEach(b => b.addEventListener('click', () => {
    const name = b.dataset.page;
    const want = name === 'board' ? '' : '#' + name;
    if(location.hash !== want) history.pushState(null, '', want || location.pathname + location.search);
  }));
  const follow = () => show(fromHash() || 'board');
  window.addEventListener('popstate', follow);
  window.addEventListener('hashchange', follow);
  const first = fromHash();
  if(first) show(first);
}
