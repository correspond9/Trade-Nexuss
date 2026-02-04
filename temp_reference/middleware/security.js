const express = require('express');
const rateLimit = require('express-rate-limit');
const helmet = require('helmet');
const cors = require('cors');
const { body, validationResult } = require('express-validator');

// Security Middleware Configuration
const securityMiddleware = {
  // Rate Limiting
  createRateLimit: (windowMs, max, message) => rateLimit({
    windowMs,
    max,
    message: { status: 'error', message },
    standardHeaders: true,
    legacyHeaders: false,
  }),

  // Helmet Configuration
  helmetConfig: helmet({
    contentSecurityPolicy: {
      directives: {
        defaultSrc: ["'self'"],
        styleSrc: ["'self'", "'unsafe-inline'"], // Remove unsafe-inline in production
        scriptSrc: ["'self'"], // Remove unsafe-inline completely
        imgSrc: ["'self'", "data:", "https:"],
        connectSrc: ["'self'", "ws:", "wss:"],
        fontSrc: ["'self'"],
        objectSrc: ["'none'"],
        mediaSrc: ["'self'"],
        frameSrc: ["'none'"],
      },
    },
    hsts: {
      maxAge: 31536000,
      includeSubDomains: true,
      preload: true
    }
  }),

  // CORS Configuration
  corsConfig: cors({
    origin: process.env.NODE_ENV === 'production' 
      ? ['https://yourdomain.com'] // Production domains
      : ['http://localhost:5173', 'http://localhost:3000'], // Development
    credentials: true,
    optionsSuccessStatus: 200
  }),

  // Input Validation Middleware
  validateRequest: (req, res, next) => {
    const errors = validationResult(req);
    if (!errors.isEmpty()) {
      return res.status(400).json({
        status: 'error',
        message: 'Validation failed',
        errors: errors.array()
      });
    }
    next();
  }
};

module.exports = securityMiddleware;