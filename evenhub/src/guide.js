export const cards = [
  { title: 'Porter la bague', body: 'Pour suivre une nuit, portez la R1 pendant votre sommeil. Au réveil, ouvrez Health dans Even sur l’iPhone.' },
  { title: 'Retrouver une nuit', body: 'Vérifiez sa date de réveil sur l’iPhone, puis dans Even sur le Mac connecté au même compte.' },
  { title: 'Collecter sur le Mac', body: 'Gardez la session Mac ouverte et déverrouillée à l’heure de collecte. Consultez le dernier essai dans R1 Bridge.' },
  { title: 'Interroger ChatGPT', body: 'Sélectionnez votre connecteur privé. Demandez « Combien ai-je dormi ces sept derniers jours ? »' },
  { title: 'Comprendre un manque', body: 'Une date sans session signifie qu’Even n’a fourni aucune durée. Comparez la date de réveil à celle affichée sur l’iPhone.' }
];

export function step(index, delta) {
  return (index + delta + cards.length) % cards.length;
}

export function deviceText(index) {
  const card = cards[index];
  return [`${index + 1}/${cards.length}  ${card.title}`, '', card.body, '', 'Appui : suite · Double appui : quitter'].join('\n');
}
