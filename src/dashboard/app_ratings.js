/* ---------- Power Ratings ---------- */
/* Places a team moved since the previous weekly update (Stage 19). The arrow
   follows RANK, not rating (Mark, 2026-09-28): a team can gain rating and
   still lose places when others gain more, and an arrow disagreeing with the
   number beside it is exactly what a reader would notice. null (no previous
   ranking) prints nothing; 0 (did not move) prints only a hidden "no change"
   so a screen reader is not left guessing. */
/* Stage 21's thresholds, in one place so the tests read the same numbers
   the page uses. Probabilities on the page are in percent, so the market gap
   and the coin flip are in percentage points. */
const INSIGHT = {RANK_MOVE_MIN: 3, MARKET_GAP_MIN: 10, COIN_FLIP_WITHIN: 5, TREND_MIN_WEEKS: 4};
function rankMoveHtml(change){
  if(change === null || change === undefined) return '';
  if(change === 0) return '<span class="visually-hidden">, no change in rank</span>';
  const up = change > 0, n = Math.abs(change);
  const words = `${up ? 'up' : 'down'} ${n} place${n === 1 ? '' : 's'} since the last update`;
  return `<span class="trend-arrow ${up?'up':'down'}" title="${words[0].toUpperCase() + words.slice(1)}"><span aria-hidden="true">${up?'&#9650;':'&#9660;'}${n}</span><span class="visually-hidden">, ${words}</span></span>`;
}
/* The one line above the table naming the biggest rise and the biggest fall
   (Stage 19). League-wide, not the searched view. Ties are named together,
   two at most and then counted, so a week where five teams rose three places
   does not print a paragraph. Since Stage 21 it names only moves of
   INSIGHT.RANK_MOVE_MIN places or more, and stays hidden in a week with
   none: a one-place shuffle in the middle of the table is not news. */
function moversSentence(teams){
  const moved = teams.filter(t => typeof t.rank_change === 'number'
                                  && Math.abs(t.rank_change) >= INSIGHT.RANK_MOVE_MIN);
  if(!moved.length) return '';
  const changes = moved.map(t => t.rank_change);
  const most = Math.max(...changes), least = Math.min(...changes);
  const named = v => moved.filter(t => t.rank_change === v).map(t => t.name).sort();
  const list = a => a.length <= 2 ? a.join(' and ') : `${a.slice(0, 2).join(', ')} and ${a.length - 2} more`;
  const places = n => `${n} place${n === 1 ? '' : 's'}`;
  const parts = [];
  if(most > 0) parts.push(`${list(named(most))} up ${places(most)}`);
  if(least < 0) parts.push(`${list(named(least))} down ${places(-least)}`);
  return `Biggest moves since the last update: ${parts.join('; ')}.`;
}
/* This season's net rating, week by week, from the same history Team
   Deep-Dive draws (Stage 21). Empty before TREND_MIN_WEEKS weeks exist: two
   or three points draw a line that says more than they know. */
function seasonTrend(team){
  const pts = ((teamHistory && teamHistory.timeline) || {})[team] || [];
  const live = pts.filter(p => /^\d{4} Wk\d+$/.test(p.label) && typeof p.net === 'number');
  if(!live.length) return [];
  const season = live[live.length - 1].label.slice(0, 4);
  const vals = live.filter(p => p.label.startsWith(season + ' ')).map(p => p.net);
  return vals.length >= INSIGHT.TREND_MIN_WEEKS ? vals : [];
}
/* A sparkline scaled to the team's own weeks: it shows direction, and the
   Net column beside it gives the size. The last point is marked. */
function trendSvg(vals){
  if(!vals.length) return '<span class="trend-none" title="Too few weeks this season to draw a trend">&mdash;</span>';
  const W = 84, H = 24, P = 3;
  const lo = Math.min(...vals), hi = Math.max(...vals), span = (hi - lo) || 1;
  const x = i => P + i * (W - 2 * P) / (vals.length - 1);
  const y = v => H - P - (v - lo) / span * (H - 2 * P);
  const pts = vals.map((v, i) => `${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(' ');
  const last = vals.length - 1;
  const words = vals.map(fmtRating).join(', ');
  return `<svg class="trend-spark" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" role="img" aria-label="Net rating each week this season: ${words}">`
    + `<polyline points="${pts}"/><circle cx="${x(last).toFixed(1)}" cy="${y(vals[last]).toFixed(1)}" r="2.5"/></svg>`;
}
let sortKey = 'net', sortDir = -1;
function renderRatings(){
  const movers = document.getElementById('ratings-movers');
  if(movers){
    const line = moversSentence(teams);
    movers.textContent = line;
    movers.hidden = !line;
  }
  const sorted = [...teams].sort((a,b)=>{
    if(sortKey==='team') return a.team.localeCompare(b.team)*sortDir;
    const av = (a[sortKey]===null||a[sortKey]===undefined) ? -Infinity : a[sortKey];
    const bv = (b[sortKey]===null||b[sortKey]===undefined) ? -Infinity : b[sortKey];
    return (av-bv)*sortDir;
  });
  // The # is the team's POWER RATING rank and it travels with the team. It is
  // NOT the row's position in the current sort: on a page titled Power
  // Ratings, sorting by Playoff Odds and relabelling the 9th-rated team "#1"
  // asserts something the model never said, and "#1" is exactly the part a
  // casual reader takes away. The rank is computed once in Python from the
  // net-rating order (`build_teams_js`) so every view agrees on it -- which
  // also means it survives filtering, and a searched team keeps its league
  // position instead of becoming "1" for being the only match on screen.
  const ranked = sorted.map(t=>({...t, _rank: t.rank}));
  const searchEl = document.getElementById('ratings-search');
  const q = searchEl ? searchEl.value.trim().toLowerCase() : '';
  const visible = q ? ranked.filter(t=>
    t.team.toLowerCase().includes(q) || (t.name && t.name.toLowerCase().includes(q))
  ) : ranked;

  /* The simulation count, printed into the Playoff Odds glossary entry.

     It used to live in a card above this table and was shown only while some
     team actually had odds -- a caveat about data that is not on screen being
     just more words. The card is gone; the sentence is on Methodology now,
     where it is a definition rather than a caveat and is therefore true
     whether or not this table has odds in it today. So there is no longer a
     condition, only the number.

     Still filled from playoffMeta rather than written into the prose: the
     count is a property of the run that produced the odds, and a figure typed
     into a sentence is a figure nothing recomputes. */
  const sims = document.getElementById('playoff-sims');
  if(sims && playoffMeta && playoffMeta.n_simulations){
    sims.textContent = playoffMeta.n_simulations.toLocaleString();
  } else if(sims){
    sims.textContent = 'many thousands of';
  }

  const sosNote = document.getElementById('sos-empty-note');
  if(sosNote){
    const anySos = teams.some(t=>t.sos!==null && t.sos!==undefined);
    sosNote.style.display = anySos ? 'none' : 'block';
  }

  const maxAbs = Math.max(...teams.map(t=>Math.abs(t.net)), 0.0001);

  // Print the domain the bars are drawn against. Computed from the whole
  // league, not the filtered view -- searching for one team must not silently
  // rescale the axis under the reader.
  const axMin = document.querySelector('#ratings-table .ax-min');
  const axMax = document.querySelector('#ratings-table .ax-max');
  if(axMin && axMax){
    axMin.textContent = '−' + fmtRatingScale(maxAbs);
    axMax.textContent = '+' + fmtRatingScale(maxAbs);
  }

  const body = document.getElementById('ratings-body');
  if(visible.length === 0){
    body.innerHTML = ratingsNoMatchRow(q);
    return;
  }
  body.innerHTML = visible.map((t)=>{
    const i = t._rank - 1;
    const width = (Math.abs(t.net)/maxAbs)*100;
    // Places moved since the previous weekly update, computed in Python
    // (previous_ranks) so it agrees with the # column. Stage 19 replaced a
    // rating-delta arrow here: the arrow now follows RANK.
    const trendHtml = rankMoveHtml(t.rank_change);
    return `<tr>
      <td class="rank">${i+1}</td>
      <td><div class="team-cell"><a class="row-link" href="${routeHash({page:'teamdive', team:t.team})}"><img class="team-logo" src="${teamLogo(t.team)}" alt="" loading="lazy" referrerpolicy="no-referrer" data-hide-on-error><span class="team-abbr">${t.team}</span><span class="team-full">${t.name}</span></a>${trendHtml}</div></td>
      <td class="num"><div class="net-cell-inner">
        <div class="srs-bar-track diverging" title="${fmtRating(t.net)} per 100 plays; league scale ±${fmtRatingScale(maxAbs)}, centre line is zero"><div class="srs-bar-fill" style="left:${t.net>=0?50:50-width/2}%; width:${width/2}%;"></div></div>
        <span class="net-value">${fmtRating(t.net)}</span>
      </div></td>
      <td class="trend-cell">${trendSvg(seasonTrend(t.team))}</td>
      <td class="num">${fmtRating(t.off)}</td>
      <td class="num">${fmtRating(t.def)}</td>
      <td class="num">${(t.sos===null||t.sos===undefined)
        ? '<span title="No games played yet, so there are no opponents to average.">—</span>'
        : fmtRating(t.sos)}</td>
      <td class="num">${(t.playoff===null||t.playoff===undefined)
        ? '<span title="This team was not in the simulation.">—</span>'
        : t.playoff.toFixed(1)+'%'}</td>
    </tr>`;
  }).join('');
}
document.querySelectorAll('#ratings-table th[data-key]').forEach(th=>{
  const sortBy = ()=>{
    const key = th.dataset.key;
    if(key==='rank') return;
    if(sortKey===key){sortDir*=-1;} else {sortKey=key; sortDir=-1;}
    document.querySelectorAll('#ratings-table th').forEach(h=>{
      h.classList.remove('sorted');
      if(h.hasAttribute('aria-sort')) h.setAttribute('aria-sort', 'none');
    });
    th.classList.add('sorted');
    th.setAttribute('aria-sort', sortDir === -1 ? 'descending' : 'ascending');
    renderRatings();
  };
  th.addEventListener('click', sortBy);
  // A header that sorts is a control, so a keyboard has to reach it: it
  // carries tabindex="0" in the markup, and Enter or Space sorts.
  th.addEventListener('keydown', e=>{
    if(e.key === 'Enter' || e.key === ' '){ e.preventDefault(); sortBy(); }
  });
});
renderRatings();

const ratingsSearchEl = document.getElementById('ratings-search');
if(ratingsSearchEl){
  ratingsSearchEl.addEventListener('input', ()=> renderRatings());
}

/* Proof of lock (Stage 46 item 5): which commit last changed a week's
   picks before its first kickoff, and any commit after it, each linked to
   GitHub, where its time cannot be edited. commits are oldest first, from
   src/sports/nfl/lock_proof.py. Empty when there is nothing to say. */
function lockUtc(ms){
  const d = new Date(ms);
  // ET, as every other time on the board (Stage 68 item 18c, U18).
  return d.toLocaleDateString('en-US', {weekday: 'short', month: 'short', day: 'numeric', timeZone: 'America/New_York'})
    + ', ' + d.toLocaleTimeString('en-US', {hour: 'numeric', minute: '2-digit', timeZone: 'America/New_York'}) + ' ET';
}
function lockCommitLink(c){
  return `<a href="${escapeHtml(c.url)}" target="_blank" rel="noopener">${escapeHtml(c.short)}</a>`;
}
function lockProofHtml(commits, games){
  if(!commits || !commits.length || !games || !games.length) return '';
  const kicks = games.map(kickoffInstant).filter(k => k !== null);
  if(!kicks.length) return '';
  const first = Math.min(...kicks);
  const at = c => Date.parse(c.committed_utc);
  const before = commits.filter(c => at(c) < first), after = commits.filter(c => at(c) >= first);
  const parts = [];
  if(before.length){
    const last = before[before.length - 1];
    const hours = Math.floor((first - at(last)) / 3600000);
    const lead = hours >= 48 ? `${Math.floor(hours / 24)} days` : `${hours} hour${hours === 1 ? '' : 's'}`;
    parts.push(`These picks were last changed in commit ${lockCommitLink(last)} on ${lockUtc(at(last))}, ${lead} before the week's first kickoff.`);
    if(before.length > 1) parts.push(`First saved in ${lockCommitLink(before[0])} on ${lockUtc(at(before[0]))}.`);
  } else {
    parts.push('No commit of these picks is dated before the first kickoff.');
  }
  if(after.length){
    // Stage 77 item 17 (the 2026-10-13 audit's copy fix 6): the sentence says
    // what happened; each commit's own subject, why it was changed, is the
    // link's title, one hover or long-press away, rather than a run of
    // "Stage 52: the NFL becomes the first sport module" in the middle of it.
    const links = after.map(c => lockCommitLink(c).replace('<a href=', `<a title="${escapeHtml(c.subject)}" href=`));
    parts.push(`Changed after kickoff in commit${after.length === 1 ? '' : 's'} ${links.join(', ')}.`);
  }
  return parts.join(' ');
}
function renderLockProof(weekKey, weekData){
  const el = document.getElementById('board-lock-note');
  if(!el) return;
  const commits = (lockProof && lockProof.weeks) ? lockProof.weeks[weekKey] : null;
  const html = (weekData && !weekData.preview) ? lockProofHtml(commits, weekData.games) : '';
  el.innerHTML = html;
  el.hidden = !html;
  // Stage 77 item 16 (the 2026-10-13 audit's copy fix 5): on a preview week
  // the phone's "When these picks were saved, and where to check" opened
  // nothing, since nothing is saved yet; the preview note above it already
  // says when they lock, so the button goes.
  const prov = document.getElementById('board-prov-btn');
  if(prov) prov.hidden = !!(weekData && weekData.preview);
}
