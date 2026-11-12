/* The day boards' shared functions (Stage 87 item 1; decision 0006).
   The NHL and NBA pages carried byte-identical copies of these; each page now
   includes this file before its own script, in the same <script> block, so a
   fix lands on both boards at once. A function that differs between the sports
   stays in that sport's nhl.js or nba.js. */

function stateHtml(kind, title, text){
  return `<div class="state state--${kind}" role="status"><span class="state-title">${title}</span>${text ? `<p>${text}</p>` : ''}</div>`;
}

function setScrollStop(el, scrolls){
  const attrs = {tabindex: () => '0', role: () => 'region', 'aria-label': scrollStopLabel};
  const marked = el.hasAttribute('data-scroll-stop');
  const added = marked ? el.getAttribute('data-scroll-stop').split(' ').filter(Boolean) : [];
  if(scrolls && !el.querySelector(FOCUSABLE_INSIDE)){
    for(const [name, value] of Object.entries(attrs)){
      if(added.includes(name)) el.setAttribute(name, value(el));
      else if(!el.hasAttribute(name)){ el.setAttribute(name, value(el)); added.push(name); }
    }
    el.setAttribute('data-scroll-stop', added.join(' '));
  } else if(marked){
    added.forEach(name => el.removeAttribute(name));
    el.removeAttribute('data-scroll-stop');
  }
}

function fitTables(){
  document.querySelectorAll('.table-wrap').forEach(w => {
    const t = w.querySelector('table');
    if(!t || !w.clientWidth) return;
    const fits = t.offsetWidth <= w.clientWidth;
    w.classList.toggle('fits', fits);
    setScrollStop(w, !fits);
  });
}

/* Stage 77 item 32 (the 2026-10-13 audit's B1): the board's eyebrow names the
   week it shows. Before opening night the board opens on the week of the
   first games, and it said "This Week" over "Week of Oct 19" on the 13th. */
function weekEyebrow(week, thisWeek){
  if(week === thisWeek) return 'This Week';
  const next = dayDate(thisWeek);
  next.setUTCDate(next.getUTCDate() + 7);
  if(week === dayIso(next)) return 'Next Week';
  return week > thisWeek ? 'Coming Up' : 'Earlier';
}

function markerPath(shape, cx, cy, r){
  const s = r * 0.92;
  if(shape === 'square') return `<rect x="${(cx-s).toFixed(1)}" y="${(cy-s).toFixed(1)}" width="${(2*s).toFixed(1)}" height="${(2*s).toFixed(1)}" rx="1"`;
  if(shape === 'triangle') return `<polygon points="${cx},${(cy-r*1.15).toFixed(1)} ${cx+r},${(cy+r*0.75).toFixed(1)} ${cx-r},${(cy+r*0.75).toFixed(1)}"`;
  return `<circle cx="${cx}" cy="${cy}" r="${r}"`;
}

function side(pHome, g){
  if(pHome === null || pHome === undefined) return null;
  if(Math.abs(pHome - 50) < EVEN_BAND) return {team: null, pct: Math.max(pHome, 100 - pHome)};
  return pHome >= 50 ? {team: g.home, pct: pHome} : {team: g.away, pct: 100 - pHome};
}

function sideText(s){ return s.team ? `${s.team} ${Math.round(s.pct)}%` : `even (${Math.round(s.pct)}%)`; }
/* The saved pick and the chance its leading model gave it, as the row and
   the card both print it (Stage 75 item 2): "TOR 63%", or "TOR 51% · even"
   inside EVEN_BAND, where the card's headline used to call the game too
   close beside a row that said "TOR 51%". */
function pickText(g, p){
  const lead = p.b !== null && p.b !== undefined ? p.b : p.a;
  const chance = Math.round((p.pick === g.home ? lead : 1 - lead) * 100);
  return `${p.pick} ${chance}%${Math.abs(lead * 100 - 50) < EVEN_BAND ? ' · even' : ''}`;
}

function lanes(vals){
  const keys = Object.keys(vals).filter(k => vals[k] !== null && vals[k] !== undefined);
  const out = {};
  keys.forEach(k => { out[k] = keys.some(o => o !== k && Math.abs(vals[o] - vals[k]) < NEAR) ? LANE[k] : 0; });
  return out;
}

function american(p){ return p > 0 ? `+${p}` : `−${Math.abs(p)}`; }
function endTeam(abbr){
  const src = logo(abbr);
  const img = src ? `<img class="card-end-logo" src="${src}" alt="" loading="lazy" referrerpolicy="no-referrer" data-hide-on-error>` : '';
  return `<span class="card-end-team">${img}${abbr}</span>`;
}

function badge(picked, result){
  if(!picked) return '<span class="pick-badge placeholder"></span>';
  const graded = result === 'correct' || result === 'wrong';
  const state = !graded ? 'picked' : (result === 'correct' ? 'correct' : 'incorrect');
  const path = state === 'incorrect' ? '<path d="M6 6l12 12M18 6L6 18"/>' : '<path d="M20 6L9 17l-5-5"/>';
  return `<span class="pick-badge ${state}"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round">${path}</svg></span>`;
}

/* A model's side is the side of 50% its chance for the home team falls on,
   the rule the saved pick follows (exactly 50% picks the home team). */
function modelSide(prob, g){ return prob === null || prob === undefined ? null : (prob >= 0.5 ? g.home : g.away); }
function winnerOf(g){
  if(g.status !== 'final' || g.hs === null || g.hs === undefined || g.as === null || g.as === undefined || g.hs === g.as) return null;
  return g.hs > g.as ? g.home : g.away;
}

function weekDays(week){
  const out = [];
  const d = dayDate(week);
  for(let i = 0; i < 7; i++){ out.push(dayIso(d)); d.setUTCDate(d.getUTCDate() + 1); }
  return out;
}

function defaultDay(week, games, today){
  if(weekDays(week).includes(today)) return today;
  const days = [...new Set(games.map(g => g.day))].sort();
  return days[0] || week;
}

/* "3 games, 1 of 1 correct so far", from the saved picks' grades. */
function daySummary(games, picks){
  const n = games.length;
  if(!n) return 'No games this day.';
  const graded = games.map(g => picks[g.id]).filter(p => p && (p.result === 'correct' || p.result === 'wrong'));
  const right = graded.filter(p => p.result === 'correct').length;
  let s = `${n} game${n === 1 ? '' : 's'}`;
  if(graded.length) s += `, ${right} of ${graded.length} correct so far`;
  else {
    const locked = games.filter(g => picks[g.id]).length;
    if(locked) s += `, ${locked} locked`;
  }
  return s;
}

/* Stage 75 item 3: an opened card is brought on screen. A row near the
   bottom of a phone opened its card below the fold and never scrolled
   (NHL card 612 to 1052 px, NFL 704 to 1195 px, on an 844 px phone). 'nearest'
   leaves a card that is already in view where it is. */
function revealOpened(panel){
  const still = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;
  panel.scrollIntoView({block: 'nearest', behavior: still ? 'auto' : 'smooth'});
}

function stepWeek(by){
  const i = WEEK_KEYS.indexOf(currentWeek) + by;
  if(i < 0 || i >= WEEK_KEYS.length) return;
  currentWeek = WEEK_KEYS[i];
  renderBoard();
  replaceRoute('board');
}

/* Stage 80 item 57 (the 2026-10-13 audit's F11): on the day board [ and ]
   step a day and Shift with them a week. A day past the week's edge opens
   the next week on its first day (the week before on its last). */
function stepDay(by){
  const days = weekDays(currentWeek);
  const i = days.indexOf(currentDay) + by;
  if(i >= 0 && i < days.length){
    currentDay = days[i];
  } else {
    const w = WEEK_KEYS.indexOf(currentWeek) + by;
    if(w < 0 || w >= WEEK_KEYS.length) return;
    currentWeek = WEEK_KEYS[w];
    const next = weekDays(currentWeek);
    currentDay = by > 0 ? next[0] : next[next.length - 1];
  }
  renderBoard();
  replaceRoute('board');
}

/* Which way a key steps, and whether a week: Shift+[ arrives as "{". */
function dayKeyStep(e){
  if(e.ctrlKey || e.metaKey || e.altKey) return null;
  const by = e.key === '[' || e.key === '{' ? -1 : e.key === ']' || e.key === '}' ? 1 : 0;
  return by ? {by, week: e.shiftKey || e.key === '{' || e.key === '}'} : null;
}

/* Stage 79 item 46: a graded pick as src/core/accuracy.js reads it. */
function accGames(graded){
  return graded.map(({p, g}) => ({day: g.day, a: p.a, b: p.b, m: p.market ? p.market.prob : null,
    home: winnerOf(g) === g.home, c: pickChance(p, g), right: p.result === 'correct'}));
}

/* Stage 84 item 7 (the 2026-11-02 review): the held-out seasons' scores with
   the registered Brier column (tests/test_heldout_table.py). */
function heldOutTable(scores, names, sport){
  const rows = names.filter(([, k]) => scores[k]).map(([n, k]) => { const v = scores[k];
    return `<tr><th scope="row">${n}</th><td class="num">${Number(v.games).toLocaleString('en-US')}</td><td class="num">${v.log_loss.toFixed(4)}</td><td class="num">${v.brier.toFixed(4)}</td><td class="num">${(v.accuracy * 100).toFixed(1)}%</td></tr>`; }).join('');
  return `<div class="table-wrap"><table class="metrics-table ${sport}-table"><caption class="visually-hidden">Scores on the held-out seasons</caption>
    <thead><tr><th scope="col">Forecast</th><th scope="col" class="num">Games</th><th scope="col" class="num">Log loss</th><th scope="col" class="num">Brier</th><th scope="col" class="num">Accuracy</th></tr></thead>
    <tbody>${rows}</tbody></table></div>`;
}

/* Stage 84 items 1 and 2 (the 2026-11-02 review): the registered forward test,
   from results/<sport>/forward_<season>.json (tests/test_forward_on_page.py). */
function forwardHtml(f, sport){
  const NAMES = [['Model A', 'model_a'], ['Model B', 'model_b'], ['Market', 'market'], ['Base rate', 'base_rate']];
  const PAIRS = [['Model A against the base rate', 'model_a_minus_base_rate'], ['Model B against Model A', 'model_b_minus_model_a'], ['Model B against the market', 'model_b_minus_market']];
  const sgn = x => (x < 0 ? '&minus;' : '+') + Math.abs(x).toFixed(4);
  if (!f || !f.graded_picks) return `<p class="${sport}-lede">No saved pick has a final score yet, so the forward test has nothing to score.</p>`;
  const rows = NAMES.filter(([, k]) => f.scores[k]).map(([n, k]) => { const v = f.scores[k];
    return `<tr><th scope="row">${n}</th><td class="num">${v.games}</td><td class="num">${v.log_loss.toFixed(4)}</td><td class="num">${v.brier.toFixed(4)}</td><td class="num">${(v.accuracy * 100).toFixed(1)}%</td></tr>`; }).join('');
  const pairs = PAIRS.filter(([, k]) => f.comparisons[k]).map(([n, k]) => { const c = f.comparisons[k];
    return `<tr><th scope="row">${n}</th><td class="num">${c.games}</td><td class="num">${c.days}</td>`
      + (c.note ? `<td colspan="2">${c.note}</td>` : `<td class="num">${sgn(c.diff)}</td><td class="num">[${sgn(c.low)}, ${sgn(c.high)}]`
        + (c.few_days ? `<br><span class="forward-games">games [${sgn(c.few_days.game_low)}, ${sgn(c.few_days.game_high)}]</span>` : '') + '</td>') + '</tr>'; }).join('');
  // Stage 95 item 37: under 20 game days the day-block interval is rough, so the
  // interval that resamples single games is printed under it, and this says why.
  const few = PAIRS.map(([, k]) => f.comparisons[k]).find(c => c && c.few_days);
  const fewNote = few ? ` Only ${few.days} game days are in so far, under the ${few.few_days.min_days} that make whole-day resampling dependable, so each interval is shown with the one that resamples single games under it (&ldquo;games&rdquo;), which is narrower because it ignores how games on one day move together. The day-block interval is the one the registration uses.` : '';
  const level = (f.interval_rule.level * 100).toFixed(2);
  return `<p class="${sport}-lede">Every saved pick whose game is final, ${f.graded_picks} of them through ${f.through}, scored as the registration says (<code>${f.registered}</code>). Model B and the market are scored only on the picks that had a price.${f.market_price ? ' ' + f.market_price.said : ''}</p>
    <div class="table-wrap"><table class="metrics-table ${sport}-table"><caption class="visually-hidden">The forward test's scores</caption>
    <thead><tr><th scope="col">Forecaster</th><th scope="col" class="num">Picks</th><th scope="col" class="num">Log loss</th><th scope="col" class="num">Brier</th><th scope="col" class="num">Accuracy</th></tr></thead><tbody>${rows}</tbody></table></div>
    <div class="table-wrap"><table class="metrics-table ${sport}-table"><caption class="visually-hidden">The forward test's comparisons</caption>
    <thead><tr><th scope="col">Comparison</th><th scope="col" class="num">Games</th><th scope="col" class="num">Days</th><th scope="col" class="num">Log loss difference</th><th scope="col" class="num">${level}% interval</th></tr></thead><tbody>${pairs}</tbody></table></div>
    <p class="${sport}-lede">A difference below zero means the first forecaster did better. Each interval resamples whole game days ${f.interval_rule.resamples.toLocaleString('en-US')} times, paired on the games both forecasters scored.${fewNote} The intervals are reported, not judged: the season-end decision rule is registered on its own.</p>${calibrationTable(f, sport, level)}`;
}

/* Stage 84 item 5: calibration intercept and slope for Models A and B, from
   the same file. Older files have no calibration block, and show none. */
function calibrationTable(f, sport, level){
  if (!f.calibration) return '';
  const NAMES = [['Model A', 'model_a'], ['Model B', 'model_b']];
  const fx = x => (x < 0 ? '&minus;' : '') + Math.abs(x).toFixed(2);
  const cell = v => v.value === null ? `<td colspan="2">${v.note}</td>`
    : `<td class="num">${fx(v.value)}</td><td class="num">[${fx(v.low)}, ${fx(v.high)}]</td>`;
  const rows = NAMES.filter(([, k]) => f.calibration[k]).map(([n, k]) => { const c = f.calibration[k];
    return `<tr><th scope="row">${n}</th><td class="num">${c.games}</td>`
      + (c.note ? `<td colspan="4">${c.note}</td>` : cell(c.intercept) + cell(c.slope)) + '</tr>'; }).join('');
  return `
    <div class="table-wrap"><table class="metrics-table ${sport}-table"><caption class="visually-hidden">Calibration of Models A and B</caption>
    <thead><tr><th scope="col">Calibration</th><th scope="col" class="num">Picks</th><th scope="col" class="num">Intercept</th><th scope="col" class="num">${level}% interval</th><th scope="col" class="num">Slope</th><th scope="col" class="num">${level}% interval</th></tr></thead><tbody>${rows}</tbody></table></div>
    <p class="${sport}-lede">Calibration asks whether the probabilities mean what they say. A perfectly calibrated model has an intercept of 0 and a slope of 1. An intercept above 0 means home teams won more often than the model said; a slope above 1 means its probabilities sat too close to 50%, and below 1 too far from it. They are two fits, not one: the intercept is fitted with the slope held at 1 (calibration in the large), and the slope is fitted with an intercept of its own. Intervals resample whole game days, as above, and are reported, not judged.</p>`;
}

/* Stage 85 item 3 (the 2026-11-02 review): the drift baseline's season-to-
   season spread, from experiments/<stage>/results/model_a_by_season.json.
   (tests/test_season_spread.py). */
function spreadHtml(s, sport){
  if (!s || !s.seasons) return '';
  const items = s.seasons.map(r => `${r.label} ${r.log_loss.toFixed(4)}`).join(', ');
  return `<p class="${sport}-lede">How far one season moves on its own: the same Model A, at the same settings and with the backtest&#39;s walk-forward, scored a log loss of ${items}, a range of ${s.spread.range.toFixed(4)} from the best season to the worst. The baseline pools the last two (${s.baseline.pooled_confirmation.toFixed(4)}).</p>`;
}

/* Stage 84 item 6 (the 2026-11-02 review): the daily run writes the drift
   check's result and the page never showed it. */
function driftStatus(d, rule){
  const n = x => Number(x).toLocaleString('en-US');
  const min = rule ? (rule.rule.checkpoints || [rule.rule.min_games])[0] : 100;
  if (!d || !d.games) return 'No pick has been graded yet, so the drift check has nothing to test.';
  const own = d.without_availability ? ` for the same picks, ${d.without_availability} of which were made without the injury report and are held to the backtest without it` : '';
  const now = `Model A&#39;s mean log loss over ${d.games} graded games is ${d.mean_log_loss.toFixed(4)}, against ${d.baseline.toFixed(4)} in the backtest${own}.`;
  if (d.games < min) return `${d.games} of the ${min} graded games the drift check needs before it can flag. ${now}`;
  const last = (d.looks || []).slice(-1)[0];
  const when = !last ? '' : ` Its last look was at ${n(last.games)} graded games${d.next_look ? `; the next is at ${n(d.next_look)}` : ', the season&#39;s last'}.`;
  return d.flagged ? `<b>Flagged.</b> ${now} At a registered look that was significantly above the backtest, and an issue is open.${when}` : `Not flagged. ${now}${when}`;
}

/* Stage 85 item 1 (the 2026-11-02 review): the drift check looks only at the
   registered checkpoints, at a level shared among them (tests/test_drift_looks.py). */
function driftLooks(rule){
  if (!rule || !rule.rule.checkpoints) return '';
  const r = rule.rule, cs = r.checkpoints.map(x => Number(x).toLocaleString('en-US'));
  const list = cs.length > 1 ? `${cs.slice(0, -1).join(', ')} and ${cs[cs.length - 1]}` : cs[0];
  // Stage 95 item 31: each look against the backtest over a season's first that many games.
  const at = key => r.checkpoints.map(c => `${Number(c).toLocaleString('en-US')}, ${Number(rule[key + '_by_look'][String(c)]).toFixed(4)}`).join('; ');
  const base = rule.baseline_by_look
    ? `log loss over a season&#39;s first that many games, the confirmation seasons pooled (${at('baseline')}${rule.baseline_no_availability_by_look ? `; a pick made without the injury report against the model without it: ${at('baseline_no_availability')}` : ''})`
    : rule.baseline_no_availability
    ? `figure for those picks (${rule.baseline.value.toFixed(4)} for a pick made with the injury report, ${rule.baseline_no_availability.value.toFixed(4)} for one made without it)`
    : rule.baseline.value.toFixed(4);
  return `it looks only at ${list} graded games, and at each flags when the one-sided ${pct(r.per_look_level)} lower bound of Model A&#39;s log loss over the first that many is above the backtest&#39;s ${base}. That is the one-sided ${pct(r.one_sided_level)} shared among the ${cs.length} looks, which holds the season&#39;s chance of a false flag near ${pct(1 - r.one_sided_level)}. A flag at any look stands for the season.`;
}

function setMoreSheetOpen(open){
  const sheet = document.getElementById('bnav-more-sheet');
  if(!sheet) return;
  sheet.classList.toggle('open', open);
  sheet.inert = !open;
}
