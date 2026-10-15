/* Season accuracy for the NHL's and NBA's pages (Stage 79 item 46, the
   2026-10-13 UI/UX audit's L5 and B4). The NHL's Accuracy was a table and
   the NBA's Checking the AI's work prose only, where the NFL's Season
   Accuracy draws a race, a trend and a calibration diagram. One component
   draws all three for both sports, in the NFL's look: the race is the NFL
   scoreboard's markup (its classes, so the shared stylesheet styles it),
   and the two SVGs follow its charts' conventions. Each sport passes the
   graded games it builds from its own saved picks:

     {day, a, b, m, home, c, right}

   a, b and m are Model A's, Model B's and the market's chance that the home
   side wins (null when that forecast had none), home whether the home side
   won, c the chance the pick gave the side it picked, and right whether the
   pick was. With nothing graded each chart draws its frame and says inside
   it why it is empty, rather than leaving a sentence where a chart will be.
   Included ahead of each sport's script, after routes.js. */
const ACC_SERIES = [
  {key: 'm', name: 'Market', subject: 'The betting market', series: 'var(--series-c)', shape: 'tri'},
  {key: 'b', name: 'Model B', subject: 'Model B', series: 'var(--series-b)', shape: 'sq'},
  {key: 'a', name: 'Model A', subject: 'Model A', series: 'var(--series-a)', shape: 'dot'},
];
/* A forecast's record: the games it picked a side in (50% exactly picks
   none) and how many of those its side won. */
function accRecord(games, key){
  const decided = games.filter(g => g[key] !== null && g[key] !== undefined && g[key] !== 0.5);
  const correct = decided.filter(g => (g[key] > 0.5) === g.home).length;
  return {correct, n: decided.length, pct: decided.length ? correct / decided.length * 100 : null};
}
/* The NFL scoreboard's sentence (scoreboardVerdict), for three forecasts. */
function accVerdict(rows){
  if(rows.every(r => r.n === 0)) return 'Nothing is graded yet.';
  const sorted = [...rows].sort((a, b) => b.correct - a.correct);
  const top = sorted[0], gap = top.correct - sorted[1].correct;
  if(!rows.every(r => r.n === rows[0].n)) return `${top.subject} has the best record so far.`;
  if(gap > 0) return `${top.subject} leads by ${gap} game${gap === 1 ? '' : 's'}.`;
  const level = sorted.filter(r => r.correct === top.correct);
  if(level.length === rows.length) return 'All three are level so far.';
  return `${level.map((r, i) => i === 0 ? r.subject : r.subject.replace(/^The /, 'the ')).join(' and ')} are level at the top.`;
}
function accRaceHtml(games){
  const rows = ACC_SERIES.map(s => ({...s, ...accRecord(games, s.key)}));
  const race = [...rows].sort((a, b) => b.correct - a.correct);
  const row = r => `<div class="score-row">
      <div class="score-name"><span class="score-mark ${r.shape}" style="--series:${r.series}" aria-hidden="true"></span>${r.name}</div>
      <div class="score-track" aria-hidden="true"><div class="score-fill" style="--series:${r.series}; width:${r.pct ?? 0}%"></div><div class="score-coin"></div></div>
      <div class="score-figure"><span class="score-pct">${r.pct === null ? '&ndash;' : `${r.pct.toFixed(1)}%`}</span><span class="score-count">${r.correct} of ${r.n}</span></div>
    </div>`;
  return `<div class="scoreboard" role="region" aria-label="Season scoreboard">
    <div class="scoreboard-eyebrow">Picked the winner &middot; ${games.length} game${games.length === 1 ? '' : 's'} graded</div>
    <div class="scoreboard-verdict">${accVerdict(rows)}</div>
    ${race.map(row).join('')}
    <div class="score-axis" aria-hidden="true"><span></span><div class="score-axis-track"><span class="coin">50% &middot; a coin flip</span><span class="full">100%</span></div><span></span></div>
  </div>`;
}
/* The chart frame's size: the NFL's, narrower on a phone, and no text under
   11 px (the audit's V3). */
function accFrame(){
  const phone = !!(window.matchMedia && window.matchMedia('(max-width:640px)').matches);
  return phone ? {W: 300, H: 230, padL: 40, padR: 16, padT: 14, padB: 36, fs: 11}
               : {W: 680, H: 230, padL: 44, padR: 24, padT: 14, padB: 36, fs: 11};
}
function accEmpty(f, text){
  return `<text class="acc-empty" x="${(f.W + f.padL - f.padR) / 2}" y="${(f.H - f.padB + f.padT) / 2}" text-anchor="middle" font-size="${f.fs + 1}" fill="var(--text-2)">${text}</text>`;
}
/* Running accuracy by day, one line per forecast, ending in its marker. */
function accTrendHtml(games){
  const f = accFrame();
  const days = [...new Set(games.map(g => g.day))].sort();
  const x = i => days.length <= 1 ? f.padL : f.padL + i / (days.length - 1) * (f.W - f.padL - f.padR);
  const y = v => f.padT + (1 - v / 100) * (f.H - f.padT - f.padB);
  const grid = [0, 25, 50, 75, 100].map(v => `<line x1="${f.padL}" y1="${y(v).toFixed(1)}" x2="${f.W - f.padR}" y2="${y(v).toFixed(1)}" stroke="var(--border)" stroke-width="1"${v === 50 ? ' stroke-dasharray="4 3"' : ''}/>`
    + `<text x="${f.padL - 6}" y="${(y(v) + 4).toFixed(1)}" text-anchor="end" font-size="${f.fs}" fill="var(--text-2)">${v}%</text>`).join('');
  let body;
  if(days.length < 2){
    body = accEmpty(f, days.length ? 'The trend starts once two days are graded.' : 'Nothing is graded yet.');
  }else{
    body = ACC_SERIES.map(s => {
      const pts = days.map((d, i) => ({i, ...accRecord(games.filter(g => g.day <= d), s.key)})).filter(p => p.pct !== null);
      if(pts.length < 2) return '';
      const path = pts.map((p, k) => `${k ? 'L' : 'M'}${x(p.i).toFixed(1)},${y(p.pct).toFixed(1)}`).join(' ');
      const last = pts[pts.length - 1];
      return `<path d="${path}" fill="none" stroke="${s.series}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>`
        + accMarker(s.shape, x(last.i), y(last.pct), s.series);
    }).join('');
  }
  return `<div class="method-block acc-chart">
    <h3>Running accuracy</h3>
    <p>Each forecast's share of its picks that won, counted from the first graded day to each day since.</p>
    ${accLegend()}
    <svg viewBox="0 0 ${f.W} ${f.H}" style="width:100%; height:auto; max-width:${f.W}px;" role="img" aria-label="Line chart of running accuracy by day for the market, Model B and Model A.${days.length < 2 ? ' Not enough is graded to draw it yet.' : ''}">${grid}${body}</svg>
  </div>`;
}
function accMarker(shape, cx, cy, colour){
  const r = 4.5;
  if(shape === 'sq') return `<rect x="${(cx - r).toFixed(1)}" y="${(cy - r).toFixed(1)}" width="${2 * r}" height="${2 * r}" fill="${colour}" stroke="var(--surface)" stroke-width="2"/>`;
  if(shape === 'tri') return `<path d="M${cx.toFixed(1)},${(cy - r - 1).toFixed(1)} L${(cx + r + 1).toFixed(1)},${(cy + r).toFixed(1)} L${(cx - r - 1).toFixed(1)},${(cy + r).toFixed(1)} Z" fill="${colour}" stroke="var(--surface)" stroke-width="2"/>`;
  return `<circle cx="${cx.toFixed(1)}" cy="${cy.toFixed(1)}" r="${r}" fill="${colour}" stroke="var(--surface)" stroke-width="2"/>`;
}
function accLegend(){
  return `<div class="acc-legend">${ACC_SERIES.map(s => `<span><span class="score-mark ${s.shape}" style="--series:${s.series}" aria-hidden="true"></span>${s.name}</span>`).join('')}</div>`;
}
/* A Wilson interval for k right of n, at 95%: the NFL's reliability diagram
   draws one on every point (Stage 19), because a bin of a few picks says
   little and its interval shows how little. */
function accWilson(k, n){
  if(!n) return [0, 1];
  const z = 1.96, p = k / n, d = 1 + z * z / n;
  const mid = (p + z * z / (2 * n)) / d, half = z * Math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d;
  return [Math.max(0, mid - half), Math.min(1, mid + half)];
}
const ACC_BINS = [[0.5, 0.55], [0.55, 0.6], [0.6, 0.65], [0.65, 0.7], [0.7, 1.01]];
/* How sure each pick was, against how often picks that sure came true, with
   the line a well-calibrated forecast would sit on. A pick is Model B's or
   Model A's, so its dot is in the text colour, not either model's. */
function accDiagramHtml(games){
  const f = accFrame();
  const lo = 50, hi = 100;
  const x = v => f.padL + (v - lo) / (hi - lo) * (f.W - f.padL - f.padR);
  const y = v => f.padT + (1 - v / 100) * (f.H - f.padT - f.padB);
  const ticks = [50, 60, 70, 80, 90, 100];
  const axes = ticks.map(v => `<line x1="${x(v).toFixed(1)}" y1="${f.padT}" x2="${x(v).toFixed(1)}" y2="${f.H - f.padB}" stroke="var(--border)" stroke-width="1"/>`
      + `<text x="${x(v).toFixed(1)}" y="${f.H - f.padB + 20}" text-anchor="middle" font-size="${f.fs}" fill="var(--text-2)">${v}%</text>`).join('')
    + [0, 50, 100].map(v => `<text x="${f.padL - 6}" y="${(y(v) + 4).toFixed(1)}" text-anchor="end" font-size="${f.fs}" fill="var(--text-2)">${v}%</text>`).join('')
    + `<line x1="${x(50).toFixed(1)}" y1="${y(50).toFixed(1)}" x2="${x(100).toFixed(1)}" y2="${y(100).toFixed(1)}" stroke="var(--text-2)" stroke-width="1" stroke-dasharray="4 3"/>`;
  const bins = ACC_BINS.map(([a, b]) => {
    const inBin = games.filter(g => g.c >= a && g.c < b);
    const n = inBin.length, k = inBin.filter(g => g.right).length;
    return n ? {n, k, said: inBin.reduce((t, g) => t + g.c, 0) / n * 100, rate: k / n * 100, ci: accWilson(k, n)} : null;
  }).filter(Boolean);
  const body = !games.length ? accEmpty(f, 'Nothing is graded yet.')
    : bins.map(p => `<line x1="${x(p.said).toFixed(1)}" y1="${y(p.ci[0] * 100).toFixed(1)}" x2="${x(p.said).toFixed(1)}" y2="${y(p.ci[1] * 100).toFixed(1)}" stroke="var(--text-2)" stroke-width="1.5"/>`
      + `<circle cx="${x(p.said).toFixed(1)}" cy="${y(p.rate).toFixed(1)}" r="5" fill="var(--text)" stroke="var(--surface)" stroke-width="2"><title>Said ${p.said.toFixed(1)}%, right ${p.rate.toFixed(1)}% over ${p.n} pick${p.n === 1 ? '' : 's'} (95% interval ${Math.round(p.ci[0] * 100)}% to ${Math.round(p.ci[1] * 100)}%)</title></circle>`).join('');
  const thin = games.length && games.length < 30 * ACC_BINS.length;
  return `<div class="method-block acc-chart">
    <h3>How sure, and how often right</h3>
    <p>Each dot is the graded picks made at about one level of sureness: how sure they were, across, and how often they came true, up. A well-calibrated forecast sits on the dashed line; the bar through each dot is its 95% interval.${thin ? ` With ${games.length} graded, every interval is wide: a dot means little under 30 picks.` : ''}</p>
    <svg viewBox="0 0 ${f.W} ${f.H}" style="width:100%; height:auto; max-width:${f.W}px;" role="img" aria-label="Calibration diagram of the graded picks: how sure each was against how often picks that sure came true.${games.length ? '' : ' Nothing is graded yet.'}">${axes}${body}</svg>
  </div>`;
}
function accuracyHtml(games){
  return accRaceHtml(games) + accTrendHtml(games) + accDiagramHtml(games);
}
