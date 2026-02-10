import React, { useEffect, useState } from 'react';
import OrderModal from '../components/OrderModal';
import { apiService } from '../services/apiService';

const MCX_OPTIONS = [
  { key: 'CRUDEOIL', label: 'CRUDEOIL' },
  { key: 'NATURALGAS', label: 'NATURALGAS' },
];

const MCX_FUTURES = [
  'CRUDEOIL',
  'NATURALGAS',
  'COPPER',
  'GOLD',
  'GOLDM',
  'SILVER',
  'SILVERM',
  'SILVERMIC',
  'ALUMINIUM',
];

const formatExpiry = (dateStr) => {
  const date = new Date(dateStr);
  if (Number.isNaN(date.getTime())) return dateStr;
  const day = date.getDate();
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  return `${day} ${months[date.getMonth()]}`;
};

const OptionChainTable = ({ chain, onOpenOrder }) => {
  const strikes = chain?.strikes || {};
  const strikeList = Object.keys(strikes)
    .map((k) => parseFloat(k))
    .sort((a, b) => a - b)
    .slice(0, 50);

  if (!strikeList.length) {
    return (
      <div className="text-sm text-gray-500 py-6 text-center">No option chain data available.</div>
    );
  }

  return (
    <div className="divide-y divide-gray-100">
      {strikeList.map((strike) => {
        const row = strikes[strike];
        const ce = row?.CE || {};
        const pe = row?.PE || {};
        return (
          <div key={strike} className="grid grid-cols-5 gap-2 items-center py-2 text-xs">
            <div className="text-right font-semibold text-gray-700">{ce?.ltp?.toFixed?.(2) ?? ce?.ltp ?? '—'}</div>
            <div className="flex justify-end gap-1">
              <button
                onClick={() => onOpenOrder({ symbol: `${chain.underlying} ${strike} CE`, action: 'BUY', ltp: ce?.ltp, lotSize: chain.lot_size, expiry: chain.expiry })}
                className="px-2 py-1 rounded bg-blue-600 text-white"
              >
                B
              </button>
              <button
                onClick={() => onOpenOrder({ symbol: `${chain.underlying} ${strike} CE`, action: 'SELL', ltp: ce?.ltp, lotSize: chain.lot_size, expiry: chain.expiry })}
                className="px-2 py-1 rounded bg-red-600 text-white"
              >
                S
              </button>
            </div>
            <div className="text-center font-bold text-gray-900">{strike}</div>
            <div className="flex justify-start gap-1">
              <button
                onClick={() => onOpenOrder({ symbol: `${chain.underlying} ${strike} PE`, action: 'BUY', ltp: pe?.ltp, lotSize: chain.lot_size, expiry: chain.expiry })}
                className="px-2 py-1 rounded bg-blue-600 text-white"
              >
                B
              </button>
              <button
                onClick={() => onOpenOrder({ symbol: `${chain.underlying} ${strike} PE`, action: 'SELL', ltp: pe?.ltp, lotSize: chain.lot_size, expiry: chain.expiry })}
                className="px-2 py-1 rounded bg-red-600 text-white"
              >
                S
              </button>
            </div>
            <div className="text-left font-semibold text-gray-700">{pe?.ltp?.toFixed?.(2) ?? pe?.ltp ?? '—'}</div>
          </div>
        );
      })}
    </div>
  );
};

const FuturesList = ({ rows }) => (
  <div className="divide-y divide-gray-100">
    {rows.map((row) => (
      <div key={row.symbol} className="flex items-center justify-between py-2 text-sm">
        <div className="font-semibold text-gray-800">{row.symbol}</div>
        <div className="text-xs text-gray-500">{row.expiry}</div>
        <div className="font-semibold text-gray-700">{row.ltp?.toFixed?.(2) ?? row.ltp ?? '—'}</div>
      </div>
    ))}
  </div>
);

const Commodities = () => {
  const [chains, setChains] = useState({});
  const [expiries, setExpiries] = useState({});
  const [activeTabs, setActiveTabs] = useState({});
  const [futuresTabs, setFuturesTabs] = useState('current');
  const [futures, setFutures] = useState([]);
  const [modalOpen, setModalOpen] = useState(false);
  const [modalOrderData, setModalOrderData] = useState(null);
  const [modalOrderType, setModalOrderType] = useState('BUY');

  const displayFuturesExpiry = futures.find((row) => row.expiry && row.expiry !== '—')?.expiry;

  const loadExpiries = async (symbol) => {
    try {
      const data = await apiService.get('/commodities/expiries', { underlying: symbol });
      const list = Array.isArray(data?.data) ? data.data : [];
      return list.slice(0, 2);
    } catch (err) {
      return [];
    }
  };

  const loadChain = async (symbol, expiry) => {
    try {
      const data = await apiService.get('/commodities/options', { underlying: symbol, expiry });
      return data?.data || null;
    } catch (err) {
      return null;
    }
  };

  const loadFutures = async (tab) => {
    try {
      const data = await apiService.get('/commodities/futures', { tab });
      const list = Array.isArray(data?.data) ? data.data : [];
      const bySymbol = new Map(list.map((row) => [row.symbol, row]));
      const rows = MCX_FUTURES.map((symbol) => bySymbol.get(symbol) || { symbol, expiry: '—', ltp: null });
      setFutures(rows);
    } catch (err) {
      setFutures(MCX_FUTURES.map((symbol) => ({ symbol, expiry: '—', ltp: null })));
    }
  };

  useEffect(() => {
    (async () => {
      const expiryMap = {};
      const tabMap = {};
      for (const item of MCX_OPTIONS) {
        const list = await loadExpiries(item.key);
        expiryMap[item.key] = list;
        tabMap[item.key] = list[0] || null;
      }
      setExpiries(expiryMap);
      setActiveTabs(tabMap);
    })();
  }, []);

  useEffect(() => {
    MCX_OPTIONS.forEach(async (item) => {
      const expiry = activeTabs[item.key];
      if (!expiry) return;
      const chain = await loadChain(item.key, expiry);
      setChains((prev) => ({ ...prev, [`${item.key}_${expiry}`]: chain }));
    });
  }, [activeTabs]);

  useEffect(() => {
    loadFutures(futuresTabs);
  }, [futuresTabs]);

  const handleOpenOrderModal = (leg) => {
    setModalOrderData({
      symbol: leg.symbol,
      action: leg.action,
      ltp: leg.ltp,
      lotSize: leg.lotSize,
      expiry: leg.expiry,
      exchange_segment: 'MCX_COM',
      legs: null,
    });
    setModalOrderType(leg.action || 'BUY');
    setModalOpen(true);
  };

  const handleCloseModal = () => {
    setModalOpen(false);
    setModalOrderData(null);
  };

  return (
    <div className="p-4 space-y-6">
      <div className="bg-white border border-gray-200 rounded-lg">
        <div className="border-b border-gray-200 px-4 py-3 font-semibold">Commodities</div>
        <div className="p-4 grid grid-cols-1 lg:grid-cols-3 gap-4">
          {MCX_OPTIONS.map((item) => {
            const exps = expiries[item.key] || [];
            const activeExpiry = activeTabs[item.key];
            const chainKey = activeExpiry ? `${item.key}_${activeExpiry}` : null;
            const chain = chainKey ? chains[chainKey] : null;

            return (
              <div key={item.key} className="border rounded-lg">
                <div className="flex items-center justify-between px-3 py-2 border-b bg-gray-50">
                  <div className="font-semibold text-sm">{item.label} Options</div>
                  <div className="flex gap-2">
                    {exps.map((exp, idx) => (
                      <button
                        key={exp}
                        onClick={() => setActiveTabs((prev) => ({ ...prev, [item.key]: exp }))}
                        className={`px-2 py-1 text-xs rounded ${activeExpiry === exp ? 'bg-indigo-600 text-white' : 'bg-white border text-gray-700'}`}
                      >
                        {idx === 0 ? 'Current' : 'Next'}
                      </button>
                    ))}
                  </div>
                </div>
                <div className="px-3 py-2 text-xs text-gray-500">Expiry: {activeExpiry ? formatExpiry(activeExpiry) : '—'}</div>
                <div className="px-3 pb-3">
                  <div className="grid grid-cols-5 text-[11px] font-semibold text-gray-500 border-b pb-1">
                    <span className="text-right">CE LTP</span>
                    <span className="text-right">CE</span>
                    <span className="text-center">Strike</span>
                    <span>PE</span>
                    <span>PE LTP</span>
                  </div>
                  <OptionChainTable chain={chain} onOpenOrder={handleOpenOrderModal} />
                </div>
              </div>
            );
          })}

          <div className="border rounded-lg">
            <div className="flex items-center justify-between px-3 py-2 border-b bg-gray-50">
              <div className="font-semibold text-sm">MCX Futures</div>
              <div className="flex gap-2">
                <button
                  onClick={() => setFuturesTabs('current')}
                  className={`px-2 py-1 text-xs rounded ${futuresTabs === 'current' ? 'bg-indigo-600 text-white' : 'bg-white border text-gray-700'}`}
                >
                  Current
                </button>
                <button
                  onClick={() => setFuturesTabs('next')}
                  className={`px-2 py-1 text-xs rounded ${futuresTabs === 'next' ? 'bg-indigo-600 text-white' : 'bg-white border text-gray-700'}`}
                >
                  Next
                </button>
              </div>
            </div>
            <div className="px-3 py-2 text-xs text-gray-500">Expiry: {displayFuturesExpiry ? formatExpiry(displayFuturesExpiry) : '—'}</div>
            <div className="px-3 pb-3">
              <FuturesList rows={futures} />
            </div>
          </div>
        </div>
      </div>

      <OrderModal
        isOpen={modalOpen}
        onClose={handleCloseModal}
        orderData={modalOrderData}
        orderType={modalOrderType}
      />
    </div>
  );
};

export default Commodities;
