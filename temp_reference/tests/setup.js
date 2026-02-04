// Jest setup file for testing environment
const { execSync } = require('child_process');

// Set test environment variables
process.env.NODE_ENV = 'test';
process.env.JWT_SECRET = 'test-jwt-secret-key-for-testing';
process.env.API_KEY_PEPPER = 'test-api-key-pepper-for-testing';

// Mock external services if needed
jest.mock('./services/option-greeks-service');

// Global test timeout
jest.setTimeout(30000);

// Setup and teardown hooks
beforeAll(() => {
  console.log('🧪 Setting up test environment');
});

afterAll(() => {
  console.log('🧹 Test environment cleanup');
});

beforeEach(() => {
  // Clear any test-specific mocks
  jest.clearAllMocks();
});
