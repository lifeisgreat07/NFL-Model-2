/* ---------- Week Board ---------- */
let currentBoardWeek = latestWeekKey;
let currentFilter = 'all';
/* Kickoff order, not confidence. A week is a sequence of games before it is a
   ranking of them: the reader's first question is what is on next, and the
   board answering with "most confident" made them re-sort every visit to find
   out. Confidence is still one click away, and is still the secondary sort
   inside a single kickoff slot, which is where it earns its place -- thirteen
   of week 1's sixteen games start at the same minute. */
let currentSort = 'chronological';

function populateWeekSelect(selectEl, onChange, initial){
  if(weekKeysSorted.length===0){
    selectEl.innerHTML = `<option>No weeks saved yet</option>`;
    selectEl.disabled = true;
    return;
  }
  selectEl.innerHTML = weekKeysSorted.map(k=>`<option value="${k}">${weekLabel(k)}</option>`).join('');
  selectEl.value = initial || weekKeysSorted[weekKeysSorted.length-1];
  selectEl.addEventListener('change', ()=> onChange(selectEl.value));
}

/* Marks the side a model picked, and - once the game is played - whether that
   pick was right.

   Three states, and the colour is what separates them:

     picked, not graded  tick in --accent    "this is the model's pick"
     picked, correct     tick in --good      "the pick was right"
     picked, wrong       cross in --warn     "the pick was wrong"
     not picked          dashed outline      the other side, or a toss-up

   The pre-game tick is deliberately NOT green. The version before this drew a
   green tick on unplayed games, which said a model had been proved right about
   a game nobody had played; that was one of six graded-colour violations fixed
   in PR #52, and the onboarding copy had to be rewritten because it described
   the tick as showing "which team each model actually favors" - which is the
   job being restored here, minus the false verdict.

   --accent is the right token for it: Job 2 is the model's lean and the active
   thing. --good and --warn stay Job 3, graded outcomes only, and still cannot
   appear on a game that has not happened. Bold weight beside the badge carries
   the same information for anyone who cannot separate the two hues. */
function pickBadge(picked, graded, correct){
  // A graded game with no verdict is a tie (Stage 30 item 1): no badge, since
  // a tick or a cross would each claim a result the game did not have.
  if(!picked || (graded && (correct === null || correct === undefined)))
    return `<span class="pick-badge placeholder"></span>`;
  const tick = '<path d="M20 6L9 17l-5-5"/>';
  const cross = '<path d="M6 6l12 12M18 6L6 18"/>';
  const state = !graded ? 'picked' : (correct ? 'correct' : 'incorrect');
  const label = !graded ? "this model's pick"
    : (correct ? "this model's pick: correct" : "this model's pick: missed");
  return `<span class="pick-badge ${state}" title="${label}">`
    + `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round">${state === 'incorrect' ? cross : tick}</svg></span>`;
}

/* The graded tag on a card: Model B's verdict (Model A's when B had no
   pick), or "Tie" for a graded game with no winner. Until Stage 30 item 1 a
   tie fell through `?? ... ? 'correct' : 'incorrect'` to "Missed" with the
   warn colour, because null is falsy. */
function gradedTagHtml(g){
  if(!g.graded) return '';
  const verdict = g.model_b_correct ?? g.model_a_correct;
  if(g.result === 'tie' || verdict === null || verdict === undefined)
    return `<span class="graded-tag tie">Tie</span>`;
  return `<span class="graded-tag ${verdict ? 'correct' : 'incorrect'}">${verdict ? 'Correct' : 'Missed'}</span>`;
}

/* Turns the model's own numbers into a football sentence.

   g.why holds what the football-only model actually used: each feature's
   contribution, signed toward the HOME team. Those are the real quantities the
   model added up, not a story told afterwards -- which is the only reason it is
   honest to narrate them at all.

   Three rules, so the wording is derived rather than chosen:
     - the favourite is whichever side the football-only model gives over 50%;
     - each contribution is flipped, if needed, to point toward that favourite,
       so "helps" and "hurts" mean the same thing in every card;
     - how much one reason dominates is its share of the total movement on the
       card, and that share picks the phrase. A reason carrying most of the
       card gets "almost entirely"; a near-tie gets neither name promoted.

   Deliberately returns markup so tests/test_plain_language.py scans this copy.
   A helper returning bare text would escape the jargon guard entirely, which
   is the sort of gap that only shows up months later. */
const WHY_IN_WORDS = {
  off_matchup: {
    toward: (fav, dog) => `${fav}'s offense against ${dog}'s defense`,
    neutral: 'the offense-versus-defense matchup',
  },
  def_matchup: {
    toward: (fav, dog) => `${fav}'s defense against ${dog}'s offense`,
    neutral: 'the defense-versus-offense matchup',
  },
  qb_matchup: {toward: () => 'the quarterback matchup', neutral: 'the quarterback matchup'},
  qb_change:  {toward: () => 'a change at quarterback', neutral: 'the change at quarterback'},
};

function whyParts(g){
  if(!g.why) return null;
  const homeFav = g.fbA_home >= 50;
  const fav = homeFav ? g.home : g.away;
  const dog = homeFav ? g.away : g.home;
  const sign = homeFav ? 1 : -1;
  const parts = Object.keys(WHY_IN_WORDS)
    .filter(k => typeof g.why[k] === 'number' && g.why[k] !== 0)
    .map(k => ({key:k, toward: g.why[k] * sign,
                text: WHY_IN_WORDS[k].toward(fav, dog),
                neutral: WHY_IN_WORDS[k].neutral}))
    .sort((a,b) => Math.abs(b.toward) - Math.abs(a.toward));
  if(!parts.length) return null;
  const total = parts.reduce((s,p) => s + Math.abs(p.toward), 0);
  return {fav, dog, parts, total, helps: parts.filter(p=>p.toward>0), hurts: parts.filter(p=>p.toward<0)};
}

function whySentence(g){
  const w = whyParts(g);
  if(!w) return '';
  const top = w.parts[0];
  const share = w.total > 0 ? Math.abs(top.toward)/w.total : 0;

  // Nothing is really driving this one. Saying so is more useful than naming
  // the largest of several tiny numbers as though it were a reason.
  if(w.total < 0.10){
    return `<p class="why-words">Nothing much separates these two. ${w.fav} come out
      barely ahead, and a game this close is one the model expects to get wrong
      about as often as it gets it right.</p>`;
  }

  let lead;
  if(top.toward > 0 && share >= 0.6){
    lead = `${w.fav} are ahead here almost entirely on ${top.text}.`;
  } else if(top.toward > 0 && w.helps.length > 1){
    // Second factor named neutrally. Spelling both out in full gives
    // "mainly on KC's offense against DEN's defense, with KC's defense
    // against DEN's offense adding to it" -- correct, and nobody finishes it.
    lead = `${w.fav} are ahead here mainly on ${top.text}, with ${w.helps[1].neutral} adding to it.`;
  } else if(top.toward > 0){
    lead = `${w.fav} are ahead here on ${top.text}.`;
  } else {
    // The biggest single factor points at the underdog and the favourite still
    // wins on the rest. Worth saying plainly -- it is the most interesting
    // thing on such a card, and hiding it would flatter the pick.
    lead = `${w.fav} come out ahead despite ${top.text}, which favours ${w.dog}.`;
  }

  // Named by which side it favours, not as "X pulls the other way". The first
  // version read "DEN's offense against KC's defense pulls the other way",
  // which states a fact about Denver's offense and then contradicts it in the
  // same breath. Whose side a factor is on is the thing a reader wants.
  const against = top.toward > 0 && w.hurts.length
    ? ` ${w.hurts[0].neutral.charAt(0).toUpperCase() + w.hurts[0].neutral.slice(1)} favours ${w.dog}.`
    : '';

  return `<p class="why-words">${lead}${against}</p>`;
}

function whyMarketSentence(g){
  if(g.spread === null || g.spread === undefined) return '';
  const modelFav = g.fbA_home >= 50 ? g.home : g.away;
  // spread_line is POSITIVE when the home team is favoured. Verified against
  // the saved predictions rather than assumed: SEA home vs NE, spread_line
  // +3.5, market_prob_home 0.6539 -- the market has the home side at 65%, so
  // positive is home. The card's "Vegas line: LAC -10.5" display negates it,
  // which is the football convention and the reason this is easy to get
  // backwards. The first version of this line did, and said "the betting line
  // agrees" on a game where Model A had ARI at 80.5% and the line had LAC by
  // 10.5 -- confidently wrong, on every card, and invisible in the diff.
  const lineFav = g.spread > 0 ? g.home : g.away;
  const by = fmtPoints(Math.abs(g.spread));
  return lineFav === modelFav
    ? `<p class="why-words dim">The betting line agrees, making ${lineFav} favourites by ${by}.</p>`
    : `<p class="why-words dim">The betting line disagrees, making ${lineFav} favourites by ${by}.</p>`;
}

/* The sentence under a label saying whose it is (Stage 17). whySentence() is
   Model A's reasoning -- it reads g.why, which holds the football-only
   model's contributions, and names Model A's favourite -- while the card's
   headline is Model B's. Where they disagree (KC@MIA, week 3: Model B KC 86%,
   Model A MIA 57%) an unlabelled "MIA are ahead here..." sits under "KC 86%
   to win" and reads as a contradiction. The label goes only where there is a
   sentence to label. */
function whyLabelled(g){
  const words = whySentence(g);
  return words ? `<div class="why-by">Model A&#39;s reasoning</div>${words}` : '';
}

/* ---------- Units (Stage 14: one meaning per number) ----------
   "Points" on this page means football points and nothing else: a spread,
   a margin, a pick'em value. A gap between two percentages is "pp"
   (percentage points), never "pt" -- before Stage 14 the Model Lab and
   Methodology tables wrote accuracy gaps as "+0.83pt", one character from
   a point spread. tests/test_units.py bans a bare "pt"/"pts" anywhere a
   reader can see it.

   fmtPoints writes a spread in words with its unit. Lines move in half
   points, so a whole number drops its ".0" ("6 points", "6.5 points"), and
   one point is singular. The card said "favourites by 6.0" with no unit. */
function fmtPoints(n){
  const v = Math.round(Math.abs(n) * 10) / 10;
  const text = Number.isInteger(v) ? String(v) : v.toFixed(1);
  return `${text} point${v === 1 ? '' : 's'}`;
}

/* A rating, shown per 100 plays (Stage 14; Mark chose it from a rendered
   side-by-side on 2026-09-26). The model and the data stay in EPA per play
   -- BUF +0.149 -- and only the display is rescaled: +14.9 expected points
   better than an average team over 100 plays. One decimal, a sign on
   anything that is not zero, and a rating that rounds to zero shows as 0.0
   rather than -0.0. ratingScale() is the one place the factor lives -- a
   function, not a const, because renderRatings() runs at load from higher
   up this script, where a const declared here would still be in its
   temporal dead zone. tests/test_per_100_plays.py holds the display to the
   data. */
function ratingScale(){ return 100; }
function fmtRating(epaPerPlay){
  const v = Math.round(epaPerPlay * ratingScale() * 10) / 10;
  // No branch for zero: Math.round gives -0 for a small negative, and
  // (-0).toFixed(1) is "0.0", so a rating that rounds to zero is unsigned.
  return v > 0 ? '+' + v.toFixed(1) : v.toFixed(1);
}
/* A bar's scale, in the same units, to the nearest whole number. */
function fmtRatingScale(epaPerPlay){
  return String(Math.round(Math.abs(epaPerPlay) * ratingScale()));
}

function whyRow(label, val, text){
  const pct = Math.min(50, Math.abs(val)*300); // scaled for visual width, not a real unit
  const cls = val >= 0 ? 'pos' : 'neg';
  return `<div class="why-row">
    <span class="why-label">${label}</span>
    <div class="why-bar-track"><div class="why-bar-fill ${cls}" style="width:${pct}%;"></div></div>
    <span class="why-val">${text !== undefined ? text : `${val>=0?'+':''}${val.toFixed(3)}`}</span>
  </div>`;
}
/* Stage 77 item 23 (the audit's copy row 12): a why{} value is that part's
   push on Model A's log-odds, signed toward the home side -- not a rating,
   so it is not printed in points per 100 plays. It is printed as the points
   of win chance it gave a team: Model A's home chance with the part, less
   the chance with the part taken back out of the log-odds. "SEA +1.2" means
   that part added 1.2 points to SEA's chance. */
function whyChance(val, homePct, home, away){
  if(typeof homePct !== 'number' || homePct <= 0 || homePct >= 100) return '—';
  const p = homePct / 100;
  const without = 1 / (1 + Math.exp(-(Math.log(p / (1 - p)) - val)));
  const pts = Math.round((p - without) * 1000) / 10;
  if(pts === 0) return 'even';
  return `${pts > 0 ? home : away} +${Math.abs(pts).toFixed(1)}`;
}

/* The Week Board's summary strip is gone: Games / Most confident / Biggest
   model gap. The owner asked for it removed twice -- "I do not need this at
   all" -- and each tile earns that independently. Games duplicated the "16
   games" badge already in the page head. Biggest model gap is the A-vs-market
   gap he separately called unnecessary on the cards, stated in a unit
   ("59pt") nobody has a scale for. Most confident restated what the first
   card in the default sort already showed, because the board sorted by
   confidence at the time. It no longer does -- the default is now kickoff
   order -- so that particular argument has expired even though the decision
   it supported has not. Recorded rather than quietly reworded: the tile is
   still not coming back, but the next person should not find a reason here
   that stopped being true and assume the rest of the paragraph is current.

   Kept as an empty function rather than deleted outright because renderGames
   calls it and the #week-glance node is a stable hook: the strip may come
   back as something that earns its space, and an empty seam is easier to fill
   than a removed one is to rebuild. */
function renderWeekGlance(gamesList){
  const el = document.getElementById('week-glance');
  if(el) el.innerHTML = slateSummaryHtml(gamesList);
}
/* Stage 80 item 59 (the 2026-10-13 audit's F16): a graded week's summary,
   at the top of the Week Board: "Model B 10–4 · Model A 12–2 · Market 9–5 ·
   1 tie", and while the week is still being played, how many games are in.
   Each record counts the games graded with a winner, as the Season Accuracy
   page does; a tie counts for no one and is named. The seam above held a
   strip until Stage 9, left empty for one that earns its space. */
function slateSummaryHtml(games){
  const graded = (games || []).filter(g => g.graded && g.result !== 'tie');
  if(!graded.length) return '';
  const rec = key => {
    const v = graded.map(g => g[key]).filter(x => x !== null && x !== undefined);
    const won = v.filter(x => x === true || x === 1).length;
    return `${won}–${v.length - won}`;
  };
  const parts = [['Model B', 'model_b_correct'], ['Model A', 'model_a_correct'], ['Market', 'market_correct']]
    .map(([name, key]) => `<span>${name} <b>${rec(key)}</b></span>`);
  // A tie is graded and counts for no one, so it is named; a cancelled game
  // is never graded, so it is not counted as still to come.
  const ties = games.filter(g => g.graded && g.result === 'tie').length;
  const due = games.filter(g => g.status !== 'cancelled'), done = due.filter(g => g.graded).length;
  if(ties) parts.push(`<span>${ties} tie${ties === 1 ? '' : 's'}</span>`);
  const of = done < due.length ? ` <span class="slate-of">${done} of ${due.length} graded</span>` : '';
  return `<p class="slate-summary">${parts.join(' · ')}${of}</p>`;
}

/* ---------- The matchup title, built in ONE place ----------
   Two functions render a .game-card: renderGames() for the Week Board and
   renderPicksGrid() for My Picks. Both used to hand-build this title, and
   that is not a tidiness complaint -- it is why the `@` separator survived
   on My Picks after being changed everywhere else. One edit, two sites, one
   of them missed, and nothing could tell: the diff looked complete.

   Appearance is deliberately NOT unified here. On My Picks the two pick
   buttons already carry both team abbreviations, so the title is a quiet
   label rather than a heading, and it is measured at 11px / weight 400 /
   --text-2 on the rendered page. Whether that is right is a Stage 9/10
   question about the card, not something a refactor should decide on its
   way past. The variant keeps the CSS free to differ while the MARKUP can
   only be written once.

   The note that used to sit here warned that `.game-kickoff` held a
   confidence rank and would collide with a real kickoff. That happened, and
   the class is now `.game-confidence`; the kickoff line on both cards is
   `.card-kickoff`. Left as a record rather than deleted: the warning was
   written a fortnight before the collision, which is the argument for
   writing them down at all. */
/* ---------- The pick button ----------
   A team tile rather than a word: a logo above the abbreviation, so the thing
   you tap is recognisable at a glance instead of three capital letters.

   The logo is decorative and carries alt="" deliberately. The abbreviation is
   real text beside it, so a screen reader that announced both would read the
   team twice; and the button's accessible name has to stay the abbreviation
   because that is what the pick is recorded as. onerror hides the image
   rather than leaving a broken-image glyph -- the logos come from a third
   party and the tile has to survive that host being unreachable, which is why
   the abbreviation is the text and not the picture. */
function pickButton(team, pick, locked){
  // `locked` is emitted here so the first frame is right; paintPickCard
  // re-derives it on every path, the same way it re-derives `selected`.
  return `<button class="pick-btn ${pick===team?'selected':''}" data-team="${team}"`
    + (locked ? ` disabled aria-label="${team}, locked at kickoff"` : '') + `>`
    + `<img class="pick-logo" src="${teamLogo(team)}" alt="" loading="lazy" referrerpolicy="no-referrer" data-hide-on-error>`
    + `<span class="pick-abbr">${team}</span>`
    + `</button>`;
}

/* ---------- The card's probability line (Stage 17, card v2) ----------
   Mark chose "B refined" on 2026-09-27 from rendered side-by-sides (dark,
   light, deutan): the team-colour bar is kept and shows Model B's split; the
   three probabilities sit on ONE line beneath it, on the same scale, with the
   shapes Season Accuracy uses (Model A circle, Model B square, Market
   triangle). Model B is the headline because it is the better model on
   proper scoring rules (Model Lab); the market is shown as a probability,
   not only as a spread.

   Everything is stored as the HOME side's percentage; a side is named by
   which half of the line it falls in. Within CARD_EVEN_BAND points of 50 a
   series has picked nobody, and the card says so rather than bolding a team
   on a 50.4 / 49.6 split. */
const CARD_EVEN_BAND = 2;

function cardSide(pHome, g){
  if(pHome === null || pHome === undefined) return null;
  if(Math.abs(pHome - 50) < CARD_EVEN_BAND) return {team: null, pct: Math.max(pHome, 100 - pHome)};
  return pHome >= 50 ? {team: g.home, pct: pHome} : {team: g.away, pct: 100 - pHome};
}

/* Markers closer than CARD_NEAR points would hide one another. 7 is measured,
   not picked: the narrowest line (176px, at a 360px screen) gives a 12px
   marker 6.8 points of the scale, so two markers 7 points apart on the same
   lane cannot touch at any supported width. (The first cut used 3 points and
   9px lanes; measured on the built page, markers overlapped by more than half
   a pixel on 12 of week 3's 16 cards at 1280px and 13 at 390px.) When they would, each takes a FIXED lane -- the Market above the line, Model B on it,
   Model A below -- so the same series always moves the same way and a reader
   learns it once. A marker with no neighbour stays on the line. */
/* The card's series, in the same colours and shapes as SERIES below. A copy
   rather than a reference: SERIES is declared further down the script than
   the Week Board's first render, and reading a const before its line throws
   (it did, in the first render of this card). tests/test_card_v2.py holds
   the two to each other. */
const CARD_SERIES = {
  a:      {label:'Model A', color:'var(--series-a)', shape:'circle'},
  b:      {label:'Model B', color:'var(--series-b)', shape:'square'},
  market: {label:'Market',  color:'var(--series-c)', shape:'triangle'},
};

const CARD_NEAR = 7;
const CARD_LANE = {market: -1, b: 0, a: 1};

function cardLanes(vals){
  const keys = Object.keys(vals).filter(k => vals[k] !== null && vals[k] !== undefined);
  const out = {};
  keys.forEach(k => {
    const crowded = keys.some(o => o !== k && Math.abs(vals[o] - vals[k]) < CARD_NEAR);
    out[k] = crowded ? CARD_LANE[k] : 0;
  });
  return out;
}

function cardSideText(s){
  return s.team ? `${s.team} ${Math.round(s.pct)}%` : `even (${Math.round(s.pct)}%)`;
}

/* The one sentence a screen reader hears for the whole visual. */
function cardAria(g){
  const b = cardSide(g.mktB_home, g), a = cardSide(g.fbA_home, g), m = cardSide(g.mkt_home, g);
  return [`Model B ${cardSideText(b)}`, m ? `Market ${cardSideText(m)}` : null,
          `Model A ${cardSideText(a)}`].filter(Boolean).join('. ') + '.';
}

/* Whether the two models pick different teams: the one test behind the
   card's "Models split" badge, its "Model A picks X; Model B picks Y" line
   and the Model Disagreement filter. The badge and the filter used to test
   a 12-point gap instead, so a card could say "Models agree" above a line
   saying the models picked different teams (TEN@NYG, 2026 week 3: Model A
   TEN 53%, Model B NYG 55%) -- and 12 points apart on the same team read
   as a split. A model within CARD_EVEN_BAND of 50 has picked nobody, which
   is not a disagreement about who wins. */
function modelsSplit(g){
  const a = cardSide(g.fbA_home, g), b = cardSide(g.mktB_home, g);
  return !!(a && b && a.team && b.team && a.team !== b.team);
}

/* Named only when Model A picks the OTHER team from Model B -- not when one
   of them calls it even, which is not a disagreement about who wins. */
function cardDisagreement(g){
  if(!modelsSplit(g)) return '';
  const a = cardSide(g.fbA_home, g), b = cardSide(g.mktB_home, g), m = cardSide(g.mkt_home, g);
  const withB = m && m.team === b.team ? 'Model B and the market pick' : 'Model B picks';
  return `Model A picks <b>${a.team}</b>; ${withB} <b>${b.team}</b>.`;
}

/* A game that is over but not graded yet (Stage 26 item 1, from the
   2026-09-28 audit). The card went on saying "GB 68% to win" after the final
   whistle. Now it says what Model B picked and who won, in the headline's
   own neutral grey: no right or wrong, which is the graded tag's to say once
   grading runs, and no word on when grading happens, which Mark removed on
   2026-09-28 as redundant. The score is the weekend refresh's, so it is
   stated as a result, not scored. Returns '' for any other state. */
function cardProvisional(g){
  if(g.status !== 'final' || g.graded || !gameHasScore(g)) return '';
  if(g.away_score === g.home_score) return 'a tie';
  return `${g.away_score > g.home_score ? g.away : g.home} won`;
}

/* Stage 75 item 3: an opened card is brought on screen. A row near the
   bottom of a phone opened its card below the fold and never scrolled
   (NHL card 612 to 1052 px, NFL 704 to 1195 px, on an 844 px phone). 'nearest'
   leaves a card that is already in view where it is. */
function revealOpened(panel){
  const still = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;
  panel.scrollIntoView({block: 'nearest', behavior: still ? 'auto' : 'smooth'});
}

/* Stage 80 item 63 (F13): what this card's shared image says. src/core/share_card.js,
   which the build puts on the page, draws it when "Share image" is pressed. */
function shareAttr(g, awayC, homeC){
  const has = v => v !== null && v !== undefined;
  const lead = has(g.mktB_home) ? ['Model B', g.mktB_home] : ['Model A', g.fbA_home];
  const s = cardSide(lead[1], g);
  const forecasts = [['Model B', g.mktB_home], ['Market', g.mkt_home], ['Model A', g.fbA_home]]
    .filter(([, v]) => has(v)).map(([label, v]) => ({label, text: cardSideText(cardSide(v, g))}));
  const verdict = g.graded ? (g.model_b_correct ?? g.model_a_correct) : undefined;
  const result = !g.graded ? null : (g.result === 'tie' || !has(verdict)) ? 'Tie' : verdict ? 'Correct' : 'Missed';
  const score = g.status === 'final' && gameHasScore(g) ? `Final: ${g.away} ${g.away_score}, ${g.home} ${g.home_score}` : null;
  return escapeHtml(JSON.stringify({sport: 'NFL', away: g.away, home: g.home, colours: [awayC, homeC], lead: lead[0], team: s.team,
    pct: s.pct, homePct: lead[1], forecasts, when: kickoffLabel(g), result, score}));
}
/* Stage 80 item 64 (V2): the logo of the side Model B picks (Model A's
   without a market), faint and grey, in the card's corner (styles.css). */
function watermark(g){
  const s = cardSide(g.mktB_home ?? g.fbA_home, g);
  return s && s.team ? ` style="--wm:url('${teamLogo(s.team)}')"` : '';
}
function cardProbHtml(g, awayC, homeC){
  const b = cardSide(g.mktB_home, g), a = cardSide(g.fbA_home, g), m = cardSide(g.mkt_home, g);
  const vals = {b: g.mktB_home, a: g.fbA_home, market: g.mkt_home};
  const lanes = cardLanes(vals);
  const mark = k => {
    if(vals[k] === null || vals[k] === undefined) return '';
    const s = CARD_SERIES[k];
    // One axis (Stage 75 item 1): the bar draws the away team first, so a
    // home share v sits at 100 - v from the left, and the lead model's
    // marker lands on the split. tests/browser/check_card_axis.py.
    // 12px markers on 12px lanes: a laned marker clears its neighbour.
    return `<svg class="card-mk" data-series="${k}" style="left:${100 - vals[k]}%; top:calc(50% + ${lanes[k] * 12}px)" width="12" height="12" viewBox="0 0 12 12" aria-hidden="true">`
      + `${markerPath(s.shape, 6, 6, 4.5)} fill="${s.color}"/></svg>`;
  };
  const key = (k, side) => {
    const s = CARD_SERIES[k];
    return `<span class="card-key"><svg width="12" height="12" viewBox="0 0 14 14" aria-hidden="true">${markerPath(s.shape, 7, 7, 5)} fill="${s.color}"/></svg>`
      + `${s.label} <b>${cardSideText(side)}</b></span>`;
  };
  const bPicksAway = b.team === g.away, bPicksHome = b.team === g.home;
  const done = cardProvisional(g);
  const after = done ? `<span class="card-hl-to">&middot; ${done}</span>` : '<span class="card-hl-to">to win</span>';
  const headline = b.team
    ? `<span class="card-hl-label">Model B${done ? ' picked' : ''}</span> <b>${b.team} ${Math.round(b.pct)}%</b> ${after}`
    : `<span class="card-hl-label">Model B</span> <b>Too close to call</b>${done ? ` <span class="card-hl-to">&middot; ${done}</span>` : ''}`;
  const disagree = cardDisagreement(g);
  return `<div class="card-hl">${headline}</div>
      <div class="card-viz">
        <span class="card-end">${favStar('nfl', g.away, escapeHtml(teamFullName(g.away)))}${pickBadge(bPicksAway, g.graded, g.model_b_correct)}${barTeam(g.away)}</span>
        <div class="card-scale" role="img" aria-label="${cardAria(g)}">
          <div class="tele-bar">
            <div class="tele-bar-seg" style="width:${100-g.mktB_home}%; background:${awayC};"></div>
            <div class="tele-bar-seg" style="width:${g.mktB_home}%; background:${homeC};"></div>
          </div>
          <div class="card-line"><span class="card-mid"></span><span class="card-mid-label">50%</span>${mark('a')}${mark('market')}${mark('b')}</div>
        </div>
        <span class="card-end">${pickBadge(bPicksHome, g.graded, g.model_b_correct)}${barTeam(g.home)}${favStar('nfl', g.home, escapeHtml(teamFullName(g.home)))}</span>
      </div>
      <div class="card-keys">${key('b', b)}${m ? key('market', m) : ''}${key('a', a)}</div>
      ${disagree ? `<div class="card-disagree">${disagree}</div>` : ''}`;
}

function matchupHeader(g, variant){
  return `<div class="matchup-header${variant ? ' ' + variant : ''}">${g.away} <span class="at-symbol">at</span> ${g.home}</div>`;
}

/* The Week Board's logos sit at the two ends of Model B's bar, beside each
   team's abbreviation (Mark, 2026-09-28: he preferred them there to the
   header Stage 17 put them in). 20px, the size the Stage 8 restyle set for
   logos in the core UI. Decorative, alt="", because the abbreviation beside
   each logo is the name, and a screen reader would otherwise read every team
   twice. onerror hides a logo ESPN will not serve and leaves the
   abbreviation: the same fallback as every other logo here, and the reason
   the logos are hot-linked rather than copied into the repository (CLAUDE.md
   Stage 12). On a phone the logo stacks above the abbreviation, so the ends
   are no wider than the abbreviation alone and the probability line keeps
   the width CARD_NEAR was measured on. */
/* A team's full name, for a star's label (Stage 80 item 53); the code when
   the team history is missing. */
function teamFullName(team){ return ((teamHistory || {}).names || {})[team] || team; }
function barTeam(team){
  return `<span class="card-end-team"><img class="card-end-logo" src="${teamLogo(team)}" alt="" loading="lazy" referrerpolicy="no-referrer" data-hide-on-error>${team}</span>`;
}

/* ---------- Kickoff order ----------
   ISO date + 24-hour zero-padded time compares correctly as a string, which is
   why NO Date is constructed here. Parsing "2026-09-13" + "13:00" into a Date
   attaches the RUNTIME's timezone to a value that is Eastern, so the board
   would reorder itself depending on where the reader is sitting -- and the
   failure is silent, because a misplaced card still looks like a card.
   Verified against the real feed rather than assumed: every gameday is
   YYYY-MM-DD and every gametime_et is HH:MM zero-padded, including the 09:30
   London kickoffs, so lexical order IS chronological order.

   A game with no date sinks rather than sorting first. An unknown kickoff is
   unknown, not midnight. That branch is not hypothetical housekeeping: it is
   what every saved week looked like before these fields existed, and what a
   week looks like again if the schedule stops supplying them.

   At module scope so the suite can execute them -- the comparator they serve
   lives inside renderGames(), which needs a DOM and a week of real data, and
   a sort nobody can run is a sort nobody can check. */
/* ---------- Kickoff, in words ----------
   Built from the string parts, never from a Date, for the same reason
   kickoffKey below is a string compare: the stored time is EASTERN, and a
   Date is interpreted in the reader's zone, so "8:20 PM ET" would quietly
   become 5:20 PM for anyone on the west coast while still reading as a
   correct-looking kickoff. ET is stated in the output because a time whose
   zone is unstated is unfalsifiable by whoever reads it.

   Returns '' rather than a placeholder when there is no date. A week saved
   before these fields existed has none, and an empty string renders nothing
   at all -- which is honest -- where "TBD" would be a claim nobody made. */
const KICKOFF_MONTHS = ['Jan','Feb','Mar','Apr','May','Jun',
                        'Jul','Aug','Sep','Oct','Nov','Dec'];

function kickoffLabel(g){
  if(!g.gameday) return '';
  const parts = g.gameday.split('-');
  const date = `${KICKOFF_MONTHS[Number(parts[1]) - 1]} ${Number(parts[2])}`;
  const day = g.weekday ? `${g.weekday}, ` : '';
  if(!g.gametime_et) return `${day}${date}`;
  // Stage 80 item 57: in the visitor's own time zone, through the one place
  // an Eastern start becomes an instant (kickoffLocalLabel, after renderGames).
  if(!startZone()) return kickoffLocalLabel(g);
  const hm = g.gametime_et.split(':');
  const hour24 = Number(hm[0]);
  const suffix = hour24 >= 12 ? 'PM' : 'AM';
  const hour12 = hour24 % 12 === 0 ? 12 : hour24 % 12;
  return `${day}${date} · ${hour12}:${hm[1]} ${suffix} ET`;
}

/* ---------- Where a game stands (Stage 15) ----------
   One line from the weekend refresh's snapshot, or '' for no line at all.
   "final" needs both scores; a snapshot can go stale after grading (Monday
   night's game is still "upcoming" in Monday morning's snapshot when
   Tuesday grades it), so a graded game says nothing here unless the
   snapshot has its final score -- the graded tag already says how the pick
   did, and "score not in yet" beside it would contradict it. */
/* Both scores are in. Compared with null, not by truth: 0 is a real score. */
function gameHasScore(g){
  return g.away_score !== null && g.away_score !== undefined
    && g.home_score !== null && g.home_score !== undefined;
}

/* A neutral site (Stage 37 item 6). The game still has a listed home team.
   From v2.6 (Stage 38 N1, experiments/nfl/stage38/n1_registry.json) neither
   model gives it the home edge, and the pick records that (edge_out). A pick
   saved before v2.6 did give it the edge, and its card still says so: the
   card describes the pick that was saved, never the model that came after. */
function cardSiteLine(g){
  if(!g.neutral) return '';
  const where = g.venue ? ` · ${escapeHtml(g.venue)}` : '';
  if(g.edge_out) return `Neutral site${where}. Neither model gives ${escapeHtml(g.home)} a home edge here.`;
  return `Neutral site${where}. The models gave ${escapeHtml(g.home)} the home edge (picks saved before v2.6).`;
}

function cardStatusLine(g){
  const hasScore = gameHasScore(g);
  // Just the score. Until 2026-09-28 an ungraded final also said when the
  // picks would be graded; Mark called that redundant, and the graded tag
  // says it once it happens.
  if(g.status === 'final' && hasScore) return `Final: ${g.away} ${g.away_score}, ${g.home} ${g.home_score}`;
  if(g.status === 'started' && !g.graded) return 'Kicked off · final score not in yet';
  // Mark's call (2026-10-05): the card stays and shows its pick, and the
  // game is graded for nobody and left out of every count.
  if(g.status === 'cancelled') return 'Cancelled · not played, so not graded';
  return '';
}

/* ---------- Where to watch, the quarterbacks, team news (Stage 17) ----------
   Three small facts, each from a file that was checked before it got here:
   the channel from src/sports/nfl/tv_channels.py (one network, only one that passed
   its checks), the quarterbacks from the saved pick itself (so the card
   cannot name a different one from the model's), and the news from
   src/sports/nfl/team_news.py. Each returns '' when it has nothing to say, and nothing
   is drawn -- a blank line or "no news" would be a claim nobody made.

   Once a game is final or graded, "where to watch" and "who is hurt" are
   history, so the channel and the news go; the quarterbacks stay, because
   they are part of the pick. */
/* The one HTML escaper. Until Stage 25 there were three identical
   copies: this one under another name, one for What's Changed and
   one local to renderTeamNews. */
function escapeHtml(s){
  return String(s).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
}

/* Two strings that reached innerHTML as written, until Stage 23 (the
   2026-09-28 audit): what a reader types into the Power Ratings search, and
   the context notes on a card, which come from sourced web reports. Each
   now goes through escapeHtml(), and each is a function of its own so
   tests/test_template_sinks.py can run it in node. */
function ratingsNoMatchRow(q){
  return `<tr><td colspan="8" style="text-align:center; padding:var(--s6); color:var(--text-2);">No teams match "${escapeHtml(q)}"</td></tr>`;
}

function contextNotesHtml(notes){
  return notes.map(n=>`<li style="margin-bottom:var(--s1);">${escapeHtml(n)}</li>`).join('');
}

function cardTvPill(g){
  if(!g.tv || g.graded || g.status === 'final' || g.status === 'cancelled') return '';
  // "regional" on the pill itself (Stage 37 item 2, Mark's observation in
  // the 2026-10-04 audit): nine cards reading "CBS" implied every viewer
  // gets all nine. Which games a viewer gets depends on their market, which
  // nfl.com does not say, so the pill says regional and nothing more.
  const regional = g.tv_regional ? '<span class="tv-regional"> · regional</span>' : '';
  return `<span class="tv-pill"><span class="visually-hidden">On TV: </span>${escapeHtml(g.tv)}${regional}</span>`;
}

/* One header per kickoff slot on the Week Board (Stage 37 item 2): a
   Sunday's 1:00 PM games read as one group under one time instead of the
   same time on every card. Only under the chronological sort -- under any
   other order a slot header would contradict the order the cards are in. */
function slotKey(g){
  return g.gameday ? `${g.gameday} ${g.gametime_et || ''}` : '';
}

function slotHeadBefore(sorted, i, pinned = 0){
  // Stage 80 item 53: the first `pinned` cards are a favourite team's games,
  // under a head of their own; the slots, and their counts, are the rest's.
  if(pinned){
    if(i === 0) return `<h3 class="slot-head">Your teams<span class="slot-count"> · ${pinned} game${pinned === 1 ? '' : 's'}</span></h3>`;
    if(i < pinned) return '';
    if(currentSort !== 'chronological') return i === pinned ? '<h3 class="slot-head">Every other game</h3>' : '';
    return slotHeadBefore(sorted.slice(pinned), i - pinned);
  }
  if(currentSort !== 'chronological') return '';
  const key = slotKey(sorted[i]);
  if(!key || (i > 0 && slotKey(sorted[i - 1]) === key)) return '';
  const n = sorted.filter(g => slotKey(g) === key).length;
  return `<h3 class="slot-head">${escapeHtml(kickoffLabel(sorted[i]))}`
    + `<span class="slot-count"> · ${n} game${n === 1 ? '' : 's'}</span></h3>`;
}

/* Sunday-afternoon CBS and FOX games are regional: nfl.com says so
   (territory REGIONAL) but not where, so one line on the page says so once,
   rather than every card implying every viewer gets that game. Only when a
   card on screen carries such a channel. */
function boardTvNote(games){
  return games.some(g => cardTvPill(g) !== '' && g.tv_regional);
}

function cardQbLine(g){
  if(!g.away_qb && !g.home_qb) return '';
  const side = (team, name, basis) => !name ? `${team} none on record`
    : `${team} <b>${escapeHtml(name)}</b>`
      + (basis === 'last_game' ? ' (assumed: last game&#39;s starter)' : '');
  return `Quarterbacks: ${side(g.away, g.away_qb, g.away_qb_basis)} · ${side(g.home, g.home_qb, g.home_qb_basis)}`;
}

// One team's news, or null. The pick's own quarterback on the injury report
// comes first, because it is the item that changes how far to trust the pick;
// then a new starter; then other starters out or doubtful, by name up to two
// and as a count beyond that, so the line stays one line. Questionable
// players are left to Team Deep-Dive.
function cardNewsTeam(team, entry){
  if(!entry) return null;
  const published = entry.injury_report === 'published';
  const out = published ? (entry.out || []) : [], doubtful = published ? (entry.doubtful || []) : [];
  const qb = entry.qb && entry.qb.name ? entry.qb : null;
  const bits = [];
  const qbListed = !qb ? null : out.some(p => p.name === qb.name) ? 'out'
    : doubtful.some(p => p.name === qb.name) ? 'doubtful' : null;
  if(qbListed) bits.push(`QB ${qb.name} ${qbListed}`);
  else if(qb && qb.changed_from) bits.push(`new QB`);
  const others = out.map(p => [p.name, 'out']).concat(doubtful.map(p => [p.name, 'doubtful']))
    .filter(([name]) => !qb || name !== qb.name);
  if(others.length > 2) bits.push(`${others.length} starters out or doubtful`);
  else others.forEach(([name, status]) => bits.push(`${name} ${status}`));
  return bits.length ? `${team}: ${bits.join(', ')}` : null;
}

function cardNewsLine(g, news){
  if(!news || !news.teams || g.graded || g.status === 'final' || g.status === 'cancelled') return '';
  const parts = [g.away, g.home].map(t => cardNewsTeam(t, news.teams[t])).filter(Boolean);
  return parts.length ? `<b>Team news</b> ${parts.map(escapeHtml).join(' · ')}` : '';
}

function kickoffKey(g){
  return g.gameday ? `${g.gameday}T${g.gametime_et || '00:00'}` : null;
}

function byConfidence(a, b){
  return (a.confidence_rank ?? 999) - (b.confidence_rank ?? 999);
}

function byKickoff(a, b){
  const ka = kickoffKey(a), kb = kickoffKey(b);
  if(ka === null && kb === null) return byConfidence(a, b);
  if(ka === null) return 1;
  if(kb === null) return -1;
  if(ka !== kb) return ka < kb ? -1 : 1;
  // Thirteen of week 1's sixteen games kick off at the same minute, so without
  // a tiebreak this sort would leave most of the board in file order and look
  // like it had done nothing.
  return byConfidence(a, b);
}

/* Stage 68 item 36 (option N2 of the rendered Stage 68 design options,
   Mark's pick on 2026-10-10): on a phone each game is a compact row, as on
   the NHL's day board, that opens to its full card. Fifteen open cards were
   9,146 px of page and 30 logo requests at load; the rows are about 1,600 px.
   Wider than 640 px the rows are not shown and every card is, as before.
   The row says the time, the game, Model B's pick and, once graded,
   whether it was right. */
function phoneRowHtml(g, n){
  const time = g.gametime_et ? kickoffClock(g) : '';
  const s = cardSide(g.mktB_home, g) || cardSide(g.fbA_home, g);
  const pick = !s ? '—' : s.team ? `${escapeHtml(s.team)} ${Math.round(s.pct)}%` : 'Toss-up';
  const verdict = g.graded ? (g.model_b_correct ?? g.model_a_correct) : undefined;
  // An ungraded final says Final and no more, as its card does (cardProvisional).
  const res = !g.graded ? (g.status === 'final' ? ['final', 'Final'] : ['', '']) : (g.result === 'tie' || verdict === null || verdict === undefined) ? ['tie', 'Tie']
    : verdict ? ['correct', 'Correct'] : ['incorrect', 'Missed'];  // Stage 77 item 26: one pair of result words
  return `<button type="button" class="game-row nfl-row" aria-expanded="false" aria-controls="card-${n}"${scoreMark(g)}>`
    + `<span class="nfl-row-time"><span class="score-off">${time}</span>${scoreSlot('clock')}</span>`
    + `<span class="nfl-row-game"><span class="score-off">${escapeHtml(g.away)} @ ${escapeHtml(g.home)}</span>${scoreSlot('game')}${g.flag ? ` <span class="nfl-row-flag" role="img" aria-label="flagged: a note to read">${FLAG_ICON}</span>` : ''}</span>`
    + `<span class="nfl-row-pick">${pick}</span>`
    + `<span class="nfl-row-res ${res[0]}">${res[1]}</span>`
    + `<svg class="game-row-chev nfl-row-chev" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 9l6 6 6-6"/></svg></button>`;
}

/* Stage 21's two game insights, for the week on the board: Model B and the
   market MARKET_GAP_MIN points or more apart (Model B, because Model A never
   sees the market and is that far from it in most games), and a game both
   models put within COIN_FLIP_WITHIN points of 50%. In kickoff order. */
/* Stage 77 item 28 (N5): a flagged row is marked with a flag, not a dot --
   the dot means "live" on the home page and in the sidebar -- and a week
   with one says what the flag means, once, above the phone rows. */
const FLAG_ICON = '<svg viewBox="0 0 24 24" width="12" height="12" fill="currentColor" aria-hidden="true"><path d="M5 22V3h12l-2.5 4.5L17 12H7v10z"/></svg>';
const FLAG_LEGEND = `<p class="nfl-flag-legend"><span class="nfl-row-flag">${FLAG_ICON}</span><span class="visually-hidden">A flag</span> marks a game with a note to read before you trust its pick. The note is in the game's card.</p>`;
function boardInsights(games){
  const out = [];
  for(const g of [...games].sort(byKickoff)){
    const mkt = g.mkt_home;
    if(typeof mkt === 'number' && Math.abs(g.mktB_home - mkt) >= INSIGHT.MARKET_GAP_MIN){
      out.push({kind: 'market', g,
        text: `Model B gives ${g.home} ${Math.round(g.mktB_home)}%, the market ${Math.round(mkt)}%.`});
    }
    if(Math.abs(g.fbA_home - 50) <= INSIGHT.COIN_FLIP_WITHIN && Math.abs(g.mktB_home - 50) <= INSIGHT.COIN_FLIP_WITHIN){
      out.push({kind: 'flip', g,
        text: `Both models put it between ${50 - INSIGHT.COIN_FLIP_WITHIN}% and ${50 + INSIGHT.COIN_FLIP_WITHIN}%.`});
    }
  }
  return out;
}
const INSIGHT_LABEL = {market: 'vs market', flip: 'coin flip'};
function renderBoardInsights(gamesList){
  const box = document.getElementById('board-insights');
  const list = document.getElementById('board-insights-list');
  if(!box || !list) return;
  const items = boardInsights(gamesList);
  box.hidden = !items.length;
  list.innerHTML = items.map(i => `<li><span class="insight-chip insight-${i.kind}">${INSIGHT_LABEL[i.kind]}</span>`
    + `<span><b>${escapeHtml(i.g.away)} at ${escapeHtml(i.g.home)}</b>: ${escapeHtml(i.text)}</span></li>`).join('');
}
/* ---------- Favourite teams (Stage 80 item 53, the 2026-10-13 audit's F7) ----------
   The same functions as src/core/favs.js, which the NHL's and NBA's pages
   include; tests/test_favourite_teams.py holds the two copies equal. */
const FAV_KEY = 'site:favs';
const FAV_STAR = '<svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true"><path d="M12 3.5l2.6 5.3 5.9.9-4.3 4.1 1 5.8-5.2-2.7-5.2 2.7 1-5.8-4.3-4.1 5.9-.9z"/></svg>';
function favsAll(){
  try{ const all = JSON.parse(localStorage.getItem(FAV_KEY) || '{}'); return all && typeof all === 'object' ? all : {}; }
  catch(e){ return {}; }
}
function favs(sport){ const list = favsAll()[sport]; return Array.isArray(list) ? list : []; }
function isFav(sport, team){ return favs(sport).includes(team); }
function toggleFav(sport, team){
  const all = favsAll(), list = favs(sport);
  all[sport] = list.includes(team) ? list.filter(t => t !== team) : list.concat(team);
  try{ localStorage.setItem(FAV_KEY, JSON.stringify(all)); }catch(e){}
  return all[sport].includes(team);
}
function favLabel(on, name){ return on ? `Remove ${name} from your teams` : `Add ${name} to your teams`; }
function favStar(sport, team, name){
  const on = isFav(sport, team);
  return `<button type="button" class="fav-star" data-fav-sport="${sport}" data-fav-team="${team}" data-fav-name="${name}"`
    + ` aria-pressed="${on}" aria-label="${favLabel(on, name)}">${FAV_STAR}</button>`;
}
/* Games with a favourite team first, each group in its own order. */
function favFirst(sport, games){
  const list = favs(sport);
  if(!list.length) return games;
  const mine = g => list.includes(g.home) || list.includes(g.away);
  return games.filter(mine).concat(games.filter(g => !mine(g)));
}
/* One listener for every star on the page; `redraw` puts the starred games
   back on top. */
function installFavStars(redraw){
  document.addEventListener('click', e => {
    const b = e.target.closest('.fav-star');
    if(!b) return;
    e.preventDefault();
    e.stopPropagation();
    const on = toggleFav(b.dataset.favSport, b.dataset.favTeam);
    document.querySelectorAll('.fav-star').forEach(x => {
      if(x.dataset.favSport !== b.dataset.favSport || x.dataset.favTeam !== b.dataset.favTeam) return;
      x.setAttribute('aria-pressed', String(on));
      x.setAttribute('aria-label', favLabel(on, x.dataset.favName));
    });
    if(!redraw) return;
    redraw();
    // The star was drawn again, perhaps higher up with its game: focus follows it.
    const again = document.querySelector(`.page.active .fav-star[data-fav-sport="${b.dataset.favSport}"][data-fav-team="${b.dataset.favTeam}"]`);
    if(again && !b.isConnected) again.focus();
  });
}

/* The visitor's time-zone setting (Stage 80 item 57): src/core/prefs.js's functions, word for word. */
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

/* ---------- Compare mode (Stage 80 item 55, the 2026-10-13 audit's F9) ----------
   "Cards | Table" beside the sort: the week as one table, a game a row, with
   each model's side and chance, the market's and the result, so the three
   can be read down a column. Mark chose the table at 641 px and wider only
   (2026-10-14); a phone keeps its rows, which open to the same card. The
   table follows the board's filter and sort until a column is chosen; then
   that column sorts it, strongest first, and again turns it round. The
   choice of view is kept in this browser. */
const VIEW_KEY = 'nfl:boardView';
const TABLE_MIN = '(min-width: 641px)';
let boardView = 'cards';
try{ if(localStorage.getItem(VIEW_KEY) === 'table') boardView = 'table'; }catch(e){}
let compareSort = {key: null, dir: -1};
function tableView(){ return boardView === 'table' && window.matchMedia(TABLE_MIN).matches; }
const COMPARE_COLS = [['kickoff', 'Kickoff', ''], ['game', 'Game', ''], ['a', 'Model A', 'num'],
                      ['b', 'Model B', 'num'], ['market', 'Market', 'num'], ['result', 'Result', '']];
const COMPARE_PROB = {a: 'fbA_home', b: 'mktB_home', market: 'mkt_home'};
function compareKick(g){
  if(!g.gametime_et) return escapeHtml((g.weekday || '').slice(0, 3));
  const day = startZone() ? (g.weekday || '').slice(0, 3) : kickoffLocalDay(g);
  return `${escapeHtml(day)} ${kickoffClock(g)}`;
}
function compareValue(g, key){
  if(key === 'kickoff') return (g.gameday || '') + (g.gametime_et || '');
  if(key === 'game') return `${g.away} ${g.home}`;
  if(key === 'result'){
    if(!g.graded) return 0;
    const v = g.model_b_correct ?? g.model_a_correct;
    return g.result === 'tie' || v === null || v === undefined ? 1 : v ? 3 : 2;
  }
  const s = cardSide(g[COMPARE_PROB[key]], g);
  return s ? s.pct : -1;
}
/* Kickoff and game read first to last; a chance or a result strongest first. */
function compareRows(games, sort){
  if(!sort.key) return games;
  const up = sort.key === 'kickoff' || sort.key === 'game';
  const dir = (up ? 1 : -1) * (sort.dir === -1 ? 1 : -1);
  return games.map((g, i) => [g, i]).sort(([a, i], [b, j]) => {
    const x = compareValue(a, sort.key), y = compareValue(b, sort.key);
    return x < y ? -dir : x > y ? dir : i - j;
  }).map(([g]) => g);
}
function compareSortState(key, sort, boardSort){
  if(sort.key === key){
    const up = key === 'kickoff' || key === 'game';
    return (sort.dir === -1) === up ? 'ascending' : 'descending';
  }
  return !sort.key && key === 'kickoff' && boardSort === 'chronological' ? 'ascending' : 'none';
}
function compareTableHtml(games, sort, boardSort, weekLabel){
  const cell = (g, key) => { const s = cardSide(g[COMPARE_PROB[key]], g); return s ? cardSideText(s) : '—'; };
  const rows = compareRows(games, sort).map(g => `<tr><td>${compareKick(g)}</td>`
    + `<td><b>${escapeHtml(g.away)} @ ${escapeHtml(g.home)}</b></td>`
    + `<td class="num">${cell(g, 'a')}</td><td class="num">${cell(g, 'b')}</td><td class="num">${cell(g, 'market')}</td>`
    + `<td>${gradedTagHtml(g) || '—'}</td></tr>`).join('');
  return `<div class="table-wrap"><table class="metrics-table compare-table"><caption class="visually-hidden">${escapeHtml(weekLabel)}: every game, each model's side and chance, the market's and the result</caption>
    <thead><tr>${COMPARE_COLS.map(([key, label, cls]) => `<th scope="col"${cls ? ` class="${cls}"` : ''} aria-sort="${compareSortState(key, sort, boardSort)}"><button type="button" class="cmp-sort" data-cmp="${key}">${label}</button></th>`).join('')}</tr></thead>
    <tbody>${rows}</tbody></table></div>`;
}
function installCompare(){
  const seg = document.getElementById('view-seg');
  if(!seg) return;
  const mark = () => seg.querySelectorAll('[data-view]').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.view === boardView)));
  mark();
  seg.addEventListener('click', e => {
    const b = e.target.closest('[data-view]');
    if(!b || b.dataset.view === boardView) return;
    boardView = b.dataset.view;
    try{ localStorage.setItem(VIEW_KEY, boardView); }catch(e2){}
    mark();
    renderGames();
  });
  document.getElementById('game-grid').addEventListener('click', e => {
    const b = e.target.closest('.cmp-sort');
    if(!b) return;
    const key = b.dataset.cmp;
    compareSort = compareSort.key === key ? {key, dir: -compareSort.dir} : {key, dir: -1};
    renderGames();
    const again = document.querySelector(`#game-grid .cmp-sort[data-cmp="${key}"]`);
    if(again) again.focus();
  });
  // Across 641 px the board changes view, so it is drawn again.
  const mq = window.matchMedia(TABLE_MIN);
  if(mq.addEventListener) mq.addEventListener('change', () => { if(boardView === 'table') renderGames(); });
}

function renderGames(){
  const grid = document.getElementById('game-grid');
  grid.classList.remove('is-table');
  const badge = document.getElementById('board-badge');
  const weekData = weeks[currentBoardWeek];
  const gamesList = weekData ? weekData.games : [];
  // The badge now speaks only when there is nothing to count. "16 games" above
  // sixteen visible cards told the reader what they could already see; "No
  // games" is the one state the grid cannot say for itself.
  badge.textContent = gamesList.length ? '' : 'No games';
  badge.hidden = gamesList.length > 0;
  renderWeekGlance(gamesList);
  renderBoardInsights(gamesList);
  renderLockProof(currentBoardWeek, weekData);
  const tvNote = document.getElementById('board-tv-note');
  if(tvNote) tvNote.hidden = true;
  // Tuesday's picks for a week Thursday has not locked yet. Said above the
  // cards, not only in the week label, because it changes how every number
  // below it reads: these can move, and none of them is ever graded.
  const previewNote = document.getElementById('board-preview-note');
  if(previewNote){
    const isPreview = !!(weekData && weekData.preview);
    previewNote.hidden = !isPreview;
    previewNote.textContent = previewNoteText(weekData, Date.now());
  }

  const pdfLink = document.getElementById('picks-pdf-link');
  if(pdfLink){
    const hasPdf = picksPdfs.indexOf(currentBoardWeek) !== -1;
    pdfLink.hidden = !hasPdf;
    const pdfNone = document.getElementById('picks-pdf-none');
    if(pdfNone){
      pdfNone.hidden = hasPdf;
      pdfNone.textContent = hasPdf ? '' : pdfNoneText(weekData);
    }
    if(hasPdf){
      pdfLink.href = 'dist/picks_' + currentBoardWeek + '.pdf';
      pdfLink.setAttribute('aria-label', 'Download printable PDF of picks for ' + currentBoardWeek.replace('_week', ' week '));
    }
  }

  if(!weekData || gamesList.length === 0){
    grid.innerHTML = stateHtml('waiting', 'No picks for this week yet',
      'The model saves its picks for a week before that week&#39;s first kickoff. They appear here as soon as they are saved.');
    return;
  }

  const filtered = gamesList.filter(g=>{
    if(currentFilter==='all') return true;
    if(currentFilter==='flagged') return !!g.flag;
    // The badge's own test, so the filter shows exactly the cards that say
    // "Models split" (see modelsSplit).
    if(currentFilter==='divergent') return modelsSplit(g);
    return true;
  });

  if(filtered.length === 0){
    grid.innerHTML = stateHtml('filtered', 'No games match this filter',
      'Every game this week is still here; this filter just hides all of them.',
      {label: 'Show all games', act: 'show-all-games'});
    return;
  }

  // Stage 80 item 53: a favourite team's games first, then the rest in this order.
  const sorted = favFirst('nfl', [...filtered].sort((a,b)=>{
    if(currentSort === 'chronological') return byKickoff(a,b);
    if(currentSort === 'confidence'){
      // lower confidence_rank = more confident; nulls (ungraded/old-format) sink to the bottom
      const ra = a.confidence_rank ?? 999, rb = b.confidence_rank ?? 999;
      return ra - rb;
    }
    if(currentSort === 'confidence_asc'){
      const ra = a.confidence_rank ?? -1, rb = b.confidence_rank ?? -1;
      return rb - ra;  // highest rank number = least confident = closest game, shown first
    }
    if(currentSort === 'disagreement'){
      const da = Math.abs(a.fbA_home - a.mktB_home), db = Math.abs(b.fbA_home - b.mktB_home);
      return db - da;
    }
    if(currentSort === 'spread'){
      const sa = a.spread === null || a.spread === undefined ? -1 : Math.abs(a.spread);
      const sb = b.spread === null || b.spread === undefined ? -1 : Math.abs(b.spread);
      return sb - sa;
    }
    if(currentSort === 'alpha'){
      return a.home.localeCompare(b.home);
    }
    return 0;
  }));

  if(tvNote) tvNote.hidden = !boardTvNote(sorted);
  // Stage 80 item 55: the week as one table, at 641 px and wider.
  if(tableView()){
    grid.classList.add('is-table');
    grid.innerHTML = compareTableHtml(sorted, compareSort, currentSort, weekLabel(currentBoardWeek));
    return;
  }
  const news = weekData.news;

  const cards = sorted.map(g=>{
    // Within EVEN_BAND points of 50 the model has not picked anybody, and
    // bolding one side of a 50.4/49.6 split states a confidence it does not have.
    const EVEN_BAND = 2;
    const leanOf = p => Math.abs(p - 50) < EVEN_BAND ? 'even' : (p >= 50 ? 'home' : 'away');
    const aLean = leanOf(g.fbA_home), bLean = leanOf(g.mktB_home);
    // A game neither model will call. Distinct from "models agree", which on a
    // 50/50 game would claim consensus where there is only shared uncertainty.
    const tossUp = aLean === 'even' && bLean === 'even';
    const aHomeWin = aLean === 'home', aAwayWin = aLean === 'away';
    const bHomeWin = bLean === 'home', bAwayWin = bLean === 'away';
    const idSafe = (g.home+g.away).replace(/[^a-zA-Z]/g,'');
    const [awayC, homeC] = matchupColors(g.away, g.home);
    const spreadText = (g.spread===null || g.spread===undefined) ? "No line available"
      : g.spread === 0 ? "PK"
      : (g.spread>0 ? `${g.home} -${g.spread}` : `${g.away} -${Math.abs(g.spread)}`);
    const gradedTag = gradedTagHtml(g);
    // RETIRED in Stage 11: an "Illustrative margin" row ("KC by ~10.1")
    // used to sit in the panel below, a point margin back-solved from the
    // win probability. Margin modelling was tested as a predictor and
    // REJECTED (Model Lab), so the page was showing a number of the kind the
    // project had decided not to trust, and at card size its "~" read as a
    // minus. The Vegas line above is the real point margin on the card.
    // tests/test_no_illustrative_margin.py keeps it from coming back.

    // The sentence sits on the card, not behind the toggle. A reason nobody
    // expands is a reason nobody reads, and "why is this team favoured" was
    // the whole point of the item -- the numbers stay behind the toggle for
    // anyone who wants to check the sentence against them.
    const whyHtml = g.why ? `
      ${whyLabelled(g)}
      ${whyMarketSentence(g)}
      <button class="btn btn-link why-toggle" data-why="${idSafe}" aria-expanded="false" aria-controls="why-${idSafe}">+ the numbers behind this</button>
      <div class="why-panel" id="why-${idSafe}">
        <p class="why-unit">Points of win chance each part gave a team in Model A's pick.</p>
        ${whyRow('Offense edge', g.why.off_matchup, whyChance(g.why.off_matchup, g.fbA_home, g.home, g.away))}
        ${whyRow('Defense edge', g.why.def_matchup, whyChance(g.why.def_matchup, g.fbA_home, g.home, g.away))}
        ${whyRow('QB edge', g.why.qb_matchup, whyChance(g.why.qb_matchup, g.fbA_home, g.home, g.away))}
        ${(g.why.ol_continuity !== undefined) ? whyRow('O-line continuity', g.why.ol_continuity, whyChance(g.why.ol_continuity, g.fbA_home, g.home, g.away)) : ''}
        ${trackRecordHtml(g.mktB_home, 'panel')}
      </div>` : '';
    const kickoff = kickoffLabel(g);
    const tvPill = cardTvPill(g);
    const statusLine = cardStatusLine(g);
    const siteLine = cardSiteLine(g);
    const qbLine = cardQbLine(g), newsLine = cardNewsLine(g, news);
    return `<div class="game-card ${g.flag?'has-flag':''}"${scoreMark(g)} data-share="${shareAttr(g, awayC, homeC)}"${watermark(g)}>
      ${matchupHeader(g)}
      ${kickoff || tvPill ? `<div class="card-kickoff">${kickoff}${tvPill}</div>` : ''}
      ${statusLine ? `<div class="card-status score-off">${statusLine}</div>` : ''}
      <div class="card-status score-on" data-score-slot="line"></div>
      ${siteLine ? `<div class="card-site">${siteLine}</div>` : ''}
      <div class="game-top">
        <div class="tag-row" style="display:flex; gap:var(--s2); align-items:center;">
          ${gradedTag}
          ${/* The badge says WHETHER the models disagree, not by how much. It
                read `gap 59pt` -- a number nobody has a scale for, and the
                A-vs-market gap the owner named as unnecessary on the card
                twice. Three states, matching the component study: a near-even
                call is worth flagging on its own, because "the models agree"
                on a 50/50 game means they agree they do not know. */''}
          <span class="conf-tag ${tossUp ? 'tag-neutral' : ''}">${
            tossUp ? 'Toss-up' : (modelsSplit(g) ? 'Models split' : 'Models agree')}</span>
        </div>
      </div>
      ${cardProbHtml(g, awayC, homeC)}
      <div class="market-ref">Vegas line: <b>${spreadText}</b></div>
      ${qbLine ? `<div class="card-qbs">${qbLine}</div>` : ''}
      ${newsLine ? `<div class="card-news">${newsLine}</div>` : ''}
      ${trackRecordHtml(g.mktB_home, 'card')}
      ${whyHtml}
      ${(g.notes && g.notes.length) ? `<button class="btn btn-link toggle-flag" data-idx="${idSafe}" aria-expanded="false" aria-controls="flag-${idSafe}">+ view context (${g.notes.length})</button>
      <div class="flag-note" id="flag-${idSafe}">
        <b>Context:</b>
        <ul style="margin:var(--s2) 0 0 var(--s5); padding:0;">
          ${contextNotesHtml(g.notes)}
        </ul>
      </div>` : ''}
      <button type="button" class="btn btn-link share-btn" data-share-card>Share image</button>
    </div>`;
  });
  const mine = favs('nfl'), pinned = sorted.filter(g => mine.includes(g.home) || mine.includes(g.away)).length;
  grid.innerHTML = cards.map((card, i) => slotHeadBefore(sorted, i, pinned) + phoneRowHtml(sorted[i], i) + card).join('');
  if(sorted.some(g => g.flag)) grid.insertAdjacentHTML('afterbegin', FLAG_LEGEND);
  showFilteredNote(grid);
  // Stage 68 item 36 (N2): each card follows its phone row, which opens it.
  grid.querySelectorAll(':scope > .game-card').forEach((card, i) => {
    card.id = `card-${i}`; card.classList.add('nfl-collapsible');
    card.dataset.game = gameKey(currentBoardWeek, sorted[i]);  // Stage 76 item 9: #game/<key>
  });
  grid.querySelectorAll('.nfl-row').forEach(btn => btn.addEventListener('click', () => {
    const open = btn.getAttribute('aria-expanded') !== 'true';
    btn.setAttribute('aria-expanded', String(open));
    const card = document.getElementById(btn.getAttribute('aria-controls'));
    card.classList.toggle('is-open', open);
    if(open) revealOpened(card);
  }));

  document.querySelectorAll('.toggle-flag').forEach(btn=>{
    const originalLabel = btn.textContent;
    btn.addEventListener('click', ()=>{
      const note = document.getElementById('flag-'+btn.dataset.idx);
      // aria-expanded follows the panel, as .dive-game-head's does (Stage 26):
      // the + / − in the label is not announced as a state.
      btn.setAttribute('aria-expanded', note.classList.toggle('open') ? 'true' : 'false');
      btn.textContent = note.classList.contains('open')
        ? originalLabel.replace('+ view', '− hide')
        : originalLabel;
    });
  });
  document.querySelectorAll('.why-toggle').forEach(btn=>{
    btn.addEventListener('click', ()=>{
      const panel = document.getElementById('why-'+btn.dataset.why);
      btn.setAttribute('aria-expanded', panel.classList.toggle('open') ? 'true' : 'false');
      btn.textContent = panel.classList.contains('open') ? '− hide the numbers' : '+ the numbers behind this';
    });
  });
}

/* ---------- A start in the visitor's own time zone (Stage 80 item 57) ----------
   The only place an Eastern start becomes an instant. It sits here, outside
   the kickoff-order block above, which must never build a Date (the order
   and the Eastern labels stay string work, tests/test_kickoff_order.py).

   A start given as an Eastern date and clock ("2026-10-15", "20:15") as an
   instant, so it can be printed in the visitor's own time zone (Stage 80
   item 57). Eastern's offset is read from the browser's time-zone data, so
   daylight saving is right on either side of its change. */
const ET_PARTS = new Intl.DateTimeFormat('en-US', {timeZone: 'America/New_York', hourCycle: 'h23', year: 'numeric',
  month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit'});
function etInstant(day, hhmm){
  const [y, m, d] = day.split('-').map(Number), [h, mi] = hhmm.split(':').map(Number);
  const want = Date.UTC(y, m - 1, d, h, mi);
  let t = want + 5 * 3600 * 1000;
  for(let i = 0; i < 2; i++){
    const p = Object.fromEntries(ET_PARTS.formatToParts(new Date(t)).map(x => [x.type, x.value]));
    t += want - Date.UTC(Number(p.year), Number(p.month) - 1, Number(p.day), Number(p.hour) % 24, Number(p.minute));
  }
  return t;
}
/* A start's clock, "8:15 PM": Eastern as the data has it, or the visitor's own. */
function kickoffClock(g){
  if(startZone()){
    const [h, m] = g.gametime_et.split(':').map(Number);
    return `${h % 12 === 0 ? 12 : h % 12}:${String(m).padStart(2, '0')} ${h >= 12 ? 'PM' : 'AM'}`;
  }
  return new Date(etInstant(g.gameday, g.gametime_et)).toLocaleTimeString('en-US', {hour: 'numeric', minute: '2-digit'});
}
/* Stage 80 item 61 (F15): a game not yet final or graded is marked for
   src/core/scores.js, which the build puts on the page and which fills the
   empty slots with ESPN's score while the game is on. Here, after the
   kickoff-order block, because it builds a Date. */
function scoreMark(g){
  if(!g.gameday || !g.gametime_et || g.graded || g.status === 'final' || g.status === 'cancelled') return '';
  const start = new Date(etInstant(g.gameday, g.gametime_et)).toISOString();
  return ` data-score-sport="nfl" data-score-key="${escapeHtml(g.away)}@${escapeHtml(g.home)}" data-score-start="${start}"`;
}
function scoreSlot(name){ return `<span class="score-on" data-score-slot="${name}"></span>`; }
/* The label and the short day of a start, in the visitor's own zone. */
function kickoffLocalLabel(g){
  const at = new Date(etInstant(g.gameday, g.gametime_et));
  return `${at.toLocaleDateString('en-US', {weekday: 'long', month: 'short', day: 'numeric'})} · ${kickoffClock(g)}`;
}
function kickoffLocalDay(g){
  return new Date(etInstant(g.gameday, g.gametime_et)).toLocaleDateString('en-US', {weekday: 'short'});
}
/* Stage 77 item 31 (N6): on a phone the filter chips sit behind Options, so
   a filter left on hid most of the week with nothing on screen to say so.
   An active filter now says which, above the rows, with a way to clear it;
   CSS shows it only where the chips are hidden. */
function filteredNoteHtml(label){
  return `<p class="nfl-filtered-note">Filtered: ${escapeHtml(label)} &middot; <button type="button" class="btn btn-link" data-clear-filter>clear</button></p>`;
}
function showFilteredNote(grid){
  if(currentFilter === 'all') return;
  const chip = document.querySelector(`#filter-row .filter-btn[data-filter=${currentFilter}]`);
  if(!chip) return;
  grid.insertAdjacentHTML('afterbegin', filteredNoteHtml(chip.textContent.trim()));
  grid.querySelector('[data-clear-filter]').addEventListener('click', () => {
    const all = document.querySelector('#filter-row .filter-btn[data-filter=all]');
    if(all) all.click();
  });
}
/* SCOPED TO #filter-row, deliberately. `.filter-btn` is a shared pill style,
   not a Week Board filter: nine elements wear it and only three are filters.
   The other six are "Got it" on the onboarding banner and, on My Picks, "Copy
   these into my log", "Back to my picks", "Copy Share Link", "Export My Picks"
   and "Import My Picks". An unscoped querySelectorAll gave all nine this
   handler, so tapping Export My Picks stripped .active from All Games, painted
   Export in the accent, and set currentFilter to undefined -- which falls
   through the filter's final `return true`, so the board still showed every
   game with no pill marked and nothing errored. Measured in headless Chromium
   before the fix: .active went from ["All Games"] to ["Export My Picks"].
   Select the buttons that have the attribute this handler reads. */
document.querySelectorAll('#filter-row .filter-btn[data-filter]').forEach(btn=>{
  btn.addEventListener('click', ()=>{
    // .active is the look; aria-pressed is the state a screen reader hears
    // (Stage 26: every chip on the page says which one is on the same way).
    document.querySelectorAll('#filter-row .filter-btn[data-filter]').forEach(b=>{
      b.classList.toggle('active', b === btn);
      b.setAttribute('aria-pressed', b === btn ? 'true' : 'false');
    });
    currentFilter = btn.dataset.filter;
    renderGames();
  });
});
populateWeekSelect(document.getElementById('week-select'), (val)=>{
  currentBoardWeek = val;
  // The football tumbles while the week swaps. The work is synchronous, so
  // stop() is called immediately -- it waits for the current revolution to
  // finish, which is what makes a fast swap read as one deliberate turn rather
  // than a flicker. A slow machine gets more turns, not a stutter.
  brandMark.start();
  renderGames();
  syncWeekStepper('week');
  brandMark.stop();
}, latestWeekKey);
wireWeekStepper('week');
document.getElementById('sort-select').addEventListener('change', (e)=>{ currentSort = e.target.value; renderGames(); });
/* After the change listener, not before. enhanceSelect() writes back through
   dispatchEvent('change'), so wiring it first would build a control whose
   clicks reached nothing -- the written-tested-never-called shape, in the one
   ordering where it still looks correct on screen. */
enhanceSelect(document.getElementById('sort-select'));
renderGames();

/* ---------- Onboarding banner (first-visit only) ---------- */
const ONBOARDING_KEY = 'nfl_pickem_onboarding_dismissed';

/* ---------- Theme toggle ---------- */
// Stage 62 item 1: one key for the whole site (src/core/isolation.py's
// SHARED_STORAGE_KEYS). The first-paint script in page.html still reads the
// old 'nfl_pickem_theme' when the new key is empty, so a returning visitor
// keeps the choice they made before.
const THEME_KEY = 'site:theme';
function currentTheme(){
  return document.documentElement.getAttribute('data-theme') === 'light' ? 'light' : 'dark';
}
function updateThemeLabel(){
  const label = document.getElementById('theme-toggle-label');
  if(label) label.textContent = currentTheme() === 'light' ? 'Dark mode' : 'Light mode';
}
/* Stage 47 item 11: paper is white, so a page in the dark theme prints in
   the light one, and goes back to the reader's theme afterwards. */
(function printInLight(){
  let before = null;
  window.addEventListener('beforeprint', () => {
    before = document.documentElement.getAttribute('data-theme');
    document.documentElement.setAttribute('data-theme', 'light');
  });
  window.addEventListener('afterprint', () => {
    if(before === null) document.documentElement.removeAttribute('data-theme');
    else document.documentElement.setAttribute('data-theme', before);
  });
})();
(function initTheme(){
  updateThemeLabel();
  // The sidebar's button, and the top bar's below 1080px (Stage 26 item 3).
  document.querySelectorAll('#theme-toggle, .topbar-theme').forEach(btn => btn.addEventListener('click', ()=>{
    const next = currentTheme() === 'light' ? 'dark' : 'light';
    if(next === 'light'){
      document.documentElement.setAttribute('data-theme','light');
    } else {
      document.documentElement.removeAttribute('data-theme');
    }
    try{ localStorage.setItem(THEME_KEY, next); }catch(e){}
    updateThemeLabel();
  }));
})();
// The top bar's height, for the sticky table headers that stick below it
// under 1080px (Stage 30 item 2). Measured, not assumed: the bar grows with
// the safe area and when its title wraps. 0 when the bar is not shown.
// offsetHeight is the BORDER box, so the observer watches the border box:
// the default content box does not fire when only the padding changes, and
// the safe area reaches the bar as padding (--safe-top). Stage 35.
(function initTopbarHeight(){
  const bar = document.querySelector('.topbar');
  if(!bar) return;
  const write = () => document.documentElement.style.setProperty('--topbar-h', bar.offsetHeight + 'px');
  write();
  if(typeof ResizeObserver === 'function') new ResizeObserver(write).observe(bar, {box: 'border-box'});
  window.addEventListener('resize', write);
})();
function dismissOnboarding(){
  try{ localStorage.setItem(ONBOARDING_KEY, '1'); }catch(e){}
  const el = document.getElementById('onboarding-banner');
  if(el) el.style.display = 'none';
}
/* Stage 77 item 27 (N2): a week without a printable PDF says why, where the
   link would be. A PDF is made for each saved week, so a preview week has
   none until its picks lock. */
function pdfNoneText(weekData){
  return weekData && weekData.preview
    ? 'The printable PDF comes when these picks lock.'
    : 'No printable PDF for this week.';
}
/* N1's two buttons, shown on a phone only: Options holds the sort, the PDF
   and the filters; the provenance line and the regional-TV note sit behind
   one tap. */
(function phoneBoardButtons(){
  const page = document.getElementById('page-board');
  [['board-options-btn', 'nfl-options-open'], ['board-prov-btn', 'nfl-prov-open']].forEach(([id, cls]) => {
    const btn = document.getElementById(id);
    if(!btn || !page) return;
    btn.addEventListener('click', () => {
      const open = !page.classList.contains(cls);
      page.classList.toggle(cls, open);
      btn.setAttribute('aria-expanded', String(open));
    });
  });
})();
/* Stage 77 item 29 (N4): on a phone the banner shows one line, and its
   "How to read a card" opens the banner's own three points and "How to
   read this" in place, where the cards are. It used to go to Methodology,
   which has no section on reading a card. */
(function phoneOnboardingGuide(){
  const btn = document.getElementById('onboarding-phone-more');
  const banner = document.getElementById('onboarding-banner');
  if(!btn || !banner) return;
  btn.addEventListener('click', () => {
    const open = !banner.classList.contains('onboarding-open');
    banner.classList.toggle('onboarding-open', open);
    btn.setAttribute('aria-expanded', String(open));
  });
})();
(function initOnboarding(){
  let dismissed = false;
  try{ dismissed = localStorage.getItem(ONBOARDING_KEY) === '1'; }catch(e){}
  const el = document.getElementById('onboarding-banner');
  if(el && !dismissed) el.style.display = 'block';
})();

/* ---------- The first-visit tour (Stage 80 item 58, the 2026-10-13 audit's F12) ----------
   Three steps on the Week Board, each a spotlight on one part of it with a
   line on how to read it: the week stepper, a game, and its result. Mark
   chose it as mocked (2026-10-14), for new visitors only: it runs on a first
   visit and never again in that browser (site:tour), and a browser that has
   been here before, which has left one of the site's keys, never sees it.
   Skip, Esc or Done ends it; the Settings sheet's "Show them again" asks for
   it once more. */
const TOUR_KEY = 'site:tour';
const TOUR_STEPS = [
  {target: ['#week-step'], title: 'Step through the weeks',
   text: 'The arrows, or [ and ], move a week at a time. Each week is saved before its first kickoff.'},
  {target: ['.game-row.nfl-row', '.game-card'], title: 'Every game, both models',
   text: 'Model A reads football data only; Model B adds the Vegas spread. The bar shows how sure each is.'},
  {target: ['.nfl-row-res.correct, .nfl-row-res.incorrect', '.graded-tag', '.card-hl'], title: 'Graded after the game',
   text: 'Green if Model B picked the winner, red if not. Nothing is changed once the game starts.'},
];
/* Whether this browser should be shown the tour: asked for it again, or new
   here (none of the site's keys: a theme, favourites, picks, a dismissed
   banner, a last visit). */
function tourWanted(store){
  try{
    const asked = store.getItem(TOUR_KEY);
    if(asked) return asked === 'show';
    for(let i = 0; i < store.length; i++){
      const k = store.key(i) || '';
      if(/^(site:|nfl[_:]|nhl:|nba:)/.test(k)) return false;
    }
    return true;
  }catch(e){ return false; }
}
/* The first of a step's targets that is on the page and drawn (a closed
   row's card is not), so a phone's step is its rows' and a wide screen's its cards'. */
function tourTarget(step, root){
  for(const sel of step.target){
    const el = [...root.querySelectorAll(sel)].find(x => x.getBoundingClientRect().width > 0 && !x.closest('[hidden]'));
    if(el) return el;
  }
  return null;
}
function startTour(){
  const page = document.getElementById('page-board');
  if(!page || !page.classList.contains('active') || !tourWanted(localStorage)) return;
  // A visit that arrives at one game (a shared #game/ link) is shown that
  // game, not walked away from it: the browser checks' game route caught it.
  if(location.hash && !/^#board(\/|$)/.test(location.hash)) return;
  const ring = document.createElement('div'), pop = document.createElement('div');
  ring.className = 'tour-ring';
  pop.className = 'tour-pop';
  pop.setAttribute('role', 'dialog');
  pop.setAttribute('aria-labelledby', 'tour-title');
  pop.setAttribute('aria-describedby', 'tour-text');
  let at = -1, target = null;
  const back = document.activeElement;
  // Leaving the Week Board ends the tour: its steps are the board's.
  const leave = new MutationObserver(() => { if(!page.classList.contains('active')) end(); });
  function end(){
    try{ localStorage.setItem(TOUR_KEY, 'done'); }catch(e){}
    leave.disconnect();
    ring.remove(); pop.remove();
    window.removeEventListener('resize', place);
    document.removeEventListener('keydown', onKey, true);
    if(back && back.focus) back.focus();
  }
  function place(){
    if(!target) return;
    const r = target.getBoundingClientRect(), pad = 6;
    Object.assign(ring.style, {top: `${r.top + window.scrollY - pad}px`, left: `${r.left + window.scrollX - pad}px`,
                               width: `${r.width + 2 * pad}px`, height: `${r.height + 2 * pad}px`});
    const w = Math.min(320, document.documentElement.clientWidth - 32);
    const left = Math.max(16, Math.min(r.left + window.scrollX, document.documentElement.clientWidth - w - 16));
    const below = r.bottom + 12 + pop.offsetHeight < window.innerHeight;
    Object.assign(pop.style, {width: `${w}px`, left: `${left}px`,
      top: `${(below ? r.bottom + 12 : Math.max(8, r.top - 12 - pop.offsetHeight)) + window.scrollY}px`});
  }
  function show(i){
    const found = TOUR_STEPS.slice(i).map(s => tourTarget(s, page));
    const skip = found.findIndex(Boolean);
    if(skip < 0){ end(); return; }
    at = i + skip;
    target = found[skip];
    const last = at === TOUR_STEPS.length - 1;
    const step = TOUR_STEPS[at];
    pop.innerHTML = `<p class="tour-count">${at + 1} of ${TOUR_STEPS.length}</p><h2 id="tour-title">${step.title}</h2>`
      + `<p id="tour-text">${step.text}</p><div class="tour-actions"><button type="button" class="btn btn-link" data-tour-skip>Skip the tour</button>`
      + `<button type="button" class="btn" data-tour-next>${last ? 'Done' : 'Next'}</button></div>`;
    target.scrollIntoView({block: 'center'});
    place();
    pop.querySelector('[data-tour-next]').focus();
  }
  function onKey(e){
    if(e.key === 'Escape'){ e.preventDefault(); e.stopPropagation(); end(); }
  }
  pop.addEventListener('click', e => {
    if(e.target.closest('[data-tour-skip]')) end();
    else if(e.target.closest('[data-tour-next]')) at === TOUR_STEPS.length - 1 ? end() : show(at + 1);
  });
  document.body.append(ring, pop);
  leave.observe(page, {attributes: true, attributeFilter: ['class']});
  window.addEventListener('resize', place);
  document.addEventListener('keydown', onKey, true);
  show(0);
}
// Once the page has settled on the page its address names: the tour is the Week Board's.
window.addEventListener('load', () => setTimeout(startTour, 300));

/* Where the orientation banner sits (Stage 13). On a phone it goes in among
   the cards, after the first ORIENTATION_AFTER of them, so the first screen
   shows games rather than instructions (before this, at 390x844 the banner
   was 610px tall and the first card started at 914px, below the fold).
   Wider than that it stays in its markup home, above the week summary, where
   the cards beside it are already on screen.

   renderGames() rewrites #game-grid with innerHTML, which would drop the
   banner if it were inside, so the node is held here, not looked up, and
   every rewrite of the grid re-places it. The observer only moves it when
   it is somewhere else, so its own move cannot set it off again. */
const ORIENTATION_AFTER = 2;
const ORIENTATION_PHONE = '(max-width:640px)';
function orientationSlot(cardCount, isPhone){
  return isPhone && cardCount >= ORIENTATION_AFTER ? ORIENTATION_AFTER : null;
}
(function placeOrientationWiring(){
  const banner = document.getElementById('onboarding-banner');
  const grid = document.getElementById('game-grid');
  const home = document.getElementById('week-glance');
  if(!banner || !grid || !home || !window.matchMedia) return;
  const phone = window.matchMedia(ORIENTATION_PHONE);
  function placeOrientation(){
    const cards = [...grid.children].filter(c => c.classList.contains('game-card'));
    const slot = orientationSlot(cards.length, phone.matches);
    if(slot === null){
      if(banner.nextElementSibling !== home) home.parentNode.insertBefore(banner, home);
      return;
    }
    const after = cards[slot - 1];
    if(after.nextElementSibling !== banner) after.after(banner);
  }
  new MutationObserver(placeOrientation).observe(grid, {childList:true});
  if(phone.addEventListener) phone.addEventListener('change', placeOrientation);
  placeOrientation();
})();

/* ---------- Picks lock at kickoff (Stage 11) ----------
   Before this, a pick could be made after the result was known and the
   Season Accuracy race counted it: writing every graded winner into storage
   put "My picks 100.0%, 32 of 32" on the page (measured 2026-09-26). On a
   dashboard whose whole claim is that its numbers are true, that was the one
   number a visitor could make false by clicking.

   Three rules, all here as plain functions so the suite can execute them:
     1. A game's buttons lock at its kickoff, or once it is graded.
     2. Every pick is stored with the time it was made (PICK_TIMES_KEY).
     3. A graded pick is COUNTED only if its time is before kickoff. A pick
        with no time -- everything saved before this existed, and anything
        arriving through a share link, which carries no times -- is kept and
        shown, but not counted, and the page says how many it left out.

   This is honesty on a static site, not security: the times live in the
   visitor's own browser and a determined person can edit them. What it
   removes is the accidental and the casual case, and the page no longer
   counts a pick it knows was made late.

   The kickoff is an INSTANT here, unlike kickoffKey above, because it is
   compared with the visitor's clock. It is built with Date.UTC from the
   Eastern wall-clock fields plus the US daylight-saving rule, never with
   `new Date("2026-09-13T13:00")`, which would read an Eastern time in the
   visitor's zone and lock a Los Angeles visitor three hours late. */
function easternOffsetHours(y, m, d, hh){
  // US rule since 2007: daylight time (UTC-4) from 02:00 on the second
  // Sunday of March to 02:00 on the first Sunday of November, else UTC-5.
  const firstSunday = mon => 1 + (7 - new Date(Date.UTC(y, mon - 1, 1)).getUTCDay()) % 7;
  const key = m * 10000 + d * 100 + hh;
  const start = 3 * 10000 + (firstSunday(3) + 7) * 100 + 2;
  const end = 11 * 10000 + firstSunday(11) * 100 + 2;
  return (key >= start && key < end) ? 4 : 5;
}

function kickoffInstant(g){
  // null means "kickoff unknown", which never locks on time alone. A day
  // with no time locks from the start of that day: early rather than late.
  if(!g || !g.gameday) return null;
  const p = g.gameday.split('-').map(Number);
  const t = (g.gametime_et || '00:00').split(':').map(Number);
  if(p.length !== 3 || p.some(isNaN) || t.some(isNaN)) return null;
  const off = easternOffsetHours(p[0], p[1], p[2], t[0]);
  return Date.UTC(p[0], p[1] - 1, p[2], t[0] + off, t[1] || 0);
}

function isPickLocked(g, nowMs){
  if(g && g.graded) return true;
  const k = kickoffInstant(g);
  return k !== null && nowMs >= k;
}

// 'counted', 'late' (made at or after kickoff) or 'untimed' (no time, or a
// game whose kickoff is unknown, so the time cannot be checked against it).
function pickVerdict(pickedAt, g){
  const t = pickedAt ? Date.parse(pickedAt) : NaN;
  const k = kickoffInstant(g);
  if(isNaN(t) || k === null) return 'untimed';
  return t < k ? 'counted' : 'late';
}

// The one tally behind every record on the page: the My Picks badge, the
// streak strip, the trend line and the scoreboard race. Four hand-written
// loops did this before, which is four places to forget the lock.
function tallyMyPicks(picks, times, keys, weekMap){
  const r = {wins: 0, losses: 0, late: 0, untimed: 0};
  keys.forEach(k => {
    ((weekMap[k] && weekMap[k].games) || []).forEach(g => {
      const pid = k + '|' + g.home + '|' + g.away;
      const pick = picks[pid];
      if(!pick || !g.graded || g.actual_home_win === null || g.actual_home_win === undefined) return;
      const v = pickVerdict(times[pid], g);
      if(v !== 'counted'){ r[v]++; return; }
      if(pick === (g.actual_home_win ? g.home : g.away)) r.wins++; else r.losses++;
    });
  });
  return r;
}

// Picks are kept in this browser only (a static site has no accounts), so a
// visitor on a new device sees none, and picks copied in from a share link
// carry no time. Said wherever the page reports picks it cannot count.
const PICKS_LIVE_HERE = 'Your picks live in this browser: Export and Import on My Picks move them to another device.';

function leftOutSentence(t){
  const n = t.late + t.untimed;
  if(!n) return '';
  const parts = [];
  if(t.late) parts.push(`${t.late} made after kickoff`);
  if(t.untimed) parts.push(`${t.untimed} with no record of when ${t.untimed === 1 ? 'it was' : 'they were'} made`);
  return `${n} of your graded picks ${n === 1 ? 'is' : 'are'} not counted: ${parts.join(', ')}.`;
}

// The My Picks record badge. Graded picks that were all late or untimed
// say "0 counted" and why, not "No graded picks yet" -- they are graded,
// and the visitor can see them (Stage 37 item 1).
function recordBadgeText(t){
  const left = t.late + t.untimed;
  if(t.wins + t.losses > 0) return `${t.wins}-${t.losses} on graded picks` + (left ? ` (${left} not counted)` : '');
  if(left) return `0 counted: ${left} graded pick${left === 1 ? '' : 's'} made after kickoff or with no time`;
  return 'No graded picks yet';
}

// A stored time means "made no later than this". A pick with no time whose
// game has NOT kicked off can be stamped with now truthfully: it is sitting
// in storage now, so it was made by now, and now is before kickoff. That is
// what keeps a pick saved before this change, or copied in from a share link
// for a game still to come, from being thrown out. A game already locked is
// never stamped -- there, now proves nothing about before kickoff.
function stampUnlockedPicks(picks, times, gameOf, nowMs){
  let stamped = 0;
  Object.keys(picks).forEach(pid => {
    if(times[pid]) return;
    const g = gameOf(pid);
    if(!g || kickoffInstant(g) === null || isPickLocked(g, nowMs)) return;
    times[pid] = new Date(nowMs).toISOString();
    stamped++;
  });
  return stamped;
}
/* ---------- end of the picks lock ---------- */

/* ---------- My Picks Log (localStorage, this device only) ---------- */
let currentPicksWeek = latestWeekKey;
const PICKS_STORAGE_KEY = 'nfl_pickem_my_picks';
const PICK_TIMES_KEY = 'nfl_pickem_pick_times';

function loadPickTimes(){
  try{ return JSON.parse(localStorage.getItem(PICK_TIMES_KEY) || '{}'); }
  catch(e){ return {}; }
}
function savePickTimes(times){
  try{ localStorage.setItem(PICK_TIMES_KEY, JSON.stringify(times)); }
  catch(e){ console.warn('Could not save pick times locally', e); }
}

// Find the game a pick id names, so a handler can ask whether it is locked.
function gameForPid(pid){
  const [k, home, away] = pid.split('|');
  return ((weeks[k] && weeks[k].games) || []).find(g => g.home === home && g.away === away) || null;
}

function loadMyPicks(){
  try{ return JSON.parse(localStorage.getItem(PICKS_STORAGE_KEY) || '{}'); }
  catch(e){ return {}; }
}
function saveMyPicks(picks){
  try{ localStorage.setItem(PICKS_STORAGE_KEY, JSON.stringify(picks)); }
  catch(e){ console.warn('Could not save picks locally', e); }
}

/* ---------- Shareable picks link ----------
   A static site with no backend, so the picks have to travel inside the URL
   itself. Three decisions worth stating:

   1. One week per link, not the whole log. A week is ~16 games; a season is
      272, and a URL carrying all of them would be long enough that mail
      clients and chat apps start wrapping and truncating it. Truncation on a
      link is the bad case, because a half-decoded pick set still looks like a
      pick set.

   2. The fragment (#), never the query string. Fragments are not sent to the
      server, so someone's picks do not end up in GitHub Pages' request logs
      just because they shared them.

   3. One character per game, positional -- which is compact but only correct
      if both ends agree on the game order. So the link carries a fingerprint
      of the exact schedule the sender saw. If the receiver's copy of that
      week differs at all, the link is REFUSED rather than decoded against the
      wrong games. Silently attaching someone's picks to the wrong fixtures is
      worse than not opening the link. */
const SHARE_VERSION = '1';

// FNV-1a. Not a security hash -- it exists to notice that two schedules
// differ, and it only has to survive being pasted through a chat window.
function scheduleFingerprint(games){
  const s = games.map(g => g.away + '@' + g.home).join(',');
  let h = 0x811c9dc5;
  for(let i = 0; i < s.length; i++){
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 0x01000193) >>> 0;
  }
  return h.toString(36);
}

function encodeSharedPicks(weekKey){
  const weekData = weeks[weekKey];
  if(!weekData || !(weekData.games||[]).length) return null;
  const myPicks = loadMyPicks();
  const games = weekData.games;

  // h = home, a = away, - = no pick. Fixed length, one char per game, in the
  // week's own order.
  let bits = '', picked = 0;
  games.forEach(g => {
    const pick = myPicks[weekKey + '|' + g.home + '|' + g.away];
    if(pick === g.home){ bits += 'h'; picked++; }
    else if(pick === g.away){ bits += 'a'; picked++; }
    else bits += '-';
  });
  if(picked === 0) return null;
  return { token: [SHARE_VERSION, weekKey, bits, scheduleFingerprint(games)].join('~'),
           picked };
}

function decodeSharedPicks(token){
  const parts = String(token).split('~');
  if(parts.length !== 4) return {error: 'That link is not in a format this page recognises.'};
  const [version, weekKey, bits, fingerprint] = parts;

  if(version !== SHARE_VERSION){
    return {error: `That link was made by a different version of this page (v${version}).`};
  }
  const weekData = weeks[weekKey];
  if(!weekData || !(weekData.games||[]).length){
    return {error: `This site has no data for ${weekKey.replace('_',' ')}, so those picks cannot be shown.`};
  }
  const games = weekData.games;
  if(bits.length !== games.length){
    return {error: `That link covers ${bits.length} games but this site has ${games.length} for that week, so the picks cannot be lined up. Nothing was imported.`};
  }
  if(fingerprint !== scheduleFingerprint(games)){
    // The dangerous case, and the reason the fingerprint exists at all.
    return {error: 'That link was made from a different version of this week\'s schedule. Lining the picks up by position would attach them to the wrong games, so nothing was imported.'};
  }

  const picks = {};
  let picked = 0;
  games.forEach((g, i) => {
    const c = bits[i];
    if(c === 'h'){ picks[weekKey + '|' + g.home + '|' + g.away] = g.home; picked++; }
    else if(c === 'a'){ picks[weekKey + '|' + g.home + '|' + g.away] = g.away; picked++; }
    else if(c !== '-'){ /* tolerated: unknown char reads as no pick */ }
  });
  return {weekKey, picks, picked};
}

function copyShareLink(btn){
  const encoded = encodeSharedPicks(currentPicksWeek);
  const label = btn ? btn.textContent : '';
  const flash = (msg) => {
    if(!btn) return;
    btn.textContent = msg;
    setTimeout(()=>{ btn.textContent = label; }, 2600);
  };
  if(!encoded){
    flash('No picks this week');
    return;
  }
  const url = location.origin + location.pathname + '#picks=' + encoded.token;

  // Clipboard access needs a secure context; opened from a file:// path it
  // will not be there. Falling back to a prompt keeps the link reachable
  // rather than failing with nothing on screen.
  const fallback = () => {
    window.prompt('Copy this link to share your picks:', url);
    flash('Link ready');
  };
  if(navigator.clipboard && navigator.clipboard.writeText){
    navigator.clipboard.writeText(url)
      .then(()=> flash(copiedText(encoded.picked)))
      .catch(fallback);
  } else {
    fallback();
  }
}

/* Stage 77 item 18 (the 2026-10-13 audit's copy fix 7): "Copied (1 picks)"
   said what was copied in brackets and miscounted one. */
function copiedText(n){ return `Link copied · ${n} pick${n === 1 ? '' : 's'}`; }

// Non-null only while a shared link is open. renderPicksGrid reads it, which
// is what keeps the shared view from touching localStorage at all.
let sharedPicksView = null;

/* Stage 77 item 19 (the 2026-10-13 audit's copy fix 8): "1 pick for 2026
   week6, shared from someone else's device" read the week's key aloud and
   began with a number. Who did what comes first, and the week as the
   stepper names it. */
function sharedNote(picked, weekKey, mine){
  const m = /_week(\d+)$/.exec(weekKey || '');
  const week = m ? `Week ${m[1]}` : String(weekKey || '').replace('_', ' ');
  return `Someone shared ${picked} pick${picked === 1 ? '' : 's'} for ${week} with you. `
    + 'Nothing has been saved to this device. '
    + (mine ? 'Your own picks are untouched and will come back when you leave this view.'
            : 'You have no picks of your own logged yet.');
}
function showSharedPicks(decoded){
  sharedPicksView = decoded;
  currentPicksWeek = decoded.weekKey;
  const sel = document.getElementById('picks-week-select');
  if(sel) sel.value = decoded.weekKey;
  // Deliberately NOT a change event: that handler ends the shared view, so
  // dispatching one here would close the thing it is opening. The select is
  // moved directly and the stepper is told about it, which is the one case
  // where the "let the select emit and everyone listens" rule cannot apply.
  // Without this the arrows and their label keep showing the previous week
  // while the grid shows the shared one -- two controls disagreeing about the
  // same state, which is the exact failure a shared stepper exists to prevent.
  syncWeekStepper('picks-week');

  const banner = document.getElementById('shared-picks-banner');
  const note = document.getElementById('shared-picks-note');
  if(note){
    const mine = Object.keys(loadMyPicks()).length;
    note.textContent = sharedNote(decoded.picked, decoded.weekKey, mine);
  }
  if(banner) banner.style.display = 'block';
  // Dismiss any pending undo. It refers to a pick made on THIS device a
  // moment ago, and leaving it up means shared view is showing a "Pick saved
  // -- Undo" button that still writes to local storage, which is exactly the
  // guarantee this view is supposed to make. Seen in a screenshot of the
  // receive path; nothing in the logic would have surfaced it.
  const toast = document.getElementById('undo-toast');
  if(toast) toast.classList.remove('visible');
  lastPickChange = null;

  setActivePage('picks');
  renderPicksGrid();
}

function exitSharedPicks(){
  sharedPicksView = null;
  const banner = document.getElementById('shared-picks-banner');
  if(banner) banner.style.display = 'none';
  if(location.hash.indexOf('picks=') !== -1){
    history.replaceState(null, '', location.pathname + location.search);
  }
  renderPicksGrid();
}

function importSharedPicks(){
  if(!sharedPicksView) return;
  const incoming = sharedPicksView.picks;
  const existing = loadMyPicks();
  const clashes = Object.keys(incoming).filter(k => existing[k] && existing[k] !== incoming[k]);

  // Asked, not assumed. These picks belong to someone else, and overwriting
  // a real logged pick would corrupt the record the Season Accuracy page is
  // scored from.
  let overwrite = false;
  if(clashes.length){
    overwrite = window.confirm(
      `${clashes.length} of these games already have a different pick logged on this device.\n\n`
      + `OK = replace yours with the shared pick.\n`
      + `Cancel = keep your own and only fill in the games you have not picked.`);
  }
  const merged = overwrite ? {...existing, ...incoming} : {...incoming, ...existing};
  // A link carries no pick times. Wherever a pick CHANGED, the old time
  // belongs to the old pick and goes with it; games still to come are
  // re-stamped on the next render, locked ones stay uncounted.
  const times = loadPickTimes();
  Object.keys(merged).forEach(k => { if(existing[k] !== merged[k]) delete times[k]; });
  saveMyPicks(merged);
  savePickTimes(times);
  exitSharedPicks();
  alert('Shared picks copied into your log.');
}

function readSharedPicksFromUrl(){
  const m = /[#&]picks=([^&]+)/.exec(location.hash || '');
  if(!m) return;
  const decoded = decodeSharedPicks(decodeURIComponent(m[1]));
  if(decoded.error){
    // Say what went wrong and drop the bad fragment, rather than leaving a
    // link that fails again on every refresh.
    alert(decoded.error);
    history.replaceState(null, '', location.pathname + location.search);
    return;
  }
  showSharedPicks(decoded);
}

function exportMyPicks(){
  const picks = loadMyPicks();
  const payload = { exported: new Date().toISOString(), picks, pick_times: loadPickTimes() };
  const blob = new Blob([JSON.stringify(payload, null, 2)], {type: 'application/json'});
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = 'my_picks_export.json';
  document.body.appendChild(a); a.click(); document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

function importMyPicks(file){
  const reader = new FileReader();
  reader.onload = (e) => {
    try{
      const payload = JSON.parse(e.target.result);
      const incoming = payload.picks || payload; // tolerate a bare picks object too
      if(typeof incoming !== 'object' || incoming === null) throw new Error('not an object');
      const existing = loadMyPicks();
      // Merge rather than overwrite -- imported picks fill in gaps, but don't
      // silently clobber picks already made on this device for the same game.
      const merged = {...incoming, ...existing};
      // Times travel with the picks they belong to: an imported pick keeps
      // the time in the file (older exports have none), a kept pick keeps
      // its own. A pick is never paired with another pick's time.
      const times = loadPickTimes();
      const incomingTimes = (payload && typeof payload.pick_times === 'object' && payload.pick_times) || {};
      Object.keys(merged).forEach(k => {
        if(existing[k] !== undefined) return;
        if(incomingTimes[k]) times[k] = incomingTimes[k]; else delete times[k];
      });
      saveMyPicks(merged);
      savePickTimes(times);
      alert(`Imported ${Object.keys(incoming).length} picks (existing picks on this device were kept where they overlap).`);
      renderPicksGrid();
    } catch(err){
      alert('Could not read that file -- make sure it\'s a picks export from this same site.');
    }
  };
  reader.readAsText(file);
}

/* ---------- One card, one pick ----------
   The single implementation of "what a card looks like given a pick". It is
   called for every card by renderPicksGrid, and for exactly one card by the
   tap handler and by Undo -- so the full render and the surgical update
   cannot drift, which is the .game-card failure this repo has already paid
   for once: two render paths, one edit, a diff that looked complete.

   Everything else on a picks card -- the matchup, the kickoff -- is
   independent of the pick and is never redrawn. */
function paintPickCard(group, pick){
  if(!group) return;
  const modelBPick = group.dataset.modelB;
  // The lock is re-read from the clock on every paint, so a page left open
  // across a kickoff locks the card the next time anything touches it.
  const game = gameForPid(group.dataset.pid);
  const locked = !sharedPicksView && isPickLocked(game, Date.now());
  group.querySelectorAll('.pick-btn').forEach(btn=>{
    btn.classList.toggle('selected', btn.dataset.team === pick);
    // The button is a control with a persistent on/off state, so it says so
    // rather than relying on a colour a screen reader cannot see.
    btn.setAttribute('aria-pressed', btn.dataset.team === pick ? 'true' : 'false');
    btn.disabled = locked;
    if(locked) btn.setAttribute('aria-label', `${btn.dataset.team}, locked at kickoff`);
    else btn.removeAttribute('aria-label');
  });
  const agrees = group.parentElement && group.parentElement.querySelector('.pick-agrees');
  if(agrees) agrees.textContent = pickAgreesText(pick, modelBPick);
  const status = group.parentElement && group.parentElement.querySelector('.pick-lock');
  if(status) status.innerHTML = locked ? pickLockHtml(pick, pickVerdict(loadPickTimes()[group.dataset.pid], game)) : '';
}

/* What a locked card says under its buttons. Only a pick that will NOT be
   counted gets more than the lock itself, and it says why in plain words. */
const LOCK_ICON = '<svg class="lock-icon" viewBox="0 0 16 16" width="12" height="12" aria-hidden="true" focusable="false"><path d="M4.5 7V5a3.5 3.5 0 0 1 7 0v2" fill="none" stroke="currentColor" stroke-width="1.6"/><rect x="3" y="7" width="10" height="7" rx="1.5" fill="currentColor"/></svg>';
function pickLockHtml(pick, verdict){
  let why = '';
  if(pick && verdict === 'late') why = ' This pick was made after kickoff, so it is not counted.';
  else if(pick && verdict === 'untimed') why = ' There is no record of when this pick was made, so it is not counted.';
  return `${LOCK_ICON}<span>Locked at kickoff.${why}</span>`;
}

/* Whose picks are being described changes the pronoun, and that is the only
   thing sharedPicksView changes here. Extracted so the sentence exists once. */
function pickAgreesText(pick, modelBPick){
  if(!pick) return `Model B picks: ${modelBPick}`;
  const agree = pick === modelBPick;
  const suffix = sharedPicksView
    ? (agree ? ' (they agree)' : ' (they differ)')
    : (agree ? ' (you agree)' : ' (you differ)');
  return `Model B picks: ${modelBPick}${suffix}`;
}

/* The record badge and the streak strip are the only things outside a card
   that a single pick can change. They sit above the grid, not under the
   finger, so redrawing them costs nothing the user can feel. */
function refreshPickTotals(myPicks){
  const badge = document.getElementById('picks-record-badge');
  // A share link carries no pick times, so a shared week is never scored:
  // anyone can build a link after the results are in.
  const times = sharedPicksView ? {} : loadPickTimes();
  const t = tallyMyPicks(myPicks, times, weekKeysSorted, weeks);
  if(badge) badge.textContent = sharedPicksView
    ? 'Shared picks are not scored'
    : recordBadgeText(t);

  renderPicksStreak(myPicks, times);
}

function renderPicksStreak(myPicks, times){
  const container = document.getElementById('picks-streak-strip');
  const weekRecords = []; // {label, wins, losses, status}
  weekKeysSorted.forEach(k=>{
    // Counted picks only, through the same tally as the badge above it.
    const {wins, losses} = tallyMyPicks(myPicks, times, [k], weeks);
    const total = wins+losses;
    let status = 'none';
    if(total>0) status = wins>losses ? 'win' : (losses>wins ? 'loss' : 'even');
    weekRecords.push({label:k, wins, losses, status});
  });

  const graded = weekRecords.filter(w=>w.status!=='none');
  if(graded.length === 0){
    container.innerHTML = '';
    return;
  }

  // Current streak: consecutive most-recent graded weeks with the SAME
  // win/loss direction, counting backward from the latest graded week.
  let streak = 0, streakType = null;
  for(let i=graded.length-1; i>=0; i--){
    const w = graded[i];
    if(w.status==='even') break;
    if(streakType===null){ streakType = w.status; streak = 1; }
    else if(w.status===streakType){ streak++; }
    else break;
  }
  const streakLabel = streak>0 ? `${streak}-week ${streakType==='win'?'winning':'losing'} streak` : '';

  container.innerHTML = `
    <div class="streak-row">
      <div class="streak-cells">
        ${weekRecords.map(w=>`<span class="streak-cell ${w.status}" title="${w.label}: ${w.wins}-${w.losses}"></span>`).join('')}
      </div>
      ${streakLabel ? `<span class="streak-label ${streakType}">${streakLabel}</span>` : ''}
    </div>`;
}

let lastPickChange = null;

function renderPicksGrid(){
  const grid = document.getElementById('picks-grid');
  const badge = document.getElementById('picks-record-badge');
  const weekData = weeks[currentPicksWeek];
  const gamesList = weekData ? weekData.games : [];
  // While a share link is open the grid renders THEIR picks and never reads
  // this device's storage, so viewing someone else's week cannot be mistaken
  // for -- or quietly become -- your own log.
  const myPicks = sharedPicksView ? sharedPicksView.picks : loadMyPicks();
  grid.classList.toggle('picks-readonly', !!sharedPicksView);

  if(!weekData || gamesList.length === 0){
    grid.innerHTML = stateHtml('waiting', 'No games to pick for this week yet',
      'Games appear here once the model has saved its picks for the week.');
    badge.textContent = '—';
    return;
  }

  if(!sharedPicksView){
    const times = loadPickTimes();
    if(stampUnlockedPicks(myPicks, times, gameForPid, Date.now())) savePickTimes(times);
  }
  refreshPickTotals(myPicks);

  const now = Date.now();
  grid.innerHTML = gamesList.map(g=>{
    const pid = currentPicksWeek+'|'+g.home+'|'+g.away;
    const pick = myPicks[pid];
    const modelBPick = g.mktB_home >= 50 ? g.home : g.away;
    const kickoff = kickoffLabel(g);
    const locked = !sharedPicksView && isPickLocked(g, now);
    return `<div class="game-card">
      ${matchupHeader(g, 'quiet')}
      ${kickoff ? `<div class="card-kickoff">${kickoff}</div>` : ''}
      <div class="pick-buttons" data-pid="${pid}" data-model-b="${modelBPick}">
        ${pickButton(g.away, pick, locked)}
        ${pickButton(g.home, pick, locked)}
      </div>
      <div class="pick-lock"></div>
      <div class="pick-agrees"></div>
    </div>`;
  }).join('');

  // paintPickCard is the LAST writer on every path, including this one. The
  // markup above still emits `selected` so the first frame is never wrong,
  // but the class it wrote is immediately re-derived here -- so if the two
  // ever disagree, the single authority wins rather than the string template.
  // `.pick-agrees` is emitted empty for the same reason: one implementation
  // of that sentence, not two that drift.
  grid.querySelectorAll('.pick-buttons').forEach(group=>{
    paintPickCard(group, myPicks[group.dataset.pid]);
  });

  // No handlers at all in shared view. Disabling them here rather than
  // ignoring the click inside the handler means there is no path from a tap
  // on someone else's picks to a write against this device's storage.
  if(sharedPicksView) return;

  grid.querySelectorAll('.pick-buttons').forEach(group=>{
    const pid = group.dataset.pid;
    group.querySelectorAll('.pick-btn').forEach(btn=>{
      btn.addEventListener('click', ()=>{
        // Checked here as well as by `disabled`: a page left open across a
        // kickoff still has live buttons until something repaints the card.
        if(isPickLocked(gameForPid(pid), Date.now())){
          paintPickCard(group, loadMyPicks()[pid]);
          return;
        }
        const picks = loadMyPicks(), times = loadPickTimes();
        const previous = picks[pid], previousAt = times[pid];
        const clicked = btn.dataset.team;
        // Clicking your already-selected pick clears it, rather than being
        // a no-op -- otherwise there's no way to un-pick a game at all.
        if(previous === clicked){
          delete picks[pid]; delete times[pid];
        } else {
          picks[pid] = clicked; times[pid] = new Date().toISOString();
        }
        lastPickChange = {pid, previous, previousAt};
        saveMyPicks(picks); savePickTimes(times);
        // NOT renderPicksGrid(). That replaces the whole grid through
        // innerHTML, which destroys the button being tapped along with every
        // other card -- and on iOS the page jumps to the top when the element
        // under your finger is removed mid-tap. Reported from a phone:
        // "changing my pick on cards below the first two scrolls to the top".
        // It does not reproduce in headless Chromium, which has scroll
        // anchoring on by default and absorbs it; that is a difference in
        // engines, not evidence there was nothing to fix.
        //
        // It is also the rule this repo already wrote down after an open
        // breakdown vanished on a filter change: a wholesale innerHTML
        // re-render silently destroys interaction state. Focus, the active
        // touch and the scroll position are all interaction state.
        //
        // Nothing else on the card depends on the pick, so nothing else needs
        // redrawing. The totals above the grid do, and they are not under the
        // finger.
        paintPickCard(group, picks[pid]);
        refreshPickTotals(picks);
        showUndoToast();
      });
    });
  });
}

function showUndoToast(){
  let toast = document.getElementById('undo-toast');
  if(!toast){
    toast = document.createElement('div');
    toast.id = 'undo-toast';
    toast.className = 'undo-toast';
    toast.setAttribute('role', 'status');  // Stage 75 item 6; body.html carries it from the start
    document.body.appendChild(toast);
  }
  toast.innerHTML = `<span>Pick saved</span><button class="btn btn-link undo-btn" id="undo-action">Undo</button>`;
  toast.classList.add('visible');
  document.getElementById('undo-action').onclick = ()=>{
    if(!lastPickChange) return;
    // Undo is a pick too: after kickoff it would be a late change.
    if(isPickLocked(gameForPid(lastPickChange.pid), Date.now())){
      lastPickChange = null;
      toast.classList.remove('visible');
      return;
    }
    const picks = loadMyPicks(), times = loadPickTimes();
    if(lastPickChange.previous === undefined){
      delete picks[lastPickChange.pid];
    } else {
      picks[lastPickChange.pid] = lastPickChange.previous;
    }
    if(lastPickChange.previousAt === undefined) delete times[lastPickChange.pid];
    else times[lastPickChange.pid] = lastPickChange.previousAt;
    saveMyPicks(picks); savePickTimes(times);
    const pid = lastPickChange.pid;
    lastPickChange = null;
    toast.classList.remove('visible');
    // Same surgical path as the tap that created this toast. Undo is not
    // under the finger, but routing it through renderPicksGrid would leave
    // two ways for a card to reach its painted state, and the one nobody
    // looks at is the one that drifts.
    const group = document.querySelector(`#picks-grid .pick-buttons[data-pid="${CSS.escape(pid)}"]`);
    paintPickCard(group, picks[pid]);
    refreshPickTotals(picks);
  };
  clearTimeout(showUndoToast._timer);
  showUndoToast._timer = setTimeout(()=>{ toast.classList.remove('visible'); }, 5000);
}
populateWeekSelect(document.getElementById('picks-week-select'), (val)=>{
  // A share link covers exactly one week, so navigating away from that week
  // ends the shared view rather than showing an empty grid attributed to
  // someone else.
  if(sharedPicksView && val !== sharedPicksView.weekKey) exitSharedPicks();
  currentPicksWeek = val;
  renderPicksGrid();
  syncWeekStepper('picks-week');
}, latestWeekKey);
wireWeekStepper('picks-week');
renderPicksGrid();
// Last, so every function and the week selector it touches already exist.
readSharedPicksFromUrl();

// Pasting a share link into a tab that already has the dashboard open changes
// only the fragment, so the browser does not reload and none of the above runs
// again -- the link would appear to do nothing at all. Found by testing the
// receive path as a real second visit rather than as a fresh page load.
// The same listener handles the back button out of a shared view.
window.addEventListener('hashchange', ()=>{
  if(/[#&]picks=/.test(location.hash || '')) readSharedPicksFromUrl();
  else if(sharedPicksView) exitSharedPicks();
});

