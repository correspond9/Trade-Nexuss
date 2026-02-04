console.log('=== FUTURES INSTRUMENT COUNTING METHODOLOGY ===\n');

// Using actual Dhan data
const actualSegmentCounts = {
    'NSE_E': 8964,    // Equity stocks
    'MCX_M': 66832    // Commodities
};

console.log('📊 HOW FUTURES ARE COUNTED:\n');

// STOCK FUTURES COUNTING
console.log('📈 STOCK FUTURES (NSE):');
console.log('🔍 COUNTING BASIS:');
console.log('   • Base: All NSE Equity stocks (NSE_E segment)');
console.log(`   • Available stocks: ${actualSegmentCounts['NSE_E'].toLocaleString()}`);
console.log('   • Each stock = 1 underlying asset');
console.log('');
console.log('📅 EXPIRY MULTIPLIER:');
console.log('   • Your specification: "Current + next monthly"');
console.log('   • Expiries per stock: 2');
console.log('   • Total futures per stock: 2 (current month + next month)');
console.log('');
const stockFuturesTotal = actualSegmentCounts['NSE_E'] * 2;
console.log('🧮 CALCULATION:');
console.log(`   ${actualSegmentCounts['NSE_E'].toLocaleString()} stocks × 2 expiries = ${stockFuturesTotal.toLocaleString()} futures contracts`);
console.log('');
console.log('💡 EXAMPLES:');
console.log('   • RELIANCE: RELIANCE-Jan2026-FUT, RELIANCE-Feb2026-FUT (2 instruments)');
console.log('   • TCS: TCS-Jan2026-FUT, TCS-Feb2026-FUT (2 instruments)');
console.log('   • INFY: INFY-Jan2026-FUT, INFY-Feb2026-FUT (2 instruments)');
console.log(`   📊 STOCK FUTURES TOTAL: ${stockFuturesTotal.toLocaleString()} instruments\n`);

// COMMODITY FUTURES COUNTING
console.log('🛢️ COMMODITY FUTURES (MCX):');
console.log('🔍 COUNTING BASIS:');
console.log('   • Base: All MCX commodity instruments (MCX_M segment)');
console.log(`   • Available instruments: ${actualSegmentCounts['MCX_M'].toLocaleString()}`);
console.log('   • Each instrument already includes different expiries');
console.log('');
console.log('📅 WHAT MCX_M INCLUDES:');
console.log('   • Gold futures: GOLD-Jan2026-FUT, GOLD-Feb2026-FUT, etc.');
console.log('   • Silver futures: SILVER-Jan2026-FUT, SILVER-Feb2026-FUT, etc.');
console.log('   • Crude Oil futures: CRUDEOIL-Jan2026-FUT, CRUDEOIL-Feb2026-FUT, etc.');
console.log('   • Mini contracts: GOLDM, SILVERM, etc.');
console.log('   • All commodity variants with all available expiries');
console.log('');
const commodityFuturesTotal = actualSegmentCounts['MCX_M'];
console.log('🧮 CALCULATION:');
console.log(`   Direct count from MCX_M segment: ${commodityFuturesTotal.toLocaleString()} instruments`);
console.log('   (Each instrument already represents a specific commodity + expiry combination)');
console.log('');
console.log('💡 EXAMPLES:');
console.log('   • GOLD-05Feb2026-FUT (1 instrument)');
console.log('   • GOLD-27Jan2026-FUT (1 instrument)');
console.log('   • SILVER-05Feb2026-FUT (1 instrument)');
console.log('   • CRUDEOIL-27Jan2026-FUT (1 instrument)');
console.log('   • NATURALGAS-05Feb2026-FUT (1 instrument)');
console.log('   • GOLDM-05Feb2026-FUT (Gold Mini) (1 instrument)');
console.log(`   📊 COMMODITY FUTURES TOTAL: ${commodityFuturesTotal.toLocaleString()} instruments\n`);

// COMPARISON WITH OPTIONS COUNTING
console.log('🔄 COMPARISON: FUTURES vs OPTIONS COUNTING:');
console.log('');
console.log('📈 OPTIONS COUNTING:');
console.log('   • Each strike = 2 instruments (CE + PE)');
console.log('   • Multiple strikes per underlying');
console.log('   • Example: NIFTY 100 strikes × 2 = 200 instruments');
console.log('');
console.log('📊 FUTURES COUNTING:');
console.log('   • Each underlying = 1 instrument per expiry');
console.log('   • No strike prices (single price per expiry)');
console.log('   • Example: RELIANCE 2 expiries = 2 instruments');
console.log('');
console.log('🎯 KEY DIFFERENCE:');
console.log('   • Options: Strike-based multiplication (× strikes × 2)');
console.log('   • Futures: Expiry-based multiplication (× expiries only)');

// TOTAL FUTURES BREAKDOWN
const totalFutures = stockFuturesTotal + commodityFuturesTotal;
console.log(`\n🚀 TOTAL FUTURES INSTRUMENTS: ${totalFutures.toLocaleString()}`);
console.log('   📈 Stock Futures: 17,928 instruments');
console.log('   🛢️ Commodity Futures: 66,832 instruments');
console.log(`   📊 Percentage: ${((stockFuturesTotal/totalFutures)*100).toFixed(1)}% Stock, ${((commodityFuturesTotal/totalFutures)*100).toFixed(1)}% Commodities`);

console.log('\n=== 📋 COUNTING BASES SUMMARY ===');
console.log('📈 STOCK FUTURES:');
console.log('   Base: NSE Equity stocks (NSE_E)');
console.log('   Multiplier: Number of expiries (2)');
console.log('   Logic: Stock × Expiry = Individual futures contract');
console.log('');
console.log('🛢️ COMMODITY FUTURES:');
console.log('   Base: MCX commodity instruments (MCX_M)');
console.log('   Multiplier: None (already includes expiries)');
console.log('   Logic: Direct count of all commodity + expiry combinations');
console.log('');
console.log('💡 ACCURACY NOTES:');
console.log('   • Stock futures: Theoretical maximum based on available stocks');
console.log('   • Commodity futures: Actual available instruments from Dhan');
console.log('   • Not all stocks may have active futures contracts');
console.log('   • Some instruments may be delisted or inactive');
