/* The NBA's pages (Stage 61). Everything below reads one JSON block,
   #nba-data, written by src/sports/nba/site.py from the NBA's own files:
   the registered backtest's answers, its validation grid and the history's
   coverage. There is no board: no live NBA picks this season. */
const DATA = JSON.parse(document.getElementById('nba-data').textContent);
const ET = 'America/New_York';

function escapeHtml(s){
  return String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}
function pct(x, digits){ return (x * 100).toFixed(digits ?? 0) + '%'; }
function signed(x, digits){ const v = Number(x).toFixed(digits); return (x > 0 ? '+' : x < 0 ? '−' : '') + v.replace('-', ''); }
function seasonLabel(y){ return `${y}-${String((y + 1) % 100).padStart(2, '0')}`; }
function num(n){ return Number(n).toLocaleString('en-US'); }

/* ---------- tables that scroll ----------
   The NFL board's rule (src/dashboard/app.js, Stage 12), as the NHL's pages
   copy it until Stage 53 moves it into the shared shell: a table wider than
   its box gets the box into the Tab order as a named region, so a keyboard
   user can scroll it (WCAG 2.1.1; axe's scrollable-region-focusable). */
const FOCUSABLE_INSIDE = 'a[href], button, input, select, textarea, [tabindex]:not([tabindex="-1"])';
function scrollStopLabel(el){
  const cap = el.querySelector('caption');
  let heading = null;
  for(let node = el; node && !heading && !node.matches('.page'); node = node.parentElement){
    for(let sib = node.previousElementSibling; sib; sib = sib.previousElementSibling){
      if(sib.matches('h2, h3, h4')){ heading = sib; break; }
    }
  }
  const name = (cap || heading) ? (cap || heading).textContent.trim().replace(/\s+/g, ' ') : '';
  return (name ? `Table: ${name}` : 'Table') + ', scrolls sideways';
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
(function(){
  let queued = false;
  const later = () => { if(queued) return; queued = true; requestAnimationFrame(() => { queued = false; fitTables(); }); };
  window.addEventListener('resize', later);
  if(document.fonts && document.fonts.ready) document.fonts.ready.then(later);
  const root = document.querySelector('main');
  if(root && window.MutationObserver){
    new MutationObserver(later).observe(root, {childList: true, subtree: true, attributes: true, attributeFilter: ['class']});
  }
  later();
})();

/* ---------- the backtest ---------- */
const B = DATA.backtest;
const P = DATA.protocol;
const Q = B.questions;
const QUESTION = {
  H1: 'Does Model A beat knowing only how often the home team wins?',
  H2: 'Does adding the market to Model A improve it?',
  H3: 'Does Model B beat the market alone?',
  M1: 'What does the availability term add? (a measurement, not a test)',
};
const FORECASTS = [
  ['Model A', 'model_a'], ['Model A without availability', 'model_a_no_availability'],
  ['Model B', 'model_b'], ['Market', 'market'], ['Base rate', 'base_rate'],
];
const CONFIRM = P.confirmation_seasons.map(seasonLabel).join(' and ');
const VALIDATE = P.validation_seasons.map(seasonLabel).join(' and ');
function better(diff){ return diff < 0 ? 'lower' : 'higher'; }

/* ---------- why no picks ---------- */
function renderSeason(){
  const s = B.scores;
  document.getElementById('season-body').innerHTML = `
    <div class="nba-notice"><b>No live NBA picks this season.</b> The backtest found that the betting market alone forecasts NBA games slightly better than our best model, and the two things a live pick needs before tip-off, a price and the injury report, cannot be read where this site runs. So instead of picks we expect to do worse than the market, this section shows what was tested and what it found.</div>
    <p class="nba-lede">Three questions were registered on ${escapeHtml(DATA.registered)}, before any NBA model was fitted, and answered once on ${num(Q.H1.games)} games of ${CONFIRM}. Lower log loss is better.</p>
    <ol class="nba-answers">
      <li><b>Model A beats a coin weighted for home court.</b> Its log loss is ${s.model_a.log_loss.toFixed(4)} against ${s.base_rate.log_loss.toFixed(4)} for the home team&#39;s past win rate (H1, <b>${Q.H1.label}</b>).</li>
      <li><b>Adding the market to Model A helps.</b> Model B&#39;s log loss is ${s.model_b.log_loss.toFixed(4)}, ${Math.abs(Q.H2.diff).toFixed(4)} ${better(Q.H2.diff)} than Model A&#39;s (H2, <b>${Q.H2.label}</b>).</li>
      <li><b>But the market alone is better still.</b> The market&#39;s own probability scores ${s.market.log_loss.toFixed(4)}, and Model B is ${Math.abs(Q.H3.diff).toFixed(4)} ${better(Q.H3.diff)}, a small gap whose interval does not reach zero (H3, <b>${Q.H3.label}</b>). What Model A adds to the market costs more than it gives.</li>
      <li><b>Who plays matters.</b> Leaving out the share of each team&#39;s expected minutes that plays raises Model A&#39;s log loss by ${Math.abs(Q.M1.diff).toFixed(4)} (M1, a measurement). In the backtest that share comes from the box score; live it would come from the injury report.</li>
    </ol>
    <h2 class="section-title">What would change this</h2>
    <p class="nba-lede">A live NBA pick needs a scheduled job that reads ESPN&#39;s price and injury report before each tip-off, from a machine those sites answer. And by H3 the pick to lead with would be the market&#39;s, not Model B&#39;s. The forward-test season the registration holds back, ${seasonLabel(P.forward_holdout_season)}, is untouched either way.</p>`;
}

/* ---------- model lab ---------- */
function renderModelLab(){
  const rows = Object.entries(Q).map(([id, q]) => `<tr><th scope="row">${id}</th><td>${QUESTION[id] || ''}</td><td class="num">${signed(q.diff, 4)}</td><td class="num">[${signed(q.low, 4)}, ${signed(q.high, 4)}]</td><td>${q.label ? `<b>${q.label}</b>` : 'a measurement'}</td></tr>`).join('');
  const scores = FORECASTS.filter(([, k]) => B.scores[k]).map(([n, k]) => { const v = B.scores[k];
    return `<tr><th scope="row">${n}</th><td class="num">${num(v.games)}</td><td class="num">${v.log_loss.toFixed(4)}</td><td class="num">${v.brier.toFixed(4)}</td><td class="num">${pct(v.accuracy, 1)}</td></tr>`; }).join('');
  const chosen = DATA.tuning.chosen;
  const grid = DATA.tuning.grid.map(g => { const on = g.H_days === chosen.H_days && g.lambda === chosen.lambda;
    return `<tr${on ? ' class="nba-chosen"' : ''}><td class="num">${g.H_days}</td><td class="num">${g.lambda}</td><td class="num">${g.log_loss.toFixed(5)}</td><td>${on ? 'chosen' : ''}</td></tr>`; }).join('');
  document.getElementById('modellab-body').innerHTML = `
    <p class="nba-lede">Registered before any NBA model was fitted (<code>experiments/nba/stage61/registry.json</code>), tuned on ${VALIDATE} (H = ${B.H_days} days, ridge strength ${B.lambda}), and answered once on ${CONFIRM}. A difference below zero means the first model forecast better. Each interval is a paired bootstrap of whole game days at ${pct(Q.H1.level, 2)}; a result counts only when the interval excludes zero.</p>
    <div class="table-wrap"><table class="metrics-table nba-table"><caption class="visually-hidden">The backtest's questions</caption>
    <thead><tr><th scope="col">#</th><th scope="col">Question</th><th scope="col" class="num">Log loss difference</th><th scope="col" class="num">Interval</th><th scope="col">Label</th></tr></thead>
    <tbody>${rows}</tbody></table></div>
    <h2 class="section-title">Scores on ${CONFIRM}</h2>
    <div class="table-wrap"><table class="metrics-table nba-table"><caption class="visually-hidden">Scores on the held-out seasons</caption>
    <thead><tr><th scope="col">Forecast</th><th scope="col" class="num">Games</th><th scope="col" class="num">Log loss</th><th scope="col" class="num">Brier</th><th scope="col" class="num">Accuracy</th></tr></thead>
    <tbody>${scores}</tbody></table></div>
    <p class="nba-lede">Accuracy is printed, never decides: at this many games it moves by a game or two between machines, where log loss does not.</p>
    <h2 class="section-title">Tuning on ${VALIDATE}</h2>
    <p class="nba-lede">Model A&#39;s log loss over the validation seasons for each registered pair of half-life (days) and ridge strength. The lowest was kept and fixed before the held-out seasons were scored.</p>
    <div class="table-wrap"><table class="metrics-table nba-table"><caption class="visually-hidden">The tuning grid</caption>
    <thead><tr><th scope="col" class="num">Half-life</th><th scope="col" class="num">Ridge</th><th scope="col" class="num">Log loss</th><th scope="col"></th></tr></thead>
    <tbody>${grid}</tbody></table></div>`;
}

/* ---------- methodology ---------- */
function renderMethod(){
  const cov = DATA.coverage.map(c => `<tr><th scope="row">${seasonLabel(c.season)}</th><td class="num">${num(c.games)}</td><td class="num">${num(c.priced)}</td><td class="num">${num(c.closing)}</td></tr>`).join('');
  document.getElementById('method-body').innerHTML = `
    <p class="nba-lede"><b>Model A</b> reads three numbers about a game, each home minus away. Two are team ratings from a ridge regression of every earlier game&#39;s margin, recent games counting more (half as much every ${B.H_days} days): one on points, one on points per 100 possessions. The third is availability: the share of each team&#39;s expected minutes that plays, where a player&#39;s expected minutes are his recent minutes per team game. A logistic regression turns the three into a home-win probability.</p>
    <p class="nba-lede"><b>Model B</b> is Model A plus the market&#39;s home-win probability: ESPN&#39;s moneyline with the bookmaker&#39;s margin taken out evenly, the closing price where there is one.</p>
    <p class="nba-lede"><b>The test.</b> Every regular-season, play-in and playoff game from ${seasonLabel(P.training_from_season)} on. Before each game day both models are refitted on every earlier game and predict that day&#39;s games, so nothing a game did is known before it. The settings were chosen on ${VALIDATE} only, then fixed, and ${CONFIRM} were scored once. ${P.budget_m} questions shared a ${pct(P.alpha)} error budget, so each interval is at ${pct(1 - P.alpha / P.budget_m, 2)}.</p>
    <p class="nba-lede"><b>What the backtest knew that a live pick would not:</b> who actually played, from the box score. A live pick would know only the injury report before tip-off. The registration measures that gap (M2) once there are live games to measure it on.</p>
    <h2 class="section-title">The games</h2>
    <p class="nba-lede">Box scores are ESPN&#39;s. Where ESPN&#39;s is empty (about 500 games of 2015-16 to 2017-18, and six play-in games of 2020-21) they come from SportsDataverse&#39;s copy, and the few games neither has are left out and named in the repository.</p>
    <div class="table-wrap"><table class="metrics-table nba-table"><caption class="visually-hidden">Games and prices per season</caption>
    <thead><tr><th scope="col">Season</th><th scope="col" class="num">Games</th><th scope="col" class="num">With a price</th><th scope="col" class="num">Closing price</th></tr></thead>
    <tbody>${cov}</tbody></table></div>`;
}

/* ---------- checking ---------- */
function renderReliability(){
  document.getElementById('reliability-body').innerHTML = `
    <h2 class="section-title">Before anything was fitted</h2>
    <p class="nba-lede">The questions, the seasons, the settings to search, the bootstrap and the labels were written down and committed on ${escapeHtml(DATA.registered)} (<code>experiments/nba/stage61/registry.json</code>), before any NBA feature was computed on a real game. H3 had been expected to come back INCONCLUSIVE; it came back ${Q.H3.label}, and it is reported as it came out. Nothing was re-run or re-tuned.</p>
    <h2 class="section-title">After</h2>
    <p class="nba-lede">Every number on these pages is read from the committed results files when the page is built, and tests hold those files to the registration: the whole grid searched on the validation seasons only, the lowest kept, each label following from its interval. Those tests were checked in turn, by breaking the code on purpose and confirming a test fails.</p>
    <p class="nba-lede">A separate auditing agent, Booth, re-ran the confirmation on a Linux machine before the results were merged: every number agreed with the committed file to the twelfth decimal place. On Windows the full backtest, tuning included, reproduced both files byte for byte.</p>`;
}

/* ---------- pages, theme ----------
   As the NFL board and the NHL's pages do: every button for the page shown
   carries aria-current, the tab's title names the page, and a change the
   reader asked for moves focus to its heading. Four pages fit the phone's
   bottom bar, so there is no More sheet. */
const BASE_TITLE = document.title;
function showPage(name, opts){
  document.querySelectorAll('.page').forEach(p => p.classList.toggle('active', p.id === 'page-' + name));
  document.querySelectorAll('[data-page]').forEach(b => {
    const on = b.dataset.page === name;
    b.classList.toggle('active', on);
    if(on) b.setAttribute('aria-current', 'page'); else b.removeAttribute('aria-current');
  });
  window.scrollTo(0, 0);
  const page = document.getElementById('page-' + name);
  const heading = page && page.querySelector('.page-head h2');
  document.title = name === 'season' || !heading ? BASE_TITLE : `${heading.textContent.trim()} — Pick'em Model`;
  if(opts && opts.focus && heading){
    heading.setAttribute('tabindex', '-1');
    heading.focus({preventScroll: true});
  }
}
document.querySelectorAll('[data-page]').forEach(b => b.addEventListener('click', () => showPage(b.dataset.page, {focus: true})));
/* The browser checks (tests/browser/check_page.py) open each page by its section id. */
window.setActivePage = id => showPage(String(id).replace(/^page-/, ''));
(function(){
  const bar = document.querySelector('.topbar');
  if(!bar) return;
  const write = () => document.documentElement.style.setProperty('--topbar-h', bar.offsetHeight + 'px');
  write();
  if(typeof ResizeObserver === 'function') new ResizeObserver(write).observe(bar, {box: 'border-box'});
  window.addEventListener('resize', write);
})();
function currentTheme(){ return document.documentElement.getAttribute('data-theme') === 'light' ? 'light' : 'dark'; }
function themeLabel(){ const l = document.getElementById('theme-toggle-label'); if(l) l.textContent = currentTheme() === 'light' ? 'Dark mode' : 'Light mode'; }
document.querySelectorAll('#theme-toggle, .topbar-theme').forEach(btn => btn.addEventListener('click', () => {
  const next = currentTheme() === 'light' ? 'dark' : 'light';
  if(next === 'light') document.documentElement.setAttribute('data-theme', 'light');
  else document.documentElement.removeAttribute('data-theme');
  try{ localStorage.setItem('site:theme', next); }catch(e){}
  themeLabel();
}));

document.getElementById('built-line').textContent = `Built ${new Date(DATA.built_utc).toLocaleString('en-US', {timeZone: ET, month: 'short', day: 'numeric', year: 'numeric'})}`;
themeLabel();
renderSeason();
renderModelLab();
renderMethod();
renderReliability();
document.body.classList.remove('is-entering');
