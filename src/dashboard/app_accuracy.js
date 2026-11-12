/* ---------- What actually happened at this confidence level ----------

   The reliability diagram on Model Lab answers "are the probabilities honest?"
   for someone reading the research. This puts the same answer on the pick
   itself, where a person is actually deciding something.

   Given a stated probability, it finds the backtest bin that probability falls
   in and reports what really happened in that bin across ~1087 games, with the
   Wilson interval. Motivated by a confirmed finding, re-derived 2026-09-06 by
   src/sports/nfl/research/verify_low_confidence_finding.py: across the 343 games where Model A's
   own probability sits within 0.05 of a coin flip it hits 52.48%, while the
   market hits 64.14% on those same games -- a -11.66pt gap, CI [-18.37,
   -5.25]. A number like 52% on a pick card reads as "slightly favoured"
   unless the track record behind it is shown too.

   Two details that are easy to get wrong:

     1. The bins are over the probability of a HOME win across [0,1], not over
        "probability of whichever side we picked" -- calibration.py bins that
        way deliberately, so the direction of any miscalibration survives. That
        means an AWAY pick has to be read as the complement: a 65% away pick is
        a 35% home probability, so it belongs in the 30-40% bin, and that bin's
        historical rate has to be flipped before it means anything about the
        away side. Getting this backwards would show a confident pick as though
        it historically lost.
     2. A bin whose interval spans 50% has a track record that cannot be
        distinguished from a coin flip. That is worth saying out loud rather
        than leaving the reader to compare three numbers themselves. */
/* "2022-2025", not "2022-2023-2024-2025". Falls back to listing them when the
   seasons aren't contiguous, since collapsing a gap would misstate the span. */
function seasonRange(seasons){
  if(!seasons || !seasons.length) return 'the backtest window';
  const first = seasons[0], last = seasons[seasons.length - 1];
  const contiguous = seasons.every((s, i) => s === first + i);
  return contiguous ? `${first}&ndash;${last}` : seasons.join(', ');
}

function pickTrackRecord(homeProbPct, modelKey){
  if(!calibration || !calibration.models || !calibration.models[modelKey]) return null;
  if(homeProbPct === null || homeProbPct === undefined) return null;

  const p = homeProbPct / 100;
  const bin = calibration.models[modelKey].bins.find(
    b => p >= b.lo && (b.hi < 1 ? p < b.hi : p <= b.hi));
  if(!bin) return null;

  // Which side the card is actually picking, and therefore which direction the
  // bin's home-win rate has to be read in.
  const pickedHome = homeProbPct >= 50;
  const rate  = pickedHome ? bin.observed : 100 - bin.observed;
  // Flipping an interval reverses its ends: the complement of [lo, hi] is
  // [100-hi, 100-lo]. Writing it the other way round yields lo > hi, which
  // renders as a backwards range rather than failing loudly.
  const lo    = pickedHome ? bin.ci_lo : 100 - bin.ci_hi;
  const hi    = pickedHome ? bin.ci_hi : 100 - bin.ci_lo;

  return {
    label: bin.label, n: bin.n, rate, lo, hi,
    underpowered: bin.underpowered,
    coinFlip: lo <= 50 && hi >= 50,
  };
}

/* `where` decides whether the ordinary case is drawn on the card or tucked
   into the breakdown the card already has a toggle for.

   The reason is that this block is not per-game -- it is per confidence BAND,
   so most of a week's cards carry a byte-identical paragraph. Rendered inline
   on all sixteen it was ~140px of repeated text per card, which is what stopped
   the cards being the near-square shape the component study measured, and it
   is also the thing a reader stops seeing by the third card.

   What stays on the card is the band with too few games to report a rate at
   all. That is a statement about missing evidence, it differs between games,
   and nothing else on the card implies it.

   The coin-flip case USED to stay here too, and it was removed on the owner's
   call: "I don't need the week board essentially telling me over and over that
   a split decision is not much better than a coinflip." He is right that it
   repeats -- seven of sixteen cards carried it in Week 1, every one of them
   saying the same thing about a band around 58-59% -- and the card already
   says MODELS SPLIT and prints two probabilities either side of 50%. It is a
   different claim (calibration of the band, not disagreement between models),
   but it is not a claim a reader needs seven times on one screen.

   It is not deleted: the routine path below still renders it inside the
   breakdown, so it is one click away on every card it applies to.

   This also happens to be what makes the cards uniform. That block was 129px
   and appeared on some cards and not others, which alone accounted for a
   205px spread in card height; without it the spread is 20px.

   'any' keeps the old always-inline behaviour for other callers. */
function trackRecordHtml(homeProbPct, where='any'){
  const t = pickTrackRecord(homeProbPct, 'model_b');
  if(!t) return '';
  const notable = t.underpowered;
  if(where === 'card' && !notable) return '';
  if(where === 'panel' && notable) return '';
  if(t.underpowered){
    return `<div class="track-record thin">Only ${t.n} past game${t.n===1?'':'s'}
      landed at this confidence &mdash; too few to report a track record.</div>`;
  }
  const coin = t.coinFlip
    ? ` <span class="track-coin">That range includes 50%, so this band has not
        been shown to beat a coin flip.</span>`
    : '';
  // Was three lines carrying "95% CI 67.2-81.4%" on every card. The number was
  // honest and the phrasing was not for this reader -- and "CI" slipped past
  // the jargon guard, which bans "confidence interval" spelled out. Same
  // information, said the way you would say it out loud.
  return `<div class="track-record${t.coinFlip?' warn':''}">
    <b>When picks looked this sure before,</b> they were right
    <b>${t.rate.toFixed(1)}%</b> of the time &mdash; ${t.n} past games, and the
    real rate is somewhere around ${t.lo.toFixed(0)}&ndash;${t.hi.toFixed(0)}%.${coin}
    <span class="track-note">A record for this band of picks over
    ${seasonRange(calibration.backtest_seasons)}, not a second guess at this game.</span>
  </div>`;
}

/* ---------- Chart series identity ----------
   One definition of what each series looks like, shared by every chart on
   the page. Colour follows the ENTITY, not its position in whatever subset
   is currently drawn, so hiding Model A on the reliability diagram never
   repaints the market. `shape` and `dash` are the secondary encoding: on a
   greyscale print, in forced-colours mode, or for a reader whose vision the
   OKLab checks can only approximate, identity survives without colour. */
const SERIES = {
  a:      {label:'Model A',  color:'var(--series-a)', shape:'circle',   dash:''},
  b:      {label:'Model B',  color:'var(--series-b)', shape:'square',   dash:''},
  market: {label:'Market',   color:'var(--series-c)', shape:'triangle', dash:''},
  picks:  {label:'My Picks', color:'var(--series-d)', shape:'diamond',  dash:'6,4'},
};

/* Marker path for a series shape, centred on (cx,cy). Sized by `r` as a
   radius so every shape reads at roughly the same visual weight; the skill's
   floor is an 8px marker, so r stays >= 4.5 wherever these are hit targets. */
function markerPath(shape, cx, cy, r){
  const s = r * 0.92;
  switch(shape){
    case 'square':   return `<rect x="${(cx-s).toFixed(1)}" y="${(cy-s).toFixed(1)}" width="${(2*s).toFixed(1)}" height="${(2*s).toFixed(1)}" rx="1"`;
    case 'triangle': return `<polygon points="${cx.toFixed(1)},${(cy-r*1.15).toFixed(1)} ${(cx+r).toFixed(1)},${(cy+r*0.75).toFixed(1)} ${(cx-r).toFixed(1)},${(cy+r*0.75).toFixed(1)}"`;
    case 'diamond':  return `<polygon points="${cx.toFixed(1)},${(cy-r*1.2).toFixed(1)} ${(cx+r*1.2).toFixed(1)},${cy.toFixed(1)} ${cx.toFixed(1)},${(cy+r*1.2).toFixed(1)} ${(cx-r*1.2).toFixed(1)},${cy.toFixed(1)}"`;
    default:         return `<circle cx="${cx.toFixed(1)}" cy="${cy.toFixed(1)}" r="${r.toFixed(1)}"`;
  }
}

/* Legend swatches carry the shape as well as the colour, so the legend is a
   real key to the marks rather than four coloured squares. */
function seriesLegend(keys){
  return keys.map(k=>{
    const s = SERIES[k];
    return `<span style="display:inline-flex; align-items:center; gap:var(--s2); margin-right:var(--s4); white-space:nowrap;">
      <svg width="14" height="14" viewBox="0 0 14 14" aria-hidden="true" style="flex-shrink:0;">
        ${markerPath(s.shape, 7, 7, 5)} fill="${s.color}"/>
      </svg>${s.label}</span>`;
  }).join('');
}

/* ---------- Season Accuracy ---------- */
/* End-labels for a line chart (Stage 19): given where each line ends, where
   to put its label so no two are closer than `gap` and the block stays within
   [lo, hi]. Labels keep their lines' order; a label moves only as far as it
   has to. Returns the positions in the input's order. */
const TREND_LABEL_GAP = 14;
function spreadLabels(ys, gap, lo, hi){
  const order = ys.map((v, i) => ({v, i})).sort((a, b) => a.v - b.v || a.i - b.i);
  const out = order.map(o => Math.min(Math.max(o.v, lo), hi));
  for(let k = 1; k < out.length; k++) out[k] = Math.max(out[k], out[k-1] + gap);
  const over = out.length ? out[out.length-1] - hi : 0;
  if(over > 0){
    for(let k = 0; k < out.length; k++) out[k] -= over;
    for(let k = out.length - 2; k >= 0; k--) out[k] = Math.min(out[k], out[k+1] - gap);
  }
  const res = new Array(ys.length);
  order.forEach((o, k) => { res[o.i] = out[k]; });
  return res;
}

/* Charts drawn for a phone (Stage 26 item 4, from the 2026-09-28 audit).
   The trend and reliability charts were drawn 680 and 470 units wide and
   shrunk to fit, so on a 375px phone their text came out 4px and 6px tall.
   Below 640px (the page's phone width, as ORIENTATION_PHONE) each is drawn
   at about the width it will have, with its text sized for that width, so it
   renders at 11-12px. Mark chose this from rendered side-by-sides on
   2026-09-28, with the trend chart's names at the line ends dropped on a
   phone: the legend above it names every line, by colour and by the marker
   shape each line ends in. Decided once, when the chart is built; a phone
   turned sideways keeps the chart it loaded with, which still scales. */
const CHART_PHONE = '(max-width:640px)';
function chartIsPhone(){
  return !!(window.matchMedia && window.matchMedia(CHART_PHONE).matches);
}
/* One chart style (Stage 79 item 45, the 2026-10-13 audit's N9 and V3). Every
   SVG chart is an svg.chart: its text, grid, 50% or perfect-calibration
   reference and interval whiskers are styled once, in styles.css's "One chart
   style" block, which the NHL's and NBA's charts (src/core/accuracy.js) share.
   A series' marker is 12 units across (CHART_MARK_R); a whisker is drawn by
   chartWhisker. Text is 11 units or more; drawn at a phone's width below
   640px and at its full width on a desktop, no chart's text renders under
   11px at 390 or 1440px (tests/browser/check_chart_text.py measures both).
   Between them a desktop drawing wider than its box still shrinks, which the
   trend's container width (Stage 79 item 49) takes up. */
const CHART_MARK_R = 6;
function chartWhisker(cx, top, bottom, colour){
  const cap = y => `<line class="chart-whisker" x1="${(cx-3.5).toFixed(1)}" y1="${y.toFixed(1)}" x2="${(cx+3.5).toFixed(1)}" y2="${y.toFixed(1)}" stroke="${colour}"/>`;
  return `<line class="chart-whisker" x1="${cx.toFixed(1)}" y1="${top.toFixed(1)}" x2="${cx.toFixed(1)}" y2="${bottom.toFixed(1)}" stroke="${colour}"/>${cap(top)}${cap(bottom)}`;
}
/* At 11 units a tick label is about 6 units a character ("Wk 18" measured
   29.8). Label every k-th tick, the fewest that leaves 4 units between
   neighbours: every week of a desktop season up to week 17. */
function chartTickStep(labels, gap){
  const widest = Math.max(0, ...labels.map(t => t.length)) * 6;
  return Math.max(1, Math.ceil((widest + 4) / Math.max(gap, 1)));
}

/* Stage 79 item 49 (the 2026-10-13 audit's N9): on a desktop the trend is
   drawn at its box's own width, so it fills the 1124 px block a fixed 680 left
   half empty and one unit stays one pixel (its 11-unit text 11 px) at any
   width. `width` is that box's width; the chart is redrawn when it changes
   (sizeTrendChart), the first time when the page is shown. A phone keeps its
   300-unit drawing (Stage 26 item 4). */
const TREND_MIN_W = 360;
function buildCumulativeTrendChart(width){
  // Two points, not one. A trend needs somewhere to go, and a single graded
  // week drew either nothing (every series short-circuits at valid.length < 2)
  // or, when an empty week was still being emitted as a data point, three flat
  // horizontal lines that looked like a considered finding and were an artifact
  // of charting a week with no games in it.
  //
  // Says so rather than rendering nothing, following the calibration section
  // further down this same page, which already handles its own not-enough-data
  // case in words. An absent chart invites "is it broken?"; a sentence does not.
  if(!accuracy.weeks || accuracy.weeks.length < 2){
    const n = (accuracy.weeks || []).length;
    return `<div class="method-block">
      <h3>Accuracy over the season</h3>
      <p>${n === 0
          ? 'No weeks have been graded yet, so there is no trend to show. This fills in after the first week’s games are played and graded.'
          : 'Only one week has been graded so far. A trend line needs at least two, so this chart appears once the second week is in — a single point drawn as a line would suggest a direction that has not been measured.'}</p>
    </div>`;
  }
  const myPicks = loadMyPicks(), pickTimes = loadPickTimes();

  let cA=0, nA=0, cB=0, nB=0, cM=0, nM=0, cP=0, nP=0;
  const points = accuracy.weeks.map(w=>{
    cA += w.model_a_correct; nA += w.model_a_n;
    cB += w.model_b_correct; nB += w.model_b_n;
    cM += w.market_correct; nM += w.market_n;
    const weekKey = Object.keys(weeks).find(k=>weeks[k].season===w.season && weeks[k].week===w.week);
    if(weekKey){
      // Counted picks only -- the same tally as the scoreboard above it.
      const t = tallyMyPicks(myPicks, pickTimes, [weekKey], weeks);
      cP += t.wins; nP += t.wins + t.losses;
    }
    return {
      label: `${w.season} Wk${w.week}`,
      a: nA>0 ? (cA/nA*100) : null, b: nB>0 ? (cB/nB*100) : null,
      m: nM>0 ? (cM/nM*100) : null, p: nP>0 ? (cP/nP*100) : null,
    };
  });

  // padR leaves room for the direct end-labels: four series is inside the
  // "<= 4 series are also direct-labeled" rule, so identity never rests on
  // colour alone even for a reader who skips the legend.
  const phone = chartIsPhone();
  const W = phone ? 300 : Math.max(TREND_MIN_W, Math.round(width || 680)), H = phone ? 230 : 220, padL = phone ? 34 : 36, padR = phone ? 20 : 74;
  const padT=14, padB=28;
  const n = points.length;
  const x = i => n<=1 ? padL : padL + (i/(n-1))*(W-padL-padR);
  const allVals = points.flatMap(p=>[p.a,p.b,p.m,p.p]).filter(v=>v!==null);
  const yMin = Math.max(0, Math.min(...allVals, 40) - 5);
  const yMax = Math.min(100, Math.max(...allVals, 60) + 5);
  const y = v => padT + (1-(v-yMin)/(yMax-yMin))*(H-padT-padB);

  // Series drawn in fixed order, each with a direct end-label. The labels
  // are placed together once every line is known (Stage 19): sorted by where
  // their lines end and spread to a minimum gap, the block moved back inside
  // the plot if spreading pushed it out. Nudging one label at a time, in draw
  // order and always downwards, left two labels overprinting whenever two
  // lines ended together.
  const ends = [];
  function lineFor(key, seriesKey){
    const s = SERIES[seriesKey];
    const valid = points.map((p,i)=>({i, v:p[key]})).filter(d=>d.v!==null);
    if(valid.length < 2) return '';
    const d = valid.map((d,idx)=>`${idx===0?'M':'L'}${x(d.i).toFixed(1)},${y(d.v).toFixed(1)}`).join(' ');
    const last = valid[valid.length-1];
    ends.push({x: x(last.i), y: y(last.v), label: s.label});
    const dash = s.dash ? ` stroke-dasharray="${s.dash}"` : '';
    return `<path d="${d}" fill="none" stroke="${s.color}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"${dash}/>
      ${markerPath(s.shape, x(last.i), y(last.v), CHART_MARK_R)} fill="${s.color}" stroke="var(--surface)" stroke-width="2"/>`;
  }
  function endLabels(){
    if(phone) return '';   // the legend names the lines on a phone
    const placed = spreadLabels(ends.map(e => e.y), TREND_LABEL_GAP, padT + 4, H - padB);
    return ends.map((e, k) =>
      `<text class="chart-label" x="${(e.x+CHART_MARK_R+5).toFixed(1)}" y="${(placed[k]+4).toFixed(1)}">${e.label}</text>`).join('');
  }

  // The weeks under the x-axis. A season's weeks as "Wk 1"; the season
  // itself only when the points span more than one.
  const oneSeason = new Set(accuracy.weeks.map(w => w.season)).size === 1;
  const tickText = w => `${oneSeason ? '' : w.season + ' '}Wk ${w.week}`;
  const every = chartTickStep(accuracy.weeks.map(tickText), n <= 1 ? W : (W - padL - padR) / (n - 1));
  // Counted back from the latest week, which is always labelled.
  const weekTicks = accuracy.weeks.map((w, i) => (n - 1 - i) % every ? '' :
    `<text x="${x(i).toFixed(1)}" y="${(H - padB + 16).toFixed(1)}" text-anchor="middle">${tickText(w)}</text>`).join('');

  const gridLines = [];
  for(let gv = Math.ceil(yMin/10)*10; gv <= yMax; gv += 10){
    gridLines.push(`<line class="${gv === 50 ? 'chart-ref' : 'chart-grid'}" x1="${padL}" y1="${y(gv).toFixed(1)}" x2="${W-padR}" y2="${y(gv).toFixed(1)}"/>
      <text x="${padL-6}" y="${(y(gv)+4).toFixed(1)}" text-anchor="end">${gv}%</text>`);
  }

  // My picks are in the legend only when they have a line to name. When
  // every graded pick was late or untimed there is none, and the chart says
  // why instead (Stage 37 item 1).
  const picksDrawn = points.filter(p => p.p !== null).length >= 2;
  const legend = seriesLegend(picksDrawn ? ['a','b','market','picks'] : ['a','b','market']);
  const allMine = tallyMyPicks(myPicks, pickTimes, weekKeysSorted, weeks);
  const picksNote = !picksDrawn && nP === 0 && (allMine.late + allMine.untimed) > 0
    ? `<p class="score-foot">My picks has no line yet. ${leftOutSentence(allMine)} ${PICKS_LIVE_HERE}</p>` : '';

  return `<div class="method-block">
    <h3>Cumulative Accuracy Trend</h3>
    <p style="margin-bottom:var(--s3);">Running accuracy as the season progresses -- not week-by-week noise, but how each approach has performed overall up to that point.</p>
    <div style="font-size:var(--fs-11); color:var(--text-2); margin-bottom:var(--s2);">${legend}</div>
    <div class="trend-plot" id="trend-plot" data-w="${W}"><svg class="chart" viewBox="0 0 ${W} ${H}" style="width:100%; height:auto; max-width:${W}px;" role="img" aria-label="Line chart of running accuracy by week for Model A, Model B, the market and, once you have made picks, yours. Each week's own figures are in the Week by week table below.">
      ${gridLines.join('')}
      ${lineFor('a','a')}
      ${lineFor('b','b')}
      ${lineFor('m','market')}
      ${lineFor('p','picks')}
      ${endLabels()}
      ${weekTicks}
    </svg></div>
    ${picksNote}
  </div>`;
}

function buildCalibrationChart(){
  if(!accuracy.calibration || accuracy.calibration.length === 0) return '';

  // Refuse to draw a calibration chart that has no power behind it. Plotting
  // a bucket of n=1 against a perfect-calibration line renders a coin flip
  // as though it were a measurement -- the chart looks authoritative and
  // says nothing. Live calibration needs many graded weeks; until then this
  // states the sample size plainly instead.
  if(accuracy.calibration_underpowered){
    return `<div class="method-block">
      <h3>Not enough games yet to check</h3>
      <p style="margin-bottom:0;">Not enough graded games yet to say whether these percentages are honest.
      Only <b style="color:var(--text)">${accuracy.n_graded}</b> game${accuracy.n_graded===1?'':'s'}
      ${accuracy.n_graded===1?'has':'have'} been graded so far, spread across
      ${accuracy.calibration.length} confidence buckets &mdash; every one of them below the
      ${accuracy.min_bucket_n}-game floor this dashboard requires before reporting a hit rate.
      A bucket of one game reporting &ldquo;0% actual&rdquo; is a coin flip, not a finding, so it
      isn't charted. The counts are still shown in the table below.
      The same check across every past season is on <b style="color:var(--text)">Model Lab</b>.</p>
    </div>`;
  }

  // pad holds the axis's "100%" at the chart style's 11 units (Stage 79 item 45).
  const S = 260, pad = 38;
  const scale = v => pad + (v/100)*(S-2*pad);

  const points = accuracy.calibration.map(c => ({x: c.avg_predicted, y: c.actual_rate, n: c.n, bucket: c.bucket}));
  const maxN = Math.max(...points.map(p=>p.n), 1);

  const dots = points.map(p => {
    const r = 4 + (p.n/maxN)*8; // dot size reflects sample size in that bucket
    return `<circle cx="${scale(p.x).toFixed(1)}" cy="${(S-scale(p.y)).toFixed(1)}" r="${r.toFixed(1)}" fill="var(--series-b)" fill-opacity="0.85" stroke="var(--surface)" stroke-width="2">
      <title>${p.bucket}: predicted ${p.x}%, actual ${p.y}% (n=${p.n})</title>
    </circle>`;
  }).join('');

  return `
    <div style="display:flex; align-items:flex-start; gap:var(--s5); flex-wrap:wrap; margin-bottom:var(--s4);">
      <svg class="chart" viewBox="0 0 ${S} ${S}" style="width:260px; height:260px; flex-shrink:0;" role="img" aria-label="Calibration chart: each confidence bucket's average predicted chance against how often those picks were right. The same buckets are in the table below.">
        <line class="chart-ref" x1="${pad}" y1="${S-pad}" x2="${S-pad}" y2="${pad}"/>
        <line class="chart-grid" x1="${pad}" y1="${S-pad}" x2="${pad}" y2="${pad}"/>
        <line class="chart-grid" x1="${pad}" y1="${S-pad}" x2="${S-pad}" y2="${S-pad}"/>
        <text x="${pad}" y="${S-pad+15}">0%</text>
        <text x="${S-pad}" y="${S-pad+15}" text-anchor="end">100%</text>
        <text x="${pad-6}" y="${S-pad+4}" text-anchor="end">0%</text>
        <text x="${pad-6}" y="${pad+4}" text-anchor="end">100%</text>
        ${dots}
      </svg>
      <div style="font-size:var(--fs-12); color:var(--text-2); max-width:280px; padding-top:var(--s2);">
        <div style="margin-bottom:var(--s2);"><span style="display:inline-block; width:8px; height:1.5px; background:var(--border-strong); margin-right:var(--s1); vertical-align:middle;"></span>Dashed line = perfectly honest</div>
        <div><span style="display:inline-block; width:8px; height:8px; border-radius:50%; background:var(--series-b); margin-right:var(--s1); vertical-align:middle;"></span>Each dot = one confidence bucket (bigger dot = more games)</div>
        <div style="margin-top:var(--s2);">Dots above the line mean we're underconfident in that bucket; below means overconfident.</div>
      </div>
    </div>`;
}

/* ---------- Reliability diagram (backtest calibration) ----------

   What this chart answers: when a model says 70%, does that side actually win
   about 70% of the time? Every point is one probability bin; x is the average
   probability the model stated inside that bin, y is how often the home team
   really won. Perfect calibration is the diagonal.

   Two decisions worth naming, because they are what separate this from the
   live calibration panel on Season Accuracy:

   1. It is drawn from the BACKTEST (~1087 games), not from the handful of
      graded games this season. The live panel refuses to draw itself until it
      has the sample to justify a claim; this one has it.
   2. Every point carries a Wilson interval. A reliability diagram of bare
      dots invites the reader to treat every off-diagonal point as a defect.
      Most of these intervals cross the diagonal, which means "consistent with
      perfect calibration" -- and the chart has to be able to say so.

   Bins under the min-n floor are drawn hollow rather than tinted, so the
   "don't lean on this one" signal survives greyscale and colour-blindness. */
const RELIABILITY_SERIES = [['model_a','a'], ['model_b','b'], ['market','market']];
let relVisible = {model_a:true, model_b:true, market:true};

/* ---------- Reliability points: a 24px target at every width (Stage 12) ----------
   Each point's transparent halo is its hit target. It was r=11, 22 units in
   the chart's 470-unit viewBox, and the chart scales with its container, so
   the target was 22 CSS px only when the chart rendered at exactly 470px:
   the browser checker measured 21-22px at 360, 390, 1024 and 1280 wide,
   under WCAG 2.5.8's 24. The radius is now worked out from the rendered
   width so the halo is never under 24 CSS px across, and never smaller than
   it was. Pure, so the suite can execute it; applied by sizeRelHalos(). */
const REL_HALO_BASE_R = 11;
function relHaloRadius(renderedWidth, viewBoxWidth, minPx){
  if(!(renderedWidth > 0) || !(viewBoxWidth > 0)) return REL_HALO_BASE_R;  // hidden page: nothing to size yet
  return Math.max(REL_HALO_BASE_R, (minPx / 2) * (viewBoxWidth / renderedWidth));
}

function buildReliabilityDiagram(){
  if(!calibration || !calibration.models) return '';

  const phone = chartIsPhone();
  const W = phone ? 300 : 470, padL = phone ? 52 : 48, padR = phone ? 18 : 16, padT = 14;
  // The desktop plot stays 390, as it was before the phone drawing (it leaves
  // 16 spare units at the right); only the phone plot fills its width.
  const PLOT = phone ? W - padL - padR : 390;
  const H = padT + PLOT + (phone ? 44 : 40);
  const x = v => padL + (v/100)*PLOT;
  const y = v => padT + (1 - v/100)*PLOT;

  const grid = [0,25,50,75,100].map(g=>`
    <line class="chart-grid" x1="${x(g).toFixed(1)}" y1="${padT}" x2="${x(g).toFixed(1)}" y2="${(padT+PLOT).toFixed(1)}"/>
    <line class="chart-grid" x1="${padL}" y1="${y(g).toFixed(1)}" x2="${(padL+PLOT).toFixed(1)}" y2="${y(g).toFixed(1)}"/>
    <text x="${x(g).toFixed(1)}" y="${(padT+PLOT+16).toFixed(1)}" text-anchor="middle">${g}%</text>
    <text x="${(padL-8).toFixed(1)}" y="${(y(g)+4).toFixed(1)}" text-anchor="end">${g}%</text>`).join('');

  // Marks are drawn series by series in fixed order so overlaps stack the same
  // way on every render -- a chart whose z-order shuffles between loads is a
  // chart nobody can point at in a screenshot.
  const marks = RELIABILITY_SERIES.map(([modelKey, seriesKey])=>{
    const m = calibration.models[modelKey];
    if(!m) return '';
    const s = SERIES[seriesKey];
    const pts = m.bins.map(b=>{
      const cx = x(b.mean_predicted), cy = y(b.observed);
      const barTop = y(b.ci_hi), barBot = y(b.ci_lo);
      // Wilson interval. Drawn under the marker so the marker's surface ring
      // still separates it from whatever it overlaps.
      const bar = chartWhisker(cx, barTop, barBot, s.color);
      const fill = b.underpowered ? 'var(--surface)' : s.color;
      const marker = `${markerPath(s.shape, cx, cy, CHART_MARK_R)} fill="${fill}" stroke="${b.underpowered ? s.color : 'var(--surface)'}" stroke-width="2"/>`;
      const tip = [
        `<b>${s.label} &middot; ${b.label} bin</b>`,
        `Stated ${b.mean_predicted}% &rarr; actually won <b>${b.observed}%</b>`,
        `95% interval ${b.ci_lo}%&ndash;${b.ci_hi}% over ${b.n} game${b.n===1?'':'s'}`,
        b.underpowered
          ? `Under the ${calibration.min_bin_n}-game floor &mdash; too thin to lean on`
          : (b.consistent_with_perfect
              ? 'Interval covers the stated rate: consistent with perfect calibration'
              : 'Interval excludes the stated rate: a real miss in this bin'),
      ].join('<br>');
      // A transparent halo makes the hit target larger than the mark, which
      // matters most for the thin bins nobody can click precisely.
      // tabindex -1 on every point: initReliabilityDiagram hands the one Tab
      // stop to a single point (roving tabindex, Stage 26).
      return `<g class="rel-point" tabindex="-1" role="img"
                 aria-label="${s.label}, ${b.label} bin: stated ${b.mean_predicted} percent, observed ${b.observed} percent, ${b.n} games"
                 data-tip="${tip.replace(/"/g,'&quot;')}" data-cx="${cx.toFixed(1)}" data-cy="${cy.toFixed(1)}">
        ${bar}
        <circle class="rel-halo" cx="${cx.toFixed(1)}" cy="${cy.toFixed(1)}" r="${REL_HALO_BASE_R}" fill="transparent" stroke="none" opacity="0"/>
        ${marker}
      </g>`;
    }).join('');
    return `<g class="rel-series" data-model="${modelKey}">${pts}</g>`;
  }).join('');

  // The toggle row doubles as the legend: each control carries the series'
  // own marker shape and colour next to its name, sits directly above the
  // plot, and is always visible. Per-series direct labels inside the plot
  // were tried and dropped -- Model B and the market finish 0.3 points apart
  // in the top bin, so their labels collide exactly where the chart is most
  // crowded. The rule those labels serve is that identity must never rest on
  // colour alone; here the marker SHAPE carries it, which survives greyscale
  // and colour-blindness at every one of the 30 points rather than at three.
  const filters = RELIABILITY_SERIES.map(([modelKey, seriesKey])=>{
    const s = SERIES[seriesKey];
    return `<button class="btn btn-chip btn-toggle rel-toggle" data-model="${modelKey}" aria-pressed="true">
      <svg width="12" height="12" viewBox="0 0 12 12" aria-hidden="true">${markerPath(s.shape, 6, 6, 4.5)} fill="${s.color}"/></svg>${s.label}</button>`;
  }).join('');

  // The three decomposition scalars are single numbers, not shapes -- a bar
  // chart of three values that differ in the third decimal place would be a
  // worse read than the numbers themselves. Uncertainty is shown once,
  // outside the per-model rows, because it is a property of the games and is
  // identical for all three by construction.
  const statRows = RELIABILITY_SERIES.map(([modelKey, seriesKey])=>{
    const m = calibration.models[modelKey];
    if(!m) return '';
    const s = SERIES[seriesKey], d = m.decomposition;
    return `<div class="rel-stat">
      <span class="nm"><svg width="11" height="11" viewBox="0 0 11 11" aria-hidden="true">${markerPath(s.shape, 5.5, 5.5, 4.2)} fill="${s.color}"/></svg>${s.label}</span>
      <span class="v">${d.reliability.toFixed(6)}</span>
      <span class="v">${d.resolution.toFixed(6)}</span>
    </div>`;
  }).join('');

  const tableRows = RELIABILITY_SERIES.map(([modelKey, seriesKey])=>{
    const m = calibration.models[modelKey];
    if(!m) return '';
    return m.bins.map(b=>`<tr>
      <td>${SERIES[seriesKey].label}</td><td>${b.label}</td>
      <td class="num">${b.n}</td><td class="num">${b.mean_predicted}%</td>
      <td class="num">${b.observed}%${b.underpowered?'&nbsp;*':''}</td>
      <td class="num">${b.ci_lo}&ndash;${b.ci_hi}%</td></tr>`).join('');
  }).join('');

  const p = calibration.provenance || {};
  const n = calibration.models.model_a ? calibration.models.model_a.metrics.n : 0;
  const base = calibration.models.model_a
    ? (calibration.models.model_a.decomposition.base_rate*100).toFixed(1) : '--';

  return `<div class="method-block">
    <h3>Reliability Diagram &mdash; Are the Probabilities Honest?</h3>
    <p style="margin-bottom:var(--s3);">When a model says <b style="color:var(--text)">70%</b>, does that side actually win about 70% of the time? Each mark is one probability bin across ${n} backtested games, with its 95% interval.</p>
    <details class="disclosure rel-how">
      <summary>How to read this</summary>
      <p style="margin:var(--s2) 0 var(--s4);">Accuracy only asks whether we picked the right side; this asks something harder. The vertical bar on each mark is its 95% Wilson interval. The dashed diagonal is perfect calibration &mdash; and a mark whose bar crosses that line is <i>consistent</i> with being perfectly calibrated, however far the mark itself sits from it.</p>
    </details>
    <div class="rel-filters">${filters}</div>
    <div class="rel-wrap">
      <div class="rel-plot">
        <svg class="chart" viewBox="0 0 ${W} ${H}" style="width:100%; height:auto;" role="group" aria-label="Reliability diagram: stated probability against observed win rate. One Tab stop; arrow keys move between points, Home and End go to the first and last.">
          ${grid}
          <line class="chart-ref" x1="${x(0).toFixed(1)}" y1="${y(0).toFixed(1)}" x2="${x(100).toFixed(1)}" y2="${y(100).toFixed(1)}"/>
          <text x="${(x(100)-4).toFixed(1)}" y="${(y(100)+15).toFixed(1)}" text-anchor="end">perfect calibration</text>
          ${marks}
          <text class="chart-title" x="${(padL+PLOT/2).toFixed(1)}" y="${(padT+PLOT+34).toFixed(1)}" text-anchor="middle">Probability the model stated</text>
          <text class="chart-title" x="12" y="${(padT+PLOT/2).toFixed(1)}" text-anchor="middle" transform="rotate(-90 12 ${(padT+PLOT/2).toFixed(1)})">How often it actually happened</text>
        </svg>
        <div class="rel-tip" id="rel-tip"></div>
      </div>
      <div class="rel-side">
        <div class="rel-stat" style="border-bottom:1px solid var(--border-strong);">
          <span class="nm" style="color:var(--text-2); font-size:var(--fs-11); letter-spacing:.06em; text-transform:uppercase;">Brier decomposition</span>
          <span class="v" style="font-size:var(--fs-11); letter-spacing:.06em; text-transform:uppercase;" title="Mean squared gap between stated probability and observed rate. Lower is better; 0 is perfect calibration.">Reliab. &darr;</span>
          <span class="v" style="font-size:var(--fs-11); letter-spacing:.06em; text-transform:uppercase;" title="How far the bins sit from the base rate. Higher is better; 0 means the model says nothing.">Resol. &uarr;</span>
        </div>
        ${statRows}
        <details class="disclosure rel-how">
          <summary>What these numbers mean</summary>
          <p style="font-size:var(--fs-12); margin-top:var(--s3);">Brier = reliability &minus; resolution + uncertainty (Murphy, 1973). <b style="color:var(--text)">Reliability</b> is miscalibration: lower is better. <b style="color:var(--text)">Resolution</b> is how far the model dares to move away from the base rate: higher is better. A model that always predicts the ${base}% base rate scores a perfect 0 on reliability and a useless 0 on resolution &mdash; which is exactly why accuracy alone can't tell those two apart. Uncertainty (${calibration.models.model_a ? calibration.models.model_a.decomposition.uncertainty.toFixed(6) : '--'}) belongs to the games, not to any model.</p>
        </details>
        <p style="font-size:var(--fs-12); margin-top:var(--s3);">Model B's numbers look better than the market's on resolution and worse on reliability, and until 2026-09-05 this panel called that "a lead, not a claim" because nothing had tested it. It has now been tested, with a 5,000-resample paired bootstrap, and <b style="color:var(--text)">the lead did not survive</b>: every one of the four gaps against the market has a 95% interval that includes zero. Brier &minus;0.000622, CI [&minus;0.002395, +0.001141]. Resolution +0.001141, CI [&minus;0.002196, +0.004597]. At 1,087 games those differences are indistinguishable from noise, so the honest reading of this chart is that <b style="color:var(--text)">Model B and the market are calibrated about equally well</b> &mdash; not that one edges the other.</p>
        <p style="font-size:var(--fs-12); margin-top:var(--s3);">The same test did find two things that hold. Against <b style="color:var(--text)">Model A</b>, Model B is genuinely better &mdash; Brier &minus;0.019133, CI [&minus;0.025838, &minus;0.012687], and resolution +0.016814, CI [+0.008990, +0.024819] &mdash; which is the first version of "the spread helps" that rests on proper scoring rules rather than on accuracy, a metric this project has already shown moves by a whole game between platforms. And the market genuinely beats Model A: Brier +0.018511, CI [+0.011496, +0.025553]. See <b style="color:var(--text)">the experiment log above</b> for all three, and <code>src/sports/nfl/research/bootstrap_brier_gap.py</code> for the method.</p>
        <details class="disclosure rel-table" style="margin-top:var(--s3);">
          <summary>Show the numbers as a table</summary>
          <div class="table-wrap" style="margin-top:var(--s2);"><table class="metrics-table"><caption class="visually-hidden">Backtest calibration by probability bin, with 95% intervals</caption>
            <thead><tr><th scope="col">Series</th><th scope="col">Bin</th><th scope="col">Games</th><th scope="col">Stated</th><th scope="col">Observed</th><th scope="col">95% interval</th></tr></thead>
            <tbody>${tableRows}</tbody>
          </table></div>
          <p style="font-size:var(--fs-11); color:var(--text-2); margin-top:var(--s2);">* Fewer than ${calibration.min_bin_n} games in the bin &mdash; shown for completeness, drawn hollow on the chart, and not a measurement.</p>
        </details>
        <p class="rel-prov">Computed by <code>src/sports/nfl/research/calibration.py</code> over ${JSON.stringify(calibration.backtest_seasons)} &middot; model v${calibration.model_version} &middot; ${calibration.generated_at}<br>
        ${p.platform || 'unknown platform'} &middot; Python ${p.python || '?'} &middot; numpy ${p.numpy || '?'} &middot; pandas ${p.pandas || '?'} &middot; scikit-learn ${p['scikit-learn'] || '?'}<br>
        The machine is recorded because it has mattered before: see &ldquo;Backtest accuracy is not reproducible across platforms&rdquo; above.</p>
      </div>
    </div>
  </div>`;
}

/* Wires up the hover/focus readout and the series toggles. Runs after the
   markup is in the DOM, so the chart is a plain string everywhere else. */
function initReliabilityDiagram(){
  const tip = document.getElementById('rel-tip');
  if(!tip) return;
  const plot = tip.parentElement;

  function show(el){
    tip.innerHTML = el.dataset.tip;
    tip.classList.add('on');
    // Position in the plot's own pixel space, converting from the SVG's
    // viewBox units. Flips to the other side near an edge so the readout
    // never runs off the panel.
    const svg = plot.querySelector('svg');
    const box = svg.getBoundingClientRect();
    const vb = svg.viewBox.baseVal;
    const k = box.width / vb.width;
    let left = (+el.dataset.cx) * k + 16;
    let top  = (+el.dataset.cy) * k - 10;
    if(left + tip.offsetWidth > box.width) left = (+el.dataset.cx) * k - tip.offsetWidth - 16;
    // Clamp both axes to the plot box. Flipping to the left of a mark near the
    // right edge can still put the readout off the panel entirely, which is
    // how the first version of this hid its own y-axis label.
    left = Math.max(0, Math.min(left, Math.max(0, box.width - tip.offsetWidth)));
    top = Math.max(0, Math.min(top, box.height - tip.offsetHeight));
    tip.style.left = left + 'px';
    tip.style.top = top + 'px';
  }
  function hide(){ tip.classList.remove('on'); }

  // Size the halos now and whenever the chart's width changes -- including
  // the moment Model Lab opens, when the chart goes from 0 wide to its real
  // width. Without ResizeObserver, a window resize is the fallback.
  const svgEl = plot.querySelector('svg');
  function sizeRelHalos(){
    if(!svgEl) return;
    const r = relHaloRadius(svgEl.getBoundingClientRect().width, svgEl.viewBox.baseVal.width, 24);
    // Rounded UP: rounding to nearest could leave a halo at 23.99px.
    const rUp = (Math.ceil(r * 100) / 100).toFixed(2);
    svgEl.querySelectorAll('.rel-halo').forEach(c => c.setAttribute('r', rUp));
  }
  sizeRelHalos();
  if(window.ResizeObserver && svgEl) new ResizeObserver(sizeRelHalos).observe(svgEl);
  else window.addEventListener('resize', sizeRelHalos);

  // One Tab stop for the whole chart (Stage 26 item 10). Each of the thirty
  // points used to be its own Tab stop, so reaching the table below meant
  // thirty presses through marks a keyboard reader may not want. Roving
  // tabindex: exactly one visible point holds tabindex 0 and is the way in;
  // the arrow keys move through the visible points in drawing order (series
  // by series, bin by bin), Home and End jump to the ends, and a point in a
  // series switched off is skipped and never keeps the Tab stop.
  const points = [...plot.querySelectorAll('.rel-point')];
  const visiblePoints = () => points.filter(p => p.closest('.rel-series').style.display !== 'none');
  function setRoving(el){ points.forEach(p => p.setAttribute('tabindex', p === el ? '0' : '-1')); }
  if(points.length) setRoving(points[0]);

  points.forEach(el=>{
    el.addEventListener('mouseenter', ()=>show(el));
    el.addEventListener('focus', ()=>{ setRoving(el); show(el); });
    el.addEventListener('mouseleave', hide);
    el.addEventListener('blur', hide);
    el.addEventListener('keydown', e=>{
      const vis = visiblePoints(), i = vis.indexOf(el);
      let next = null;
      if(e.key === 'ArrowRight' || e.key === 'ArrowDown') next = vis[Math.min(i + 1, vis.length - 1)];
      else if(e.key === 'ArrowLeft' || e.key === 'ArrowUp') next = vis[Math.max(i - 1, 0)];
      else if(e.key === 'Home') next = vis[0];
      else if(e.key === 'End') next = vis[vis.length - 1];
      if(!next) return;
      e.preventDefault();
      next.focus();   // the focus handler moves the Tab stop with it
    });
  });

  document.querySelectorAll('.rel-toggle').forEach(btn=>{
    btn.addEventListener('click', ()=>{
      const key = btn.dataset.model;
      relVisible[key] = !relVisible[key];
      // Never let the reader turn everything off -- an empty plot reads as a
      // broken chart rather than a chosen filter.
      if(!Object.values(relVisible).some(Boolean)){ relVisible[key] = true; return; }
      btn.setAttribute('aria-pressed', String(relVisible[key]));
      const g = document.querySelector(`.rel-series[data-model="${key}"]`);
      if(g) g.style.display = relVisible[key] ? '' : 'none';
      // The Tab stop never stays on a hidden point, or the chart drops out
      // of the Tab order the moment its series is switched off.
      const holder = points.find(p => p.getAttribute('tabindex') === '0');
      if(!holder || !visiblePoints().includes(holder)) setRoving(visiblePoints()[0]);
      hide();
    });
  });
}

/* The scoreboard's sentence. A pure function of the three records, so the
   harness in tests/test_scoreboard.py can run it over ties, leads and
   unequal game counts without a page. Ranked by games right, not by the
   rounded percentage, because two records that differ by one game can
   print the same percentage. */
function scoreboardVerdict(rows){
  // Every graded game so far a tie: no record exists yet, and "level" would
  // read as three equal records rather than none (Stage 35).
  if(rows.every(r => r.n === 0)) return 'No graded game has a winner yet.';
  const sorted = [...rows].sort((a, b) => b.correct - a.correct);
  const top = sorted[0], gap = top.correct - sorted[1].correct;
  const sameGames = rows.every(r => r.n === rows[0].n);
  const lead = top.subject;
  if(!sameGames) return `${lead} has the best record so far.`;
  if(gap > 0) return `${lead} leads by ${gap} game${gap === 1 ? '' : 's'}.`;
  const level = sorted.filter(r => r.correct === top.correct);
  if(level.length === rows.length) return 'All three are level so far.';
  const names = level.map((r, i) => i === 0 ? r.subject : r.subject.replace(/^The /, 'the '));
  return `${names.join(' and ')} are level at the top.`;
}
/* nGraded is accuracy.n_graded: every game checked against a result, a tie
   included. The rule, since Stage 30 item 1 (tests/test_tie_rendering.py):
   a tie is GRADED -- it has a result -- but DECIDES nothing, so it counts in
   n_graded and in no row's record. Until Stage 35 the eyebrow printed the
   market row's n here, which leaves ties out (and any game saved without a
   market price), so a tie put it one below the calibration text's count of
   graded games. Each row's "N of M" is that row's own decided games.
   A row's pct is null when it has decided nothing yet -- every graded game
   a tie -- and then draws no bar and a dash, never r.pct.toFixed on null. */
/* Stage 77 item 20 (the 2026-10-13 audit's copy fix 9): picks are made on My
   Picks Log, not on the Week Board, which the invitation used to name. */
const JOIN_THE_RACE = 'Make your own picks on My Picks Log to join this race.';
function scoreboardHtml(o, mine, leftOut, nGraded){
  const rows = [
    {name: 'Market', subject: 'The betting market', series: 'var(--series-c)', shape: 'tri', ...o.market},
    {name: 'Model B', subject: 'Model B', series: 'var(--series-b)', shape: 'sq', ...o.model_b},
    {name: 'Model A', subject: 'Model A', series: 'var(--series-a)', shape: 'dot', ...o.model_a},
  ];
  const race = [...rows].sort((a, b) => b.correct - a.correct);
  // Graded picks that all came too late, or with no time, still join the
  // race as a row that says so (Stage 37 item 1, Mark's observation in the
  // 2026-10-04 audit): leaving the row out read as the picks being lost.
  if(mine) race.push({name: 'My picks', series: 'var(--series-d)', shape: 'diamond', ...mine});
  else if(leftOut) race.push({name: 'My picks', series: 'var(--series-d)', shape: 'diamond',
                              correct: 0, n: 0, pct: null, noneCounted: true});
  const row = r => `<div class="score-row">
      <div class="score-name"><span class="score-mark ${r.shape}" style="--series:${r.series}" aria-hidden="true"></span>${r.name}</div>
      <div class="score-track" aria-hidden="true"><div class="score-fill" style="--series:${r.series}; width:${r.pct ?? 0}%"></div><div class="score-coin"></div></div>
      <div class="score-figure"><span class="score-pct">${r.pct == null ? '&ndash;' : `${r.pct.toFixed(1)}%`}</span><span class="score-count">${r.noneCounted ? '0 counted' : `${r.correct} of ${r.n}`}</span></div>
    </div>`;
  return `<div class="scoreboard" role="region" aria-label="Season scoreboard">
    <div class="scoreboard-eyebrow">Picked the winner &middot; ${nGraded} game${nGraded === 1 ? '' : 's'} graded</div>
    <div class="scoreboard-verdict">${scoreboardVerdict(rows)}</div>
    ${race.map(row).join('')}
    <div class="score-axis" aria-hidden="true"><span></span><div class="score-axis-track"><span class="coin">50% &middot; a coin flip</span><span class="full">100%</span></div><span></span></div>
    ${mine || leftOut ? '' : `<div class="score-foot">${JOIN_THE_RACE}</div>`}
    ${leftOut ? `<div class="score-foot">${leftOut} Only picks made before kickoff are counted.${mine ? '' : ` ${PICKS_LIVE_HERE}`}</div>` : ''}
  </div>`;
}
/* Season Accuracy's second score (Stage 19): how sure each forecast was, not
   only whether it picked the winner. The numbers are Python's average log
   loss over the games all three forecasts priced (build_forecast_score), and
   null below 50 graded games -- null renders nothing. The words stay plain on
   purpose (Mark, 2026-09-28); Methodology's glossary names the technical
   term. Lowest first, because lower is better. */
function forecastScoreHtml(s){
  if(!s) return '';
  // Shape before series, unlike scoreboardHtml's rows: mutation cases anchor
  // on that function's exact text, and a second copy of it here made one of
  // them match twice.
  const rows = [
    {name: 'Market', shape: 'tri', series: 'var(--series-c)', score: s.market},
    {name: 'Model B', shape: 'sq', series: 'var(--series-b)', score: s.model_b},
    {name: 'Model A', shape: 'dot', series: 'var(--series-a)', score: s.model_a},
  ].sort((a, b) => a.score - b.score);
  const body = rows.map(r => `<tr><td><span class="score-mark ${r.shape}" style="--series:${r.series}" aria-hidden="true"></span>${r.name}</td><td class="num">${r.score.toFixed(3)}</td></tr>`).join('');
  return `
    <div class="method-block forecast-score">
      <h3>How sure, and how right</h3>
      <p>Picking the winner is only half of it. This score also weighs how sure each forecast was: a pick made at 90% that loses costs far more than one made at 55%. <b style="color:var(--text)">Lower is better.</b> Calling every game 50&ndash;50 scores ${s.coin_flip.toFixed(3)}, whatever happens.</p>
      <div class="table-wrap"><table class="metrics-table"><caption class="visually-hidden">Forecast score for each forecast; lower is better</caption>
        <thead><tr><th scope="col">Forecast</th><th scope="col">Score</th></tr></thead>
        <tbody>${body}</tbody>
      </table></div>
      <p style="font-size:var(--fs-12); color:var(--text-2); margin-top:var(--s2);">Over the ${s.n} games all three had a number for. The Methodology page explains how it is worked out.</p>
    </div>`;
}
/* Stage 46 item 9: the games each model picked against the market's
   favourite. Few games a season, so it leads with the interval and says
   plainly when there is none; the rate alone would read as a finding it
   is not. Numbers are Python's (build_against_market). */
function againstMarketHtml(m){
  if(!m) return '';
  const row = (label, r) => {
    if(!r.n) return `<tr><td>${label}</td><td>No game yet</td></tr>`;
    return `<tr><td>${label}</td><td>${r.right} of ${r.n} right <span class="against-ci">(95% interval ${r.lo}% to ${r.hi}%)</span></td></tr>`;
  };
  return `
    <div class="method-block against-market">
      <h3>Picking against the market</h3>
      <p>The graded games where a model picked the side the betting market made the underdog. So few that the interval matters more than the record: an interval that spans 50% says this season cannot tell a good contrarian pick from a coin flip.</p>
      <div class="table-wrap"><table class="metrics-table"><caption class="visually-hidden">Games each model picked against the market's favourite, with how many it got right</caption>
        <thead><tr><th scope="col">Model</th><th scope="col">Against the favourite</th></tr></thead>
        <tbody>${row('Model B', m.model_b)}${row('Model A', m.model_a)}</tbody>
      </table></div>
      <p style="font-size:var(--fs-12); color:var(--text-2); margin-top:var(--s2);">Out of the ${m.priced} graded games with a market price. A game the market priced at exactly 50% has no favourite and is left out.</p>
    </div>`;
}
function renderAccuracy(){
  const el = document.getElementById('accuracy-content');
  if(!accuracy.overall){
    // This is the whole page until the first week of the season is played, so
    // it is written for a reader, not for whoever runs the scripts. The old
    // copy said "Run grade_predictions.py after a week's games finish", which
    // tells a visitor nothing except that something is missing.
    el.innerHTML = stateHtml('waiting', 'Nothing to score yet', [
      `Every pick on this site is saved before kickoff and checked against the
      real result afterwards. No games have been played and graded yet, so there
      is no record to show — and a record built from anything other than
      already-saved picks would not be worth showing.`,
      `This page fills in on its own the day after the first week's games
      finish: how often each model was right, how that changes week to week, and
      whether the confidence numbers turn out to be honest.`], null, 'state--readable');
    return;
  }
  const o = accuracy.overall;

  // My Picks record: only picks made before their game's kickoff are in the
  // race, and the page says how many it left out.
  const mineTally = tallyMyPicks(loadMyPicks(), loadPickTimes(), weekKeysSorted, weeks);
  const myWins = mineTally.wins, myTotal = mineTally.wins + mineTally.losses;
  const myPct = myTotal > 0 ? Math.round(1000*myWins/myTotal)/10 : null;

  const cardsHtml = scoreboardHtml(o, myTotal > 0 ? {correct: myWins, n: myTotal, pct: myPct} : null,
                                   leftOutSentence(mineTally), accuracy.n_graded);

  const cumulativeChartHtml = buildCumulativeTrendChart(0);

  // Each week names its own board when that week is saved (Stage 26 item 5);
  // a week the page has no board for stays plain text rather than a link to
  // a route that would open something else.
  const weekCell = w => {
    const key = `${w.season}_week${w.week}`, label = `${w.season} Wk ${w.week}`;
    return weekKeysSorted.includes(key)
      ? `<a class="row-link week-link" href="${routeHash({page:'board', week:key})}">${label}</a>` : label;
  };
  const weeklyRows = accuracy.weeks.map(w=>`
    <tr>
      <td>${weekCell(w)}</td>
      <td class="num">${w.model_a_correct}/${w.model_a_n}</td>
      <td class="num">${w.model_b_correct}/${w.model_b_n}</td>
      <td class="num">${w.market_correct}/${w.market_n}</td>
    </tr>`).join('');
  // An empty tbody renders as a header with nothing under it, which reads as a
  // broken table rather than an empty one. Every not-enough-data case on this
  // page now says what it is waiting for.
  const weeklyHtml = `
    <div class="method-block">
      <h3>Week by week</h3>
      ${weeklyRows
        ? `<div class="table-wrap"><table class="metrics-table"><caption class="visually-hidden">Correct picks by week for each model</caption>
        <thead><tr><th scope="col">Week</th><th scope="col">Model A</th><th scope="col">Model B</th><th scope="col">Market</th></tr></thead>
        <tbody>${weeklyRows}</tbody>
      </table></div>`
        : `<p>Nothing graded yet. Each week appears here the day after its games are played.</p>`}
    </div>`;

  const calibChartHtml = buildCalibrationChart();

  // Underpowered rows keep their real counts but the "actual rate" is dimmed
  // and marked, so the number is visible without reading as a result.
  const calibRows = accuracy.calibration.map(c=>{
    const rate = c.underpowered
      ? `<span style="color:var(--text-2);" title="n=${c.n}, below the ${accuracy.min_bucket_n}-game floor -- not a meaningful rate">${c.actual_rate}%&nbsp;*</span>`
      : `${c.actual_rate}%`;
    return `<tr><td>${c.bucket}</td><td class="num">${c.n}</td><td class="num">${c.avg_predicted}%</td><td class="num">${rate}</td></tr>`;
  }).join('');
  const anyUnderpowered = accuracy.calibration.some(c=>c.underpowered);
  const calibFootnote = anyUnderpowered
    ? `<p style="font-size:var(--fs-11); color:var(--text-2); margin-top:var(--s2);">* Fewer than ${accuracy.min_bucket_n} games in this bucket &mdash; the rate is shown for completeness but is not a meaningful measurement.</p>`
    : '';
  const calibHtml = `
    <div class="method-block">
      <h3>Are these percentages honest?</h3>
      <p>Does a game we picked at, say, 65% confidence actually win about 65% of the time? Compares the average predicted probability in each confidence bucket to how often the pick was actually right.</p>
      ${calibChartHtml}
      <div class="table-wrap"><table class="metrics-table"><caption class="visually-hidden">Stated confidence against how often the pick was right, by bucket</caption>
        <thead><tr><th scope="col">Confidence Bucket</th><th scope="col">Games</th><th scope="col">Avg Predicted</th><th scope="col">Actual Correct Rate</th></tr></thead>
        <tbody>${calibRows || '<tr><td colspan="4">Not enough graded games yet.</td></tr>'}</tbody>
      </table></div>
      ${calibFootnote}
    </div>`;

  el.innerHTML = cardsHtml + forecastScoreHtml(accuracy.forecast_score) + cumulativeChartHtml + weeklyHtml + calibHtml
    + againstMarketHtml(accuracy.against_market);
}
renderAccuracy();
/* Stage 79 item 49: the trend redrawn at its box's width whenever that
   changes, including from 0 to its width the first time Accuracy is shown. */
function sizeTrendChart(){
  const plot = document.getElementById('trend-plot');
  if(!plot || chartIsPhone()) return;
  const w = Math.round(plot.clientWidth);
  if(!w || w === Number(plot.dataset.w)) return;
  const tmp = document.createElement('div');
  tmp.innerHTML = buildCumulativeTrendChart(w);
  const fresh = tmp.querySelector('#trend-plot');
  if(fresh) plot.replaceWith(fresh);
}
{
  const plotBox = document.getElementById('accuracy-content');
  if(plotBox && window.ResizeObserver) new ResizeObserver(sizeTrendChart).observe(plotBox);
  else window.addEventListener('resize', sizeTrendChart);
}

(function mountReliabilityDiagram(){
  const el = document.getElementById('reliability-diagram');
  if(!el) return;
  const html = buildReliabilityDiagram();
  if(!html) return;          // no calibration.json in this build
  el.innerHTML = html;
  initReliabilityDiagram();
})();

