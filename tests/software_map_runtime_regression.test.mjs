// Use the production map keyboard handler and restore path; no browser build.
import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import { readFileSync } from 'node:fs';
const source = readFileSync(process.env.MICROCOSM_DOCS_JS || new URL('../assets/docs.js', import.meta.url), 'utf8');
const map = source.slice(source.indexOf('// --- Selected-node inspector'));
const handler = map.match(/fig\.addEventListener\('keydown', function \(ev\) \{[\s\S]*?\n    \}\);/)?.[0];
const restore = map.match(/function restore\(\) \{[\s\S]*?\n    \}/)?.[0];
const clear = map.match(/function clearToOverview\(\) \{[^\n]+\}/)?.[0];
assert.ok(handler && restore && clear, 'production map reset functions are available');
function setup({ pinned = null, locked = null } = {}) {
  const order = [];
  const pill = (id, active) => ({
    id, active, pressed: active ? 'true' : 'false',
    getAttribute(name) { return name === 'data-graph-focus' ? id : this.pressed; },
    setAttribute(name, value) { if (name === 'aria-pressed') this.pressed = value; },
    classList: { toggle(name, value) { this.owner.active = value; } },
    focus() { order.push('focus:' + id); },
  });
  const all = pill('all', !locked), group = pill('shared_spine', !!locked);
  all.classList.owner = all; group.classList.owner = group;
  let listener;
  const context = {
    pinnedId: pinned, lockedSet: locked, focusBtns: [all, group],
    byId: pinned ? { [pinned]: {} } : {},
    fig: { addEventListener(type, fn) { listener = fn; }, querySelector() { return all; } },
    cancelPendingHover() { order.push('cancel-hover'); },
    clearHash() { order.push('clear-hash'); },
    clearActive() { order.push('whole-map'); },
    renderDefault() { order.push('render-default'); },
    syncTwinCurrent(id) { order.push('sync:' + id); },
    applyFocus() { order.push('focused-subset'); },
    isolate() { order.push('pinned-node'); }, renderNode() {},
  };
  vm.runInNewContext(`${restore}\n${clear}\n${handler}`, context);
  return { context, all, group, order, press: key => listener({ key }) };
}

test('Escape leaves a selected focus subset and returns keyboard focus to Whole map', () => {
  const state = setup({ locked: { 'primitive:project': 1 } });
  state.press('Escape');
  assert.equal(state.context.lockedSet, null);
  assert.equal(state.all.pressed, 'true');
  assert.equal(state.group.pressed, 'false');
  assert.equal(state.all.active, true);
  assert.equal(state.group.active, false);
  assert.ok(state.order.includes('whole-map'));
  assert.ok(!state.order.includes('focused-subset'));
  assert.ok(state.order.indexOf('focus:all') < state.order.indexOf('render-default'));
});

test('Escape from a pinned node also clears a previous focus subset', () => {
  const state = setup({ pinned: 'component:example', locked: { 'component:example': 1 } });
  state.press('Escape');
  assert.equal(state.context.pinnedId, null);
  assert.equal(state.context.lockedSet, null);
  assert.ok(state.order.includes('clear-hash'));
  assert.ok(state.order.includes('whole-map'));
  assert.equal(state.all.pressed, 'true');
});

test('other keys and Escape on an unchanged overview do not reset the map', () => {
  const subset = { 'primitive:project': 1 };
  const selected = setup({ locked: subset });
  selected.press('Enter');
  assert.equal(selected.context.lockedSet, subset);
  assert.deepEqual(selected.order, []);
  const overview = setup();
  overview.press('Escape');
  assert.deepEqual(overview.order, []);
});
