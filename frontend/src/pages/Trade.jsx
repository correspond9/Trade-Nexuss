import React, { useState, useEffect, useRef } from 'react';
import normalizeUnderlying from '../utils/underlying';
import { apiService } from '../services/apiService';
import { getLotSize as getConfiguredLotSize } from '../config/tradingConfig';
import OrdersTab from './Orders';
import BasketsTab from './BASKETS';
import WatchlistComponent from './WATCHLIST';
import OptionMatrixComponent from './OPTIONS';
import PositionsTab from './POSITIONS';
import OrderModal from '../components/OrderModal';
// import marketDataCache from '../services/marketDataCache'; // Temporarily disabled

const expiryCache = new Map();
const EXPIRY_CACHE_TTL_MS = 2 * 60 * 1000;

// Convert ISO dates to display format (DD MMM) for UI
const formatExpiry = (dateStr) => {
  const date = new Date(dateStr);
  const day = date.getDate();
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  return `${day} ${months[date.getMonth()]}`;
};

const parseExpiryDate = (value) => {
  const raw = String(value || '').trim();
  if (!raw) return null;

  const isoMatch = raw.match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (isoMatch) {
    const dt = new Date(`${raw}T00:00:00`);
    return Number.isNaN(dt.getTime()) ? null : dt;
  }

  const alt = new Date(raw);
  if (!Number.isNaN(alt.getTime())) {
    return alt;
  }

  const compact = raw.toUpperCase().match(/^(\d{1,2})([A-Z]{3})(\d{2}|\d{4})$/);
  if (compact) {
    const day = Number(compact[1]);
    const monthMap = { JAN: 0, FEB: 1, MAR: 2, APR: 3, MAY: 4, JUN: 5, JUL: 6, AUG: 7, SEP: 8, OCT: 9, NOV: 10, DEC: 11 };
    const month = monthMap[compact[2]];
    const yearNum = Number(compact[3]);
    const year = yearNum < 100 ? (2000 + yearNum) : yearNum;
    if (!Number.isFinite(day) || month === undefined || !Number.isFinite(year)) {
      return null;
    }
    const dt = new Date(year, month, day);
    return Number.isNaN(dt.getTime()) ? null : dt;
  }

  return null;
};

const toIsoDate = (dateObj) => {
  const year = dateObj.getFullYear();
  const month = String(dateObj.getMonth() + 1).padStart(2, '0');
  const day = String(dateObj.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
};

// Fetch expiry dates from authoritative options cache
const fetchExpiryDates = async (selectedIndex = 'NIFTY 50') => {
  try {
    // Convert display name to symbol
    const symbol = normalizeUnderlying(selectedIndex);

    const cached = expiryCache.get(symbol);
    if (cached && (Date.now() - cached.ts) < EXPIRY_CACHE_TTL_MS) {
      return cached.value;
    }
    
    console.log('[TRADE] Fetching expiries from authoritative API for', symbol);
    const data = await apiService.get('/options/available/expiries', { underlying: symbol });
    console.log('[TRADE] Authoritative API response:', data);
    
    const expiries = Array.isArray(data?.data) ? data.data : [];
    console.log('[TRADE] Parsed expiries from authoritative cache:', expiries);
    
    if (!expiries.length) {
      console.warn('[TRADE] No expiries found in authoritative cache');
      return { displayExpiries: [], isoExpiries: [] };
    }

    const normalized = Array.from(new Set(
      expiries
        .map((exp) => parseExpiryDate(exp))
        .filter(Boolean)
        .map((dateObj) => toIsoDate(dateObj))
    )).sort();

    // Select current and next upcoming expiry only
    const now = new Date();
    const today = toIsoDate(new Date(now.getFullYear(), now.getMonth(), now.getDate()));
    
    console.log('[TRADE] All expiries (normalized):', normalized);
    console.log('[TRADE] Today:', today);
    
    let currentIndex = normalized.findIndex(exp => exp >= today);
    if (currentIndex === -1) {
      console.warn('[TRADE] No future expiries found, using first available');
      currentIndex = 0;
    }
    
    const selected = normalized.slice(currentIndex, currentIndex + 2);
    
    console.log('[TRADE] Selected indices:', currentIndex, 'to', currentIndex + 2);
    console.log('[TRADE] Selected expiries (ISO):', selected);
    console.log('[TRADE] Selected expiries (Display):', selected.map(formatExpiry));
    const value = {
      displayExpiries: selected.map(formatExpiry),
      isoExpiries: selected
    };
    expiryCache.set(symbol, { ts: Date.now(), value });
    return value;
    
  } catch (error) {
    console.error('[TRADE] Error fetching from authoritative API:', error);
    return { displayExpiries: [], isoExpiries: [] };
  }
};

const Trade = () => {
  const [leftTab, setLeftTab] = useState('options');
  const [rightTab, setRightTab] = useState('orders');
  const [selectedIndex, setSelectedIndex] = useState('NIFTY 50');
  const [expiries, setExpiries] = useState([]); // Display format
  const [isoExpiries, setIsoExpiries] = useState([]); // ISO format
  const [expiry, setExpiry] = useState(null); // Current expiry (display format)
  const [isoExpiry, setIsoExpiry] = useState(null); // Current expiry (ISO format)
  const [sortBy, setSortBy] = useState('A-Z');
  const [modalOpen, setModalOpen] = useState(false);
  const [modalOrderData, setModalOrderData] = useState(null);
  const [modalOrderType, setModalOrderType] = useState('BUY');
  const pageRef = useRef(null);
  
  useEffect(() => {
    try {
      window.scrollTo({ top: 0, behavior: 'auto' });
    } catch {
      window.scrollTo(0, 0);
    }
  }, []);
  
  
  
  // Update expiries when selected index changes
  useEffect(() => {
    const loadExpiries = async () => {
      const expiryData = await fetchExpiryDates(selectedIndex);
      
      // Handle both old format (array) and new format (object)
      if (Array.isArray(expiryData)) {
        // Old format - backward compatibility
        setExpiries(expiryData);
        setIsoExpiries(expiryData); // Assume same format for now
        if (expiryData.length > 0) {
          setExpiry(expiryData[0]);
          setIsoExpiry(expiryData[0]);
        }
      } else {
        // New format
        setExpiries(expiryData.displayExpiries);
        setIsoExpiries(expiryData.isoExpiries);
        if (expiryData.displayExpiries.length > 0) {
          setExpiry(expiryData.displayExpiries[0]);
          setIsoExpiry(expiryData.isoExpiries[0]);
        } else {
          setExpiry(null);
          setIsoExpiry(null);
        }
      }
    };
    
    loadExpiries();
  }, [selectedIndex]);
  
  // Remove useAppContext - tabs will manage their own data

  const leftTabs = [
    { id: 'options', name: 'Options' },
    { id: 'watchlist', name: 'Watchlist' },
  ];

  const rightTabs = [
    { id: 'orders', name: 'Orders' },
    { id: 'positions', name: 'Positions' },
    { id: 'baskets', name: 'Baskets' },
  ];

  const indices = ['NIFTY 50', 'NIFTY BANK', 'SENSEX'];
  const sortOptions = ['A-Z', '%', 'LTP'];

  const handleOpenOrderModal = (legs) => {
    // Handle single order or multiple legs (for straddle)
    if (Array.isArray(legs) && legs.length > 0) {
      const firstLeg = legs[0];
      const expiryIso = isoExpiry || expiry;
      const underlyingFromLeg = String(firstLeg?.underlying || '').trim() || normalizeUnderlying(selectedIndex);
      const fallbackLot = getConfiguredLotSize(underlyingFromLeg);
      const resolvedLot = Number(firstLeg?.lotSize || fallbackLot || 1);
      setModalOrderData({
        symbol: firstLeg.symbol,
        action: firstLeg.action,
        ltp: firstLeg.ltp,
        lotSize: resolvedLot,
        underlying: underlyingFromLeg,
        expiry: expiryIso,
        expiry_display: expiry,
        legs: legs.length > 1 ? legs : null // For straddle orders
      });
      setModalOrderType(firstLeg.action || 'BUY');
      setModalOpen(true);
    }
  };

  const handleCloseModal = () => {
    setModalOpen(false);
    setModalOrderData(null);
  };

  const handleExpiryChange = (newExpiry) => {
    setExpiry(newExpiry);
    // Find corresponding ISO expiry
    const index = expiries.indexOf(newExpiry);
    if (index !== -1 && index < isoExpiries.length) {
      setIsoExpiry(isoExpiries[index]);
    }
  };

  return (
    <div className="w-full bg-gray-50 min-h-screen" ref={pageRef}>
      {/* Main Container - Exact match to Straddly scaling */}
      <div className="w-full max-w-full mx-auto">
        <div className="flex flex-col lg:flex-row">
          {/* Left Panel - Straddle/Options/Watchlist */}
          <div className="lg:w-1/3 w-full">
            {/* Left Tab Navigation */}
            <div className="flex gap-1 border border-gray-200 rounded-t-lg p-1 bg-gray-100/60">
              {leftTabs.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setLeftTab(tab.id)}
                  className={`flex-1 px-[1em] py-[0.6em] min-h-[2.4em] leading-tight font-semibold rounded-md transition-colors ${
                    leftTab === tab.id
                      ? 'bg-blue-600 !text-white'
                      : 'bg-white text-gray-700 hover:bg-gray-50 border border-gray-200'
                  }`}
                >
                  {tab.name}
                </button>
              ))}
            </div>

            {/* Control Bar - Expiry, Sort, Index */}
            <div className="bg-white border-x border-b border-gray-200 p-2">
              {/* First Row: Expiry and Sort */}
              <div className="flex items-center justify-between mb-2">
                {/* Expiry Selection */}
                {leftTab !== 'watchlist' && (
                  <div className="flex gap-1">
                    {expiries && expiries.length > 0 ? (
                      expiries.map((exp) => (
                        <button
                          key={exp}
                          onClick={() => handleExpiryChange(exp)}
                          className={`px-2 py-1 text-xs font-medium rounded transition-colors ${
                            expiry === exp
                              ? 'bg-blue-600 !text-white'
                              : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                          }`}
                        >
                          {exp}
                        </button>
                      ))
                    ) : (
                      <span className="text-xs text-gray-500 px-2 py-1">Loading expiries...</span>
                    )}
                  </div>
                )}

                {/* Sort Options */}
                <div className="flex items-center">
                  <span className="text-xs font-medium text-gray-700 mr-2">Sort:</span>
                  <div className="flex gap-1">
                    {sortOptions.map((option) => (
                      <button
                        key={option}
                        onClick={() => setSortBy(option)}
                        className={`px-2 py-1 text-xs font-medium rounded transition-colors ${
                          sortBy === option
                            ? 'bg-blue-600 !text-white'
                            : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                        }`}
                      >
                        {option}
                      </button>
                    ))}
                  </div>
                </div>
              </div>

              {/* Second Row: Index Selection */}
              {leftTab !== 'watchlist' && (
                <div className="flex items-center">
                  {indices.map((index) => (
                    <button
                      key={index}
                      onClick={() => setSelectedIndex(index)}
                      className={`flex-1 px-2 py-1 text-xs font-medium rounded transition-colors ${
                        selectedIndex === index
                          ? 'bg-blue-600 !text-white'
                          : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                      }`}
                    >
                      {index}
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Left Panel Content */}
            <div className="bg-white border border-gray-200 rounded-b-lg p-2 min-h-[400px]">
              {leftTab === 'watchlist' && <WatchlistComponent handleOpenOrderModal={handleOpenOrderModal} />}
              {leftTab === 'options' && <OptionMatrixComponent handleOpenOrderModal={handleOpenOrderModal} selectedIndex={selectedIndex} expiry={isoExpiry} />}
            </div>
          </div>

          {/* Right Panel - Orders/Positions/Baskets */}
          <div className="lg:w-2/3 w-full">
            {/* Right Tab Navigation */}
            <div className="bg-white border border-gray-200 rounded-t-lg overflow-hidden">
              <div className="flex gap-1 p-1 bg-gray-100/60">
                {rightTabs.map((tab) => (
                  <button
                    key={tab.id}
                    onClick={() => setRightTab(tab.id)}
                    className={`flex-1 px-[1em] py-[0.6em] min-h-[2.4em] leading-tight font-semibold rounded-md transition-colors ${
                      rightTab === tab.id
                        ? 'bg-blue-600 !text-white'
                        : 'bg-white text-gray-700 hover:bg-gray-100 border border-gray-200'
                    }`}
                  >
                    {tab.name}
                  </button>
                ))}
              </div>
            </div>

            {/* Right Panel Content */}
            <div className="bg-white border-x border-b border-gray-200 rounded-b-lg p-2 min-h-[600px]">
              {rightTab === 'positions' && <PositionsTab />}
              {rightTab === 'orders' && <OrdersTab />}
              {rightTab === 'baskets' && <BasketsTab />}
            </div>
          </div>
        </div>
      </div>
      
      
      
      {/* Order Modal */}
      <OrderModal
        isOpen={modalOpen}
        onClose={handleCloseModal}
        orderData={modalOrderData}
        orderType={modalOrderType}
      />
    </div>
  );
};

export default Trade;
