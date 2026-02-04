// Calculate total instruments based on expiry specifications

console.log('=== INSTRUMENT COUNT CALCULATION BASED ON EXPIRY SPECIFICATIONS ===\n');

// INDEX OPTIONS
const indexOptions = {
    nifty50: {
        expiries: 8 + 4, // 8 weekly + 4 quarterly
        strikes: 100,
        description: 'NIFTY50 - Latest 8 weekly + next 4 quarterly (100 strikes)'
    },
    banknifty: {
        expiries: 1 + 4, // current monthly + next 4 quarters
        strikes: 100,
        description: 'BANKNIFTY - Current monthly + next 4 quarters (100 strikes)'
    },
    sensex: {
        expiries: 1 + 4, // current monthly + next 4 quarters
        strikes: 100,
        description: 'SENSEX - Current monthly + next 4 quarters (100 strikes)'
    },
    finnifty: {
        expiries: 1 + 4, // current monthly + next 4 quarters
        strikes: 50,
        description: 'FINNIFTY - Current monthly + next 4 quarters (50 strikes)'
    },
    midcpnifty: {
        expiries: 1 + 4, // current monthly + next 4 quarters
        strikes: 50,
        description: 'MIDCPNIFTY - Current monthly + next 4 quarters (50 strikes)'
    },
    bankex: {
        expiries: 1 + 4, // current monthly + next 4 quarters
        strikes: 50,
        description: 'BANKEX - Current monthly + next 4 quarters (50 strikes)'
    }
};

// STOCK OPTIONS (NSE F&O)
// Need to get actual count from our CSV data
const stockOptions = {
    expiries: 2, // current + next monthly
    strikes: 25,
    description: 'NSE F&O Stocks - Current + next monthly (25 strikes)'
};

// STOCK FUTURES (NSE F&O)
const stockFutures = {
    expiries: 2, // current + next monthly
    description: 'NSE F&O Stocks - Current + next monthly'
};

// COMMODITIES FUTURES
const commodityFutures = {
    commodities: ['NATURALGAS', 'CRUDEOIL', 'COPPER', 'Silver', 'SilverM', 'SilverMini', 'Gold', 'GoldM', 'GoldMini'],
    expiries: 2, // current + next monthly
    description: 'Commodities - Current + next monthly futures'
};

// COMMODITIES OPTIONS
const commodityOptions = {
    commodities: ['NaturalGas', 'CrudeOil'],
    expiries: 2, // current + next monthly
    strikes: 10,
    description: 'Commodities Options - Current + next monthly (10 strikes)'
};

console.log('📈 INDEX OPTIONS:');
let indexOptionsTotal = 0;
Object.entries(indexOptions).forEach(([index, config]) => {
    const totalInstruments = config.expiries * config.strikes * 2; // 2 for CE/PE
    indexOptionsTotal += totalInstruments;
    console.log(`  ${config.description}`);
    console.log(`    Expiries: ${config.expiries}, Strikes: ${config.strikes}, Instruments: ${totalInstruments.toLocaleString()}`);
});

console.log(`\n📊 INDEX OPTIONS TOTAL: ${indexOptionsTotal.toLocaleString()} instruments\n`);

// Count actual NSE F&O stocks from CSV
const fs = require('fs');
const data = fs.readFileSync('instruments.csv', 'utf8');
const lines = data.split('\n');

const nseFoStocks = new Set();
for (let i = 1; i < lines.length; i++) {
    const line = lines[i].trim();
    if (!line) continue;
    
    const fields = line.split(',');
    const exchange = fields[0];
    const segment = fields[1];
    const symbol = fields[5];
    
    if (exchange === 'NSE' && (segment === 'EQ' || segment === 'FUT' || segment === 'OPT')) {
        // Extract base symbol (remove expiry and strike info)
        const baseSymbol = symbol.split('-')[0];
        nseFoStocks.add(baseSymbol);
    }
}

const stockCount = nseFoStocks.size;
console.log(`🏢 STOCK OPTIONS (NSE F&O):`);
console.log(`  Found ${stockCount} stocks in NSE F&O list`);
const stockOptionsTotal = stockCount * stockOptions.expiries * stockOptions.strikes * 2;
console.log(`  ${stockOptions.description}`);
console.log(`  Stocks: ${stockCount}, Expiries: ${stockOptions.expiries}, Strikes: ${stockOptions.strikes}`);
console.log(`  📊 STOCK OPTIONS TOTAL: ${stockOptionsTotal.toLocaleString()} instruments\n`);

console.log(`📈 STOCK FUTURES (NSE F&O):`);
const stockFuturesTotal = stockCount * stockFutures.expiries;
console.log(`  ${stockFutures.description}`);
console.log(`  Stocks: ${stockCount}, Expiries: ${stockFutures.expiries}`);
console.log(`  📊 STOCK FUTURES TOTAL: ${stockFuturesTotal.toLocaleString()} instruments\n`);

console.log(`🛢️ COMMODITY FUTURES:`);
const commodityFuturesTotal = commodityFutures.commodities.length * commodityFutures.expiries;
console.log(`  ${commodityFutures.description}`);
console.log(`  Commodities: ${commodityFutures.commodities.length}, Expiries: ${commodityFutures.expiries}`);
console.log(`  📊 COMMODITY FUTURES TOTAL: ${commodityFuturesTotal.toLocaleString()} instruments\n`);

console.log(`🛢️ COMMODITY OPTIONS:`);
const commodityOptionsTotal = commodityOptions.commodities.length * commodityOptions.expiries * commodityOptions.strikes * 2;
console.log(`  ${commodityOptions.description}`);
console.log(`  Commodities: ${commodityOptions.commodities.length}, Expiries: ${commodityOptions.expiries}, Strikes: ${commodityOptions.strikes}`);
console.log(`  📊 COMMODITY OPTIONS TOTAL: ${commodityOptionsTotal.toLocaleString()} instruments\n`);

// GRAND TOTALS
const grandTotal = indexOptionsTotal + stockOptionsTotal + stockFuturesTotal + commodityFuturesTotal + commodityOptionsTotal;

console.log('=== 🎯 FINAL COUNTS BY SEGMENT ===');
console.log(`📈 Index Options:        ${indexOptionsTotal.toLocaleString()} instruments`);
console.log(`🏢 Stock Options:        ${stockOptionsTotal.toLocaleString()} instruments`);
console.log(`📈 Stock Futures:        ${stockFuturesTotal.toLocaleString()} instruments`);
console.log(`🛢️ Commodity Futures:     ${commodityFuturesTotal.toLocaleString()} instruments`);
console.log(`🛢️ Commodity Options:     ${commodityOptionsTotal.toLocaleString()} instruments`);
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
