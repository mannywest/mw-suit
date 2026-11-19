// Copied from mw-tailleur-wedding-brochure/js/pricing.js (single source of truth lives there; keep in sync).
export const contact = { whatsapp: '447401885154', email: 'emmanuel@madewestern.com' };
export const consultation = { remote: 'Complimentary', inPerson: '£50 per session' };
export const leadTime = 'Typically 4–6 weeks (provisional)';
export const families = [
  { id: 'plain', name: 'Plain Wool' },
  { id: 'premium', name: 'Premium & Jacquard' },
  { id: 'italian', name: 'Italian Luxury' },
  { id: 'groomsmen', name: 'Groomsmen' },
  { id: 'fathers', name: 'Father & Son' },
];
export const packages = [
  { id: 'plain-2', family: 'plain', tag: 'Two-Piece', name: 'Two-Piece Groom Package', amount: 995 },
  { id: 'plain-3', family: 'plain', tag: 'Three-Piece', name: 'Three-Piece Groom Package', amount: 1150 },
  { id: 'premium-2', family: 'premium', tag: 'Two-Piece', name: 'Two-Piece Premium Package', amount: 1195 },
  { id: 'premium-3', family: 'premium', tag: 'Three-Piece', name: 'Three-Piece Premium Package', amount: 1350 },
  { id: 'italian-2', family: 'italian', tag: 'Two-Piece', name: 'Two-Piece Italian Luxury Package', amount: 1595, from: true },
  { id: 'italian-3', family: 'italian', tag: 'Three-Piece', name: 'Three-Piece Italian Luxury Package', amount: 1795, from: true },
  { id: 'groomsmen-2', family: 'groomsmen', tag: 'Two-Piece', name: 'Groomsmen Two-Piece', amount: 450, perPerson: true },
  { id: 'groomsmen-3', family: 'groomsmen', tag: 'Three-Piece', name: 'Groomsmen Three-Piece', amount: 500, perPerson: true },
  { id: 'fathers-2', family: 'fathers', tag: 'Two-Piece', name: 'Father & Son Two-Piece', amount: 1595 },
  { id: 'fathers-3', family: 'fathers', tag: 'Three-Piece', name: 'Father & Son Three-Piece', amount: 1795 },
];
