const fs = require('fs');

console.log('=== DEBUGGING NSE F&O STOCK COUNT ===\n');

const data = fs.readFileSync('instruments.csv', 'utf8');
const lines = data.split('\n');

// Check all NSE segments to find F&O stocks
const segmentCounts = {};
const stockSymbols = new Set();
const equitySymbols = new Set();

for (let i = 1; i < lines.length; i++) {
    const line = lines[i].trim();
    if (!line) continue;
    
    const fields = line.split(',');
    const exchange = fields[0];
    const segment = fields[1];
    const symbol = fields[5];
    const instrumentType = fields[13];
    
    if (exchange === 'NSE') {
        segmentCounts[segment] = (segmentCounts[segment] || 0) + 1;
        
        if (segment === 'EQ') {
            equitySymbols.add(symbol);
        } else if (segment === 'FUT' || segment === 'OPT') {
            const baseSymbol = symbol.split('-')[0];
            stockSymbols.add(baseSymbol);
        }
    }
}

console.log('NSE Segment Counts:');
Object.entries(segmentCounts).sort((a, b) => b[1] - a[1]).forEach(([segment, count]) => {
    console.log(`  ${segment}: ${count.toLocaleString()}`);
});

console.log(`\n📊 NSE Equity Stocks (EQ): ${equitySymbols.size.toLocaleString()}`);
console.log(`📈 NSE F&O Stocks (FUT/OPT): ${stockSymbols.size.toLocaleString()}`);

// Show some examples
console.log('\nSample F&O Stock Symbols:');
Array.from(stockSymbols).slice(0, 10).forEach((symbol, i) => {
    console.log(`  ${i+1}. ${symbol}`);
});

// Now recalculate with correct stock count
const stockCount = stockSymbols.size;

console.log('\n=== 📈 RECALCULATED INSTRUMENT COUNTS ===\n');

// INDEX OPTIONS (same as before)
const indexOptions = {
    nifty50: { expiries: 12, strikes: 100 },
    banknifty: { expiries: 5, strikes: 100 },
    sensex: { expiries: 5, strikes: 100 },
    finnifty: { expiries: 5, strikes: 50 },
    midcpnifty: { expiries: 5, strikes: 50 },
    bankex: { expiries: 5, strikes: 50 }
};

let indexOptionsTotal = 0;
Object.entries(indexOptions).forEach(([index, config]) => {
    const totalInstruments = config.expiries * config.strikes * 2;
    indexOptionsTotal += totalInstruments;
});

console.log(`📈 Index Options: ${indexOptionsTotal.toLocaleString()} instruments`);

// STOCK OPTIONS
const stockOptionsTotal = stockCount * 2 * 25 * 2; // stocks × expiries × strikes × CE/PE
console.log(`🏢 Stock Options: ${stockOptionsTotal.toLocaleString()} instruments (${stockCount} stocks)`);

// STOCK FUTURES  
const stockFuturesTotal = stockCount * 2; // stocks × expiries
console.log(`📈 Stock Futures: ${stockFuturesTotal.toLocaleString()} instruments (${stockCount} stocks)`);

// COMMODITIES (same as before)
const commodityFuturesTotal = 9 * 2; // 9 commodities × 2 expiries
const commodityOptionsTotal = 2 * 2 * 10 * 2; // 2 commodities × 2 expiries × 10 strikes × CE/PE

console.log(`🛢️ Commodity Futures: ${commodityFuturesTotal.toLocaleString()} instruments`);
console.log(`🛢️ Commodity Options: ${commodityOptionsTotal.toLocaleString()} instruments`);

const grandTotal = indexOptionsTotal + stockOptionsTotal + stockFuturesTotal + commodityFuturesTotal + commodityOptionsTotal;

console.log(`\n🚀 GRAND TOTAL: ${grandTotal.toLocaleString()} instruments`);

// WebSocket analysis
console.log('\n=== 📋 WEBSOCKET SUBSCRIPTION ANALYSIS ===');
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
