const fs = require('fs');
const csv = require('csv-parser');

const results = {
    nse_eq: 0,
    nse_fo: 0,
    bse_eq: 0,
    bse_fo: 0,
    mcx_com: 0,
    mcx_fo: 0,
    msx_fo: 0,
    total: 0,
    nse_indices: 0,
    bse_indices: 0
};

fs.createReadStream('instruments.csv')
    .pipe(csv())
    .on('data', (data) => {
        const exchange = data['SEM_EXM_EXCH_ID'];
        const segment = data['SEM_SEGMENT'];
        const instrumentType = data['SEM_EXCH_INSTRUMENT_TYPE'];
        
        results.total++;
        
        // NSE
        if (exchange === 'NSE') {
            if (segment === 'EQ') {
                results.nse_eq++;
            } else if (segment === 'FO' || segment === 'FUT' || segment === 'OPT') {
                results.nse_fo++;
            } else if (instrumentType === 'INDEX') {
                results.nse_indices++;
            }
        }
        
        // BSE
        if (exchange === 'BSE') {
            if (segment === 'EQ') {
                results.bse_eq++;
            } else if (segment === 'FO' || segment === 'FUT' || segment === 'OPT') {
                results.bse_fo++;
            } else if (instrumentType === 'INDEX') {
                results.bse_indices++;
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
    })
    .on('end', () => {
        console.log('=== Dhan Instrument Counts ===');
        console.log('NSE Equity (EQ):', results.nse_eq);
        console.log('NSE Futures & Options (FO):', results.nse_fo);
        console.log('NSE Indices:', results.nse_indices);
        console.log('BSE Equity (EQ):', results.bse_eq);
        console.log('BSE Futures & Options (FO):', results.bse_fo);
        console.log('BSE Indices:', results.bse_indices);
        console.log('MCX Commodities (COM):', results.mcx_com);
        console.log('MCX Futures & Options (FO):', results.mcx_fo);
        console.log('MSX Futures & Options (FO):', results.msx_fo);
        console.log('Total Instruments:', results.total);
        
        // Calculate totals for requested categories
        const nseTotal = results.nse_eq + results.nse_fo + results.nse_indices;
        const bseTotal = results.bse_eq + results.bse_fo + results.bse_indices;
        const mcxTotal = results.mcx_com + results.mcx_fo;
        const msxTotal = results.msx_fo;
        
        console.log('\n=== Requested Totals ===');
        console.log('NSE (All Equity, Futures, Options, Indexes):', nseTotal);
        console.log('BSE (All Equity, Futures, Options, Indexes):', bseTotal);
        console.log('MCX (All Commodities, Futures, Options):', mcxTotal);
        console.log('MSX (All Futures, Options):', msxTotal);
        console.log('Grand Total (All requested):', nseTotal + bseTotal + mcxTotal + msxTotal);
    });
