/**
 * k6 Load Testing Configuration
 * AI Publisher Pro - Performance Testing
 *
 * Install k6: brew install k6 (macOS) or download from https://k6.io
 * Run: k6 run tests/load/basic.js
 */

export const config = {
  // Base URL for the application
  baseUrl: __ENV.BASE_URL || 'http://localhost:3001',

  // Test thresholds
  thresholds: {
    // 95% of requests should complete within 500ms
    http_req_duration: ['p(95)<500'],

    // 99% of requests should complete within 1500ms
    'http_req_duration{type:api}': ['p(99)<1500'],

    // Error rate should be below 1%
    http_req_failed: ['rate<0.01'],

    // Health check should be fast
    'http_req_duration{name:health}': ['p(95)<100'],
  },

  // Stages for different test scenarios
  stages: {
    // Smoke test - verify the system works
    smoke: [
      { duration: '1m', target: 5 },
    ],

    // Load test - typical load
    load: [
      { duration: '2m', target: 10 },
      { duration: '5m', target: 10 },
      { duration: '2m', target: 0 },
    ],

    // Stress test - find breaking point
    stress: [
      { duration: '2m', target: 10 },
      { duration: '5m', target: 50 },
      { duration: '2m', target: 100 },
      { duration: '5m', target: 100 },
      { duration: '5m', target: 0 },
    ],

    // Spike test - sudden traffic increase
    spike: [
      { duration: '1m', target: 5 },
      { duration: '10s', target: 100 },
      { duration: '3m', target: 100 },
      { duration: '10s', target: 5 },
      { duration: '1m', target: 5 },
    ],

    // Soak test - extended duration
    soak: [
      { duration: '2m', target: 20 },
      { duration: '30m', target: 20 },
      { duration: '2m', target: 0 },
    ],
  },

  // Tags for organizing metrics
  tags: {
    testType: __ENV.TEST_TYPE || 'load',
  },
};

export default config;
