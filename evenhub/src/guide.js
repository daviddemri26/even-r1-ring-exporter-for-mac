export const cards = [
  { title: 'Wear your ring', body: 'Wear the R1 while you sleep. When you wake up, open Health in the Even app on your iPhone.' },
  { title: 'Find a night', body: 'Find the date you woke up on your iPhone. Look for the same date in Even on your Mac, signed in to the same account.' },
  { title: 'Collect on your Mac', body: 'Leave the Mac unlocked during a scheduled collection window. Check the last export in Even R1 Ring Exporter for Mac.' },
  { title: 'Ask ChatGPT', body: 'Select Even R1 Ring Data for ChatGPT and ask “How much did I sleep each night over the last seven days?”' },
  { title: 'Check a missing night', body: 'A missing date means Even supplied no sleep session for that date. Compare the wake-up date with Health on your iPhone.' }
];

export function step(index, delta) {
  return (index + delta + cards.length) % cards.length;
}

export function deviceText(index) {
  const card = cards[index];
  return [`${index + 1}/${cards.length}  ${card.title}`, '', card.body, '', 'Tap to continue · Double-tap to exit'].join('\n');
}
