/* ---------- Changelog ---------- */
// Escaped (escapeHtml) rather than interpolated raw: this text comes out of config.py,
// which is a source file people edit by hand, and an unescaped '<' in a
// release note would silently break the page it is describing.

/* ---------- Booth's audit log (Checking the AI's work) ---------- */
function renderAgentLog(){
  const el = document.getElementById('agent-log');
  if(!el) return;
  // null means the collector has never run. That is NOT the same as "audits
  // ran and found nothing", and the page must not let the reader read the
  // second from the first -- it is the more flattering of the two.
  if(!agentLog || !agentLog.summary){
    el.innerHTML = stateHtml('missing', 'The record has not been collected yet',
      `The audits below were written by hand. The automatic tally of every
      audit this project's verifier has run is produced by a workflow that has
      not been run yet, so rather than show an empty scoreboard this section
      says so.`);
    return;
  }
  const s = agentLog.summary;
  const stat = (n, label, note) => `<div class="agent-stat">
      <div class="agent-stat-n">${n}</div>
      <div class="agent-stat-l">${label}</div>
      ${note ? `<div class="agent-stat-note">${note}</div>` : ''}
    </div>`;
  el.innerHTML = `<div class="method-block">
    <h3>What the checking has actually caught</h3>
    <p>Every pull request in this project is reviewed a second time by a
    separate agent whose only job is to check whether what the first one
    claimed is true. These numbers are counted from those reviews, not
    written by hand.</p>
    <div class="agent-stats">
      ${stat(s.pull_requests_audited, 'changes reviewed')}
      ${stat(s.claims_checked, 'claims checked one by one')}
      ${stat(s.discrepancies_found, 'claims that turned out to be wrong',
             s.pull_requests_with_a_discrepancy + ' of the reviews found at least one')}
      ${stat(s.unverifiable, 'claims that could not be checked either way')}
    </div>
    <p style="margin-top:var(--s4);">${s.audits_without_a_verdict_block} review${s.audits_without_a_verdict_block===1?'':'s'}
    ${s.audits_without_a_verdict_block===1?'was':'were'} written before the checker started
    reporting in a fixed format, so ${s.audits_without_a_verdict_block===1?'it is':'they are'}
    counted here but ${s.audits_without_a_verdict_block===1?'its':'their'} findings are not.
    ${s.reports_disagreeing_with_themselves} review${s.reports_disagreeing_with_themselves===1?'':'s'}
    disagreed with ${s.reports_disagreeing_with_themselves===1?'itself':'themselves'} &mdash; the
    summary said one thing and the detail said another &mdash; which is recorded rather than
    quietly corrected.</p>
    <p class="rel-prov">${s.audits_total} review${s.audits_total===1?'':'s'} in total,
    ${s.audits_superseded} of them replaced by a later run of the same review and not counted.
    Collected ${agentLog.generated_utc || 'unknown'}.</p>
  </div>${agentsAtWork(agentLog.recent)}`;
}

/* Stage 90 item 3: the four agents at work. Booth audits each change, Scout
   reads its description before the audit, Spotter photographs the pages it
   can alter, and Line Judge reads the unattended runs. Their latest outputs,
   newest first, each linked to the comment or run it came from. */
const AGENT_ROLES = {Booth: 'checks each claim', Scout: 'reads the description first',
  Spotter: 'looks at the pages', 'Line Judge': 'reads the unattended runs'};
function agentsAtWork(recent){
  if(!Array.isArray(recent) || !recent.length) return '';
  const rows = recent.map(e => {
    const when = e.when ? escapeHtml(String(e.when).slice(0, 10)) : '';
    const pr = e.pr ? ` on #${Number(e.pr)}` : '';
    const link = /^https:\/\/github\.com\//.test(e.url || '') ? escapeHtml(e.url) : '';
    const says = escapeHtml(String(e.says || ''));
    return `<li class="agent-entry"><b>${escapeHtml(String(e.agent))}</b>${pr}, ${when}: `
      + (link ? `<a href="${link}" rel="noopener">${says}</a>` : says) + '</li>';
  }).join('');
  return `<div class="method-block agents-at-work">
    <h3>The agents at work</h3>
    <p>Four agents check this project's work: Booth ${AGENT_ROLES.Booth}, Scout ${AGENT_ROLES.Scout},
    Spotter ${AGENT_ROLES.Spotter} and Line Judge ${AGENT_ROLES['Line Judge']}. Their latest
    outputs, newest first, each linked to where it was posted.</p>
    <ul class="agent-entries">${rows}</ul>
  </div>`;
}

/* ---------- The scheduled jobs, run by run (Stage 41 item 4) ---------- */
const RUN_RESULTS = {success: 'Finished', failure: 'Failed', cancelled: 'Cancelled',
  skipped: 'Skipped', timed_out: 'Timed out'};
function runResultText(r){
  return r.conclusion == null ? 'Running' : (RUN_RESULTS[r.conclusion] || r.conclusion);
}
function runTriggerText(r){
  if(r.event === 'schedule') return 'GitHub&#39;s timer';
  if(r.event === 'workflow_dispatch') return 'Requested';
  return escapeHtml(String(r.event || 'unknown'));
}
function runStartedText(iso){
  if(!iso) return 'unknown';
  return new Date(iso).toLocaleString('en-US', {timeZone: 'America/New_York',
    month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit'});
}
/* Stage 46 item 6: how late each run started after the slot it served
   (recent_runs.late_minutes, from the workflow's own cron lines). Seven
   hours or more is marked, the threshold of each run's own warning
   (src/core/start_delay.py). */
const LATE_WARN_MINUTES = 7 * 60;
function lateText(m){
  if(m == null) return '&ndash;';
  const text = `${Math.floor(m / 60)}h ${String(m % 60).padStart(2, '0')}m`;
  return m >= LATE_WARN_MINUTES ? `<b>${text}</b>` : text;
}
function renderRecentRuns(){
  const el = document.getElementById('recent-runs');
  if(!el) return;
  // null: this build did not read the history (any build but the deploy, or
  // a deploy whose read failed). Not the same as "nothing ran".
  if(!recentRuns || !Array.isArray(recentRuns.runs)){
    el.innerHTML = stateHtml('missing', 'The run history was not read for this build',
      `The list of recent scheduled runs is read from GitHub when the site is
      published. This copy of the page was built without it, so rather than
      show an empty table this section says so.`);
    return;
  }
  const runs = recentRuns.runs;
  const failed = runs.filter(r => r.conclusion === 'failure' || r.conclusion === 'timed_out').length;
  const body = runs.map(r => `<tr>
      <td>${escapeHtml(r.workflow)}<div style="font-size:var(--fs-12); color:var(--text-2);">${runTriggerText(r)}</div></td>
      <td>${runStartedText(r.started_utc)}</td>
      <td>${r.url ? `<a class="row-link" href="${escapeHtml(r.url)}" style="color:var(--accent); text-decoration:underline;">${runResultText(r)}</a>` : runResultText(r)}</td>
      <td class="num">${r.minutes == null ? '&ndash;' : r.minutes.toFixed(1)}</td>
      <td class="num">${lateText(r.late_minutes)}</td>
    </tr>`).join('');
  el.innerHTML = `<div class="method-block">
    <h3>The scheduled jobs, run by run</h3>
    <p>The picks are locked, graded and checked by jobs that run on a timer with
    nobody watching. These are their last ${runs.length} runs, read from GitHub when
    this page was published: ${failed === 0 ? 'none failed' :
      failed + ' failed'}. GitHub&#39;s own timer has started jobs hours late, so
    since October 4 an outside service also asks for each run at its scheduled
    time; those show as &ldquo;Requested&rdquo;, as does a run started by hand.
    &ldquo;Late by&rdquo; is how long after its scheduled time a run started; seven
    hours or more is in bold. Times are Eastern.</p>
    ${runs.length ? `<div class="table-wrap" data-scroll-label="Recent scheduled runs"><table class="metrics-table">
      <caption class="visually-hidden">The last scheduled runs, newest first</caption>
      <thead><tr><th scope="col">Job</th><th scope="col">Started</th>
      <th scope="col">Result</th><th scope="col">Min</th><th scope="col">Late by</th></tr></thead>
      <tbody>${body}</tbody>
    </table></div>` : stateHtml('note', 'No runs yet.', 'GitHub returned no runs for these jobs.')}
    <p class="rel-prov">Read ${escapeHtml(recentRuns.read_utc || 'at an unknown time')} (UTC).
    Each result links to that run on GitHub.</p>
  </div>`;
}

function renderChangelog(){
  const content = document.getElementById('changelog-content');
  const badge = document.getElementById('changelog-badge');
  if(!content) return;

  if(!versionHistory || !versionHistory.length){
    content.innerHTML = stateHtml('missing', 'No version history in this build',
      'The list of model versions is read from the project&#39;s settings file when the page is built, and this build found none.');
    if(badge) badge.textContent = '—';
    return;
  }
  if(badge){
    badge.textContent = versionHistory.length + ' version' + (versionHistory.length===1?'':'s');
  }

  content.innerHTML = `<div class="method-block">` + versionHistory.map(v => {
    // The badge is derived, not stored: whichever entry matches the version
    // the model is actually running is the current one. Storing a flag would
    // let the page mark a release "current" that config.py disagrees with.
    const isCurrent = v.version === modelVersion;
    return `<div class="cl-entry">
      <div class="cl-meta">
        <span class="cl-version">v${escapeHtml(v.version)}</span>
        <span class="cl-date">${escapeHtml(v.date)}</span>
        ${isCurrent ? '<span class="cl-current">Running now</span>' : ''}
      </div>
      <div>
        <div class="cl-headline">${escapeHtml(v.headline)}</div>
        <div class="cl-detail">${escapeHtml(v.detail)}</div>
      </div>
    </div>`;
  }).join('') + `</div>`;
}
renderAgentLog();
renderRecentRuns();
renderChangelog();

/* ---------- Hash routes (Stage 13) ----------
   Every page, a Week Board week, a team and a Model Lab experiment have an
   address, so a link can point at one and the back button steps between
   pages:

     #board               the Week Board, latest week
     #board/2026_week2    the Week Board at that week
     #team/KC             Team Deep-Dive on that team
     #modellab/<slug>     Model Lab, scrolled to that experiment's row
     #ratings, #picks, #accuracy, #teamdive, #modellab, #method,
     #changelog, #reliability

   They coexist with share links: anything carrying `picks=` belongs to
   readSharedPicksFromUrl() and is never read as a route, and while a shared
   view is up the address is left alone. A hash that is not a route -- the
   Methodology page's own jump links (#part-method) are the live case -- is
   ignored rather than bounced to a page. A route naming a week, team or
   experiment that does not exist opens the page without it.

   A page change adds a history entry (pushState); a week or team change
   inside a page replaces the current one, so stepping through eight weeks
   does not cost eight presses of Back. Nothing writes a hash at load: an
   address with none still opens on the Week Board.

   parseRoute and routeHash are pure, so the suite runs them under node. */
const ROUTE_PAGES = ['board','ratings','teamdive','picks','accuracy','modellab','method','changelog','reliability'];
function parseRoute(hash, known){
  const raw = String(hash || '').replace(/^#/, '');
  if(/(^|&)picks=/.test(raw)) return null;
  if(raw === '') return {page:'board'};
  const slash = raw.indexOf('/');
  const head = slash === -1 ? raw : raw.slice(0, slash);
  let arg = slash === -1 ? '' : raw.slice(slash + 1);
  try{ arg = decodeURIComponent(arg); }catch(e){ arg = ''; }
  if(head === 'team') return known.teams.includes(arg) ? {page:'teamdive', team:arg} : {page:'teamdive'};
  if(head === 'game') return (known.games || []).includes(arg) ? {page:'board', week:arg.split('-')[0], game:arg} : {page:'board'};
  if(!ROUTE_PAGES.includes(head)) return null;
  if(head === 'board' && known.weeks.includes(arg)) return {page:'board', week:arg};
  if(head === 'modellab' && known.experiments.includes(arg)) return {page:'modellab', experiment:arg};
  return {page:head};
}
function routeHash(r){
  if(r.game) return '#game/' + encodeURIComponent(r.game);
  if(r.page === 'teamdive' && r.team) return '#team/' + encodeURIComponent(r.team);
  if(r.page === 'board' && r.week) return '#board/' + encodeURIComponent(r.week);
  if(r.page === 'modellab' && r.experiment) return '#modellab/' + encodeURIComponent(r.experiment);
  return '#' + r.page;
}
/* Stage 76 item 9 (the 2026-10-13 audit's F4): a game's address is its week
   and its two clubs, #game/2026_week6-SEA-DEN. Nothing in the data has to
   carry an id, and the key stays the same however the board is sorted or
   filtered. */
function gameKey(week, g){ return `${week}-${g.away}-${g.home}`; }
function experimentSlug(text){
  return String(text).toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '')
    .slice(0, 48).replace(/-+$/, '');
}

/* ---------- Model Lab: filter by decision (Stage 18) ----------
   One chip per decision the table actually holds, in a fixed order, each
   with its count, plus All and the leakage flag. Counted from the rendered
   rows rather than carried separately, so a chip can never promise rows the
   table does not have. A row's decision is its first tag; the leakage flag
   is a second tag reading LEAKAGE. */
const LAB_DECISIONS = ['ACCEPT', 'CONFIRMED FINDING', 'INCONCLUSIVE', 'REJECT', 'DEFERRED'];

function labChips(rows){
  const chips = [{key:'all', label:'All', n: rows.length}];
  LAB_DECISIONS.forEach(d => {
    const n = rows.filter(r => r.decision === d).length;
    if(n) chips.push({key: d, label: d.charAt(0) + d.slice(1).toLowerCase(), n});
  });
  const leak = rows.filter(r => r.leakage).length;
  if(leak) chips.push({key:'leakage', label:'Leakage', n: leak});
  return chips;
}

function labRowMatches(row, key){
  return key === 'all' || (key === 'leakage' ? row.leakage : row.decision === key);
}

let labShowAll = null;

(function wireLabFilters(){
  const bar = document.getElementById('lab-filter-row');
  const status = document.getElementById('lab-filter-status');
  const trs = Array.from(document.querySelectorAll(
    '#page-modellab .table-wrap[data-scroll-label="Experiment log"] tbody tr'));
  if(!bar || !trs.length) return;
  const rows = trs.map(tr => {
    const tags = Array.from(tr.querySelectorAll('td:last-child .conf-tag')).map(s => s.textContent.trim());
    return {tr, decision: tags[0], leakage: tags.includes('LEAKAGE')};
  });
  const chips = labChips(rows);
  bar.innerHTML = chips.map(c =>
    `<button type="button" class="btn btn-chip lab-filter${c.key === 'all' ? ' active' : ''}" data-decision="${c.key}"` +
    ` aria-pressed="${c.key === 'all' ? 'true' : 'false'}">${c.label}<span class="chip-n">${c.n}</span></button>`).join('');
  bar.hidden = false;
  function show(key){
    let shown = 0;
    rows.forEach(r => { const on = labRowMatches(r, key); r.tr.hidden = !on; if(on) shown++; });
    bar.querySelectorAll('.lab-filter').forEach(b => {
      const on = b.dataset.decision === key;
      b.classList.toggle('active', on);
      b.setAttribute('aria-pressed', on ? 'true' : 'false');
    });
    if(status) status.textContent = `Showing ${shown} of ${rows.length} experiments.`;
  }
  bar.addEventListener('click', e => {
    const b = e.target.closest('.lab-filter');
    if(b) show(b.dataset.decision);
  });
  labShowAll = () => show('all');
})();

/* Model Lab's experiment rows are static markup with no ids; each gets one
   from its first cell, made unique if two names slug alike. */
const routeKnown = (function(){
  const experiments = [];
  document.querySelectorAll('#page-modellab .table-wrap[data-scroll-label="Experiment log"] tbody tr').forEach(tr=>{
    const first = tr.querySelector('td');
    if(!first) return;
    let slug = experimentSlug(first.textContent), n = 2;
    while(experiments.includes(slug)) slug = experimentSlug(first.textContent) + '-' + n++;
    experiments.push(slug);
    tr.id = 'exp-' + slug;
  });
  const teams = (teamHistory && teamHistory.names) ? Object.keys(teamHistory.names) : [];
  const games = weekKeysSorted.flatMap(k => ((weeks[k] || {}).games || []).map(g => gameKey(k, g)));
  return {weeks: weekKeysSorted.slice(), teams, experiments, games};
})();

function currentRoute(page){
  if(page === 'board') return {page, week: currentBoardWeek !== latestWeekKey ? currentBoardWeek : undefined};
  if(page === 'teamdive'){
    const s = document.getElementById('teamdive-select');
    return {page, team: (s && s.value) || undefined};
  }
  return {page};
}
function inSharedView(){ return /[#&]picks=/.test(location.hash || ''); }
function routeUrl(r){ return location.pathname + location.search + routeHash(r); }

/* Stage 76 item 10 (the 2026-10-13 audit's N12): the entry is pushed BEFORE
   the page changes. setActivePage scrolls to the top, and the browser keeps
   each entry's scroll as it is when the next one is pushed, so pushing after
   it saved 0 for the page being left: Back from the Methodology put the
   Week Board at the top (left at 800 px), though Forward restored 1500. */
function goToPage(page){
  if(!inSharedView()){
    const url = routeUrl(currentRoute(page));
    if(location.pathname + location.search + location.hash !== url) history.pushState(null, '', url);
  }
  setActivePage(page, {focus:true});
}
function replaceRoute(page){
  const active = document.querySelector('.page.active');
  if(inSharedView() || !active || active.id !== 'page-' + page) return;
  history.replaceState(null, '', routeUrl(currentRoute(page)));
}

function applyRoute(r, opts){
  if(!r || !document.getElementById('page-' + r.page)) return;
  const active = document.querySelector('.page.active');
  if(!active || active.id !== 'page-' + r.page) setActivePage(r.page, opts);
  if(r.page === 'board'){
    const s = document.getElementById('week-select');
    const want = r.week || latestWeekKey;
    if(s && want && s.value !== want){ s.value = want; s.dispatchEvent(new Event('change')); }
  }
  if(r.team){
    const s = document.getElementById('teamdive-select');
    if(s && s.value !== r.team){ s.value = r.team; s.dispatchEvent(new Event('change')); }
  }
  if(r.game) openGame(r.game);
  document.querySelectorAll('tr.route-target').forEach(tr => tr.classList.remove('route-target'));
  if(r.experiment){
    const row = document.getElementById('exp-' + r.experiment);
    // A link to a row the decision filter is hiding clears the filter
    // first, or it would scroll to nothing.
    if(row && row.hidden && labShowAll) labShowAll();
    if(row){
      row.classList.add('route-target');
      row.setAttribute('tabindex', '-1');
      row.scrollIntoView({block:'center'});
      row.focus({preventScroll:true});
    }
  }
}

/* #game/<key>: the game's card, after its week is drawn. A filter that hides
   it is cleared first, as a link to a hidden Model Lab row clears its
   filter; on a phone the card's row is opened. */
function openGame(key){
  const find = () => [...document.querySelectorAll('#game-grid > .game-card')].find(c => c.dataset.game === key);
  let card = find();
  if(!card && currentFilter !== 'all'){
    const all = document.querySelector('#filter-row .filter-btn[data-filter=all]');
    if(all){ all.click(); card = find(); }
  }
  if(!card) return;
  const row = document.querySelector(`.nfl-row[aria-controls="${card.id}"]`);
  const phone = row && row.offsetParent;
  if(phone && row.getAttribute('aria-expanded') !== 'true') row.click();
  // On a phone the row names the game and its card, opened below it, drops
  // the header (Stage 75 item 3), so the row is what goes to the top.
  (phone ? row : card).scrollIntoView({block:'start'});
  // Drawing the week replaced the address with #board/<week>; the link
  // named the game, and the address keeps it.
  const want = routeUrl({page:'board', game:key});
  if(!inSharedView() && location.pathname + location.search + location.hash !== want) history.replaceState(null, '', want);
}

(function wireRoutes(){
  const week = document.getElementById('week-select');
  if(week) week.addEventListener('change', ()=> replaceRoute('board'));
  const team = document.getElementById('teamdive-select');
  if(team) team.addEventListener('change', ()=> replaceRoute('teamdive'));
  // popstate covers Back and Forward, and a fragment typed or pasted into the
  // address bar of an open tab.
  window.addEventListener('popstate', ()=> applyRoute(parseRoute(location.hash, routeKnown), {focus:true}));
  // A link that opens on a page focuses its heading, as a tap on the page's
  // nav button does (Stage 76 item 10: it left focus on <body>).
  if(location.hash) applyRoute(parseRoute(location.hash, routeKnown), {focus:true});
})();
/* Stage 80 item 64 (V5): the printed sheet's header says when it was printed. */
window.addEventListener('beforeprint', () => {
  const at = new Date().toLocaleDateString('en-US', {weekday: 'long', month: 'long', day: 'numeric', year: 'numeric'});
  document.querySelectorAll('[data-print-date]').forEach(el => { el.textContent = `Printed ${at}.`; });
});
