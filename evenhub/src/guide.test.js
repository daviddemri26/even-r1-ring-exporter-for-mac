import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { OsEventTypeList } from '@evenrealities/even_hub_sdk';
import { showGuide } from './guide.js';

test('the G2 starts on a single setup screen and double-tap opens the system exit menu', async () => {
  let startup;
  let onEvent;
  const exitRequests = [];
  await showGuide({
    createStartUpPageContainer: async page => { startup = page; return 0; },
    onEvenHubEvent: listener => { onEvent = listener; },
    shutDownPageContainer: mode => { exitRequests.push(mode); }
  });
  assert.equal(startup.containerTotalNum, 1);
  const [display] = startup.textObject;
  assert.equal(display.width, 576);
  assert.equal(display.height, 288);
  assert.equal(display.isEventCapture, 1);
  const manifest = JSON.parse(await readFile(new URL('../app.json', import.meta.url), 'utf8'));
  assert.equal(display.content.split('\n')[0], manifest.name);
  assert.ok([...manifest.name].length <= 20);
  assert.match(display.content, /On your Mac, open is\.gd\/r1mac/);
  assert.match(display.content, /Copy setup prompt/);
  assert.match(display.content, /Paste it into Codex and press Return/);

  onEvent({sysEvent: {eventSource: 1}});
  onEvent({textEvent: {containerID: 1, eventType: OsEventTypeList.CLICK_EVENT}});
  assert.deepEqual(exitRequests, []);
  onEvent({sysEvent: {eventType: OsEventTypeList.DOUBLE_CLICK_EVENT}});
  onEvent({textEvent: {containerID: 1, eventType: OsEventTypeList.DOUBLE_CLICK_EVENT}});
  assert.deepEqual(exitRequests, [1, 1]);
});

test('the phone provides one setup link and its address works without the glasses bridge', async () => {
  const page = await readFile(new URL('./index.html', import.meta.url), 'utf8');
  const setup = 'https://daviddemri26.github.io/even-r1-ring-exporter-for-mac/guides/install/';
  assert.match(page, /<h1>R1 Ring Data→ChatGPT<\/h1>/);
  assert.match(page, /Connect R1 Ring Data to ChatGPT/);
  assert.match(page, /On your Mac, open <strong id="setup-address">is\.gd\/r1mac<\/strong>/);
  assert.match(page, /Copy setup prompt/);
  assert.match(page, /Paste it into Codex on your Mac and press Return/);
  const links = [...page.matchAll(/<a href="([^"]+)"[^>]*>([^<]+)<\/a>/g)];
  assert.deepEqual(links.map(([,href,label]) => [href,label]), [[setup,'Preview the Mac setup page on this phone']]);
});
