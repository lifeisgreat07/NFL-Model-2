/* Installable, and the last board offline (Stage 80 item 62, the
   2026-10-13 UI/UX audit's F14). The build puts this on all four pages
   (src/site/build.py add_offline). It registers the site's service worker
   (src/site/sw.js, at the site's root: the page's manifest link says where
   that is), and while the browser says it has no connection it says so at
   the foot of the screen, because the board shown is then the copy this
   device kept, not the latest. It needs https or this computer (a file
   opened from disk has no worker). */
function offlineBase(href){
  const at = String(href || '').indexOf('assets/site.webmanifest');
  return at < 0 ? null : String(href).slice(0, at);
}
const OFFLINE_TEXT = "You're offline. This is the last copy of the page saved on this device.";

(function(){
  const link = document.querySelector('link[rel="manifest"]');
  const base = offlineBase(link && link.getAttribute('href'));
  const local = location.hostname === 'localhost' || location.hostname === '127.0.0.1';
  if(base !== null && 'serviceWorker' in navigator && (location.protocol === 'https:' || local)){
    navigator.serviceWorker.register(`${base}sw.js`, {scope: base || './'}).catch(() => {});
  }
  let note = null;
  function show(){
    const off = navigator.onLine === false;
    if(off && !note){
      note = document.createElement('p');
      note.className = 'offline-note';
      note.setAttribute('role', 'status');
      note.textContent = OFFLINE_TEXT;
      document.body.appendChild(note);
    }
    if(note) note.hidden = !off;
  }
  window.addEventListener('online', show);
  window.addEventListener('offline', show);
  show();
})();
