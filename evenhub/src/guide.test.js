import test from 'node:test';
import assert from 'node:assert/strict';
import { cards, deviceText, step } from './guide.js';

test('les deux sens de navigation couvrent les mêmes fiches avec retour au début', () => {
  for (let i = 0; i < cards.length; i++) {
    assert.equal(step(step(i, 1), -1), i);
    assert.ok(deviceText(i).includes(cards[i].title));
    assert.ok(deviceText(i).includes(cards[i].body));
  }
  assert.equal(step(0, -1), cards.length - 1);
  assert.equal(step(cards.length - 1, 1), 0);
});
