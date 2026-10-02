// Runs the page's scroll-stop functions (headingBefore, scrollStopLabel,
// setScrollStop) against a small fake DOM, because they are pure DOM
// bookkeeping: which attributes a box gets when it scrolls, which it loses
// when it fits, and what it is called. The code under test is read from
// src/pipeline/dashboard_template.html and passed in on stdin by
// tests/test_scrollable_regions.py; nothing here is a copy of it.
'use strict';

function simpleMatch(el, sel){
  sel = sel.trim();
  let m;
  if((m = sel.match(/^\[tabindex\]:not\(\[tabindex="-1"\]\)$/)))
    return el.hasAttribute('tabindex') && el.getAttribute('tabindex') !== '-1';
  if((m = sel.match(/^([a-z0-9]+)\[([a-z-]+)\]$/)))
    return el.tag === m[1] && el.hasAttribute(m[2]);
  if((m = sel.match(/^\.([a-z-]+)$/))) return el.classList.contains(m[1]);
  if(/^[a-z0-9]+$/.test(sel)) return el.tag === sel;
  throw new Error('fake DOM cannot match selector: ' + sel);
}

class El {
  constructor(tag, opts = {}, children = []){
    this.tag = tag;
    this.attrs = Object.assign({}, opts.attrs || {});
    const classes = new Set(opts.cls || []);
    this.classList = {contains: c => classes.has(c)};
    this.text = opts.text || '';
    this.parentElement = null;
    this.children = [];
    children.forEach(c => this.append(c));
  }
  append(c){ c.parentElement = this; this.children.push(c); return c; }
  get previousElementSibling(){
    if(!this.parentElement) return null;
    const sibs = this.parentElement.children;
    const i = sibs.indexOf(this);
    return i > 0 ? sibs[i - 1] : null;
  }
  get textContent(){ return this.text + this.children.map(c => c.textContent).join(''); }
  hasAttribute(n){ return Object.prototype.hasOwnProperty.call(this.attrs, n); }
  getAttribute(n){ return this.hasAttribute(n) ? this.attrs[n] : null; }
  setAttribute(n, v){ this.attrs[n] = String(v); }
  removeAttribute(n){ delete this.attrs[n]; }
  matches(sel){ return sel.split(',').some(s => simpleMatch(this, s)); }
  querySelectorAll(sel){
    const out = [];
    const walk = e => e.children.forEach(c => { if(c.matches(sel)) out.push(c); walk(c); });
    walk(this);
    return out;
  }
  querySelector(sel){ return this.querySelectorAll(sel)[0] || null; }
}
const h = (tag, opts, children) => new El(tag, opts, children);

const code = require('fs').readFileSync(0, 'utf8');
// eslint-disable-next-line no-new-func
const api = new Function(code + '\nreturn {headingBefore, scrollStopLabel, setScrollStop};')();
const attrs = el => Object.assign({}, el.attrs);
const out = {};

// A Method-style section: heading, paragraph, then the wide table.
function methodBlock(){
  const table = h('table');
  const wrap = h('div', {cls: ['table-wrap']}, [table]);
  const page = h('section', {cls: ['page']}, [
    h('div', {cls: ['method-block']}, [
      h('h3', {text: 'Backtest  Results\n  by season'}), h('p', {text: 'intro'}), wrap])]);
  return {page, wrap};
}

// 1. Scrolls, then fits again.
{
  const {wrap} = methodBlock();
  api.setScrollStop(wrap, true);
  out.scrolls = attrs(wrap);
  api.setScrollStop(wrap, true);
  out.scrolls_twice = attrs(wrap);
  api.setScrollStop(wrap, false);
  out.fits_again = attrs(wrap);
}
// 2. A box that never scrolled is left alone when it fits.
{
  const {wrap} = methodBlock();
  wrap.setAttribute('tabindex', '0');
  api.setScrollStop(wrap, false);
  out.never_marked = attrs(wrap);
}
// 3. Markup's own role and label survive; only the added tabindex goes.
{
  const {wrap} = methodBlock();
  wrap.setAttribute('role', 'region');
  wrap.setAttribute('aria-label', 'Set in the markup');
  api.setScrollStop(wrap, true);
  out.markup_scrolls = attrs(wrap);
  api.setScrollStop(wrap, false);
  out.markup_fits = attrs(wrap);
}
// 4. A box with a control of its own gets no extra stop -- and one that
//    was a stop and has since been re-rendered with a control loses it.
{
  const {wrap} = methodBlock();
  wrap.children[0].append(h('th', {attrs: {tabindex: '0'}}));
  api.setScrollStop(wrap, true);
  out.has_control = attrs(wrap);
  const b = methodBlock();
  api.setScrollStop(b.wrap, true);
  b.wrap.children[0].append(h('button'));
  api.setScrollStop(b.wrap, true);
  out.gains_control = attrs(b.wrap);
  const c = methodBlock();
  c.wrap.children[0].append(h('th', {attrs: {tabindex: '-1'}}));
  api.setScrollStop(c.wrap, true);
  out.minus_one_is_not_a_control = attrs(c.wrap);
}
// 5. Names.
{
  const {wrap} = methodBlock();
  out.label_heading = api.scrollStopLabel(wrap);

  const f = h('div', {cls: ['formula'], text: 'y ~ x'});
  h('section', {cls: ['page']}, [h('div', {cls: ['method-block']}, [h('h3', {text: 'Rating System'}), f])]);
  out.label_formula = api.scrollStopLabel(f);

  const given = h('div', {cls: ['table-wrap'], attrs: {'data-scroll-label': 'Experiment log'}}, [h('table')]);
  h('section', {cls: ['page']}, [h('h3', {text: 'Reliability Diagram'}), given]);
  out.label_given = api.scrollStopLabel(given);

  const cap = h('div', {cls: ['table-wrap']}, [h('table', {}, [h('caption', {text: 'Bins'})])]);
  h('section', {cls: ['page']}, [h('h3', {text: 'Section'}), cap]);
  out.label_caption = api.scrollStopLabel(cap);

  // Accuracy: a nested note with its own heading sits between the section
  // heading and the table. The note's heading is not the table's name.
  const acc = h('div', {cls: ['table-wrap']}, [h('table')]);
  h('section', {cls: ['page']}, [h('div', {cls: ['method-block']}, [
    h('h3', {text: 'Are these percentages honest?'}), h('p', {text: 'why'}),
    h('div', {cls: ['method-block']}, [h('h3', {text: 'Not enough games yet to check'}), h('p')]),
    acc])]);
  out.label_nested_note = api.scrollStopLabel(acc);

  // The heading search walks up through wrappers to an ancestor's sibling...
  const deep = h('div', {cls: ['table-wrap']}, [h('table')]);
  h('section', {cls: ['page']}, [h('h2', {text: 'Page title'}), h('div', {}, [h('div', {}, [deep])])]);
  out.label_ancestor_sibling = api.scrollStopLabel(deep);

  // ...but never past the start of its page.
  const lone = h('div', {cls: ['table-wrap']}, [h('table')]);
  h('main', {}, [h('h2', {text: 'Another page'}), h('section', {cls: ['page']}, [h('p'), lone])]);
  out.label_none = api.scrollStopLabel(lone);
}

process.stdout.write(JSON.stringify(out));
