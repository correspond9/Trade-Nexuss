const fs = require('fs');

const results = {
    nse_eq: 0,
    nse_fo: 0,
    bse_eq: 0,
    bse_fo: 0,
    mcx_com: 0,
    mcx_fo: 0,
    msx_fo: 0,
    total: 0,
    segments: {}
};

const data = fs.readFileSync('instruments.csv', 'utf8');
const lines = data.split('\n');

// Skip header
for (let i = 1; i < lines.length; i++) {
    const line = lines[i].trim();
    if (!line) continue;
    
    const fields = line.split(',');
    const exchange = fields[0];
    const segment = fields[1];
    const instrumentType = fields[13];
    
    results.total++;
    
    // Track all segments
    const key = `${exchange}_${segment}`;
    results.segments[key] = (results.segments[key] || 0) + 1;
    
    // NSE
    if (exchange === 'NSE') {
        if (segment === 'EQ') {
            results.nse_eq++;
        } else if (segment === 'FO' || segment === 'FUT' || segment === 'OPT') {
            results.nse_fo++;
        }
    }
    
    // BSE
    if (exchange === 'BSE') {
        if (segment === 'EQ') {
            results.bse_eq++;
        } else if (segment === 'FO' || segment === 'FUT' || segment === 'OPT') {
            results.bse_fo++;
        }
    }
    
    // MCX
    if (exchange === 'MCX') {
        if (segment === 'COM') {
            results.mcx_com++;
        } else if (segment === 'FO' || segment === 'FUT' || segment === 'OPT') {
            results.mcx_fo++;
        }
    }
    
    // MSX
    if (exchange === 'MSX') {
        if (segment === 'FO' || segment === 'FUT' || segment === 'OPT') {
            results.msx_fo++;
        }
    }
}

console.log('=== Dhan Instrument Counts ===');
console.log('NSE Equity (EQ):', results.nse_eq);
console.log('NSE Futures & Options (FO):', results.nse_fo);
console.log('BSE Equity (EQ):', results.bse_eq);
console.log('BSE Futures & Options (FO):', results.bse_fo);
console.log('MCX Commodities (COM):', results.mcx_com);
console.log('MCX Futures & Options (FO):', results.mcx_fo);
console.log('MSX Futures & Options (FO):', results.msx_fo);
console.log('Total Instruments:', results.total);

console.log('\n=== All Exchange/Segment Combinations ===');
Object.entries(results.segments).sort((a, b) => b[1] - a[1]).forEach(([key, count]) => {
    console.log(`${key}: ${count}`);
});

// Show some sample instruments from different segments
console.log('\n=== Sample Instruments by Exchange ===');
const samples = {
    'NSE': [],
    'BSE': [],
    'MCX': [],
    'MSX': []
};

for (let i = 1; i < lines.length; i++) {
    const line = lines[i].trim();
    if (!line) continue;
    
    const fields = line.split(',');
    const exchange = fields[0];
    const segment = fields[1];
    const symbol = fields[5];
    
    if (samples[exchange] && samples[exchange].length < 5) {
        samples[exchange].push(`${segment}: ${symbol}`);
    }
}

Object.entries(samples).forEach(([exchange, instruments]) => {
    console.log(`\n${exchange} samples:`);
    instruments.forEach(inst => console.log(`  ${inst}`));
});
