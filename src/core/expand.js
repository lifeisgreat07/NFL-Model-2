/* Expand all / Collapse all (Mark's request, 2026-10-15; he chose option B,
   an outlined button on its own line under the day's or week's header).
   A day board (the NHL's, the NBA's, at every width) and the NFL's phone
   rows open one game at a time; this opens or closes every game shown at
   once. Each row is pressed as a reader would press it, so the page's own
   handler opens its card and remembers it; while it does, the page is kept
   where it was (no row's "bring the card on screen" runs), so the header
   and the button stay under the reader's thumb. The button says what it
   will do: "Expand all" until every shown game is open, then "Collapse
   all". The build puts this on the three sport pages (src/site/build.py
   add_expand).

   expandRows and expandLabel need no page: tests/test_expand_all.py runs
   them in node. */
function expandRows(scope){
  return [...scope.querySelectorAll('button.game-row[aria-controls]')].filter(r => r.offsetParent !== null);
}
function expandLabel(rows){
  return rows.length && rows.every(r => r.getAttribute('aria-expanded') === 'true') ? 'Collapse all' : 'Expand all';
}

(function(){
  if(typeof document === 'undefined' || !document.addEventListener) return;
  const scopeOf = btn => btn.closest('.page') || document;
  function sync(){
    for(const btn of document.querySelectorAll('[data-expand-all]')){
      const rows = expandRows(scopeOf(btn));
      const label = expandLabel(rows);
      const text = btn.querySelector('span');
      if(text && text.textContent !== label) text.textContent = label;
      btn.setAttribute('aria-expanded', String(label === 'Collapse all'));
      btn.hidden = rows.length < 2;
    }
  }
  document.addEventListener('click', e => {
    const btn = e.target.closest && e.target.closest('[data-expand-all]');
    if(!btn){
      // A row pressed by hand: the button's word follows, once the page has opened or closed it.
      if(e.target.closest && e.target.closest('button.game-row')) setTimeout(sync, 0);
      return;
    }
    const rows = expandRows(scopeOf(btn));
    const open = expandLabel(rows) === 'Expand all';
    const x = window.scrollX, y = window.scrollY, keep = Element.prototype.scrollIntoView;
    Element.prototype.scrollIntoView = function(){};
    try{
      rows.forEach(r => { if((r.getAttribute('aria-expanded') === 'true') !== open) r.click(); });
    }finally{
      Element.prototype.scrollIntoView = keep;
      window.scrollTo(x, y);
    }
    sync();
  });
  // A board drawn again (a day step, a sort) draws its button afresh.
  let queued = false;
  new MutationObserver(() => {
    if(queued) return;
    queued = true;
    requestAnimationFrame(() => { queued = false; sync(); });
  }).observe(document.body, {childList: true, subtree: true});
  sync();
})();
