// Utility helper functions

import { DATE_FORMATS, VALIDATION_PATTERNS } from './constants';

// Format currency
export const formatCurrency = (amount, currency = '₹') => {
  if (amount === null || amount === undefined) return `${currency}0.00`;
  return `${currency}${Math.abs(amount).toLocaleString('en-IN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
};

// Format percentage
export const formatPercentage = (value, decimals = 2) => {
  if (value === null || value === undefined) return '0.00%';
  const sign = value >= 0 ? '+' : '';
  return `${sign}${value.toFixed(decimals)}%`;
};

// Format date
export const formatDate = (date, format = DATE_FORMATS.DISPLAY) => {
  if (!date) return '';
  
  const d = new Date(date);
  if (isNaN(d.getTime())) return '';

  const options = {
    [DATE_FORMATS.DISPLAY]: { day: '2-digit', month: 'short', year: 'numeric' },
    [DATE_FORMATS.DISPLAY_WITH_TIME]: { 
      day: '2-digit', 
      month: 'short', 
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    },
    [DATE_FORMATS.API]: { year: 'numeric', month: '2-digit', day: '2-digit' },
    [DATE_FORMATS.API_WITH_TIME]: { 
      year: 'numeric', 
      month: '2-digit', 
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      timeZone: 'UTC'
    },
  };

  return d.toLocaleDateString('en-IN', options[format] || options[DATE_FORMATS.DISPLAY]);
};

// Format time
export const formatTime = (date) => {
  if (!date) return '';
  const d = new Date(date);
  if (isNaN(d.getTime())) return '';
  return d.toLocaleTimeString('en-IN', { 
    hour: '2-digit', 
    minute: '2-digit',
    second: '2-digit'
  });
};

// Generate unique ID
export const generateId = (prefix = '') => {
  const timestamp = Date.now().toString(36);
  const randomPart = Math.random().toString(36).substring(2, 8);
  return prefix ? `${prefix}_${timestamp}_${randomPart}` : `${timestamp}_${randomPart}`;
};

// Generate client ID
export const generateClientId = (sequence) => {
  return `U${String(sequence).padStart(4, '0')}`;
};

// Validate email
export const validateEmail = (email) => {
  return VALIDATION_PATTERNS.EMAIL.test(email);
};

// Validate phone
export const validatePhone = (phone) => {
  return VALIDATION_PATTERNS.PHONE.test(phone);
};

// Validate PAN
export const validatePan = (pan) => {
  return VALIDATION_PATTERNS.PAN.test(pan);
};

// Validate Aadhar
export const validateAadhar = (aadhar) => {
  return VALIDATION_PATTERNS.AADHAR.test(aadhar);
};

// Validate IFSC
export const validateIfsc = (ifsc) => {
  return VALIDATION_PATTERNS.IFSC.test(ifsc);
};

// Calculate P&L percentage
export const calculatePnLPercentage = (pnl, investment) => {
  if (!investment || investment === 0) return 0;
  return (pnl / investment) * 100;
};

// Calculate win rate
export const calculateWinRate = (trades) => {
  if (!trades || trades.length === 0) return 0;
  const winningTrades = trades.filter(trade => trade.pnl > 0);
  return (winningTrades.length / trades.length) * 100;
};

// Calculate Sharpe ratio (simplified)
export const calculateSharpeRatio = (returns, riskFreeRate = 0.06) => {
  if (!returns || returns.length === 0) return 0;
  
  const avgReturn = returns.reduce((sum, r) => sum + r, 0) / returns.length;
  const variance = returns.reduce((sum, r) => sum + Math.pow(r - avgReturn, 2), 0) / returns.length;
  const stdDev = Math.sqrt(variance);
  
  return stdDev === 0 ? 0 : (avgReturn - riskFreeRate) / stdDev;
};

// Calculate maximum drawdown
export const calculateMaxDrawdown = (values) => {
  if (!values || values.length === 0) return 0;
  
  let maxDrawdown = 0;
  let peak = values[0];
  
  for (let i = 1; i < values.length; i++) {
    if (values[i] > peak) {
      peak = values[i];
    } else {
      const drawdown = (peak - values[i]) / peak * 100;
      maxDrawdown = Math.max(maxDrawdown, drawdown);
    }
  }
  
  return maxDrawdown;
};

// Deep clone object
export const deepClone = (obj) => {
  if (obj === null || typeof obj !== 'object') return obj;
  if (obj instanceof Date) return new Date(obj.getTime());
  if (obj instanceof Array) return obj.map(item => deepClone(item));
  
  const cloned = {};
  for (const key in obj) {
    if (obj.hasOwnProperty(key)) {
      cloned[key] = deepClone(obj[key]);
    }
  }
  return cloned;
};

// Debounce function
export const debounce = (func, wait) => {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
};

// Throttle function
export const throttle = (func, limit) => {
  let inThrottle;
  return function executedFunction(...args) {
    if (!inThrottle) {
      func.apply(this, args);
      inThrottle = true;
      setTimeout(() => inThrottle = false, limit);
    }
  };
};

// Sort array of objects by key
export const sortByKey = (array, key, direction = 'asc') => {
  return [...array].sort((a, b) => {
    let av = a[key];
    let bv = b[key];
    
    if (typeof av === 'string') {
      av = av.toUpperCase();
      bv = bv.toUpperCase();
    }
    
    if (av < bv) return direction === 'asc' ? -1 : 1;
    if (av > bv) return direction === 'asc' ? 1 : -1;
    return 0;
  });
};

// Filter array of objects by search term
export const filterBySearch = (array, searchTerm, searchKeys) => {
  if (!searchTerm) return array;
  
  const lowerSearchTerm = searchTerm.toLowerCase();
  
  return array.filter(item => {
    return searchKeys.some(key => {
      const value = item[key];
      if (value === null || value === undefined) return false;
      return String(value).toLowerCase().includes(lowerSearchTerm);
    });
  });
};

// Paginate array
export const paginate = (array, page = 1, limit = 10) => {
  const startIndex = (page - 1) * limit;
  const endIndex = startIndex + limit;
  return array.slice(startIndex, endIndex);
};

// Calculate pagination info
export const getPaginationInfo = (totalItems, page = 1, limit = 10) => {
  const totalPages = Math.ceil(totalItems / limit);
  const hasNextPage = page < totalPages;
  const hasPrevPage = page > 1;
  
  return {
    currentPage: page,
    totalPages,
    totalItems,
    limit,
    hasNextPage,
    hasPrevPage,
    startIndex: (page - 1) * limit,
    endIndex: Math.min(page * limit, totalItems),
  };
};

// Get color based on value (positive/negative)
export const getValueColor = (value) => {
  if (value > 0) return 'text-green-600';
  if (value < 0) return 'text-red-600';
  return 'text-gray-600';
};

// Get background color based on value
export const getValueBgColor = (value) => {
  if (value > 0) return 'bg-green-100';
  if (value < 0) return 'bg-red-100';
  return 'bg-gray-100';
};

// Truncate text
export const truncateText = (text, maxLength = 50) => {
  if (!text || text.length <= maxLength) return text;
  return text.substring(0, maxLength) + '...';
};

// Capitalize first letter
export const capitalize = (str) => {
  if (!str) return '';
  return str.charAt(0).toUpperCase() + str.slice(1).toLowerCase();
};

// Convert to title case
export const toTitleCase = (str) => {
  if (!str) return '';
  return str.replace(/\w\S*/g, (txt) => 
    txt.charAt(0).toUpperCase() + txt.substr(1).toLowerCase()
  );
};

// Get file extension
export const getFileExtension = (filename) => {
  if (!filename) return '';
  return filename.slice((filename.lastIndexOf('.') - 1 >>> 0) + 2);
};

// Format file size
export const formatFileSize = (bytes) => {
  if (bytes === 0) return '0 Bytes';
  
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};

// Check if object is empty
export const isEmpty = (obj) => {
  if (obj == null) return true;
  if (Array.isArray(obj) || typeof obj === 'string') return obj.length === 0;
  return Object.keys(obj).length === 0;
};

// Remove duplicates from array
export const removeDuplicates = (array, key) => {
  if (!key) return [...new Set(array)];
  
  const seen = new Set();
  return array.filter(item => {
    const value = item[key];
    if (seen.has(value)) return false;
    seen.add(value);
    return true;
  });
};

// Group array by key
export const groupBy = (array, key) => {
  return array.reduce((groups, item) => {
    const group = item[key];
    groups[group] = groups[group] || [];
    groups[group].push(item);
    return groups;
  }, {});
};