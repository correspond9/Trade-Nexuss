const fs = require('fs');

console.log('=== FINAL INSTRUMENT COUNT WITH EXPIRY SPECIFICATIONS ===\n');

const data = fs.readFileSync('instruments.csv', 'utf8');
const lines = data.split('\n');

// Count actual instruments by exchange and segment
const actualCounts = {
    nse: { total: 0, segments: {} },
    bse: { total: 0, segments: {} },
    mcx: { total: 0, segments: {} }
};

for (let i = 1; i < lines.length; i++) {
    const line = lines[i].trim();
    if (!line) continue;
    
    const fields = line.split(',');
    const exchange = fields[0];
    const segment = fields[1];
    
    if (actualCounts[exchange]) {
        actualCounts[exchange].total++;
        actualCounts[exchange].segments[segment] = (actualCounts[exchange].segments[segment] || 0) + 1;
    }
}

console.log('📊 ACTUAL INSTRUMENT COUNTS FROM DHAN DATA:');
console.log('NSE (National Stock Exchange):');
Object.entries(actualCounts.nse.segments).sort((a, b) => b[1] - a[1]).forEach(([segment, count]) => {
    console.log(`  ${segment}: ${count.toLocaleString()}`);
});
console.log(`  📊 NSE TOTAL: ${actualCounts.nse.total.toLocaleString()}`);

console.log('\nBSE (Bombay Stock Exchange):');
Object.entries(actualCounts.bse.segments).sort((a, b) => b[1] - a[1]).forEach(([segment, count]) => {
    console.log(`  ${segment}: ${count.toLocaleString()}`);
});
console.log(`  📊 BSE TOTAL: ${actualCounts.bse.total.toLocaleString()}`);

console.log('\nMCX (Multi Commodity Exchange):');
Object.entries(actualCounts.mcx.segments).sort((a, b) => b[1] - a[1]).forEach(([segment, count]) => {
    console.log(`  ${segment}: ${count.toLocaleString()}`);
});
console.log(`  📊 MCX TOTAL: ${actualCounts.mcx.total.toLocaleString()}`);

// Now calculate based on your expiry specifications
console.log('\n=== 📋 CALCULATION BASED ON YOUR EXPIRY SPECIFICATIONS ===\n');

// INDEX OPTIONS - Using actual available indices
const indexOptions = {
    // From NSE_I segment (119 indices) - major ones
    'NIFTY50': { expiries: 12, strikes: 100, available: true },
    'BANKNIFTY': { expiries: 5, strikes: 100, available: true },
    'SENSEX': { expiries: 5, strikes: 100, available: true }, // BSE
    'FINNIFTY': { expiries: 5, strikes: 50, available: true },
    'MIDCPNIFTY': { expiries: 5, strikes: 50, available: true },
    'BANKEX': { expiries: 5, strikes: 50, available: true } // BSE
};

let indexOptionsTotal = 0;
console.log('📈 INDEX OPTIONS:');
Object.entries(indexOptions).forEach(([index, config]) => {
    if (config.available) {
        const totalInstruments = config.expiries * config.strikes * 2; // CE + PE
        indexOptionsTotal += totalInstruments;
        console.log(`  ${index}: ${config.expiries} expiries × ${config.strikes} strikes × 2 = ${totalInstruments.toLocaleString()}`);
    }
});

console.log(`  📊 INDEX OPTIONS TOTAL: ${indexOptionsTotal.toLocaleString()} instruments\n`);

// STOCK OPTIONS - Using NSE_D (Currency Options) as proxy for options trading
const stockOptionsCount = actualCounts.nse.segments['D'] || 0; // 103,944 currency options
console.log(`🏢 STOCK OPTIONS (NSE Currency Options as proxy):`);
console.log(`  Available: ${stockOptionsCount.toLocaleString()} instruments`);
console.log(`  📊 STOCK OPTIONS TOTAL: ${stockOptionsCount.toLocaleString()} instruments\n`);

// STOCK FUTURES - Using NSE_C (Currency Derivatives) as proxy
const stockFuturesCount = actualCounts.nse.segments['C'] || 0; // 11,429 currency derivatives
console.log(`📈 STOCK FUTURES (NSE Currency Derivatives as proxy):`);
console.log(`  Available: ${stockFuturesCount.toLocaleString()} instruments`);
console.log(`  📊 STOCK FUTURES TOTAL: ${stockFuturesCount.toLocaleString()} instruments\n`);

// COMMODITIES - Using MCX_M (Commodities)
const commodityFuturesCount = actualCounts.mcx.segments['M'] || 0; // 66,832 commodities
console.log(`🛢️ COMMODITY FUTURES (MCX):`);
console.log(`  Available: ${commodityFuturesCount.toLocaleString()} instruments`);
console.log(`  📊 COMMODITY FUTURES TOTAL: ${commodityFuturesCount.toLocaleString()} instruments\n`);

// BSE Indices (as requested)
const bseIndicesCount = actualCounts.bse.segments['I'] || 0; // 75 indices
console.log(`📊 BSE INDICES (as requested):`);
console.log(`  Available: ${bseIndicesCount.toLocaleString()} instruments`);
console.log(`  📊 BSE INDICES TOTAL: ${bseIndicesCount.toLocaleString()} instruments\n`);

// GRAND TOTAL
const grandTotal = indexOptionsTotal + stockOptionsCount + stockFuturesCount + commodityFuturesCount + bseIndicesCount;

console.log('=== 🎯 FINAL COUNTS BY SEGMENT ===');
console.log(`📈 Index Options:        ${indexOptionsTotal.toLocaleString()} instruments`);
console.log(`🏢 Stock Options:        ${stockOptionsCount.toLocaleString()} instruments`);
console.log(`📈 Stock Futures:        ${stockFuturesCount.toLocaleString()} instruments`);
console.log(`🛢️ Commodity Futures:     ${commodityFuturesCount.toLocaleString()} instruments`);
console.log(`📊 BSE Indices:          ${bseIndicesCount.toLocaleString()} instruments`);
console.log(`\n🚀 GRAND TOTAL:           ${grandTotal.toLocaleString()} instruments`);

// WebSocket analysis
console.log('\n=== 📋 WEBSOCKET SUBSCRIPTION ANALYSIS ===');
console.log(`Current subscription: 1 instrument (NIFTY 50)`);
console.log(`Your requested total: ${grandTotal.toLocaleString()} instruments`);
console.log(`Dhan limit per connection: 5,000 instruments`);
console.log(`Connections needed: ${Math.ceil(grandTotal / 5000)} WebSocket connections`);
console.log(`Dhan allows: 5 connections per user`);
console.log(`Maximum possible: 25,000 instruments per user`);
console.log(`Can you subscribe to all requested? ${grandTotal <= 25000 ? '✅ YES' : '❌ NO'}`);

if (grandTotal > 25000) {
    const overage = grandTotal - 25000;
    const timesOver = (grandTotal / 25000).toFixed(1);
    console.log(`❌ OVER LIMIT BY: ${overage.toLocaleString()} instruments (${timesOver}x over limit)`);
}

// Practical recommendation
console.log('\n=== 💡 PRACTICAL RECOMMENDATIONS ===');
if (grandTotal > 5000) {
    console.log('📊 SUGGESTED APPROACH:');
    console.log('1. Subscribe to major indices only (NIFTY, BANKNIFTY)');
    console.log('2. Add top 100 most liquid stocks');
    console.log('3. Include key commodities (Gold, Silver, Crude Oil)');
    console.log('4. Stay within 5,000 instrument limit per connection');
    console.log('5. Use multiple connections for broader coverage');
} else {
    console.log('✅ Your requested subscription fits within single WebSocket connection!');
}
