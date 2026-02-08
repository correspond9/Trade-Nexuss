export const normalizeUnderlying = (value) => {
  if (!value) return 'NIFTY';
  const raw = String(value).trim().toUpperCase();

  // Common aliases from UI labels
  const aliases = {
    'NIFTY 50': 'NIFTY',
    'NIFTY50': 'NIFTY',
    'NIFTY BANK': 'BANKNIFTY',
    'BANK NIFTY': 'BANKNIFTY',
    'BANKNIFTY': 'BANKNIFTY',
    'SENSEX': 'SENSEX',
    'SENSEX 30': 'SENSEX',
    'BSE SENSEX': 'SENSEX',
    'S&P BSE SENSEX': 'SENSEX',
  };

  if (aliases[raw]) return aliases[raw];

  // Fallback heuristics
  if (raw.includes('BANKNIFTY') || raw.includes('NIFTY BANK')) return 'BANKNIFTY';
  if (raw.includes('SENSEX')) return 'SENSEX';
  if (raw.includes('NIFTY')) return 'NIFTY';

  return 'NIFTY';
};

export default normalizeUnderlying;
