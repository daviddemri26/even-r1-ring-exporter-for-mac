import {
  waitForEvenAppBridge, CreateStartUpPageContainer, TextContainerProperty,
  TextContainerUpgrade, OsEventTypeList
} from '@evenrealities/even_hub_sdk';
import { cards, deviceText, step } from './guide.js';

const container = { containerID: 1, containerName: 'guide' };
let index = 0;
let glasses;
let pending = Promise.resolve();

function showCard() {
  document.querySelector('#position').textContent = `Fiche ${index + 1} sur ${cards.length}`;
  document.querySelector('#title').textContent = cards[index].title;
  document.querySelector('#body').textContent = cards[index].body;
}

function move(delta) {
  index = step(index, delta);
  showCard();
  if (glasses) {
    const update = new TextContainerUpgrade({ ...container, content: deviceText(index) });
    pending = pending.then(() => glasses.textContainerUpgrade(update)).catch(reportDisplayError);
  }
}

function reportDisplayError() {
  document.querySelector('#status').textContent = 'Affichage des lunettes indisponible. Le guide reste consultable ici.';
}

async function connectDisplay() {
  const bridge = await waitForEvenAppBridge();
  const text = new TextContainerProperty({
    ...container, xPosition: 0, yPosition: 0, width: 576, height: 288,
    paddingLength: 6, isEventCapture: 1, content: deviceText(index)
  });
  const result = await bridge.createStartUpPageContainer(new CreateStartUpPageContainer({
    containerTotalNum: 1, textObject: [text]
  }));
  if (result !== 0) return reportDisplayError();
  glasses = bridge;
  bridge.onEvenHubEvent(event => {
    const target = event.textEvent ?? event.sysEvent;
    if (!target || (event.textEvent && target.containerID !== container.containerID)) return;
    switch (target.eventType) {
      case OsEventTypeList.DOUBLE_CLICK_EVENT: bridge.shutDownPageContainer(1); break;
      case OsEventTypeList.SCROLL_TOP_EVENT: move(-1); break;
      case OsEventTypeList.SCROLL_BOTTOM_EVENT:
      case OsEventTypeList.CLICK_EVENT: move(1); break;
      case undefined: if (event.textEvent) move(1); break;
    }
  });
}

document.querySelector('#previous').addEventListener('click', () => move(-1));
document.querySelector('#next').addEventListener('click', () => move(1));
showCard();
connectDisplay().catch(reportDisplayError);
