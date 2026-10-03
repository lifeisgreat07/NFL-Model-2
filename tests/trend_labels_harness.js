/*
 * Executes the shipped spreadLabels() -- where the accuracy trend chart puts
 * its end-labels so no two overprint (Stage 19).
 *
 * Driven by tests/test_accuracy_trend_labels.py.
 */
const fs = require('fs');
const path = require('path');

const { readTemplate } = require('./template_source');
const tpl = readTemplate().replace(/\r\n/g, '\n');

const i = tpl.indexOf('const TREND_LABEL_GAP');
const fn = i === -1 ? -1 : tpl.indexOf('function spreadLabels(', i);
const j = fn === -1 ? -1 : tpl.indexOf('\n}\n', fn);
if (i === -1 || fn === -1 || j === -1) {
  console.log(JSON.stringify({fatal:
    `could not extract spreadLabels (gap=${i}, fn=${fn}, end=${j}) -- the ` +
    `code moved and this harness is testing nothing`}));
  process.exit(0);
}
const {spreadLabels, TREND_LABEL_GAP} =
  new Function(tpl.slice(i, j + 2) + '\nreturn {spreadLabels, TREND_LABEL_GAP};')();

const G = 14, LO = 18, HI = 192;
const minGap = ys => { const s = ys.slice().sort((a, b) => a - b);
  return s.slice(1).reduce((m, v, k) => Math.min(m, v - s[k]), Infinity); };

const apart = [40, 100, 160];
const together = [100, 100, 101];           // Model A and B finishing on the same value
const atBottom = [190, 191, 192, 192];      // four lines ending at the floor
const reversed = [150, 100];

console.log(JSON.stringify({
  gap: TREND_LABEL_GAP,
  apart: spreadLabels(apart, G, LO, HI),
  together: spreadLabels(together, G, LO, HI),
  together_min_gap: minGap(spreadLabels(together, G, LO, HI)),
  at_bottom: spreadLabels(atBottom, G, LO, HI),
  at_bottom_min_gap: minGap(spreadLabels(atBottom, G, LO, HI)),
  reversed: spreadLabels(reversed, G, LO, HI),
  empty: spreadLabels([], G, LO, HI),
}));
