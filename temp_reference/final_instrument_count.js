console.log('=== FINAL INSTRUMENT COUNT BASED ON EXPIRY SPECIFICATIONS ===\n');

// Using data from our previous analysis of the Dhan CSV
const actualSegmentCounts = {
    'NSE_D': 103944,  // Currency Options
    'NSE_M': 33420,   // Miscellaneous  
    'NSE_C': 11429,   // Currency Derivatives
    'NSE_E': 8964,    // Equity
    'NSE_I': 119,     // Indices
    'BSE_D': 43560,   // Currency Options
    'BSE_E': 13365,   // Equity
    'BSE_C': 12733,   // Currency Derivatives
    'BSE_I': 75,      // Indices
    'MCX_M': 66832    // Commodities
};

console.log('📊 ACTUAL INSTRUMENT COUNTS FROM DHAN DATA:');
console.log('NSE Segments:');
console.log(`  D (Currency Options): ${actualSegmentCounts['NSE_D'].toLocaleString()}`);
console.log(`  M (Miscellaneous): ${actualSegmentCounts['NSE_M'].toLocaleString()}`);
console.log(`  C (Currency Derivatives): ${actualSegmentCounts['NSE_C'].toLocaleString()}`);
console.log(`  E (Equity): ${actualSegmentCounts['NSE_E'].toLocaleString()}`);
console.log(`  I (Indices): ${actualSegmentCounts['NSE_I'].toLocaleString()}`);

console.log('\nBSE Segments:');
console.log(`  D (Currency Options): ${actualSegmentCounts['BSE_D'].toLocaleString()}`);
console.log(`  E (Equity): ${actualSegmentCounts['BSE_E'].toLocaleString()}`);
console.log(`  C (Currency Derivatives): ${actualSegmentCounts['BSE_C'].toLocaleString()}`);
console.log(`  I (Indices): ${actualSegmentCounts['BSE_I'].toLocaleString()}`);

console.log('\nMCX Segments:');
console.log(`  M (Commodities): ${actualSegmentCounts['MCX_M'].toLocaleString()}`);

// Calculate based on your expiry specifications
console.log('\n=== 📋 CALCULATION BASED ON YOUR EXPIRY SPECIFICATIONS ===\n');

// INDEX OPTIONS - Based on your specifications
const indexOptions = {
    'NIFTY50': { expiries: 12, strikes: 100 }, // 8 weekly + 4 quarterly
    'BANKNIFTY': { expiries: 5, strikes: 100 }, // current + 4 quarters
    'SENSEX': { expiries: 5, strikes: 100 }, // current + 4 quarters
    'FINNIFTY': { expiries: 5, strikes: 50 }, // current + 4 quarters
    'MIDCPNIFTY': { expiries: 5, strikes: 50 }, // current + 4 quarters
    'BANKEX': { expiries: 5, strikes: 50 } // current + 4 quarters
};

let indexOptionsTotal = 0;
console.log('📈 INDEX OPTIONS:');
Object.entries(indexOptions).forEach(([index, config]) => {
    const totalInstruments = config.expiries * config.strikes * 2; // CE + PE
    indexOptionsTotal += totalInstruments;
    console.log(`  ${index}: ${config.expiries} expiries × ${config.strikes} strikes × 2 = ${totalInstruments.toLocaleString()}`);
});

console.log(`  📊 INDEX OPTIONS TOTAL: ${indexOptionsTotal.toLocaleString()} instruments\n`);

// STOCK OPTIONS - Using actual NSE equity count as proxy
const stockCount = actualSegmentCounts['NSE_E']; // 8,964 equity stocks
const stockOptionsTotal = stockCount * 2 * 25 * 2; // stocks × expiries × strikes × CE/PE
console.log(`🏢 STOCK OPTIONS (NSE Equity Stocks):`);
console.log(`  Available stocks: ${stockCount.toLocaleString()}`);
console.log(`  Calculation: ${stockCount} stocks × 2 expiries × 25 strikes × 2 (CE/PE) = ${stockOptionsTotal.toLocaleString()}`);
console.log(`  📊 STOCK OPTIONS TOTAL: ${stockOptionsTotal.toLocaleString()} instruments\n`);

// STOCK FUTURES
const stockFuturesTotal = stockCount * 2; // stocks × expiries
console.log(`📈 STOCK FUTURES (NSE Equity Stocks):`);
console.log(`  Available stocks: ${stockCount.toLocaleString()}`);
console.log(`  Calculation: ${stockCount} stocks × 2 expiries = ${stockFuturesTotal.toLocaleString()}`);
console.log(`  📊 STOCK FUTURES TOTAL: ${stockFuturesTotal.toLocaleString()} instruments\n`);

// COMMODITY FUTURES - Using actual MCX data
const commodityFuturesTotal = actualSegmentCounts['MCX_M']; // 66,832 commodities
console.log(`🛢️ COMMODITY FUTURES (MCX):`);
console.log(`  Available: ${commodityFuturesTotal.toLocaleString()} instruments`);
console.log(`  📊 COMMODITY FUTURES TOTAL: ${commodityFuturesTotal.toLocaleString()} instruments\n`);

// BSE INDICES - As requested
const bseIndicesTotal = actualSegmentCounts['BSE_I']; // 75 indices
console.log(`📊 BSE INDICES (as requested):`);
console.log(`  Available: ${bseIndicesTotal.toLocaleString()} instruments`);
console.log(`  📊 BSE INDICES TOTAL: ${bseIndicesTotal.toLocaleString()} instruments\n`);

// GRAND TOTAL
const grandTotal = indexOptionsTotal + stockOptionsTotal + stockFuturesTotal + commodityFuturesTotal + bseIndicesTotal;

console.log('=== 🎯 FINAL COUNTS BY SEGMENT ===');
console.log(`📈 Index Options:        ${indexOptionsTotal.toLocaleString()} instruments`);
console.log(`🏢 Stock Options:        ${stockOptionsTotal.toLocaleString()} instruments`);
console.log(`📈 Stock Futures:        ${stockFuturesTotal.toLocaleString()} instruments`);
console.log(`🛢️ Commodity Futures:     ${commodityFuturesTotal.toLocaleString()} instruments`);
console.log(`📊 BSE Indices:          ${bseIndicesTotal.toLocaleString()} instruments`);
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

// Practical breakdown
console.log('\n=== 📊 PRACTICAL SUBSCRIPTION BREAKDOWN ===');
console.log('If you want to stay within 5,000 instruments (single connection):');
console.log('✅ Option 1 - Index Focus:');
console.log(`   All Index Options: ${indexOptionsTotal.toLocaleString()} instruments`);
console.log(`   Remaining capacity: ${(5000 - indexOptionsTotal).toLocaleString()} instruments`);
console.log('');
console.log('✅ Option 2 - Balanced Approach:');
console.log(`   Major Indices (NIFTY, BANKNIFTY): 3,400 instruments`);
console.log(`   Top 100 Stock Options: 5,000 instruments`);
console.log(`   Key Commodities: 1,000 instruments`);
console.log(`   Total: ~9,400 instruments (needs 2 connections)`);
console.log('');
console.log('✅ Option 3 - Full Coverage:');
console.log(`   All requested: ${grandTotal.toLocaleString()} instruments`);
console.log(`   Connections needed: ${Math.ceil(grandTotal / 5000)}`);
console.log(`   Within 5 connection limit: ${grandTotal <= 25000 ? 'YES' : 'NO'}`);
