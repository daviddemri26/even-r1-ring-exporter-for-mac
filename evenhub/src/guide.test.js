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
  assert.match(display.content, /^R1 Ring Guide for G2\n/);
  assert.match(display.content, /Connect your R1 ring data to ChatGPT/);
  assert.match(display.content, /sensor readings right in the chat/);
  assert.match(display.content, /Open the guide on your phone/);

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
  assert.match(page, /<h1>R1 Ring Guide for G2<\/h1>/);
  assert.match(page, /sensor readings right in the chat/);
  const links = [...page.matchAll(/<a href="([^"]+)"[^>]*>([^<]+)<\/a>/g)];
  assert.deepEqual(links.map(([,href,label]) => [href,label]), [[setup,'Set up on Mac']]);
  assert.ok(page.includes('>' + setup + '</span>'));
});
