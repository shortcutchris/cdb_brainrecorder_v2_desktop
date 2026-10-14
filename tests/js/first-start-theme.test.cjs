const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

test('First-start applies the saved theme without requiring the settings editor', () => {
  const events = {}, root = {dataset:{}, style:{removeProperty(){},setProperty(){}}};
  const context = {
    document: {documentElement:root, getElementById(){return null}, addEventListener(name, fn){events[name]=fn}},
    localStorage: {getItem(key){return key==='cdb-studio-theme'?'midnight':null}},
    window: {addEventListener(){}},
  };
  vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../../studio/themes.js'),'utf8'),context);
  assert.equal(root.dataset.theme,'midnight');
  assert.doesNotThrow(()=>events.DOMContentLoaded());
});
