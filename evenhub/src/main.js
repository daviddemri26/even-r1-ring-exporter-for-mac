import { waitForEvenAppBridge } from '@evenrealities/even_hub_sdk';
import { showGuide } from './guide.js';

waitForEvenAppBridge().then(showGuide).catch(() => {
  document.querySelector('#status').textContent = 'The glasses display is unavailable. You can still start setup on your Mac.';
});
