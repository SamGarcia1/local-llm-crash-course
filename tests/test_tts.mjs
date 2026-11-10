import { readFile } from 'node:fs/promises';
import { test } from 'node:test';
import assert from 'node:assert/strict';
const source = await readFile(new URL('../public/tts-spike.js', import.meta.url), 'utf8');
const { createSpeaker } = await import(`data:text/javascript;base64,${Buffer.from(source).toString('base64')}`);
function setup() {
  const events = [], spoken = [];
  let cancelled = 0;
  const synth = { cancel() { cancelled++; }, resume() {}, speak(u) { spoken.push(u); } };
  const player = createSpeaker(synth, class { constructor(text) { this.text = text; } }, s => events.push(s));
  return { player, synth, events, spoken, cancelled: () => cancelled };
}
test('silent until explicit speak; empty input never queued', () => {
  const s = setup(); assert.equal(s.spoken.length, 0);
  s.player.speak('  '); assert.equal(s.spoken.length, 0);
});
test('speech uses complete text and selected voice; completion reported', () => {
  const s = setup(), voice = { lang: 'en-US' };
  s.player.speak(' Complete response. ', voice);
  const u = s.spoken[0]; assert.equal(u.text, 'Complete response.');
  assert.equal(u.voice, voice); u.onstart(); assert.equal(s.events.at(-1), 'Speaking');
  u.onend(); assert.equal(s.events.at(-1), 'Finished');
});
test('replacement and stop cancel queues and ignore stale callbacks', () => {
  const s = setup(); s.player.speak('first'); const old = s.spoken[0];
  s.player.speak('second'); old.onerror({error:'interrupted'});
  assert.equal(s.events.at(-1), 'Starting speech…');
  s.player.stop(); s.spoken[1].onend(); assert.equal(s.events.at(-1), 'Stopped');
  assert.equal(s.cancelled(), 3);
});
test('engine errors and thrown failures are recoverable', () => {
  const s = setup(); s.player.speak('hello');
  s.spoken[0].onerror({error:'not-allowed'}); assert.match(s.events.at(-1), /not-allowed/);
  s.synth.speak = () => { throw Error('unavailable'); };
  s.player.speak('retry'); assert.match(s.events.at(-1), /unavailable/);
});
