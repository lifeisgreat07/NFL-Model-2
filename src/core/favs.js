/* Favourite teams (Stage 80 item 53, the 2026-10-13 UI/UX audit's F7). A
   visitor stars a team; its games go to the top of each day or week, and
   the home names them. One list a sport, kept in this browser under one key
   every page reads, so a star on the NHL page shows on the home. Nothing
   leaves the browser. The NFL's app.js carries the same functions
   (tests/test_favourite_teams.py holds the two copies equal). Included
   ahead of each sport's script, after accuracy.js. */
const FAV_KEY = 'site:favs';
const FAV_STAR = '<svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true"><path d="M12 3.5l2.6 5.3 5.9.9-4.3 4.1 1 5.8-5.2-2.7-5.2 2.7 1-5.8-4.3-4.1 5.9-.9z"/></svg>';
function favsAll(){
  try{ const all = JSON.parse(localStorage.getItem(FAV_KEY) || '{}'); return all && typeof all === 'object' ? all : {}; }
  catch(e){ return {}; }
}
function favs(sport){ const list = favsAll()[sport]; return Array.isArray(list) ? list : []; }
function isFav(sport, team){ return favs(sport).includes(team); }
function toggleFav(sport, team){
  const all = favsAll(), list = favs(sport);
  all[sport] = list.includes(team) ? list.filter(t => t !== team) : list.concat(team);
  try{ localStorage.setItem(FAV_KEY, JSON.stringify(all)); }catch(e){}
  return all[sport].includes(team);
}
function favLabel(on, name){ return on ? `Remove ${name} from your teams` : `Add ${name} to your teams`; }
function favStar(sport, team, name){
  const on = isFav(sport, team);
  return `<button type="button" class="fav-star" data-fav-sport="${sport}" data-fav-team="${team}" data-fav-name="${name}"`
    + ` aria-pressed="${on}" aria-label="${favLabel(on, name)}">${FAV_STAR}</button>`;
}
/* Games with a favourite team first, each group in its own order. */
function favFirst(sport, games){
  const list = favs(sport);
  if(!list.length) return games;
  const mine = g => list.includes(g.home) || list.includes(g.away);
  return games.filter(mine).concat(games.filter(g => !mine(g)));
}
/* One listener for every star on the page; `redraw` puts the starred games
   back on top. */
function installFavStars(redraw){
  document.addEventListener('click', e => {
    const b = e.target.closest('.fav-star');
    if(!b) return;
    e.preventDefault();
    e.stopPropagation();
    const on = toggleFav(b.dataset.favSport, b.dataset.favTeam);
    document.querySelectorAll('.fav-star').forEach(x => {
      if(x.dataset.favSport !== b.dataset.favSport || x.dataset.favTeam !== b.dataset.favTeam) return;
      x.setAttribute('aria-pressed', String(on));
      x.setAttribute('aria-label', favLabel(on, x.dataset.favName));
    });
    if(!redraw) return;
    redraw();
    // The star was drawn again, perhaps higher up with its game: focus follows it.
    const again = document.querySelector(`.page.active .fav-star[data-fav-sport="${b.dataset.favSport}"][data-fav-team="${b.dataset.favTeam}"]`);
    if(again && !b.isConnected) again.focus();
  });
}
