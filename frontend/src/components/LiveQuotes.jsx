// Live Quotes Component - Data Flow Indicators with Real-time Price Display
import React, { useState, useEffect } from 'react';
import { TrendingUp, TrendingDown, Activity, RefreshCw } from 'lucide-react';

import { apiService } from '../services/apiService';
const CORE_INSTRUMENTS = [
  { key: 'NIFTY', label: 'NIFTY 50', exchange: 'NSE', badge: 'bg-blue-100 text-blue-700' },
  { key: 'BANKNIFTY', label: 'BANKNIFTY', exchange: 'NSE', badge: 'bg-indigo-100 text-indigo-700' },
  { key: 'SENSEX', label: 'SENSEX', exchange: 'BSE', badge: 'bg-amber-100 text-amber-700' },
  { key: 'CRUDEOIL', label: 'CRUDEOIL FUT', exchange: 'MCX', badge: 'bg-purple-100 text-purple-700' },
  { key: 'RELIANCE', label: 'RELIANCE', exchange: 'NSE', badge: 'bg-emerald-100 text-emerald-700' },
];

const LiveQuotes = () => {
  const [quotes, setQuotes] = useState(() =>
    CORE_INSTRUMENTS.reduce((acc, instrument) => {
      acc[instrument.key] = {
        symbol: instrument.key,
        price: null,
        status: 'loading',
        exchange: instrument.exchange,
      };
      return acc;
    }, {})
  );
  const [lastUpdate, setLastUpdate] = useState(null);
  const [dataFlowStatus, setDataFlowStatus] = useState('checking');
  const [marketDataSource, setMarketDataSource] = useState('unknown');
  const [pollIntervalMs, setPollIntervalMs] = useState(3000);

  const detectPayloadSource = (payload) => {
    const explicitSource = String(payload?.source || payload?.data?.source || '').toLowerCase();
    if (explicitSource.includes('snapshot')) return 'snapshot';
    if (explicitSource.includes('live') || explicitSource.includes('cache')) return 'live_cache';

    const strikeMap = payload?.data?.strikes || payload?.strikes || {};
    let hasSnapshot = false;
    let hasLive = false;

    Object.values(strikeMap).forEach((strike) => {
      const ceSource = String(strike?.CE?.source || strike?.ce?.source || '').toLowerCase();
      const peSource = String(strike?.PE?.source || strike?.pe?.source || '').toLowerCase();
      const sourceCombined = `${ceSource}|${peSource}`;
      if (sourceCombined.includes('snapshot')) hasSnapshot = true;
      if (sourceCombined.includes('live') || sourceCombined.includes('cache')) hasLive = true;
    });

    if (hasSnapshot && hasLive) return 'mixed';
    if (hasSnapshot) return 'snapshot';
    if (hasLive) return 'live_cache';
    return 'unknown';
  };

  useEffect(() => {
    let intervalId;
    const fetchPrices = async () => {
      try {
        let mcxFuturesPriceMap = {};
        try {
          const futuresPayload = await apiService.get('/commodities/futures', { tab: 'current' });
          const futuresRows = Array.isArray(futuresPayload?.data) ? futuresPayload.data : [];
          mcxFuturesPriceMap = futuresRows.reduce((acc, row) => {
            const symbol = String(row?.symbol || '').toUpperCase();
            const price = Number(row?.display_price ?? row?.ltp ?? 0);
            if (symbol && Number.isFinite(price) && price > 0) {
              acc[symbol] = price;
            }
            return acc;
          }, {});
        } catch (_error) {
          mcxFuturesPriceMap = {};
        }

        const entries = await Promise.all(
          CORE_INSTRUMENTS.map(async ({ key, exchange }) => {
            try {
              if (exchange === 'MCX') {
                const mcxPrice = mcxFuturesPriceMap[key];
                if (Number.isFinite(mcxPrice) && mcxPrice > 0) {
                  return [key, mcxPrice, 'commodity_futures', null];
                }
              }

              const payload = await apiService.get(`/market/underlying-ltp/${key}`);
              const rawPrice = payload?.ltp;
              const price = Number(rawPrice);
              const source = 'live_cache';
              return [key, Number.isFinite(price) && price > 0 ? price : null, source, null];
            } catch (error) {
              return [key, null, 'unknown', error];
            }
          })
        );

        setQuotes(prev => {
          const updated = { ...prev };
          entries.forEach(([key, price, _source, error]) => {
            if (price && price > 0) {
              updated[key] = { ...updated[key], price, status: 'success' };
            } else if (error) {
              updated[key] = { ...updated[key], status: 'error' };
            } else {
              updated[key] = { ...updated[key], status: 'no_data' };
            }
          });
          return updated;
        });

        const sourceSet = new Set(entries.map(([, , source]) => source).filter(Boolean));
        if (sourceSet.size === 0) {
          setMarketDataSource('unknown');
        } else if (sourceSet.size === 1) {
          setMarketDataSource([...sourceSet][0]);
        } else {
          const onlyUnknown = [...sourceSet].every((value) => value === 'unknown');
          setMarketDataSource(onlyUnknown ? 'unknown' : 'mixed');
        }

        const activeCount = entries.filter(([, price]) => price && price > 0).length;
        setDataFlowStatus(activeCount > 0 ? 'active' : 'waiting');
        setLastUpdate(new Date());
        setPollIntervalMs(3000);
      } catch (error) {
        console.error('[LiveQuotes] Price fetch error:', error);
        setDataFlowStatus('error');
        setPollIntervalMs(8000);
      }
    };

    fetchPrices();
    intervalId = setInterval(fetchPrices, pollIntervalMs);

    return () => {
      if (intervalId) {
        clearInterval(intervalId);
      }
    };
  }, [pollIntervalMs]);

  const getStatusColor = (status) => {
    switch (status) {
      case 'success': return 'bg-green-100 text-green-800';
      case 'no_data': return 'bg-yellow-100 text-yellow-800';
      case 'error': return 'bg-red-100 text-red-800';
      case 'loading': return 'bg-gray-100 text-gray-600';
      default: return 'bg-gray-100 text-gray-600';
    }
  };

  const getDataFlowIndicator = () => {
    switch (dataFlowStatus) {
      case 'active':
        return { color: 'bg-green-500', text: 'Data Flowing', pulse: true };
      case 'waiting':
        return { color: 'bg-yellow-500', text: 'Waiting for Data', pulse: false };
      case 'error':
        return { color: 'bg-red-500', text: 'Connection Error', pulse: false };
      default:
        return { color: 'bg-gray-400', text: 'Checking...', pulse: false };
    }
  };

  const formatPrice = (price) => {
    if (price === null || price === undefined || price === 0) return '--';
    return typeof price === 'number' ? price.toFixed(2) : price;
  };

  const getSourceBadge = () => {
    switch (marketDataSource) {
      case 'commodity_futures':
        return { text: 'MCX CURRENT FUT', classes: 'bg-purple-100 text-purple-800' };
      case 'live_cache':
        return { text: 'LIVE CACHE', classes: 'bg-green-100 text-green-800' };
      case 'snapshot':
        return { text: 'SNAPSHOT', classes: 'bg-yellow-100 text-yellow-800' };
      case 'mixed':
        return { text: 'MIXED', classes: 'bg-blue-100 text-blue-800' };
      default:
        return { text: 'UNKNOWN', classes: 'bg-gray-100 text-gray-700' };
    }
  };

  const dataFlowIndicator = getDataFlowIndicator();
  const sourceBadge = getSourceBadge();

  return (
    <div className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg shadow-sm border border-blue-200 p-4 mb-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-3">
          <Activity className="w-5 h-5 text-blue-600" />
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-semibold text-gray-900">Market Data Stream</h3>
              <span className={`text-[10px] px-2 py-0.5 rounded-full font-semibold ${sourceBadge.classes}`}>
                {sourceBadge.text}
              </span>
            </div>
            <p className="text-xs text-gray-600">Real-time instrument prices</p>
          </div>
        </div>
        <div className="flex items-center space-x-3">
          <div className="text-right">
            <div className="text-xs text-gray-600">Last Update</div>
            <div className="text-sm font-mono text-gray-900">
              {lastUpdate ? lastUpdate.toLocaleTimeString() : 'Waiting...'}
            </div>
          </div>
          <div className={`flex items-center space-x-2 px-3 py-1 rounded-full ${getStatusColor('success')}`}>
            <div className={`w-2 h-2 rounded-full ${dataFlowIndicator.color} ${dataFlowIndicator.pulse ? 'animate-pulse' : ''}`}></div>
            <span className="text-xs font-medium">{dataFlowIndicator.text}</span>
          </div>
        </div>
      </div>

      {/* Price Grid - dedicated to five core instruments */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-2 mb-4">
        {CORE_INSTRUMENTS.map(({ key, label, exchange, badge }) => (
          <div key={key} className="bg-white rounded-lg p-2 border border-gray-200 hover:shadow-md transition-shadow">
            <div className="flex items-center justify-between mb-1">
              <div className="text-xs font-semibold text-gray-700">{label}</div>
              <div className={`text-[10px] px-1.5 py-0.5 rounded-full ${badge}`}>{exchange}</div>
            </div>
            <div className={`text-lg font-bold ${quotes[key].status === 'success' ? 'text-green-600' : 'text-gray-400'}`}>
              {formatPrice(quotes[key].price)}
            </div>
            <div className="text-[11px] text-gray-500 mt-0.5">
              {quotes[key].status === 'success'
                ? '✓ Live'
                : quotes[key].status === 'no_data'
                  ? 'No Data'
                  : quotes[key].status}
            </div>
          </div>
        ))}
      </div>

      {/* Data Summary Footer */}
      <div className="bg-white rounded-lg p-3 border border-gray-200">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <div className="text-sm">
              <span className="text-gray-600">Active Instruments: </span>
              <span className="font-semibold text-green-600">
                {Object.values(quotes).filter(q => q.status === 'success').length} / {CORE_INSTRUMENTS.length}
              </span>
            </div>
            <div className="text-sm">
              <span className="text-gray-600">Update Frequency: </span>
              <span className="font-semibold text-blue-600">Polling (1s)</span>
            </div>
          </div>
          <div className="text-xs text-gray-500">
            Endpoint: /api/v2/options/live | Status: {dataFlowStatus}
          </div>
        </div>
      </div>
    </div>
  );
};

export default LiveQuotes;
