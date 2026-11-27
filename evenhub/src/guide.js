import { CreateStartUpPageContainer, TextContainerProperty, OsEventTypeList } from '@evenrealities/even_hub_sdk';

const displayText = [
  'R1 Ring Data→ChatGPT',
  '',
  'On your Mac, open is.gd/r1mac',
  'Click “Copy setup prompt”.',
  'Paste it into Codex and press Return.',
  '',
  'Double-tap for the exit menu.'
].join('\n');

export async function showGuide(bridge) {
  const text = new TextContainerProperty({
    containerID: 1, containerName: 'guide', xPosition: 0, yPosition: 0,
    width: 576, height: 288, paddingLength: 6, isEventCapture: 1, content: displayText
  });
  const result = await bridge.createStartUpPageContainer(new CreateStartUpPageContainer({
    containerTotalNum: 1, textObject: [text]
  }));
  if (result !== 0) throw new Error('The glasses could not display the guide.');

  bridge.onEvenHubEvent(({ sysEvent, textEvent }) => {
    const doubleTap = OsEventTypeList.DOUBLE_CLICK_EVENT;
    if (sysEvent?.eventType === doubleTap || (textEvent?.containerID === 1 && textEvent.eventType === doubleTap)) {
      bridge.shutDownPageContainer(1);
    }
  });
}
