/* ---------- Team Deep-Dive ----------

   The listbox handle, kept because this select is the case enhanceSelect's
   refresh() was written for. That function renders the options it can see at
   the moment it runs, and at that moment this select has none -- they are
   written below, from teamHistory, after the page has loaded. So every write
   to select.innerHTML is a moment the listbox is showing something the select
   no longer says, and has to come back through refresh().

   Null until the first render enhances it, which is why every use is guarded
   rather than assumed: the no-data branch runs BEFORE anything is enhanced. */
let teamDiveListbox = null;

/* The team Team Deep-Dive opens on when no #team/<code> link names one
   (Stage 19): the top of Power Ratings, by the rank Python computed for that
   table. It used to be the first option alphabetically -- Arizona, whatever
   Arizona's season. A link still wins: applyRoute() sets the select after
   this. With no rank 1, or a rank 1 the history file has no name for, it
   falls back to that first option, so the page never opens on nothing. */
function teamDiveDefault(names, ratedTeams){
  const top = (ratedTeams || []).find(t => t.rank === 1);
  if(top && Object.prototype.hasOwnProperty.call(names, top.team)) return top.team;
  return Object.keys(names).sort((a, b) => names[a].localeCompare(names[b]))[0];
}

function renderTeamDive(){
  const select = document.getElementById('teamdive-select');
  const content = document.getElementById('teamdive-content');
  const badge = document.getElementById('teamdive-badge');

  if(!teamHistory || !teamHistory.names || Object.keys(teamHistory.names).length === 0){
    content.innerHTML = stateHtml('missing', 'No team history in this build',
      'This page is drawn from a team history file, and the page was built without one. Nothing here is wrong with any team; the file is what is missing.');
    select.innerHTML = '';
    // Without this the button keeps naming whatever team it last rendered,
    // sitting directly above a message saying there is no data. sync() turns
    // an empty select into a disabled button, which is the honest state.
    if(teamDiveListbox) teamDiveListbox.refresh();
    badge.textContent = '—';
    return;
  }

  if(select.options.length === 0){
    const sortedTeams = Object.keys(teamHistory.names).sort((a,b)=>teamHistory.names[a].localeCompare(teamHistory.names[b]));
    select.innerHTML = sortedTeams.map(t=>`<option value="${t}">${teamHistory.names[t]} (${t})</option>`).join('');
    // Before the listbox is built, so its button names the same team.
    select.value = teamDiveDefault(teamHistory.names, teams);
    select.addEventListener('change', renderTeamDive);
    /* AFTER the change listener, never before -- the same ordering the Week
       Board's call site documents, and for the same reason. enhanceSelect
       writes back by dispatching change on the select, so a listbox built
       first would dispatch into a listener that does not exist yet: the
       button would update, the list would close, and the page below it would
       go on showing the previous team, with every source-reading test green.

       `|| teamDiveListbox` because enhanceSelect returns null for a select it
       has already enhanced. Nothing re-enters this branch today, since the
       sentinel above is the option count and teamHistory does not change
       after load -- but assigning that null would silently discard a working
       handle, and the symptom would be a listbox that stops refreshing. */
    teamDiveListbox = enhanceSelect(select) || teamDiveListbox;
  }

  const team = select.value || select.options[0]?.value;
  const points = (teamHistory.timeline[team] || []);
  badge.textContent = `${points.length} data point${points.length===1?'':'s'}`;

  if(points.length === 0){
    content.innerHTML = stateHtml('waiting', `No history for ${team} yet`,
      'This team has no rated seasons or weeks on record so far.');
    return;
  }

  const maxAbs = Math.max(...points.map(p=>Math.abs(p.net)), 0.0001);
  const rowsHtml = points.map(p=>{
    const width = (Math.abs(p.net)/maxAbs)*100;
    const isLive = p.label.includes('Wk');
    return `<div class="dive-row">
      <span class="dive-label ${isLive?'live':''}">${p.label}</span>
      <div class="srs-bar-track diverging" style="width:140px;" title="${fmtRating(p.net)} per 100 plays; scale ±${fmtRatingScale(maxAbs)} across this team's own history, centre line is zero"><div class="srs-bar-fill" style="left:${p.net>=0?50:50-width/2}%; width:${width/2}%;"></div></div>
      <span class="dive-value">${fmtRating(p.net)}</span>
      ${diveSplitHtml(p)}
    </div>`;
  }).join('');
  // Said once above the rows, not in every row: defense is the one number
  // on the page that runs backwards (Mark, 2026-09-28).
  const splitNote = points.some(p => diveSplitHtml(p))
    ? `<p class="dive-note">Net is offense minus defense. Defense counts expected points allowed, so for defense lower is better.</p>`
    : '';

  content.innerHTML = diveTeamHtml(team, teamHistory.names[team], favStar('nfl', team, teamHistory.names[team] || team)) + renderTeamNews(team)
    + `<div class="table-wrap" style="padding:var(--s5) var(--s5);">${splitNote}${diveScaleHtml(maxAbs)}${rowsHtml}</div>`
    + renderTeamGames(team);
  wireTeamGameToggles();
}

/* Stage 79 item 49 (the 2026-10-13 audit's N10): Deep-Dive's bars' scale,
   printed above the bar column. It is this team's own largest net, not the
   league's, so a full bar here and a full bar on Power Ratings are different
   sizes, and the page says so. */
function diveScaleHtml(maxAbs){
  const scale = fmtRatingScale(maxAbs);
  return `<p class="dive-note dive-scale-note">Each bar is scaled to this team's largest net in its own history, about ${scale} either way; the line through them is zero.</p>`
    + `<div class="dive-row dive-scale" aria-hidden="true"><span class="dive-label"></span>`
    + `<div class="net-axis dive-axis"><span class="ax-min">−${scale}</span><span class="ax-zero">0</span><span class="ax-max">+${scale}</span></div>`
    + `<span class="dive-value"></span></div>`;
}

/* Which team the page is showing, as a logo and the full name above
   everything else (Mark, 2026-09-28: it re-establishes whose page this is).
   The logo is decorative, alt="", because the name beside it is the text; a
   logo ESPN will not serve hides and leaves the name, the fallback every
   logo here has. */
function diveTeamHtml(team, name, star = ''){
  return `<div class="dive-team"><img class="dive-logo" src="${teamLogo(team)}" alt="" loading="lazy" referrerpolicy="no-referrer" data-hide-on-error>`
    + `<span class="dive-team-name">${name || team}</span>${star}</div>`;
}

/* Offense and defense beside a Team Deep-Dive row's net (Stage 19), in the
   same per-100-plays units through the same formatter. Nothing unless both
   are numbers -- a history point can carry net alone. On a phone the pair
   drops to a second small line under the row (CSS, below 768px). */
function diveSplitHtml(p){
  if(typeof p.off !== 'number' || typeof p.def !== 'number') return '';
  return `<span class="dive-split"><span>Offense ${fmtRating(p.off)}</span><span title="Expected points allowed: lower is better">Defense ${fmtRating(p.def)}</span></span>`;
}

/* ---------- Team Deep-Dive: this week's team news (Stage 16) ----------

   src/sports/nfl/team_news.py writes, per locked week not yet graded, each team's
   starters listed Out or Doubtful, a count of those Questionable, and the
   quarterback the saved pick was made with. generate_dashboard.py attaches
   that to weeks[k].news only while the week is still being played, so an item
   expires with its week without anything here checking dates.

   Short on purpose (CLAUDE.md Stage 16): one line per kind of news, never
   more than five, each with its source and date. ABSENT IS NOT HEALTHY: a
   report not yet out says so, and never renders as "nobody hurt". */
function newsWeekKey(){
  const keys = weekKeysSorted.filter(k => weeks[k].news && weeks[k].news.teams);
  return keys.length ? keys[keys.length - 1] : null;
}

function newsDate(iso){
  if(!iso) return null;
  const d = new Date(iso);
  if(isNaN(d)) return null;
  return d.toLocaleDateString('en-US', {timeZone:'America/New_York', weekday:'short', month:'short', day:'numeric'});
}

// [{text, source}] for one team's entry, most important first. Plain text;
// the renderer escapes it.
function teamNewsItems(entry, week, readAt){
  const items = [];
  const read = newsDate(readAt);
  const report = `Official injury report, via nflverse${read ? ` · read ${read}` : ''}`;
  const people = list => list.map(p => {
    const bits = [p.position, p.injury ? p.injury.toLowerCase() : null].filter(Boolean);
    return bits.length ? `${p.name} (${bits.join(', ')})` : p.name;
  }).join(', ');

  const qb = entry.qb;
  if(qb && qb.name){
    // The pick's quarterback on the injury report is the one line that
    // changes how far to trust the pick, so it replaces the usual QB line
    // rather than sitting two lines below it looking unrelated.
    const listed = (entry.out || []).some(p => p.name === qb.name) ? 'out'
      : (entry.doubtful || []).some(p => p.name === qb.name) ? 'doubtful' : null;
    items.push({
      text: listed
        ? `The model's pick was made with ${qb.name} at quarterback, and he is listed as ${listed}.`
        : qb.changed_from
        ? `New starting quarterback: ${qb.name}, in place of ${qb.changed_from}.`
        : `Quarterback: ${qb.name}, the same starter as last game.`,
      source: `The quarterback the model's week ${week} pick was made with`,
    });
  }

  if(entry.injury_report === 'not yet published'){
    items.push({text: `The week ${week} injury report is not out yet, so there is no injury news.`, source: report});
  } else if(entry.injury_report !== 'published'){
    items.push({text: `Starters could not be checked: there is no depth chart for this team.`,
                source: `nflverse depth charts${read ? ` · read ${read}` : ''}`});
  } else {
    const out = entry.out || [], doubtful = entry.doubtful || [];
    const q = entry.questionable_starters || 0;
    if(out.length) items.push({text: `Out: ${people(out)}.`, source: report});
    if(doubtful.length) items.push({text: `Doubtful: ${people(doubtful)}.`, source: report});
    if(q) items.push({text: `${q} starter${q === 1 ? '' : 's'} listed as questionable.`, source: report});
    if(!out.length && !doubtful.length && !q){
      items.push({text: 'No starters listed as out, doubtful or questionable.', source: report});
    }
  }
  return items;
}

function renderTeamNews(team){
  const key = newsWeekKey();
  const head = sub => `<div class="dive-news"><h3 class="dive-news-title">This week</h3>
    <div class="dive-news-sub">${sub}</div>`;
  if(!key){
    return head(`No team news right now. It appears once a week's picks are locked,
      and goes when that week has been graded.`) + `</div>`;
  }
  const w = weeks[key];
  const entry = w.news.teams[team];
  const game = (w.games || []).find(g => g.home === team || g.away === team);
  if(!entry || !game){
    return head(`${escapeHtml(team)} have no game in week ${w.week}.`) + `</div>`;
  }
  const where = game.home === team ? `vs ${escapeHtml(game.away)}` : `@ ${escapeHtml(game.home)}`;
  const rows = teamNewsItems(entry, w.week, w.news.read_at).map(it =>
    `<li class="dive-news-item"><span class="dive-news-text">${escapeHtml(it.text)}</span>
      <span class="dive-news-src">${escapeHtml(it.source)}</span></li>`).join('');
  return head(`Week ${w.week}, ${where}. Starters only; backups are left out to keep this short.`)
    + `<div class="table-wrap"><ul class="dive-news-list">${rows}</ul></div></div>`;
}

/* ---------- Team Deep-Dive: game drill-down ----------

   The net-rating history above answers "how good has this team been". This
   answers "what did the model actually say about their games, and was it
   right" -- which is the question the ratings are only a proxy for.

   Everything in `weeks` is stored from the HOME team's point of view: fbA_home
   and mktB_home are home win probabilities, spread_line is the home team's
   line (positive when home is favoured, asserted at runtime in
   ats_evaluation.py), and why{} holds contributions toward the home side. A
   page built around one selected team has to flip all of it, and getting a
   flip wrong is invisible: every number still looks like a plausible number.
   So the flip happens once, here, and tests/test_team_dive.py checks it
   against the away side of a real game rather than trusting it. */
// null/undefined stay null (not graded); everything else becomes a real
// boolean. Keeps "was the model right" a tri-state rather than collapsing
// "not graded yet" into "wrong".
function asBool(v){
  return (v === null || v === undefined) ? null : !!v;
}

function teamGamesFor(team){
  const out = [];
  weekKeysSorted.forEach(k=>{
    (weeks[k].games || []).forEach(g=>{
      if(g.home !== team && g.away !== team) return;
      const isHome = g.home === team;
      const flipPct = p => (p===null||p===undefined) ? null : (isHome ? p : 100 - p);
      out.push({
        weekKey: k,
        label: weekLabel(k),
        isHome,
        opponent: isHome ? g.away : g.home,
        probA: flipPct(g.fbA_home),
        probB: flipPct(g.mktB_home),
        line: (g.spread===null||g.spread===undefined) ? null : (isHome ? g.spread : -g.spread),
        graded: !!g.graded,
        // actual_home_win is the home side's result, so the selected team won
        // when it IS the home side and that is true, or when it is not and
        // that is false.
        won: (g.graded && g.actual_home_win !== null && g.actual_home_win !== undefined)
              ? (isHome ? !!g.actual_home_win : !g.actual_home_win) : null,
        // A graded game with no winner: Team Deep-Dive says "Tie", not "not
        // yet played" (Stage 30 item 1).
        tie: !!g.graded && g.result === 'tie',
        // Normalised to real booleans here, at the boundary, because the
        // graded files store 1/0 rather than true/false. A downstream
        // `=== true` against a 1 is quietly false, which showed up as
        // "Model A called 0 of 1" beside a game the model had plainly won,
        // and as the correct/wrong marks silently not rendering at all.
        modelACorrect: asBool(g.model_a_correct),
        modelBCorrect: asBool(g.model_b_correct),
        // Contributions point toward the HOME team, so they negate for an
        // away view -- a +0.10 edge for the home side is a -0.10 edge here.
        why: g.why ? Object.fromEntries(Object.entries(g.why)
              .map(([k2, v]) => [k2, isHome ? v : -v])) : null,
      });
    });
  });
  return out;
}

const WHY_LABELS = {off_matchup: 'Offense', def_matchup: 'Defense',
                    qb_matchup: 'QB', qb_change: 'QB change'};

/* One game's result on Team Deep-Dive: W, L, T for a tie, or "not yet
   played". A tie used to read as unplayed because its won is null. */
function diveResultHtml(g){
  if(g.tie) return `<span class="dive-result tie">T</span>`;
  if(g.won === null) return `<span class="dive-pending">not yet played</span>`;
  return `<span class="dive-result ${g.won?'won':'lost'}">${g.won?'W':'L'}</span>`;
}

/* The line above a team's games: its record over graded games, with ties
   as a third figure (W-L-T), and how many each model called. A tie has no
   winner, so it is in the record but not in either model's count. */
function diveSummaryHtml(team, games){
  const decided = games.filter(g => g.won !== null);
  const wins = decided.filter(g => g.won).length;
  const ties = games.filter(g => g.tie).length;
  const n = decided.length + ties;
  if(!n) return `<div class="dive-games-summary">None of these games have been graded yet,
       so there is no record to report.</div>`;
  const aRight = decided.filter(g => g.modelACorrect === true).length;
  const bRight = decided.filter(g => g.modelBCorrect === true).length;
  return `<div class="dive-games-summary">${team} are <b>${wins}-${decided.length-wins}${ties ? '-' + ties : ''}</b>
       across ${n} graded game${n===1?'':'s'} &middot;
       Model A called ${aRight} of ${decided.length} &middot;
       Model B called ${bRight} of ${decided.length}</div>`;
}

function renderTeamGames(team){
  const games = teamGamesFor(team);
  if(games.length === 0){
    // Distinct from "no history": the ratings chart above is backtested and
    // goes back to 2020, while saved per-game predictions only start when the
    // weekly routine does. An empty list here is normal, not broken.
    return stateHtml('note', `No saved predictions for ${team} yet.`,
      `The rating history above is replayed from past seasons; this list only covers weeks the
      live weekly run has actually saved predictions for, so it fills in from
      the first run of the season onward.`, null, 'state--after');
  }

  const summary = diveSummaryHtml(team, games);

  const rows = games.map((g, i) => {
    const pct = p => p===null ? '—' : `${p.toFixed(1)}%`;
    const lineText = g.line===null ? '—'
      : (g.line > 0 ? `-${g.line}` : (g.line < 0 ? `+${Math.abs(g.line)}` : 'PK'));
    const result = diveResultHtml(g);
    const mark = c => c === true ? '<span class="dive-tick">correct</span>'
      : c === false ? '<span class="dive-cross">missed</span>' : '';

    const whyHtml = g.why
      ? Object.entries(g.why)
          .map(([k, v]) => whyRow(WHY_LABELS[k] || k, v)).join('')
      : `<div class="why-row"><span class="why-label">No breakdown</span></div>`;

    return `<div class="dive-game" data-i="${i}">
      <button class="dive-game-head" aria-expanded="false" data-toggle="${i}">
        <span class="dive-game-week">${g.label}</span>
        <span class="dive-game-opp">${g.isHome ? 'vs' : '@'} ${g.opponent}</span>
        <span class="dive-game-line"><span class="visually-hidden">Line </span>${lineText}</span>
        <span class="dive-game-prob" title="Model B win probability for ${team}"><span class="visually-hidden">Model B </span>${pct(g.probB)}</span>
        <span class="dive-game-res"><span class="visually-hidden">Result </span>${result}</span>
      </button>
      <div class="why-panel" id="dive-why-${i}">
        <div class="dive-why-head">
          Model A gave ${team} ${pct(g.probA)} ${mark(g.modelACorrect)} &middot;
          Model B gave ${team} ${pct(g.probB)} ${mark(g.modelBCorrect)}
        </div>
        <div class="dive-why-note">Contributions shown from ${team}'s side. Positive helps ${team}.</div>
        ${whyHtml}
      </div>
    </div>`;
  }).join('');

  return `<div class="dive-games">
    <h3 class="dive-games-title">Games</h3>
    ${summary}
    <div class="table-wrap">
      <div class="dive-games-head" aria-hidden="true">
        <span class="dgh-week">Week</span><span class="dgh-opp">Opponent</span>
        <span class="dgh-line">Line</span><span class="dgh-prob" title="Model B win probability for ${team}">Model B</span>
        <span class="dgh-res">Result</span>
      </div>
      ${rows}
    </div>
  </div>`;
}

function wireTeamGameToggles(){
  document.querySelectorAll('#teamdive-content .dive-game-head').forEach(btn=>{
    btn.addEventListener('click', ()=>{
      const panel = document.getElementById('dive-why-' + btn.dataset.toggle);
      if(!panel) return;
      const open = panel.classList.toggle('open');
      btn.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
  });
}
// Called here, below WHY_LABELS, and not up beside the function definition.
// WHY_LABELS is a const, so a call placed before it sits in the temporal dead
// zone and throws the moment a team has games to render. The first draft
// dropped this call entirely while moving code around, which was silent: the
// select simply stayed empty and nothing errored.
renderTeamDive();
/* Stage 80 item 53: a star redraws the board with its team's games first. */
installFavStars(() => { renderGames(); renderTeamDive(); });
installCompare();

