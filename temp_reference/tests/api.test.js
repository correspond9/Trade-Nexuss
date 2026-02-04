const request = require('supertest');
const app = require('../comprehensive-api-integration');

describe('Trading Terminal API Tests', () => {
  let server;

  beforeAll(async () => {
    server = app.listen(0); // Use random port for testing
  });

  afterAll(async () => {
    if (server) {
      await new Promise(resolve => server.close(resolve));
    }
  });

  describe('Health Check', () => {
    it('should return health status', async () => {
      const response = await request(app)
        .get('/api/v1/health')
        .expect(200);
      
      expect(response.body).toHaveProperty('status', 'success');
      expect(response.body).toHaveProperty('services');
    });
  });

  describe('Security Tests', () => {
    it('should have security headers', async () => {
      const response = await request(app)
        .get('/api/v1/health')
        .expect(200);
      
      expect(response.headers).toHaveProperty('x-frame-options');
      expect(response.headers).toHaveProperty('x-content-type-options');
      expect(response.headers).toHaveProperty('x-xss-protection');
    });

    it('should rate limit requests', async () => {
      // Make multiple requests quickly to test rate limiting
      const promises = Array(105).fill().map(() => 
        request(app).get('/api/v1/health')
      );
      
      const responses = await Promise.allSettled(promises);
      const rejected = responses.filter(r => r.status === 'rejected' || r.value.status === 429);
      
      expect(rejected.length).toBeGreaterThan(0);
    });
  });

  describe('Input Validation Tests', () => {
    it('should validate option Greeks request', async () => {
      const invalidRequest = {
        symbol: 'INVALID_SYMBOL',
        exchange: 'INVALID_EXCHANGE'
      };

      const response = await request(app)
        .post('/api/v1/optiongreeks')
        .send(invalidRequest)
        .expect(400);
      
      expect(response.body).toHaveProperty('status', 'error');
      expect(response.body).toHaveProperty('errors');
    });

    it('should validate order request', async () => {
      const invalidOrder = {
        symbol: '',
        exchange: 'INVALID',
        action: 'INVALID',
        quantity: -1,
        price: -10,
        product: 'INVALID',
        pricetype: 'INVALID'
      };

      const response = await request(app)
        .post('/api/v1/orders/place')
        .send({ order: invalidOrder })
        .expect(400);
      
      expect(response.body).toHaveProperty('status', 'error');
    });

    it('should validate margin calculation request', async () => {
      const invalidMargin = {
        positions: 'not_an_array'
      };

      const response = await request(app)
        .post('/api/v1/margin/calculate')
        .send(invalidMargin)
        .expect(400);
      
      expect(response.body).toHaveProperty('status', 'error');
    });
  });

  describe('Option Greeks Tests', () => {
    it('should calculate Greeks for valid option', async () => {
      const validRequest = {
        symbol: 'NIFTY28NOV2526000CE',
        exchange: 'NFO',
        interest_rate: 6.5
      };

      const response = await request(app)
        .post('/api/v1/optiongreeks')
        .send(validRequest)
        .expect(200);
      
      expect(response.body).toHaveProperty('status', 'success');
      expect(response.body).toHaveProperty('greeks');
      expect(response.body.greeks).toHaveProperty('delta');
      expect(response.body.greeks).toHaveProperty('gamma');
      expect(response.body.greeks).toHaveProperty('theta');
      expect(response.body.greeks).toHaveProperty('vega');
      expect(response.body.greeks).toHaveProperty('rho');
    });

    it('should handle expired option', async () => {
      const expiredOption = {
        symbol: 'NIFTY01JAN2022000CE', // Expired option
        exchange: 'NFO'
      };

      const response = await request(app)
        .post('/api/v1/optiongreeks')
        .send(expiredOption)
        .expect(400);
      
      expect(response.body).toHaveProperty('status', 'error');
      expect(response.body.message).toContain('expired');
    });
  });

  describe('Multi Option Greeks Tests', () => {
    it('should calculate Greeks for multiple options', async () => {
      const validRequest = {
        symbols: ['NIFTY28NOV2526000CE', 'NIFTY28NOV2526100CE'],
        exchange: 'NFO',
        interest_rate: 6.5
      };

      const response = await request(app)
        .post('/api/v1/multioptiongreeks')
        .send(validRequest)
        .expect(200);
      
      expect(response.body).toHaveProperty('status', 'success');
      expect(response.body).toHaveProperty('results');
      expect(response.body.results).toHaveLength(2);
      
      response.body.results.forEach(result => {
        expect(result).toHaveProperty('greeks');
      });
    });

    it('should handle empty symbols array', async () => {
      const invalidRequest = {
        symbols: [],
        exchange: 'NFO'
      };

      const response = await request(app)
        .post('/api/v1/multioptiongreeks')
        .send(invalidRequest)
        .expect(400);
      
      expect(response.body).toHaveProperty('status', 'error');
      expect(response.body.message).toContain('non-empty array');
    });
  });

  describe('Market Data Tests', () => {
    it('should fetch market quotes', async () => {
      const response = await request(app)
        .post('/api/v1/market/quotes')
        .send({ symbol: 'NIFTY' })
        .expect(200);
      
      expect(response.body).toHaveProperty('status');
      if (response.body.status === 'success') {
        expect(response.body.data).toHaveProperty('ltp');
      }
    });

    it('should fetch instruments', async () => {
      const response = await request(app)
        .get('/api/v1/market/instruments')
        .expect(200);
      
      expect(response.body).toHaveProperty('status');
      if (response.body.status === 'success') {
        expect(Array.isArray(response.body.data)).toBe(true);
      }
    });
  });

  describe('Order Management Tests', () => {
    it('should validate order placement', async () => {
      const validOrder = {
        symbol: 'NIFTY28NOV2526000CE',
        exchange: 'NFO',
        action: 'BUY',
        quantity: 50,
        price: 150.25,
        product: 'NRML',
        pricetype: 'LIMIT'
      };

      const response = await request(app)
        .post('/api/v1/orders/place')
        .send({ order: validOrder })
        .expect(200);
      
      expect(response.body).toHaveProperty('status');
    });

    it('should handle invalid order data', async () => {
      const invalidOrder = {
        symbol: '',
        exchange: 'INVALID',
        action: 'INVALID',
        quantity: -1,
        price: -10,
        product: 'INVALID',
        pricetype: 'INVALID'
      };

      const response = await request(app)
        .post('/api/v1/orders/place')
        .send({ order: invalidOrder })
        .expect(400);
      
      expect(response.body).toHaveProperty('status', 'error');
    });
  });

  describe('Margin Calculation Tests', () => {
    it('should calculate margin for valid positions', async () => {
      const validPositions = {
        positions: [{
          symbol: 'NIFTY28NOV2526000CE',
          exchange: 'NFO',
          action: 'BUY',
          quantity: 50,
          price: 150.25,
          product: 'NRML',
          pricetype: 'LIMIT'
        }]
      };

      const response = await request(app)
        .post('/api/v1/margin/calculate')
        .send(validPositions)
        .expect(200);
      
      expect(response.body).toHaveProperty('status');
      if (response.body.status === 'success') {
        expect(response.body.data).toHaveProperty('required_margin');
      }
    });

    it('should handle empty positions array', async () => {
      const invalidPositions = {
        positions: []
      };

      const response = await request(app)
        .post('/api/v1/margin/calculate')
        .send(invalidPositions)
        .expect(400);
      
      expect(response.body).toHaveProperty('status', 'error');
    });
  });

  describe('Error Handling Tests', () => {
    it('should handle 404 for unknown endpoints', async () => {
      await request(app)
        .get('/api/v1/unknown-endpoint')
        .expect(404);
    });

    it('should handle malformed JSON', async () => {
      await request(app)
        .post('/api/v1/orders/place')
        .set('Content-Type', 'application/json')
        .send('invalid json')
        .expect(400);
    });

    it('should handle missing required fields', async () => {
      const response = await request(app)
        .post('/api/v1/optiongreeks')
        .send({})
        .expect(400);
      
      expect(response.body).toHaveProperty('status', 'error');
      expect(response.body).toHaveProperty('errors');
    });
  });
});

// Performance Tests
describe('Performance Tests', () => {
  it('should handle concurrent requests', async () => {
    const concurrentRequests = Array(50).fill().map(() => 
      request(app).get('/api/v1/health')
    );
    
    const startTime = Date.now();
    const responses = await Promise.all(concurrentRequests);
    const endTime = Date.now();
    
    expect(endTime - startTime).toBeLessThan(5000); // Should complete within 5 seconds
    expect(responses.every(r => r.status === 200)).toBe(true);
  });

  it('should handle large payload', async () => {
    const largePayload = {
      positions: Array(100).fill().map((_, index) => ({
        symbol: `SYMBOL${index}28NOV2526000CE`,
        exchange: 'NFO',
        action: 'BUY',
        quantity: 50,
        price: 150.25,
        product: 'NRML',
        pricetype: 'LIMIT'
      }))
    };

    const response = await request(app)
      .post('/api/v1/margin/calculate')
      .send(largePayload)
      .expect(200);
    
    expect(response.body).toHaveProperty('status');
  });
});

module.exports = {
  app,
  server
};
