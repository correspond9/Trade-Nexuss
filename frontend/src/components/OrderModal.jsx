import React, { useState, useEffect, useRef, useCallback } from 'react';
import { apiService } from '../services/apiService';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v2';

const OrderModal = ({ isOpen, onClose, orderData, orderType = 'BUY' }) => {
  const [quantity, setQuantity] = useState(1);
  const [orderTypeSelection, setOrderTypeSelection] = useState('Normal');
  const [priceType, setPriceType] = useState('Market');
  const [isBasketOrder, setIsBasketOrder] = useState(false);
  const [selectedBasket, setSelectedBasket] = useState('');
  const [newBasketName, setNewBasketName] = useState('');
  const [basketType, setBasketType] = useState('existing');
  const [margin, setMargin] = useState(0);
  const [marginError, setMarginError] = useState('');
  const [availableMargin, setAvailableMargin] = useState(0);
  
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
    // Fetch margin from Dhan API when modal opens
    if (isOpen && orderData) {
      fetchMargin();
    }
  }, [isOpen, orderData, quantity, currentOrderType, priceType]);

  const fetchMargin = async () => {
    try {
      const response = await fetch(`${API_BASE}/margin/calculate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          symbol: orderData.symbol,
          quantity: quantity,
          orderType: currentOrderType,
          priceType: priceType,
          price: priceType === 'Limit' ? orderData.ltp : 0,
          lotSize: orderData.lotSize
        })
      });
      
      const data = await response.json();
      
      if (data.success) {
        setMargin(data.margin);
        setMarginError('');
        setAvailableMargin(data.availableMargin);
      } else {
        // Keep blank if server fails to fetch margin
        setMarginError('');
        setMargin(0);
      }
    } catch (error) {
      console.error('Margin calculation error:', error);
      // Keep blank if server fails
      setMarginError('');
      setMargin(0);
    }
  };

  const handleOrderTypeToggle = () => {
    const newType = currentOrderType === 'BUY' ? 'SELL' : 'BUY';
    setCurrentOrderType(newType);
  };

  const handleSubmit = async () => {
    // Check if sufficient margin is available
    if (margin > availableMargin) {
      setMarginError('Insufficient margin available');
      return;
    }

    try {
      if (isSuperOrder) {
        // Place Super Order
        if (!targetPrice || !stopLossPrice) {
          setMarginError('Target price and stop loss are required for super orders');
          return;
        }

        const superOrderPayload = {
          security_id: orderData.id || orderData.security_id,
          exchange_segment: orderData.exchange || 'MCX_COM',
          transaction_type: currentOrderType,
          quantity: quantity,
          order_type: priceType === 'Market' ? 'MARKET' : 'LIMIT',
          product_type: orderTypeSelection === 'MIS' ? 'INTRADAY' : 'DELIVERY',
          price: priceType === 'Market' ? 0 : orderData.ltp,
          target_price: parseFloat(targetPrice),
          stop_loss_price: parseFloat(stopLossPrice),
          trailing_jump: parseFloat(trailingJump)
        };

        const response = await apiService.post('/trading/orders', {
          security_id: orderData.id || orderData.security_id,
          exchange_segment: orderData.exchange || 'MCX_COM',
          transaction_type: currentOrderType,
          quantity: quantity,
          order_type: priceType === 'Market' ? 'MARKET' : 'LIMIT',
          product_type: orderTypeSelection === 'MIS' ? 'INTRADAY' : 'DELIVERY',
          price: priceType === 'Market' ? 0 : orderData.ltp,
          target_price: parseFloat(targetPrice),
          stop_loss_price: parseFloat(stopLossPrice),
          trailing_jump: parseFloat(trailingJump)
        });
        
        if (response) {
          console.log('Super order placed successfully:', response);
          onClose();
        } else {
          setMarginError('Failed to place super order');
        }
      } else {
        // Place Regular Order
        const orderPayload = {
          symbol: orderData.symbol,
          action: currentOrderType,
          quantity: quantity,
          orderTypeSelection,
          priceType,
          price: priceType === 'Limit' ? orderData.ltp : 0,
          lotSize: orderData.lotSize,
          expiry: orderData.expiry,
          legs: orderData.legs || null,
          isBasketOrder,
          basketId: selectedBasket || null,
          basketName: selectedBasket === '' ? newBasketName : null,
          margin: margin
        };

        const response = await apiService.post('/trading/orders', {
          security_id: orderData.id || orderData.security_id,
          quantity: quantity,
          transaction_type: currentOrderType,
          order_type: priceType === 'Market' ? 'MARKET' : 'LIMIT',
          product_type: orderTypeSelection === 'MIS' ? 'INTRADAY' : 'DELIVERY',
          exchange: orderData.exchange || 'NSE_EQ',
          price: priceType === 'Market' ? null : orderData.ltp
        });

        if (response) {
          console.log('Order placed successfully:', response);
          onClose();
        } else {
          setMarginError('Failed to place order');
        }
      }
    } catch (error) {
      console.error('Order placement error:', error);
      setMarginError('Failed to place order. Please try again.');
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
                {orderData.expiry && <span className="text-xs"> ({orderData.expiry})</span>}
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
                      <option value="BASKET_1">NIFTY Options</option>
                      <option value="BASKET_2">Bank NIFTY</option>
                      <option value="BASKET_3">Stock Portfolio</option>
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
                Total Qty: {quantity * (orderData.lotSize || 50)}
              </div>

              {/* Margin */}
              <div>
                <div className="text-xs font-medium text-gray-700">
                  Margin: ₹{margin.toFixed(2)}
                </div>
                {marginError && (
                  <div className="text-xs text-red-600 mt-1">
                    {marginError}
                  </div>
                )}
              </div>
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