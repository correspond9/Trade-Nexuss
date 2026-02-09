import React, { useState, useEffect, useRef, useCallback } from 'react';
import { apiService } from '../services/apiService';
import { getLotSize as getConfiguredLotSize } from '../config/tradingConfig';
import { useAuth } from '../contexts/AuthContext';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v2';

const OrderModal = ({ isOpen, onClose, orderData, orderType = 'BUY' }) => {
  const { user } = useAuth();
  const [quantity, setQuantity] = useState(1);
  const [orderTypeSelection, setOrderTypeSelection] = useState('Normal');
  const [priceType, setPriceType] = useState('Market');
  const [isBasketOrder, setIsBasketOrder] = useState(false);
  const [selectedBasket, setSelectedBasket] = useState('');
  const [newBasketName, setNewBasketName] = useState('');
  const [basketType, setBasketType] = useState('existing');
  const [basketOptions, setBasketOptions] = useState([]);
  const [basketLoading, setBasketLoading] = useState(false);
  const [margin, setMargin] = useState(null);
  const [marginError, setMarginError] = useState('');
  const [availableMargin, setAvailableMargin] = useState(null);
  const [limitPrice, setLimitPrice] = useState('');
  const [depthOpen, setDepthOpen] = useState(false);
  const [depthLoading, setDepthLoading] = useState(false);
  const [depthData, setDepthData] = useState(null);
  
  // Super Order states
  const [isSuperOrder, setIsSuperOrder] = useState(false);
  const [targetPrice, setTargetPrice] = useState('');
  const [stopLossPrice, setStopLossPrice] = useState('');
  const [trailingJump, setTrailingJump] = useState(0);

  // Toggle between BUY and SELL
  const [currentOrderType, setCurrentOrderType] = useState(orderType);

  const modalRef = useRef(null);
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [modalPosition, setModalPosition] = useState({ x: 0, y: 0 });

  // Initialize modal position to center
  useEffect(() => {
    if (isOpen && !modalPosition.x && !modalPosition.y) {
      setModalPosition({
        x: window.innerWidth / 2 - 250, // 500px width / 2
        y: window.innerHeight / 2 - 200 // Approximate modal height / 2
      });
    }
  }, [isOpen]);

  // Handle ESC key press
  useEffect(() => {
    const handleEscKey = (event) => {
      if (event.key === 'Escape' && isOpen) {
        onClose();
      }
    };

    if (isOpen) {
      document.addEventListener('keydown', handleEscKey);
      return () => {
        document.removeEventListener('keydown', handleEscKey);
      };
    }
  }, [isOpen, onClose]);

  const handleMouseDown = useCallback((e) => {
    // Only allow dragging from title bar
    e.preventDefault();
    setIsDragging(true);
    setDragStart({
      x: e.clientX - modalPosition.x,
      y: e.clientY - modalPosition.y
    });
  }, [modalPosition]);

  const handleMouseMove = useCallback((e) => {
    if (isDragging) {
      const newX = e.clientX - dragStart.x;
      const newY = e.clientY - dragStart.y;
      
      // Keep modal within viewport bounds
      const maxX = window.innerWidth - 500; // modal width
      const maxY = window.innerHeight - 400; // approximate modal height
      const minX = 0;
      const minY = 0;
      
      setModalPosition({
        x: Math.max(minX, Math.min(maxX, newX)),
        y: Math.max(minY, Math.min(maxY, newY))
      });
    }
  }, [isDragging, dragStart]);

  const handleMouseUp = useCallback(() => {
    setIsDragging(false);
  }, []);

  useEffect(() => {
    if (isDragging) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
      document.body.style.userSelect = 'none'; // Prevent text selection during drag
      document.body.style.cursor = 'grabbing';
      
      return () => {
        document.removeEventListener('mousemove', handleMouseMove);
        document.removeEventListener('mouseup', handleMouseUp);
        document.body.style.userSelect = '';
        document.body.style.cursor = '';
      };
    }
  }, [isDragging, handleMouseMove, handleMouseUp]);

  useEffect(() => {
    setCurrentOrderType(orderType);
  }, [orderType]);

  useEffect(() => {
    if (!isOpen) return;
    setQuantity(1);
    setOrderTypeSelection('Normal');
    setPriceType('Market');
    setIsBasketOrder(false);
    setSelectedBasket('');
    setNewBasketName('');
    setBasketType('existing');
    setBasketOptions([]);
    setBasketLoading(false);
    setMargin(null);
    setMarginError('');
    setAvailableMargin(null);
    setIsSuperOrder(false);
    setTargetPrice('');
    setStopLossPrice('');
    setTrailingJump(0);
    setCurrentOrderType(orderType);
    setLimitPrice(orderData?.ltp ?? '');
    setDepthOpen(false);
    setDepthLoading(false);
    setDepthData(orderData?.depth ? { ...orderData.depth } : {
      bids: orderData?.depth?.bids || [],
      asks: orderData?.depth?.asks || [],
      bid: orderData?.bid ?? null,
      ask: orderData?.ask ?? null,
      ltp: orderData?.ltp ?? null,
    });
  }, [isOpen, orderType, orderData]);

  const normalizeUnderlying = (text) => {
    const value = String(text || '').trim().toUpperCase();
    if (value === 'NIFTY 50' || value === 'NIFTY50') return 'NIFTY';
    if (value === 'BANK NIFTY' || value === 'NIFTY BANK' || value === 'BANKNIFTY') return 'BANKNIFTY';
    if (value === 'BSE SENSEX' || value === 'S&P BSE SENSEX' || value === 'SENSEX 50') return 'SENSEX';
    return value;
  };

  const normalizeExpiry = (value) => {
    if (!value) return null;
    const text = String(value).trim();
    if (!text) return null;
    if (/^\d{4}-\d{2}-\d{2}$/.test(text)) return text;

    const parts = text.split(' ').filter(Boolean);
    if (parts.length === 2) {
      const [dayRaw, monRaw] = parts;
      const day = dayRaw.padStart(2, '0');
      const months = {
        Jan: '01', Feb: '02', Mar: '03', Apr: '04', May: '05', Jun: '06',
        Jul: '07', Aug: '08', Sep: '09', Oct: '10', Nov: '11', Dec: '12'
      };
      const month = months[monRaw.slice(0, 1).toUpperCase() + monRaw.slice(1, 3).toLowerCase()];
      if (month) {
        const year = new Date().getFullYear();
        return `${year}-${month}-${day}`;
      }
    }

    const parsed = new Date(text);
    if (!Number.isNaN(parsed.valueOf())) {
      return parsed.toISOString().slice(0, 10);
    }
    return text;
  };

  const parseOptionMeta = useCallback((data) => {
    const symbolText = String(data?.symbol || '').trim();
    const parts = symbolText.replace(/_/g, ' ').split(' ').filter(Boolean);
    let optionType = String(data?.optionType || '').toUpperCase();
    let strike = data?.strike;
    let underlying = '';

    if (parts.length >= 3) {
      optionType = optionType || parts[parts.length - 1].toUpperCase();
      strike = strike ?? parseFloat(parts[parts.length - 2]);
      underlying = parts.slice(0, parts.length - 2).join(' ');
    } else {
      underlying = symbolText;
    }

    return {
      underlying: normalizeUnderlying(underlying),
      optionType,
      strike: strike != null ? Number(strike) : null,
      expiry: normalizeExpiry(data?.expiry_iso ?? data?.expiry) || data?.expiry || null,
    };
  }, []);
  
  const getEffectiveLotSize = (data) => {
    const explicit = Number(data?.lotSize || 0);
    if (explicit > 0) return explicit;
    const underlying = String(data?.underlying || '').trim();
    if (underlying) {
      return Number(getConfiguredLotSize(underlying) || 1);
    }
    const meta = parseOptionMeta(data);
    if (!meta?.underlying) return 1;
    return Number(getConfiguredLotSize(meta.underlying) || 1);
  };

  useEffect(() => {
    if (!isOpen || !orderData) return;
    if (orderData?.depth) return;

    const meta = parseOptionMeta(orderData);
    if (!meta.underlying || !meta.expiry || !meta.optionType || meta.strike == null) return;

    const loadDepth = async () => {
      try {
        setDepthLoading(true);
        const response = await fetch(
          `${API_BASE}/market/option-depth?underlying=${encodeURIComponent(meta.underlying)}&expiry=${encodeURIComponent(meta.expiry)}&strike=${encodeURIComponent(meta.strike)}&option_type=${encodeURIComponent(meta.optionType)}`
        );
        if (!response.ok) {
          setDepthData(null);
          return;
        }
        const result = await response.json();
        if (result?.status === 'success') {
          setDepthData({
            bids: result?.data?.bids || [],
            asks: result?.data?.asks || [],
            bid: result?.data?.bid ?? null,
            ask: result?.data?.ask ?? null,
            ltp: result?.data?.ltp ?? null,
          });
        } else {
          setDepthData(null);
        }
      } catch (error) {
        console.warn('Failed to load depth:', error);
        setDepthData(null);
      } finally {
        setDepthLoading(false);
      }
    };

    loadDepth();
  }, [API_BASE, isOpen, orderData, parseOptionMeta]);

  useEffect(() => {
    if (!isOpen || !isBasketOrder) return;
    const loadBaskets = async () => {
      try {
        setBasketLoading(true);
        const response = await apiService.get('/trading/basket-orders', user?.id ? { user_id: user.id } : {});
        setBasketOptions(response?.data || []);
      } catch (error) {
        console.error('Failed to load baskets:', error);
        setBasketOptions([]);
      } finally {
        setBasketLoading(false);
      }
    };
    loadBaskets();
  }, [isOpen, isBasketOrder, user]);

  useEffect(() => {
    // Fetch margin when modal opens or inputs change
    if (isOpen && orderData) {
      fetchMargin();
    }
  }, [isOpen, orderData, quantity, currentOrderType, priceType, orderTypeSelection, limitPrice]);

  const resolveExchangeSegment = (data) => {
    if (data?.exchange_segment) return data.exchange_segment;
    if (data?.exchangeSegment) return data.exchangeSegment;
    const exchange = String(data?.exchange || '').toUpperCase();
    const symbol = String(data?.symbol || '').toUpperCase();
    const instrumentType = String(data?.instrumentType || '').toUpperCase();
    if (exchange.includes('MCX')) return 'MCX_COM';
    const meta = parseOptionMeta(data);
    if (
      instrumentType.includes('OPT') ||
      symbol.includes(' CE') ||
      symbol.includes(' PE') ||
      (meta?.optionType && meta?.strike != null)
    ) {
      return 'NSE_FNO';
    }
    return 'NSE_EQ';
  };

  const resolveProductType = () => (orderTypeSelection === 'MIS' ? 'MIS' : 'NORMAL');

  const fetchMargin = async () => {
    try {
      const effectiveLot = getEffectiveLotSize(orderData);
      const effectiveQty = Math.max(1, Number(quantity || 1)) * effectiveLot;
      const priceForMargin = priceType === 'Limit'
        ? Number(limitPrice || orderData?.ltp || 0)
        : Number(orderData?.ltp || 0);
      const productType = resolveProductType();
      const exchangeSegment = resolveExchangeSegment(orderData);
      const transactionType = currentOrderType;
      const optionMeta = parseOptionMeta(orderData);

      const legs = orderData?.legs?.length ? orderData.legs : null;
      const hasMultiLegs = Array.isArray(legs) && legs.length > 1;
      const canUseMulti = hasMultiLegs && legs.every((leg) => leg?.security_id || leg?.securityId);

      if (canUseMulti) {
        const scripts = legs.map((leg) => {
          const meta = parseOptionMeta(leg);
          const legLot = Number(leg?.lotSize || effectiveLot || 1);
          const legQty = Math.max(1, Number(quantity || 1)) * legLot;
          const legPrice = priceType === 'Limit'
            ? Number(leg?.ltp ?? priceForMargin)
            : Number(leg?.ltp ?? priceForMargin);
          return {
            exchange_segment: resolveExchangeSegment(leg),
            transaction_type: String(leg?.action || transactionType).toUpperCase(),
            quantity: legQty,
            product_type: productType,
            security_id: leg?.security_id || leg?.securityId,
            price: legPrice,
            symbol: leg?.symbol,
            expiry: meta?.expiry || null,
            strike: meta?.strike ?? null,
            option_type: meta?.optionType || null,
          };
        });

        const response = await fetch(`${API_BASE}/margin/calculate-multi`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            user_id: user?.id || null,
            scripts,
            include_positions: true,
            include_orders: true,
          })
        });

        const data = await response.json();
        const hasMargin = typeof data?.margin === 'number';
        if (data?.success || hasMargin) {
          setMargin(hasMargin ? data.margin : null);
          setMarginError('');
          setAvailableMargin(typeof data?.availableMargin === 'number' ? data.availableMargin : null);
          return;
        }
      }

      const response = await fetch(`${API_BASE}/margin/calculate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_id: user?.id || null,
          symbol: orderData.symbol,
          exchange_segment: exchangeSegment,
          transaction_type: transactionType,
          security_id: orderData.security_id || orderData.id || null,
            expiry: optionMeta?.expiry || null,
            strike: optionMeta?.strike ?? null,
            option_type: optionMeta?.optionType || null,
          quantity: effectiveQty,
          orderType: currentOrderType,
          priceType: priceType,
          price: priceForMargin,
          lotSize: effectiveLot,
          product_type: productType
        })
      });
      
      const data = await response.json();
      
      const hasMargin = typeof data?.margin === 'number';
      if (data?.success || hasMargin) {
        setMargin(hasMargin ? data.margin : null);
        setMarginError('');
        setAvailableMargin(typeof data?.availableMargin === 'number' ? data.availableMargin : null);
      } else {
        // Keep blank if server fails to fetch margin
        setMarginError('');
        setMargin(null);
      }
    } catch (error) {
      console.error('Margin calculation error:', error);
      // Keep blank if server fails
      setMarginError('');
      setMargin(null);
    }
  };

  const notifyUpdates = (targets) => {
    const safeTargets = Array.isArray(targets) ? targets : [];
    if (safeTargets.includes('orders')) {
      apiService.clearCacheEntry('/trading/orders');
    }
    if (safeTargets.includes('positions')) {
      apiService.clearCacheEntry('/portfolio/positions');
    }
    if (safeTargets.includes('baskets')) {
      apiService.clearCacheEntry('/trading/basket-orders');
    }
    if (typeof window !== 'undefined') {
      if (safeTargets.includes('orders')) {
        window.dispatchEvent(new CustomEvent('orders:updated'));
      }
      if (safeTargets.includes('positions')) {
        window.dispatchEvent(new CustomEvent('positions:updated'));
      }
      if (safeTargets.includes('baskets')) {
        window.dispatchEvent(new CustomEvent('baskets:updated'));
      }
    }
  };

  const handleOrderTypeToggle = () => {
    const newType = currentOrderType === 'BUY' ? 'SELL' : 'BUY';
    setCurrentOrderType(newType);
  };

  const handleSubmit = async () => {
    const productType = resolveProductType();
    const exchangeSegment = resolveExchangeSegment(orderData);
    const effectiveLot = getEffectiveLotSize(orderData);
    const effectiveQty = Math.max(1, Number(quantity || 1)) * effectiveLot;
    const resolvedPrice = priceType === 'Limit'
      ? Number(limitPrice || orderData?.ltp || 0)
      : 0;

    const marginExceeded = margin != null && availableMargin != null && margin > availableMargin;
    if (marginExceeded) {
      const warning = 'Required margin exceeds available margin. Please adjust positions or pay-in for margin call.';
      setMarginError(warning);
      window.alert(warning);
    } else {
      setMarginError('');
    }

    try {
      if (isSuperOrder) {
        // Place Super Order
        if (!targetPrice || !stopLossPrice) {
          setMarginError('Target price and stop loss are required for super orders');
          return;
        }

        const superOrderPayload = {
          symbol: orderData.symbol,
          security_id: orderData.security_id || orderData.id || null,
          exchange_segment: exchangeSegment,
          transaction_type: currentOrderType,
          quantity: effectiveQty,
          order_type: priceType === 'Market' ? 'MARKET' : 'LIMIT',
          product_type: productType,
          price: priceType === 'Market' ? 0 : resolvedPrice,
          is_super: true,
          target_price: parseFloat(targetPrice),
          stop_loss_price: parseFloat(stopLossPrice),
          trailing_jump: parseFloat(trailingJump || 0)
        };

        const response = await apiService.post('/trading/orders', {
          user_id: user?.id || null,
          ...superOrderPayload
        });
        
        if (response) {
          console.log('Super order placed successfully:', response);
          notifyUpdates(['orders', 'positions']);
          onClose();
        } else {
          setMarginError('Failed to place super order');
        }
      } else {
        // Place Regular Order
        if (isBasketOrder) {
          const legs = (orderData.legs?.length ? orderData.legs : [orderData]).map((leg) => {
            const legLot = Number(leg?.lotSize || effectiveLot || 1);
            const legQty = Math.max(1, Number(quantity || 1)) * legLot;
            const legPrice = priceType === 'Market'
              ? 0
              : Number(leg?.ltp ?? resolvedPrice);
            return {
              symbol: leg.symbol,
              security_id: leg.security_id || leg.id || null,
              exchange_segment: resolveExchangeSegment(leg),
              transaction_type: String(leg.action || currentOrderType).toUpperCase(),
              quantity: legQty,
              order_type: priceType === 'Market' ? 'MARKET' : 'LIMIT',
              product_type: productType,
              price: legPrice
            };
          });

          if (basketType === 'existing') {
            if (!selectedBasket) {
              setMarginError('Please select a basket');
              return;
            }
            const response = await apiService.post(`/trading/basket-orders/${selectedBasket}/legs`, {
              legs
            });
            if (response) {
              console.log('Basket order updated successfully:', response);
              notifyUpdates(['baskets']);
              onClose();
            } else {
              setMarginError('Failed to update basket');
            }
            return;
          }

          const basketName = newBasketName.trim();
          if (!basketName) {
            setMarginError('Basket name is required');
            return;
          }

          const response = await apiService.post('/trading/basket-orders', {
            user_id: user?.id || null,
            name: basketName,
            legs
          });

          if (response) {
            console.log('Basket order created successfully:', response);
            notifyUpdates(['baskets']);
            onClose();
          } else {
            setMarginError('Failed to create basket order');
          }
          return;
        }

        const legs = orderData.legs?.length ? orderData.legs : null;
        if (legs && legs.length > 1) {
          const responses = [];
          for (const leg of legs) {
            const legLot = Number(leg?.lotSize || effectiveLot || 1);
            const legQty = Math.max(1, Number(quantity || 1)) * legLot;
            const legPrice = priceType === 'Market'
              ? 0
              : Number(leg?.ltp ?? resolvedPrice);
            responses.push(await apiService.post('/trading/orders', {
              user_id: user?.id || null,
              symbol: leg.symbol,
              security_id: leg.security_id || leg.id || null,
              exchange_segment: resolveExchangeSegment(leg),
              transaction_type: String(leg.action || currentOrderType).toUpperCase(),
              quantity: legQty,
              order_type: priceType === 'Market' ? 'MARKET' : 'LIMIT',
              product_type: productType,
              price: legPrice
            }));
          }
          if (responses.length) {
            console.log('Multi-leg order placed successfully:', responses);
            notifyUpdates(['orders', 'positions']);
            onClose();
          } else {
            setMarginError('Failed to place multi-leg order');
          }
          return;
        }

        const response = await apiService.post('/trading/orders', {
          user_id: user?.id || null,
          symbol: orderData.symbol,
          security_id: orderData.security_id || orderData.id || null,
          exchange_segment: exchangeSegment,
          transaction_type: currentOrderType,
          quantity: effectiveQty,
          order_type: priceType === 'Market' ? 'MARKET' : 'LIMIT',
          product_type: productType,
          price: priceType === 'Market' ? 0 : resolvedPrice
        });

        if (response) {
          console.log('Order placed successfully:', response);
          notifyUpdates(['orders', 'positions']);
          onClose();
        } else {
          setMarginError('Failed to place order');
        }
      }
    } catch (error) {
      console.error('Order placement error:', error);
      setMarginError(error?.message || 'Failed to place order. Please try again.');
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50">
      {/* Semi-transparent overlay */}
      <div 
        className="absolute inset-0 bg-black bg-opacity-30"
        onClick={onClose}
      />
      
      {/* Modal */}
      <div 
        ref={modalRef}
        className="bg-white rounded-lg shadow-xl"
        style={{
          position: 'fixed',
          left: `${modalPosition.x}px`,
          top: `${modalPosition.y}px`,
          width: '500px',
          maxWidth: '90vw',
          cursor: isDragging ? 'grabbing' : 'default'
        }}
      >
        {/* Title Bar - Draggable area */}
        <div 
          className={`bg-gray-100 border-b border-gray-200 px-4 py-2 flex justify-between items-center rounded-t-lg ${
            isDragging ? 'cursor-grabbing' : 'cursor-move'
          }`}
          onMouseDown={handleMouseDown}
        >
          <div className="flex items-center space-x-3">
            {/* BUY/SELL Toggle Switch */}
            <button
              onClick={handleOrderTypeToggle}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                currentOrderType === 'BUY' ? 'bg-blue-600' : 'bg-orange-600'
              }`}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                  currentOrderType === 'BUY' ? 'translate-x-6' : 'translate-x-1'
                }`}
              />
            </button>
            <div>
              <h2 className={`text-lg font-bold ${
                currentOrderType === 'BUY' ? 'text-blue-600' : 'text-orange-600'
              }`}>
                {currentOrderType}
              </h2>
              <p className="text-xs text-gray-600">
                {orderData.symbol}
                {(orderData.expiry_display || orderData.expiry) && (
                  <span className="text-xs"> ({orderData.expiry_display || orderData.expiry})</span>
                )}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 text-xl font-bold"
          >
            ×
          </button>
        </div>

        {/* Compact Content Layout */}
        <div className="p-4">
          {/* Super Order Toggle */}
          <div className="mb-4">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-gray-700">Super Order</span>
              <button
                onClick={() => setIsSuperOrder(!isSuperOrder)}
                className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${
                  isSuperOrder ? 'bg-green-600' : 'bg-gray-200'
                }`}
              >
                <span
                  className={`inline-block h-3 w-3 transform rounded-full bg-white transition-transform ${
                    isSuperOrder ? 'translate-x-5' : 'translate-x-1'
                  }`}
                />
              </button>
            </div>
            {isSuperOrder && (
              <p className="text-xs text-gray-500 mt-1">Place order with target & stop-loss</p>
            )}
          </div>

          {/* Basket Order Section */}
          <div className="mb-4">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-gray-700">Add to Basket</span>
              <button
                onClick={() => setIsBasketOrder(!isBasketOrder)}
                className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${
                  isBasketOrder ? 'bg-green-600' : 'bg-gray-200'
                }`}
              >
                <span
                  className={`inline-block h-3 w-3 transform rounded-full bg-white transition-transform ${
                    isBasketOrder ? 'translate-x-5' : 'translate-x-1'
                  }`}
                />
              </button>
            </div>
            
            {isBasketOrder && (
              <div className="space-y-2 mt-2">
                {/* Basket Selection Type */}
                <div className="flex space-x-2">
                  <label className="flex items-center">
                    <input
                      type="radio"
                      name="basketType"
                      value="existing"
                      checked={basketType === 'existing'}
                      onChange={() => {
                        setBasketType('existing');
                        setNewBasketName('');
                      }}
                      className="mr-1 text-xs"
                    />
                    <span className="text-xs">Select Existing</span>
                  </label>
                  <label className="flex items-center">
                    <input
                      type="radio"
                      name="basketType"
                      value="new"
                      checked={basketType === 'new'}
                      onChange={() => {
                        setBasketType('new');
                        setSelectedBasket('');
                        setNewBasketName('');
                      }}
                      className="mr-1 text-xs"
                    />
                    <span className="text-xs">Create New</span>
                  </label>
                </div>

                {/* Existing Basket Selection */}
                {basketType === 'existing' && (
                  <div>
                    <select
                      value={selectedBasket}
                      onChange={(e) => {
                        setSelectedBasket(e.target.value);
                        setNewBasketName('');
                      }}
                      className="w-full px-2 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-green-500"
                    >
                      <option value="">Select Basket</option>
                      {basketLoading && (
                        <option value="" disabled>Loading...</option>
                      )}
                      {!basketLoading && basketOptions.length === 0 && (
                        <option value="" disabled>No baskets available</option>
                      )}
                      {!basketLoading && basketOptions.map((basket) => (
                        <option key={basket.id} value={basket.id}>
                          {basket.name}
                        </option>
                      ))}
                    </select>
                  </div>
                )}

                {/* New Basket Creation */}
                {basketType === 'new' && (
                  <div>
                    <input
                      type="text"
                      value={newBasketName}
                      onChange={(e) => {
                        setNewBasketName(e.target.value);
                        setSelectedBasket('');
                      }}
                      placeholder="Enter new basket name"
                      className="w-full px-2 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-green-500"
                    />
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Grid Layout for Compact Form */}
          <div className="grid grid-cols-2 gap-4">
            {/* Left Column */}
            <div className="space-y-3">
              {/* Order Type */}
              <div>
                <span className="text-xs font-medium text-gray-700">Order Type</span>
                <div className="flex space-x-2 mt-1">
                  <label className="flex items-center">
                    <input
                      type="radio"
                      name="orderType"
                      value="Normal"
                      checked={orderTypeSelection === 'Normal'}
                      onChange={(e) => setOrderTypeSelection(e.target.value)}
                      className="mr-1 text-xs"
                    />
                    <span className="text-xs">Normal</span>
                  </label>
                  <label className="flex items-center">
                    <input
                      type="radio"
                      name="orderType"
                      value="MIS"
                      checked={orderTypeSelection === 'MIS'}
                      onChange={(e) => setOrderTypeSelection(e.target.value)}
                      className="mr-1 text-xs"
                    />
                    <span className="text-xs">MIS</span>
                  </label>
                </div>
              </div>

              {/* Quantity */}
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">
                  Qty
                </label>
                <input
                  type="number"
                  value={quantity}
                  onChange={(e) => setQuantity(Math.max(1, parseInt(e.target.value) || 1))}
                  className="w-full px-2 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
                  min="1"
                />
              </div>

              {/* Price */}
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">
                  Price
                </label>
                <input
                  type="number"
                  disabled={priceType === 'Market'}
                  value={priceType === 'Market' ? '' : limitPrice}
                  onChange={(e) => setLimitPrice(e.target.value)}
                  className="w-full px-2 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:bg-gray-100"
                  placeholder={priceType === 'Market' ? 'Market' : 'Enter Price'}
                />
              </div>

              {/* Price Type */}
              <div>
                <span className="text-xs font-medium text-gray-700">Price Type</span>
                <div className="flex space-x-2 mt-1">
                  <label className="flex items-center">
                    <input
                      type="radio"
                      name="priceType"
                      value="Market"
                      checked={priceType === 'Market'}
                      onChange={(e) => setPriceType(e.target.value)}
                      className="mr-1 text-xs"
                    />
                    <span className="text-xs">Market</span>
                  </label>
                  <label className="flex items-center">
                    <input
                      type="radio"
                      name="priceType"
                      value="Limit"
                      checked={priceType === 'Limit'}
                      onChange={(e) => setPriceType(e.target.value)}
                      className="mr-1 text-xs"
                    />
                    <span className="text-xs">Limit</span>
                  </label>
                </div>
              </div>
            </div>

            {/* Right Column */}
            <div className="space-y-3">
              {/* Target Price - Show only for Super Orders */}
              {isSuperOrder && (
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">
                    Target Price *
                  </label>
                  <input
                    type="number"
                    value={targetPrice}
                    onChange={(e) => setTargetPrice(e.target.value)}
                    className="w-full px-2 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-green-500"
                    placeholder="Target price"
                  />
                </div>
              )}

              {/* Stop Loss - Show only for Super Orders */}
              {isSuperOrder && (
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">
                    Stop Loss *
                  </label>
                  <input
                    type="number"
                    value={stopLossPrice}
                    onChange={(e) => setStopLossPrice(e.target.value)}
                    className="w-full px-2 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-red-500"
                    placeholder="Stop loss"
                  />
                </div>
              )}

              {/* Trailing Jump - Show only for Super Orders */}
              {isSuperOrder && (
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">
                    Trailing Jump
                  </label>
                  <input
                    type="number"
                    value={trailingJump}
                    onChange={(e) => setTrailingJump(e.target.value)}
                    className="w-full px-2 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
                    placeholder="Optional"
                  />
                </div>
              )}

              {/* Trigger Price - Show only for regular orders */}
              {!isSuperOrder && (
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">
                    Trigger Price
                  </label>
                  <input
                    type="number"
                    disabled={priceType !== 'Limit'}
                    className="w-full px-2 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:bg-gray-100"
                    placeholder={priceType === 'Limit' ? 'Trigger' : 'Enable Limit'}
                  />
                </div>
              )}

              {/* Total Quantity */}
              <div className="text-xs text-gray-600">
                Total Qty: {quantity * getEffectiveLotSize(orderData)}
              </div>

              {/* Margin */}
              <div>
                <div className="text-xs font-medium text-gray-700">
                  Margin: {margin == null ? '—' : `₹${margin.toFixed(2)}`}
                </div>
                {marginError && (
                  <div className="text-xs text-red-600 mt-1">
                    {marginError}
                  </div>
                )}
              </div>

              {/* Depth removed from Order modal as requested */}
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex space-x-2 mt-4">
            <button
              onClick={handleSubmit}
              className={`flex-1 py-2 px-4 rounded text-sm font-medium text-white transition-colors ${
                currentOrderType === 'BUY'
                  ? 'bg-blue-600 hover:bg-blue-700'
                  : 'bg-orange-600 hover:bg-orange-700'
              }`}
            >
              {isBasketOrder 
                ? `ADD ${currentOrderType}` 
                : isSuperOrder 
                  ? `Place ${currentOrderType} Super` 
                  : currentOrderType
              }
            </button>
            <button
              onClick={onClose}
              className="flex-1 py-2 px-4 border border-gray-300 rounded text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
            >
              Cancel
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default OrderModal;
