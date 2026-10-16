/* The visitor's settings that change how a page draws (Stage 80 item 57, the
   2026-10-13 UI/UX audit's F10). Set in the Settings sheet (src/core/sheet.js),
   kept in this browser, read by every sport's page. Times: every start
   (kickoff, puck drop, tip-off) in Eastern time, as the site always printed
   them, or in the visitor's own time zone. The NFL's app.js carries the same
   functions (tests/test_settings_sheet.py holds the two copies equal).
   Included ahead of each sport's script, after favs.js. */
const TZ_KEY = 'site:tz';
/* The time zone a start is printed in: Eastern unless the visitor chose
   their own (undefined: the browser's). */
function startZone(){
  try{ return localStorage.getItem(TZ_KEY) === 'local' ? undefined : 'America/New_York'; }
  catch(e){ return 'America/New_York'; }
}
/* What follows a start's time: " ET" in Eastern time, nothing in the
   visitor's own (as the home page has always printed its times). */
function startMark(){ return startZone() ? ' ET' : ''; }
