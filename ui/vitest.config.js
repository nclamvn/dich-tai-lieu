import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    // Use jsdom for DOM testing
    environment: 'jsdom',

    // Global test setup
    setupFiles: ['./tests/setup.js'],

    // Include patterns
    include: ['./tests/**/*.test.js'],

    // Coverage configuration
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html', 'lcov'],
      include: ['app/**/*.js'],
      exclude: [
        'node_modules',
        'tests',
        '**/*.test.js',
        '**/*.spec.js'
      ],
      thresholds: {
        statements: 50,
        branches: 50,
        functions: 50,
        lines: 50
      }
    },

    // Reporter
    reporters: ['verbose', 'html'],

    // Globals
    globals: true,

    // Timeout
    testTimeout: 10000
  }
});
