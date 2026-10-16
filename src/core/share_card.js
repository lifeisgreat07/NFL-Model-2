/* A game card as an image to share (Stage 80 item 63, the 2026-10-13
   UI/UX audit's F13). Each sport's card carries what the image says in
   data-share (shareData in its own script) and a "Share image" button;
   this draws it on a canvas, 1200 by 630 (the size link previews use),
   and hands the PNG to the phone's share sheet, or downloads it where
   there is none (a desktop browser). It is drawn from the card's numbers,
   never copied from the page: the team logos come from ESPN and the NHL,
   and an image from another host would leave the canvas unreadable. The
   build puts it on the three sport pages (src/site/build.py add_share).

   The functions down to the IIFE need no page: tests/test_share_card.py
   runs them in node. */
const SHARE_W = 1200, SHARE_H = 630;
const SHARE_INK = {bg: '#0B0D10', panel: '#15181D', text: '#F2F4F7', soft: '#A3ABB8', line: '#2A303A',
  accent: '#7FA8F5', right: '#3FB97A', wrong: '#E5636B'};
const SHARE_FONT = "'Plus Jakarta Sans', sans-serif";

/* "sportalytics-nfl-SEA-at-DEN.png" */
function shareFileName(d){
  const safe = s => String(s || '').replace(/[^A-Za-z0-9]+/g, '');
  return `sportalytics-${safe(d.sport).toLowerCase()}-${safe(d.away)}-at-${safe(d.home)}.png`;
}

/* Every line of text the image draws, in order, so a test can read them. */
function shareLines(d){
  const out = [`SPORTALYTICS · ${String(d.sport).toUpperCase()}`, d.when || '', `${d.away} at ${d.home}`];
  // As the card says it: the saved pick, past tense once graded, "even" inside the band.
  const pick = d.team ? `${d.team} ${Math.round(d.pct)}%` : null;
  if(!pick) out.push(`${d.lead}: too close to call`);
  else if(d.even) out.push(`${d.lead} picked ${pick} · even`);
  else out.push(d.result ? `${d.lead} picked ${pick}` : `${d.lead}: ${pick} to win`);
  for(const f of d.forecasts || []) out.push(`${f.label} ${f.text}`);
  if(d.result) out.push(d.result);
  if(d.score) out.push(d.score);
  return out;
}

/* The drawing, on any 2D context: the page's canvas, or a test's recorder. */
function shareDraw(ctx, d, site){
  const L = shareLines(d);
  ctx.fillStyle = SHARE_INK.bg; ctx.fillRect(0, 0, SHARE_W, SHARE_H);
  ctx.fillStyle = SHARE_INK.panel; ctx.fillRect(40, 40, SHARE_W - 80, SHARE_H - 80);
  ctx.textBaseline = 'alphabetic';
  // The eyebrow and the start.
  ctx.font = `700 24px ${SHARE_FONT}`; ctx.fillStyle = SHARE_INK.accent; ctx.textAlign = 'left';
  ctx.fillText(L[0], 88, 108);
  ctx.font = `600 24px ${SHARE_FONT}`; ctx.fillStyle = SHARE_INK.soft; ctx.textAlign = 'right';
  ctx.fillText(L[1], SHARE_W - 88, 108);
  // The game.
  ctx.font = `800 64px ${SHARE_FONT}`; ctx.fillStyle = SHARE_INK.text; ctx.textAlign = 'left';
  ctx.fillText(L[2], 88, 196);
  // The pick, its number in the display face.
  ctx.font = `600 34px ${SHARE_FONT}`; ctx.fillStyle = SHARE_INK.soft;
  ctx.fillText(L[3], 88, 262);
  // The split bar: the away team first, as the card draws it.
  const x = 88, y = 300, w = SHARE_W - 176, h = 36, home = Math.max(0, Math.min(100, Number(d.homePct)));
  const [awayC, homeC] = d.colours || [SHARE_INK.line, SHARE_INK.line];
  ctx.fillStyle = awayC; ctx.fillRect(x, y, w * (100 - home) / 100, h);
  ctx.fillStyle = homeC; ctx.fillRect(x + w * (100 - home) / 100, y, w * home / 100, h);
  ctx.fillStyle = SHARE_INK.text; ctx.fillRect(x + w / 2 - 1.5, y - 10, 3, h + 20);
  ctx.font = `700 26px ${SHARE_FONT}`;
  ctx.textAlign = 'left'; ctx.fillText(d.away, x, y + h + 40);
  ctx.textAlign = 'center'; ctx.fillStyle = SHARE_INK.soft; ctx.fillText('50%', x + w / 2, y + h + 40);
  ctx.textAlign = 'right'; ctx.fillStyle = SHARE_INK.text; ctx.fillText(d.home, x + w, y + h + 40);
  // Each forecast.
  ctx.font = `600 26px ${SHARE_FONT}`; ctx.textAlign = 'left'; ctx.fillStyle = SHARE_INK.soft;
  const n = (d.forecasts || []).length;
  L.slice(4, 4 + n).forEach((t, i) => ctx.fillText(t, 88 + i * Math.floor((SHARE_W - 176) / Math.max(n, 1)), 444));
  // How it went, once graded.
  let at = 4 + n;
  if(d.result){
    ctx.font = `800 30px ${SHARE_FONT}`;
    ctx.fillStyle = d.result === 'Correct' ? SHARE_INK.right : d.result === 'Missed' ? SHARE_INK.wrong : SHARE_INK.soft;
    ctx.fillText(L[at++], 88, 506);
  }
  if(d.score){
    ctx.font = `600 26px ${SHARE_FONT}`; ctx.fillStyle = SHARE_INK.soft;
    ctx.fillText(L[at], d.result ? 260 : 88, 506);
  }
  // Where it came from.
  ctx.fillStyle = SHARE_INK.line; ctx.fillRect(88, 534, SHARE_W - 176, 2);
  ctx.font = `600 22px ${SHARE_FONT}`; ctx.fillStyle = SHARE_INK.soft; ctx.textAlign = 'left';
  ctx.fillText('Picked before the game, graded after it.', 88, 570);
  ctx.textAlign = 'right'; ctx.fillText(site, SHARE_W - 88, 570);
}

/* The site's address for the footer: the page's, up to the sport's folder. */
function shareSite(href){
  const u = new URL(href);
  return (u.host + u.pathname.replace(/(nfl|nhl|nba)\/.*$/, '').replace(/index\.html$/, '')).replace(/\/$/, '');
}

(function(){
  if(typeof document === 'undefined' || !document.addEventListener) return;
  async function share(btn){
    let d;
    try{ d = JSON.parse(btn.closest('[data-share]').getAttribute('data-share')); }catch(e){ return; }
    btn.disabled = true;
    try{
      if(document.fonts && document.fonts.ready) await document.fonts.ready;
      const c = document.createElement('canvas');
      c.width = SHARE_W; c.height = SHARE_H;
      shareDraw(c.getContext('2d'), d, shareSite(location.href));
      const blob = await new Promise(r => c.toBlob(r, 'image/png'));
      if(!blob) return;
      const name = shareFileName(d), file = new File([blob], name, {type: 'image/png'});
      if(navigator.canShare && navigator.canShare({files: [file]})){
        try{ await navigator.share({files: [file], title: `${d.away} at ${d.home}`}); return; }
        catch(e){ if(e && e.name === 'AbortError') return; }
      }
      const url = URL.createObjectURL(blob), a = document.createElement('a');
      a.href = url; a.download = name; a.hidden = true;
      document.body.appendChild(a); a.click(); a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 2000);
    }finally{ btn.disabled = false; }
  }
  document.addEventListener('click', e => {
    const btn = e.target.closest && e.target.closest('[data-share-card]');
    if(btn){ e.preventDefault(); e.stopPropagation(); share(btn); }
  });
})();
