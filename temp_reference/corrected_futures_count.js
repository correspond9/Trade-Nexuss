console.log('=== CORRECTED FUTURES COUNTING WITH ACTUAL NSE F&O DATA ===\n');

// CORRECTED DATA
const actualNSEFoStocks = 227; // CORRECT: Actual NSE F&O securities
const mcxCommodities = 66832; // From MCX_M segment

console.log('📊 CORRECTED COUNTING BASES:');
console.log(`📈 NSE F&O Stocks: ${actualNSEFoStocks} securities (NOT 8,964!)`);
console.log(`🛢️ MCX Commodities: ${mcxCommodities.toLocaleString()} instruments\n`);

// CORRECTED STOCK FUTURES COUNTING
console.log('📈 STOCK FUTURES (NSE F&O - CORRECTED):');
console.log('🔍 CORRECTED COUNTING BASIS:');
console.log('   • Base: Actual NSE F&O segment securities');
console.log(`   • Available stocks: ${actualNSEFoStocks} (NOT all NSE equity stocks)`);
console.log('   • Each stock = 1 underlying asset in F&O segment');
console.log('');
console.log('📅 EXPIRY MULTIPLIER:');
console.log('   • Your specification: "Current + next monthly"');
console.log('   • Expiries per stock: 2');
console.log('   • Total futures per stock: 2 (current month + next month)');
console.log('');
const correctedStockFuturesTotal = actualNSEFoStocks * 2;
console.log('🧮 CORRECTED CALCULATION:');
console.log(`   ${actualNSEFoStocks} F&O stocks × 2 expiries = ${correctedStockFuturesTotal} futures contracts`);
console.log('');
console.log('💡 EXAMPLES (Actual F&O Stocks):');
console.log('   • RELIANCE: RELIANCE-Jan2026-FUT, RELIANCE-Feb2026-FUT (2 instruments)');
console.log('   • TCS: TCS-Jan2026-FUT, TCS-Feb2026-FUT (2 instruments)');
console.log('   • INFY: INFY-Jan2026-FUT, INFY-Feb2026-FUT (2 instruments)');
console.log('   • ... and 224 more F&O stocks');
console.log(`   📊 CORRECTED STOCK FUTURES TOTAL: ${correctedStockFuturesTotal} instruments\n`);

// COMMODITY FUTURES (unchanged)
console.log('🛢️ COMMODITY FUTURES (MCX - Unchanged):');
console.log(`   📊 COMMODITY FUTURES TOTAL: ${mcxCommodities.toLocaleString()} instruments\n`);

// RECALCULATE TOTALS WITH CORRECTED NUMBERS
console.log('=== 🎯 RECALCULATED TOTALS ===');

// INDEX OPTIONS (unchanged)
const indexOptionsTotal = 5600;
console.log(`📈 Index Options: ${indexOptionsTotal.toLocaleString()} instruments`);

// STOCK OPTIONS (unchanged - top 100 liquid)
const stockOptionsTotal = 10000;
console.log(`🏢 Stock Options (Top 100): ${stockOptionsTotal.toLocaleString()} instruments`);

// CORRECTED STOCK FUTURES
console.log(`📈 Stock Futures (CORRECTED): ${correctedStockFuturesTotal.toLocaleString()} instruments`);

// COMMODITY FUTURES (unchanged)
console.log(`🛢️ Commodity Futures: ${mcxCommodities.toLocaleString()} instruments`);

// COMMODITY OPTIONS (unchanged)
const commodityOptionsTotal = 80;
console.log(`🛢️ Commodity Options: ${commodityOptionsTotal.toLocaleString()} instruments`);

// BSE INDICES (unchanged)
const bseIndicesTotal = 75;
console.log(`📊 BSE Indices: ${bseIndicesTotal.toLocaleString()} instruments`);

// NEW GRAND TOTAL
const correctedGrandTotal = indexOptionsTotal + stockOptionsTotal + correctedStockFuturesTotal + mcxCommodities + commodityOptionsTotal + bseIndicesTotal;

console.log(`\n🚀 CORRECTED GRAND TOTAL: ${correctedGrandTotal.toLocaleString()} instruments`);

// WebSocket analysis with corrected numbers
console.log('\n=== 📋 CORRECTED WEBSOCKET ANALYSIS ===');
console.log(`Current subscription: 1 instrument (NIFTY 50)`);
console.log(`Corrected requested total: ${correctedGrandTotal.toLocaleString()} instruments`);
console.log(`Dhan limit per connection: 5,000 instruments`);
console.log(`Connections needed: ${Math.ceil(correctedGrandTotal / 5000)} WebSocket connections`);
console.log(`Dhan allows: 5 connections per user`);
console.log(`Maximum possible: 25,000 instruments per user`);
console.log(`Can you subscribe to all requested? ${correctedGrandTotal <= 25000 ? '✅ YES' : '❌ NO'}`);

if (correctedGrandTotal > 25000) {
    const overage = correctedGrandTotal - 25000;
    const timesOver = (correctedGrandTotal / 25000).toFixed(1);
    console.log(`❌ OVER LIMIT BY: ${overage.toLocaleString()} instruments (${timesOver}x over limit)`);
} else {
    console.log(`✅ WITHIN LIMIT! Remaining capacity: ${(25000 - correctedGrandTotal).toLocaleString()} instruments`);
}

// Comparison with previous incorrect calculation
const previousTotal = 100515;
const reduction = previousTotal - correctedGrandTotal;
const reductionPercent = ((reduction / previousTotal) * 100).toFixed(1);

console.log('\n=== 📊 CORRECTION IMPACT ===');
console.log(`Previous (incorrect) total: ${previousTotal.toLocaleString()} instruments`);
console.log(`Corrected total: ${correctedGrandTotal.toLocaleString()} instruments`);
console.log(`🎉 REDUCTION: ${reduction.toLocaleString()} instruments (${reductionPercent}% less)`);

console.log('\n=== 📊 SEGMENT BREAKDOWN COMPARISON ===');
console.log('STOCK FUTURES:');
console.log(`   Previous (wrong): 17,928 instruments`);
console.log(`   Corrected: ${correctedStockFuturesTotal.toLocaleString()} instruments`);
console.log(`   Error: Used all NSE equity (${8964}) instead of F&O (${actualNSEFoStocks})`);
console.log('');
console.log('TOTAL IMPACT:');
console.log(`   Previous total: ${previousTotal.toLocaleString()}`);
console.log(`   Corrected total: ${correctedGrandTotal.toLocaleString()}`);
console.log(`   Much more realistic and achievable!`);

// Practical feasibility analysis
console.log('\n=== 💡 PRACTICAL FEASIBILITY ===');
if (correctedGrandTotal <= 25000) {
    console.log('✅ EXCELLENT! Your corrected subscription now fits within Dhan limits!');
    console.log(`📈 Connections needed: ${Math.ceil(correctedGrandTotal / 5000)}`);
    
    const connections = Math.ceil(correctedGrandTotal / 5000);
    let remaining = correctedGrandTotal;
    
    console.log('📊 Per connection distribution:');
    for (let i = 1; i <= connections; i++) {
        const connectionInstruments = Math.min(5000, remaining);
        console.log(`   Connection ${i}: ${connectionInstruments.toLocaleString()} instruments`);
        remaining -= connectionInstruments;
    }
} else {
    console.log('📊 Still need some optimization, but much more manageable now!');
}
