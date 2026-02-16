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

// Convert ISO dates to display format (DD MMM) for UI
const formatExpiry = (dateStr) => {
  const date = new Date(dateStr);
  const day = date.getDate();
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  return `${day} ${months[date.getMonth()]}`;
};

// Fetch expiry dates from authoritative options cache
const fetchExpiryDates = async (selectedIndex = 'NIFTY 50') => {
  try {
    // Convert display name to symbol
    const symbol = normalizeUnderlying(selectedIndex);
    
    console.log('[TRADE] Fetching expiries from authoritative API for', symbol);
    const data = await apiService.get('/options/available/expiries', { underlying: symbol });
    console.log('[TRADE] Authoritative API response:', data);
    
    const expiries = Array.isArray(data?.data) ? data.data : [];
    console.log('[TRADE] Parsed expiries from authoritative cache:', expiries);
    
    if (!expiries.length) {
      console.warn('[TRADE] No expiries found in authoritative cache');
      return { displayExpiries: [], isoExpiries: [] };
    }

    const sorted = expiries.slice().sort();
    // Select first 2 expiries but ensure they are current and next, not skipping any
    // If current expiry is in the list, start from it; otherwise start from first
    const today = new Date().toISOString().split('T')[0];
    
    console.log('[TRADE] All expiries (sorted):', sorted);
    console.log('[TRADE] Today:', today);
    
    let currentIndex = sorted.findIndex(exp => exp >= today);
    if (currentIndex === -1) {
      console.warn('[TRADE] No future expiries found, using first available');
      currentIndex = 0;
    }
    
    const selected = sorted.slice(currentIndex, currentIndex + 2);
    
    console.log('[TRADE] Selected indices:', currentIndex, 'to', currentIndex + 2);
    console.log('[TRADE] Selected expiries (ISO):', selected);
    console.log('[TRADE] Selected expiries (Display):', selected.map(formatExpiry));
    return {
      displayExpiries: selected.map(formatExpiry),
      isoExpiries: selected
    };
    
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
            <div className="flex border border-gray-200 rounded-t-lg overflow-hidden">
              {leftTabs.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setLeftTab(tab.id)}
                  className={`flex-1 px-2 py-2 text-xs font-medium transition-colors ${
                    leftTab === tab.id
                      ? 'bg-blue-600 text-white'
                      : 'bg-white text-gray-700 hover:bg-gray-50 border-l border-gray-200'
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
                              ? 'bg-blue-600 text-white'
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
                            ? 'bg-blue-600 text-white'
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
                          ? 'bg-blue-600 text-white'
                          : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                      }`}
                    >
                      {index}
                    </button>
                  ))}
                  <button className="p-1 text-gray-500 hover:text-gray-700 transition-colors ml-2">
                    <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                    </svg>
                  </button>
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
              <div className="flex">
                {rightTabs.map((tab) => (
                  <button
                    key={tab.id}
                    onClick={() => setRightTab(tab.id)}
                    className={`flex-1 px-3 py-2 text-xs font-medium transition-colors ${
                      rightTab === tab.id
                        ? 'bg-blue-600 text-white'
                        : 'bg-gray-50 text-gray-700 hover:bg-gray-100 border-l border-gray-200'
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
