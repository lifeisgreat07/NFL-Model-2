/* The sport menu (audit 9 D3; Mark's M1 B, 2026-11-16). Each page's
   switcher is a <details>: its button is the page you are on, and open it
   lists Home and every sport with the season's record, which the site build
   writes in (src/site/build.py add_menu, which also puts this script on all
   four pages). It opens and closes with no script at all; this closes an
   open one on Esc, putting the focus back on its button, or on a click
   anywhere outside it. */
function smClose(menus, inside){
  let closed = 0;
  for(const d of menus){
    if(!d.open || (inside && d.contains(inside))) continue;
    d.open = false;
    closed += 1;
  }
  return closed;
}

(function(){
  const menus = () => [...document.querySelectorAll('.sport-switch details.sm')];
  document.addEventListener('keydown', e => {
    if(e.key !== 'Escape') return;
    const open = menus().find(d => d.open && d.contains(document.activeElement));
    if(smClose(menus(), null) && open){
      const button = open.querySelector('summary');
      if(button) button.focus();
    }
  });
  document.addEventListener('click', e => { smClose(menus(), e.target); });
})();
