const fs = require('fs');

const data = fs.readFileSync('instruments.csv', 'utf8');
const lines = data.split('\n');

console.log('=== OPTION INSTRUMENT ANALYSIS ===\n');

// Find option instruments
const options = [];
for (let i = 1; i < lines.length; i++) {
    const line = lines[i].trim();
    if (!line) continue;
    
    const fields = line.split(',');
    const exchange = fields[0];
    const segment = fields[1];
    const symbol = fields[5];
    const optionType = fields[11];
    const strike = fields[9];
    
    if (optionType === 'CE' || optionType === 'PE') {
        options.push({
            exchange,
            segment,
            symbol,
            optionType,
            strike,
            securityId: fields[2]
        });
    }
    
    if (options.length >= 20) break; // Limit to first 20 for analysis
}

console.log('Sample Option Instruments:');
options.forEach((opt, i) => {
    console.log(`${i+1}. ${opt.exchange} ${opt.segment} ${opt.symbol} ${opt.optionType} Strike:${opt.strike} ID:${opt.securityId}`);
});

// Analyze option chain structure
console.log('\n=== OPTION CHAIN STRUCTURE ANALYSIS ===');

// Group by underlying symbol
const chains = {};
options.forEach(opt => {
    // Extract underlying from option symbol (e.g., BANKNIFTY-27Jan2026-88500-CE)
    const parts = opt.symbol.split('-');
    if (parts.length >= 3) {
        const underlying = parts[0];
        const expiry = parts[1];
        const key = `${underlying}-${expiry}`;
        
        if (!chains[key]) {
            chains[key] = {
                underlying,
                expiry,
                calls: [],
                puts: [],
                strikes: new Set()
            };
        }
        
        chains[key].strikes.add(parseFloat(opt.strike));
        if (opt.optionType === 'CE') {
            chains[key].calls.push(opt);
        } else {
            chains[key].puts.push(opt);
        }
    }
});

console.log('\nOption Chains Found:');
Object.entries(chains).forEach(([key, chain]) => {
    const totalInstruments = chain.calls.length + chain.puts.length;
    const uniqueStrikes = chain.strikes.size;
    console.log(`\n${chain.underlying} ${chain.expiry}:`);
    console.log(`  Calls: ${chain.calls.length}`);
    console.log(`  Puts: ${chain.puts.length}`);
    console.log(`  Unique Strikes: ${uniqueStrikes}`);
    console.log(`  Total Instruments: ${totalInstruments}`);
    console.log(`  Counting Method: ${totalInstruments === uniqueStrikes * 2 ? 'Individual strikes' : 'Other'}`);
});

console.log('\n=== SUBSCRIPTION COUNTING MECHANISM ===');
console.log('Based on Dhan documentation and code analysis:');
console.log('');
console.log('📊 INDIVIDUAL STRIKES COUNT:');
console.log('• Each option strike (CE/PE) = 1 instrument');
console.log('• Each strike has 2 instruments (Call + Put)');
console.log('• Option chain with 100 strikes = 200 instruments');
console.log('');
console.log('📋 SUBSCRIPTION FORMAT:');
console.log('• RequestCode: 15');
console.log('• InstrumentCount: Actual number of individual instruments');
console.log('• InstrumentList: Array of individual Security IDs');
console.log('');
console.log('💡 EXAMPLE:');
console.log('NIFTY option chain with 50 strikes:');
console.log('• 50 Call options = 50 instruments');
console.log('• 50 Put options = 50 instruments');
console.log('• Total = 100 instruments');
console.log('');
console.log('📈 LIMITS:');
console.log('• Per WebSocket message: 100 instruments max');
console.log('• Per WebSocket connection: 5,000 instruments max');
console.log('• Multiple messages allowed per connection');
