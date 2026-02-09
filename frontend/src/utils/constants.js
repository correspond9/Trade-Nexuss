// Application constants

export const APP_CONFIG = {
  name: 'Trading-Nexuss',
  version: '2.0.0',
  description: 'Professional Trading Platform',
};

export const USER_ROLES = {
  ADMIN: 'ADMIN',
  SUPER_ADMIN: 'SUPER_ADMIN',
  USER: 'USER',
};

export const TRADING_MODES = {
  PAPER: 'PAPER',
  LIVE: 'LIVE',
  DEMO: 'DEMO',
};

export const USER_STATUS = {
  ACTIVE: 'ACTIVE',
  BLOCKED: 'BLOCKED',
  INACTIVE: 'INACTIVE',
};

export const ORDER_STATUS = {
  PENDING: 'PENDING',
  EXECUTED: 'EXECUTED',
  REJECTED: 'REJECTED',
  CANCELLED: 'CANCELLED',
};

export const POSITION_STATUS = {
  OPEN: 'OPEN',
  CLOSED: 'CLOSED',
  SQUARED: 'SQUARED',
};

export const PAYOUT_STATUS = {
  PENDING: 'PENDING',
  APPROVED: 'APPROVED',
  REJECTED: 'REJECTED',
  COMPLETED: 'COMPLETED',
  HOLD: 'HOLD',
};

export const BASKET_STATUS = {
  ACTIVE: 'ACTIVE',
  PAUSED: 'PAUSED',
  INACTIVE: 'INACTIVE',
};

export const PRODUCT_TYPES = {
  NORMAL: 'NORMAL',
  MIS: 'MIS',
  CO: 'CO',
  BO: 'BO',
};

export const ORDER_SIDES = {
  BUY: 'BUY',
  SELL: 'SELL',
};

export const EXCHANGES = {
  NSE: 'NSE',
  BSE: 'BSE',
  MCX: 'MCX',
};

// API endpoints
export const API_ENDPOINTS = {
  AUTH: {
    LOGIN: '/auth/login',
    LOGOUT: '/auth/logout',
    VERIFY: '/auth/verify',
    PROFILE: '/auth/profile',
    CHANGE_PASSWORD: '/auth/change-password',
  },
  USERS: '/users',
  ORDERS: '/orders',
  POSITIONS: '/positions',
  BASKETS: '/baskets',
  PAYOUTS: '/payouts',
  TRADE: '/trade',
  MARKET_DATA: '/market-data',
};

// Default pagination
export const DEFAULT_PAGINATION = {
  page: 1,
  limit: 50,
  maxLimit: 100,
};

// Date formats
export const DATE_FORMATS = {
  DISPLAY: 'dd MMM yyyy',
  DISPLAY_WITH_TIME: 'dd MMM yyyy HH:mm',
  API: 'yyyy-MM-dd',
  API_WITH_TIME: "yyyy-MM-dd'T'HH:mm:ss'Z'",
};

// Validation patterns
export const VALIDATION_PATTERNS = {
  EMAIL: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
  PHONE: /^[6-9]\d{9}$/,
  PAN: /^[A-Z]{5}[0-9]{4}[A-Z]{1}$/,
  AADHAR: /^\d{12}$/,
  IFSC: /^[A-Z]{4}0[A-Z0-9]{6}$/,
};

// Error messages
export const ERROR_MESSAGES = {
  NETWORK_ERROR: 'Network error. Please check your connection.',
  UNAUTHORIZED: 'You are not authorized to perform this action.',
  FORBIDDEN: 'Access denied. Insufficient permissions.',
  NOT_FOUND: 'Resource not found.',
  SERVER_ERROR: 'Server error. Please try again later.',
  VALIDATION_ERROR: 'Please check your input and try again.',
};

// Success messages
export const SUCCESS_MESSAGES = {
  USER_CREATED: 'User created successfully.',
  USER_UPDATED: 'User updated successfully.',
  USER_DELETED: 'User deleted successfully.',
  ORDER_PLACED: 'Order placed successfully.',
  ORDER_CANCELLED: 'Order cancelled successfully.',
  POSITION_CLOSED: 'Position closed successfully.',
  BASKET_CREATED: 'Basket created successfully.',
  BASKET_EXECUTED: 'Basket executed successfully.',
  PAYOUT_PROCESSED: 'Payout processed successfully.',
  SETTINGS_SAVED: 'Settings saved successfully.',
};

// Color schemes for status badges
export const STATUS_COLORS = {
  [USER_STATUS.ACTIVE]: 'bg-green-100 text-green-800',
  [USER_STATUS.BLOCKED]: 'bg-red-100 text-red-800',
  [USER_STATUS.INACTIVE]: 'bg-gray-100 text-gray-800',
  
  [ORDER_STATUS.EXECUTED]: 'bg-green-100 text-green-800',
  [ORDER_STATUS.PENDING]: 'bg-yellow-100 text-yellow-800',
  [ORDER_STATUS.REJECTED]: 'bg-red-100 text-red-800',
  [ORDER_STATUS.CANCELLED]: 'bg-gray-100 text-gray-800',
  
  [POSITION_STATUS.OPEN]: 'bg-blue-100 text-blue-800',
  [POSITION_STATUS.CLOSED]: 'bg-gray-100 text-gray-800',
  [POSITION_STATUS.SQUARED]: 'bg-purple-100 text-purple-800',
  
  [PAYOUT_STATUS.PENDING]: 'bg-yellow-100 text-yellow-800',
  [PAYOUT_STATUS.APPROVED]: 'bg-green-100 text-green-800',
  [PAYOUT_STATUS.REJECTED]: 'bg-red-100 text-red-800',
  [PAYOUT_STATUS.COMPLETED]: 'bg-blue-100 text-blue-800',
  [PAYOUT_STATUS.HOLD]: 'bg-orange-100 text-orange-800',
  
  [BASKET_STATUS.ACTIVE]: 'bg-green-100 text-green-800',
  [BASKET_STATUS.PAUSED]: 'bg-yellow-100 text-yellow-800',
  [BASKET_STATUS.INACTIVE]: 'bg-gray-100 text-gray-800',
};

// Side colors
export const SIDE_COLORS = {
  [ORDER_SIDES.BUY]: 'bg-blue-100 text-blue-800',
  [ORDER_SIDES.SELL]: 'bg-red-100 text-red-800',
};

// Product type colors
export const PRODUCT_TYPE_COLORS = {
  [PRODUCT_TYPES.NORMAL]: 'bg-gray-100 text-gray-800',
  [PRODUCT_TYPES.MIS]: 'bg-yellow-100 text-yellow-800',
  [PRODUCT_TYPES.CO]: 'bg-purple-100 text-purple-800',
  [PRODUCT_TYPES.BO]: 'bg-indigo-100 text-indigo-800',
};
