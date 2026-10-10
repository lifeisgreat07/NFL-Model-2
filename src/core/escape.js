/* Text into innerHTML: the one escape helper the NHL's and NBA's scripts
   share (Stage 68 item 24). Included ahead of each sport's script. */
function escapeHtml(s){
  return String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}
