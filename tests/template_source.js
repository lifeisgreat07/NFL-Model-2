// The dashboard template, joined from its parts under src/dashboard/, for
// the JavaScript harnesses (Stage 33 item 26).
//
// The JavaScript twin of src/pipeline/template_parts.py: a line in page.html
// that reads exactly {% include "name" %} is replaced by that part's text,
// and the same things are refused (a stray file, a part included twice, a
// part without its final newline, a directive not alone on its line). It
// reads the files as they are on disk, line endings and all, as the
// harnesses read the one template file before. tests/test_template_parts.py
// holds the two joins to each other, on the real parts and on broken ones.
//
//   node tests/template_source.js [dir]   prints the joined template
'use strict';
const fs = require('fs');
const path = require('path');

const DIR = path.join(__dirname, '..', 'src', 'dashboard');
const SHELL = 'page.html';
const INCLUDE_LINE = /^\{% include "([A-Za-z0-9_.-]+)" %\}\r?\n/gm;

function readTemplate(dir = DIR) {
  const shell = fs.readFileSync(path.join(dir, SHELL), 'utf8');
  const names = [...shell.matchAll(INCLUDE_LINE)].map(m => m[1]);
  const present = fs.readdirSync(dir)
    .filter(n => n !== SHELL && fs.statSync(path.join(dir, n)).isFile()).sort();
  if (JSON.stringify(present) !== JSON.stringify([...new Set(names)].sort())) {
    throw new Error(`${path.basename(dir)}/ holds ${present} but ${SHELL} includes ${names}`);
  }
  if (new Set(names).size !== names.length) {
    throw new Error(`a part is included more than once: ${names}`);
  }
  if (shell.split('{% include').length - 1 !== names.length) {
    throw new Error(`${SHELL} has an include directive that is not alone on its own line`);
  }
  return shell.replace(INCLUDE_LINE, (_, name) => {
    const part = fs.readFileSync(path.join(dir, name), 'utf8');
    if (!part.endsWith('\n')) throw new Error(`part ${name} does not end with a newline`);
    return part;
  });
}

module.exports = { readTemplate };

if (require.main === module) {
  process.stdout.write(readTemplate(process.argv[2] || DIR));
}
