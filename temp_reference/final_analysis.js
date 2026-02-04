const fs = require('fs');

const results = {
    // NSE - All requested categories
    nse_equity: 0,        // NSE_E
    nse_currency: 0,       // NSE_C  
    nse_derivatives: 0,    // NSE_D (Currency Options)
    nse_misc: 0,          // NSE_M (Miscellaneous)
    nse_indices: 0,        // NSE_I (Indices)
    
    // BSE - Only Indices requested
    bse_equity: 0,         // BSE_E
    bse_currency: 0,       // BSE_C
    bse_derivatives: 0,    // BSE_D (Currency Options)
    bse_indices: 0,        // BSE_I (Indices)
    
    // MCX - Commodities requested
    mcx_commodities: 0,    // MCX_M (Commodities)
    
    // MSX - Futures & Options requested
    msx_instruments: 0,    // (No MSX found in data)
    
    total: 0
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
    const symbol = fields[5];
    
    results.total++;
    
    // NSE - All categories
    if (exchange === 'NSE') {
        if (segment === 'E') results.nse_equity++;           // Equity
        else if (segment === 'C') results.nse_currency++;     // Currency
        else if (segment === 'D') results.nse_derivatives++; // Derivatives (Currency Options)
        else if (segment === 'M') results.nse_misc++;         // Miscellaneous
        else if (segment === 'I') results.nse_indices++;     // Indices
    }
    
    // BSE - All categories (but user only wants indices)
    if (exchange === 'BSE') {
        if (segment === 'E') results.bse_equity++;           // Equity
        else if (segment === 'C') results.bse_currency++;     // Currency
        else if (segment === 'D') results.bse_derivatives++; // Derivatives (Currency Options)
        else if (segment === 'I') results.bse_indices++;     // Indices
    }
    
    // MCX - Commodities
    if (exchange === 'MCX') {
        if (segment === 'M') results.mcx_commodities++;      // Commodities
    }
    
    // MSX - Check if any exist
    if (exchange === 'MSX') {
        results.msx_instruments++;
    }
}

console.log('=== COMPREHENSIVE DHAN INSTRUMENT ANALYSIS ===\n');

console.log('📈 NSE (National Stock Exchange) - ALL CATEGORIES');
console.log('   Equity (NSE_E):', results.nse_equity.toLocaleString());
console.log('   Currency Derivatives (NSE_C):', results.nse_currency.toLocaleString());
console.log('   Currency Options (NSE_D):', results.nse_derivatives.toLocaleString());
console.log('   Miscellaneous (NSE_M):', results.nse_misc.toLocaleString());
console.log('   Indices (NSE_I):', results.nse_indices.toLocaleString());
const nseTotal = results.nse_equity + results.nse_currency + results.nse_derivatives + results.nse_misc + results.nse_indices;
console.log('   📊 NSE TOTAL:', nseTotal.toLocaleString());

console.log('\n📊 BSE (Bombay Stock Exchange) - INDICES ONLY (as requested)');
console.log('   Equity (BSE_E):', results.bse_equity.toLocaleString(), '(Available but not requested)');
console.log('   Currency Derivatives (BSE_C):', results.bse_currency.toLocaleString(), '(Available but not requested)');
console.log('   Currency Options (BSE_D):', results.bse_derivatives.toLocaleString(), '(Available but not requested)');
console.log('   Indices (BSE_I):', results.bse_indices.toLocaleString(), '✅ REQUESTED');
const bseTotal = results.bse_indices;
console.log('   📊 BSE TOTAL (Requested):', bseTotal.toLocaleString());

console.log('\n🛢️  MCX (Multi Commodity Exchange) - COMMODITIES');
console.log('   Commodities (MCX_M):', results.mcx_commodities.toLocaleString(), '✅ REQUESTED');
const mcxTotal = results.mcx_commodities;
console.log('   📊 MCX TOTAL:', mcxTotal.toLocaleString());

console.log('\n🌍 MSX (Metropolitan Stock Exchange)');
console.log('   Instruments found:', results.msx_instruments.toLocaleString());
console.log('   📊 MSX TOTAL:', results.msx_instruments.toLocaleString(), '(✅ REQUESTED)');

console.log('\n=== 🎯 FINAL COUNTS FOR YOUR REQUEST ===');
console.log('NSE (All Equity, Futures, Options, Indexes):', nseTotal.toLocaleString());
console.log('BSE (Indices Only):', bseTotal.toLocaleString());
console.log('MCX (All Commodities):', mcxTotal.toLocaleString());
console.log('MSX (All Futures & Options):', results.msx_instruments.toLocaleString());

const grandTotal = nseTotal + bseTotal + mcxTotal + results.msx_instruments;
console.log('🚀 GRAND TOTAL (All Requested):', grandTotal.toLocaleString());

console.log('\n=== 📋 SUBSCRIPTION ANALYSIS ===');
console.log('Current WebSocket subscription: 1 instrument (NIFTY 50)');
console.log('Dhan WebSocket limit: 5,000 instruments per connection');
console.log('Your requested total:', grandTotal.toLocaleString(), 'instruments');
console.log('Connections needed for all requested:', Math.ceil(grandTotal / 5000), 'WebSocket connections');
console.log('Dhan allows: 5 connections per user');
console.log('Can you subscribe to all requested?', grandTotal <= 25000 ? '✅ YES' : '❌ NO');

// Show specific commodity examples
console.log('\n=== 🛢️  COMMODITY EXAMPLES (MCX) ===');
const commodityExamples = [];
for (let i = 1; i < lines.length; i++) {
    const line = lines[i].trim();
    if (!line) continue;
    
    const fields = line.split(',');
    const exchange = fields[0];
    const segment = fields[1];
    const symbol = fields[5];
    
    if (exchange === 'MCX' && segment === 'M' && commodityExamples.length < 10) {
        if (symbol.includes('GOLD') || symbol.includes('SILVER') || symbol.includes('COPPER') || 
            symbol.includes('CRUDE') || symbol.includes('NATURAL') || symbol.includes('GOLDM') || 
            symbol.includes('GOLDMini')) {
            commodityExamples.push(symbol);
        }
    }
}

commodityExamples.forEach((symbol, i) => {
    console.log(`   ${i+1}. ${symbol}`);
});

console.log('\n=== 💰 COST IMPLICATIONS ===');
console.log('Current subscription: 1 instrument');
console.log('If subscribing to all requested:', grandTotal.toLocaleString(), 'instruments');
console.log('WebSocket connections needed:', Math.ceil(grandTotal / 5000));
console.log('Rate limiting considerations: Higher instrument count = more data processing');
