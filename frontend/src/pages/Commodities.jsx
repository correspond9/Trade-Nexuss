import React, { useEffect, useMemo, useState } from 'react';
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

const formatPct = (value) => {
  if (typeof value !== 'number' || Number.isNaN(value)) return '—';
  const sign = value > 0 ? '+' : '';
  return `${sign}${value.toFixed(2)}%`;
};

const OptionChainTable = ({ chain, onOpenOrder, underlyingPrice }) => {
  const strikes = chain?.strikes || {};
  const strikeList = Object.keys(strikes)
    .map((key) => ({ key, value: Number.parseFloat(key) }))
    .filter((item) => Number.isFinite(item.value))
    .sort((a, b) => a.value - b.value);

  const inferStrikeInterval = () => {
    if (strikeList.length < 2) return 0;
    let minDiff = Infinity;
    for (let idx = 1; idx < strikeList.length; idx += 1) {
      const diff = Math.abs(strikeList[idx].value - strikeList[idx - 1].value);
      if (diff > 0 && diff < minDiff) {
        minDiff = diff;
      }
    }
    return Number.isFinite(minDiff) ? minDiff : 0;
  };

  const backendStrikeInterval = Number(chain?.strike_interval || 0);
  const strikeInterval = backendStrikeInterval > 0 ? backendStrikeInterval : inferStrikeInterval();
  const chainUnderlyingLtp = Number(chain?.underlying_ltp || 0);
  const fallbackUnderlying = Number(underlyingPrice || 0);
  const liveUnderlying = fallbackUnderlying > 0 ? fallbackUnderlying : chainUnderlyingLtp;
  const fallbackAtm = Number.parseFloat(chain?.atm);
  const effectiveAtm = liveUnderlying > 0
    ? liveUnderlying
    : (strikeInterval > 0 && Number.isFinite(fallbackAtm) ? fallbackAtm : fallbackAtm);

  const centerIndex = strikeList.length
    ? (Number.isFinite(effectiveAtm)
      ? strikeList.reduce((bestIdx, item, idx, arr) => (
        Math.abs(item.value - effectiveAtm) < Math.abs(arr[bestIdx].value - effectiveAtm) ? idx : bestIdx
      ), 0)
      : Math.floor(strikeList.length / 2))
    : 0;

  const atmStrikeFromList = strikeList[centerIndex]?.value ?? null;

  const DISPLAY_SIDE = 15;
  const DISPLAY_WINDOW = (DISPLAY_SIDE * 2) + 1;
  let displayStart = Math.max(0, centerIndex - DISPLAY_SIDE);
  let displayEnd = Math.min(strikeList.length, centerIndex + DISPLAY_SIDE + 1);
  const displaySize = displayEnd - displayStart;
  if (strikeList.length >= DISPLAY_WINDOW && displaySize < DISPLAY_WINDOW) {
    const deficit = DISPLAY_WINDOW - displaySize;
    const shiftLeft = Math.min(displayStart, deficit);
    displayStart -= shiftLeft;
    displayEnd = Math.min(strikeList.length, displayEnd + (deficit - shiftLeft));
  }

  const displayStrikes = strikeList.slice(displayStart, displayEnd);

  if (!displayStrikes.length) {
    return (
      <div className="text-sm text-gray-500 py-6 text-center">No option chain data available.</div>
    );
  }

  return (
    <div className="divide-y divide-gray-100 max-h-[560px] overflow-y-auto">
      {displayStrikes.map((strikeItem) => {
        const row = strikes[strikeItem.key];
        const ce = row?.CE || {};
        const pe = row?.PE || {};
        const strike = strikeItem.value;
        const isATM = atmStrikeFromList != null && strike === atmStrikeFromList;
        return (
          <div
            key={strikeItem.key}
            data-atm={isATM ? 'true' : 'false'}
            className={`grid grid-cols-5 gap-2 items-center py-2 text-xs ${isATM ? 'bg-indigo-50 font-bold' : ''}`}
          >
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

const FuturesList = ({
  rows,
  marketOpen,
  expandedSymbol,
  depthBySymbol,
  depthLoadingBySymbol,
  onToggleDepth,
  onOpenOrder,
}) => (
  <div className="divide-y divide-gray-100">
    <div className="grid grid-cols-4 gap-2 py-2 text-[11px] font-semibold text-gray-500 border-b">
      <span>Instrument</span>
      <span className="text-center">Actions</span>
      <span className="text-right">Change %</span>
      <span className="text-right">{marketOpen ? 'Last Traded Price' : 'Closing Price'}</span>
    </div>
    {rows.map((row) => {
      const changePct = row.change_pct;
      const changeClass = typeof changePct === 'number'
        ? (changePct >= 0 ? 'text-green-600' : 'text-red-600')
        : 'text-gray-500';
      const isExpanded = expandedSymbol === row.symbol;
      const depth = depthBySymbol[row.symbol] || { bids: [], asks: [] };
      const bids = Array.isArray(depth.bids) ? depth.bids.slice(0, 5) : [];
      const asks = Array.isArray(depth.asks) ? depth.asks.slice(0, 5) : [];

      return (
        <div key={row.symbol} className="py-1 border-b border-gray-100 last:border-b-0">
          <div
            className="grid grid-cols-4 gap-2 items-center py-1 text-sm cursor-pointer"
            onClick={() => onToggleDepth(row.symbol)}
          >
            <button
              type="button"
              className="font-semibold text-gray-800 text-left"
            >
              {isExpanded ? '▾ ' : '▸ '}
              {row.instrument || row.symbol}
            </button>
            <div className="flex items-center justify-center gap-1" onClick={(event) => event.stopPropagation()}>
              <button
                onClick={() => onOpenOrder({ symbol: row.symbol, action: 'BUY', ltp: row.display_price ?? row.ltp, lotSize: row.lot_size, expiry: row.expiry })}
                className="px-2 py-1 rounded bg-blue-600 text-white text-xs"
              >
                BUY
              </button>
              <button
                onClick={() => onOpenOrder({ symbol: row.symbol, action: 'SELL', ltp: row.display_price ?? row.ltp, lotSize: row.lot_size, expiry: row.expiry })}
                className="px-2 py-1 rounded bg-red-600 text-white text-xs"
              >
                SELL
              </button>
            </div>
            <div className={`text-right font-semibold ${changeClass}`}>{formatPct(changePct)}</div>
            <div className="text-right font-semibold text-gray-700">{row.display_price?.toFixed?.(2) ?? row.display_price ?? '—'}</div>
          </div>

          {isExpanded && (
            <div className="mt-2 mb-1 p-2 rounded border bg-gray-50">
              {depthLoadingBySymbol[row.symbol] ? (
                <div className="text-xs text-gray-500">Loading top 5 bid/ask...</div>
              ) : (
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <div className="text-[11px] font-semibold text-green-700 mb-1">Top 5 Bids</div>
                    <div className="space-y-1">
                      {bids.length ? bids.map((item, idx) => (
                        <div key={`bid_${row.symbol}_${idx}`} className="grid grid-cols-2 text-xs">
                          <span className="text-gray-700">{item?.price?.toFixed?.(2) ?? item?.price ?? '—'}</span>
                          <span className="text-right text-gray-600">{item?.qty ?? '—'}</span>
                        </div>
                      )) : <div className="text-xs text-gray-500">No bid depth</div>}
                    </div>
                  </div>
                  <div>
                    <div className="text-[11px] font-semibold text-red-700 mb-1">Top 5 Asks</div>
                    <div className="space-y-1">
                      {asks.length ? asks.map((item, idx) => (
                        <div key={`ask_${row.symbol}_${idx}`} className="grid grid-cols-2 text-xs">
                          <span className="text-gray-700">{item?.price?.toFixed?.(2) ?? item?.price ?? '—'}</span>
                          <span className="text-right text-gray-600">{item?.qty ?? '—'}</span>
                        </div>
                      )) : <div className="text-xs text-gray-500">No ask depth</div>}
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      );
    })}
  </div>
);

const Commodities = () => {
  const [chains, setChains] = useState({});
  const [expiries, setExpiries] = useState({});
  const [activeTabs, setActiveTabs] = useState({});
  const [futuresTabs, setFuturesTabs] = useState('current');
  const [futures, setFutures] = useState([]);
  const [expandedFuturesSymbol, setExpandedFuturesSymbol] = useState(null);
  const [futuresDepth, setFuturesDepth] = useState({});
  const [futuresDepthLoading, setFuturesDepthLoading] = useState({});
  const [mcxMarketOpen, setMcxMarketOpen] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [modalOrderData, setModalOrderData] = useState(null);
  const [modalOrderType, setModalOrderType] = useState('BUY');

  const displayFuturesExpiry = futures.find((row) => row.expiry && row.expiry !== '—')?.expiry;

  const optionUnderlyingPrices = useMemo(() => {
    const map = {};
    futures.forEach((row) => {
      const price = Number(row?.display_price ?? row?.ltp ?? 0);
      if (Number.isFinite(price) && price > 0) {
        map[row.symbol] = price;
      }
    });
    return map;
  }, [futures]);

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
      setMcxMarketOpen(Boolean(data?.market_open));
      const bySymbol = new Map(list.map((row) => [row.symbol, row]));
      const rows = MCX_FUTURES.map((symbol) => bySymbol.get(symbol) || { symbol, instrument: `${symbol} FUT —`, change_pct: null, display_price: null, expiry: '—', ltp: null });
      setFutures(rows);
    } catch (err) {
      setFutures(MCX_FUTURES.map((symbol) => ({ symbol, instrument: `${symbol} FUT —`, change_pct: null, display_price: null, expiry: '—', ltp: null })));
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
    let mounted = true;

    const refreshChains = async () => {
      await Promise.all(
        MCX_OPTIONS.map(async (item) => {
          const expiry = activeTabs[item.key];
          if (!expiry) return;
          const chain = await loadChain(item.key, expiry);
          if (!mounted) return;
          setChains((prev) => ({ ...prev, [`${item.key}_${expiry}`]: chain }));
        })
      );
    };

    refreshChains();
    const intervalId = setInterval(refreshChains, 1000);

    return () => {
      mounted = false;
      clearInterval(intervalId);
    };
  }, [activeTabs]);

  useEffect(() => {
    let mounted = true;

    const refreshFutures = async () => {
      if (!mounted) return;
      await loadFutures(futuresTabs);
    };

    refreshFutures();
    const intervalId = setInterval(refreshFutures, 1000);

    return () => {
      mounted = false;
      clearInterval(intervalId);
    };
  }, [futuresTabs]);

  const handleOpenOrderModal = (leg) => {
    setModalOrderData({
      symbol: `${leg.symbol} FUT`,
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

  const loadFuturesDepth = async (symbol) => {
    setFuturesDepthLoading((prev) => ({ ...prev, [symbol]: true }));
    try {
      const data = await apiService.get('/commodities/depth', { symbol });
      const depth = data?.data || { bids: [], asks: [] };
      setFuturesDepth((prev) => ({
        ...prev,
        [symbol]: {
          bids: Array.isArray(depth?.bids) ? depth.bids.slice(0, 5) : [],
          asks: Array.isArray(depth?.asks) ? depth.asks.slice(0, 5) : [],
        },
      }));
    } catch (error) {
      setFuturesDepth((prev) => ({ ...prev, [symbol]: { bids: [], asks: [] } }));
    } finally {
      setFuturesDepthLoading((prev) => ({ ...prev, [symbol]: false }));
    }
  };

  const handleToggleFutureDepth = async (symbol) => {
    if (expandedFuturesSymbol === symbol) {
      setExpandedFuturesSymbol(null);
      return;
    }
    setExpandedFuturesSymbol(symbol);
    if (!futuresDepth[symbol] && !futuresDepthLoading[symbol]) {
      await loadFuturesDepth(symbol);
    }
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
                  <OptionChainTable
                    chain={chain}
                    onOpenOrder={handleOpenOrderModal}
                    underlyingPrice={optionUnderlyingPrices[item.key]}
                  />
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
              <FuturesList
                rows={futures}
                marketOpen={mcxMarketOpen}
                expandedSymbol={expandedFuturesSymbol}
                depthBySymbol={futuresDepth}
                depthLoadingBySymbol={futuresDepthLoading}
                onToggleDepth={handleToggleFutureDepth}
                onOpenOrder={handleOpenOrderModal}
              />
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
