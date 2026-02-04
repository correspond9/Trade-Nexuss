const { body } = require('express-validator');

// Order Validation Schemas
const orderValidation = [
  body('symbol')
    .notEmpty()
    .withMessage('Symbol is required')
    .isLength({ min: 5, max: 30 })
    .withMessage('Symbol must be 5-30 characters'),
    
  body('exchange')
    .isIn(['NSE', 'BSE', 'NFO', 'BFO', 'CDS', 'MCX'])
    .withMessage('Invalid exchange'),
    
  body('action')
    .isIn(['BUY', 'SELL'])
    .withMessage('Action must be BUY or SELL'),
    
  body('quantity')
    .isInt({ min: 1 })
    .withMessage('Quantity must be a positive integer'),
    
  body('price')
    .isFloat({ min: 0 })
    .withMessage('Price must be a positive number'),
    
  body('product')
    .isIn(['NRML', 'MIS', 'CNC'])
    .withMessage('Invalid product type'),
    
  body('pricetype')
    .isIn(['MARKET', 'LIMIT', 'SL', 'SL-M'])
    .withMessage('Invalid price type')
];

// Super Order Validation
const superOrderValidation = [
  ...orderValidation,
  body('target_price')
    .optional()
    .isFloat({ min: 0 })
    .withMessage('Target price must be a positive number'),
    
  body('stop_loss')
    .optional()
    .isFloat({ min: 0 })
    .withMessage('Stop loss must be a positive number'),
    
  body('trailing_jump')
    .optional()
    .isFloat({ min: 0 })
    .withMessage('Trailing jump must be a positive number')
];

// Option Greeks Validation
const optionGreeksValidation = [
  body('symbol')
    .matches(/^[A-Z]+\d{2}[A-Z]{3}\d{2}[\d.]+(CE|PE)$/)
    .withMessage('Invalid option symbol format'),
    
  body('exchange')
    .isIn(['NFO', 'BFO', 'CDS', 'MCX'])
    .withMessage('Invalid exchange'),
    
  body('interest_rate')
    .optional()
    .isFloat({ min: 0, max: 100 })
    .withMessage('Interest rate must be between 0 and 100'),
    
  body('forward_price')
    .optional()
    .isFloat({ min: 0 })
    .withMessage('Forward price must be a positive number'),
    
  body('underlying_symbol')
    .optional()
    .isLength({ min: 1, max: 20 })
    .withMessage('Underlying symbol must be 1-20 characters'),
    
  body('underlying_exchange')
    .optional()
    .isIn(['NSE', 'BSE', 'NSE_INDEX', 'NFO', 'BFO', 'CDS', 'MCX'])
    .withMessage('Invalid underlying exchange'),
    
  body('expiry_time')
    .optional()
    .matches(/^([01]?[0-9]|2[0-3]):[0-5][0-9]$/)
    .withMessage('Expiry time must be in HH:MM format')
];

// Margin Calculation Validation
const marginValidation = [
  body('positions')
    .isArray({ min: 1 })
    .withMessage('Positions must be a non-empty array'),
    
  body('positions.*.symbol')
    .notEmpty()
    .withMessage('Position symbol is required'),
    
  body('positions.*.exchange')
    .isIn(['NSE', 'BSE', 'NFO', 'BFO', 'CDS', 'MCX'])
    .withMessage('Invalid exchange in position'),
    
  body('positions.*.action')
    .isIn(['BUY', 'SELL'])
    .withMessage('Action must be BUY or SELL in position'),
    
  body('positions.*.quantity')
    .isInt({ min: 1 })
    .withMessage('Quantity must be a positive integer in position'),
    
  body('positions.*.price')
    .isFloat({ min: 0 })
    .withMessage('Price must be a positive number in position'),
    
  body('positions.*.product')
    .isIn(['NRML', 'MIS', 'CNC'])
    .withMessage('Invalid product type in position'),
    
  body('positions.*.pricetype')
    .isIn(['MARKET', 'LIMIT', 'SL', 'SL-M'])
    .withMessage('Invalid price type in position')
];

// Basket Order Validation
const basketValidation = [
  body('name')
    .isLength({ min: 1, max: 100 })
    .withMessage('Basket name must be 1-100 characters'),
    
  body('orders')
    .isArray({ min: 1 })
    .withMessage('Orders must be a non-empty array'),
    
  body('orders.*.symbol')
    .notEmpty()
    .withMessage('Symbol is required for each order'),
    
  body('orders.*.exchange')
    .isIn(['NSE', 'BSE', 'NFO', 'BFO', 'CDS', 'MCX'])
    .withMessage('Invalid exchange for each order'),
    
  body('orders.*.action')
    .isIn(['BUY', 'SELL'])
    .withMessage('Action must be BUY or SELL for each order'),
    
  body('orders.*.quantity')
    .isInt({ min: 1 })
    .withMessage('Quantity must be a positive integer for each order')
];

module.exports = {
  orderValidation,
  superOrderValidation,
  optionGreeksValidation,
  marginValidation,
  basketValidation
};
