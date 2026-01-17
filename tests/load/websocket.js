/**
 * k6 WebSocket Load Test
 * Tests WebSocket connections under load
 *
 * Run: k6 run tests/load/websocket.js
 */

import { check, sleep } from 'k6';
import ws from 'k6/ws';
import { Rate, Counter, Trend } from 'k6/metrics';
import config from './k6.config.js';

// Custom metrics
const wsConnectionErrors = new Rate('ws_connection_errors');
const wsMessagesReceived = new Counter('ws_messages_received');
const wsMessagesSent = new Counter('ws_messages_sent');
const wsConnectionDuration = new Trend('ws_connection_duration');
const wsMessageLatency = new Trend('ws_message_latency');

// Test options
export const options = {
  stages: [
    { duration: '30s', target: 10 },
    { duration: '2m', target: 20 },
    { duration: '30s', target: 50 },
    { duration: '1m', target: 50 },
    { duration: '30s', target: 0 },
  ],
  thresholds: {
    ws_connection_errors: ['rate<0.1'],
    ws_message_latency: ['p(95)<500'],
  },
};

const BASE_URL = config.baseUrl.replace('http', 'ws');
const WS_URL = `${BASE_URL}/ws`;

/**
 * Main test function
 */
export default function() {
  const connectionStart = Date.now();
  let messagesReceived = 0;
  let connected = false;

  const res = ws.connect(WS_URL, {}, function(socket) {
    connected = true;

    socket.on('open', function() {
      console.log('WebSocket connected');
      wsConnectionDuration.add(Date.now() - connectionStart);

      // Send ping to verify connection
      const pingStart = Date.now();
      socket.send(JSON.stringify({
        action: 'ping',
        timestamp: pingStart,
      }));
      wsMessagesSent.add(1);
    });

    socket.on('message', function(message) {
      messagesReceived++;
      wsMessagesReceived.add(1);

      try {
        const data = JSON.parse(message);

        // Handle pong message
        if (data.event === 'pong' || data.type === 'pong') {
          if (data.timestamp) {
            wsMessageLatency.add(Date.now() - data.timestamp);
          }
        }

        // Handle connected event
        if (data.event === 'connected') {
          console.log('Server confirmed connection');
        }

        // Handle stats update
        if (data.event === 'stats_update') {
          // Stats received
        }
      } catch (e) {
        console.log(`Error parsing message: ${e}`);
      }
    });

    socket.on('error', function(e) {
      console.log(`WebSocket error: ${e}`);
      wsConnectionErrors.add(1);
    });

    socket.on('close', function() {
      console.log('WebSocket closed');
    });

    // Keep connection alive for a while
    socket.setTimeout(function() {
      // Subscribe to a test job
      socket.send(JSON.stringify({
        action: 'subscribe',
        job_id: `load-test-${__VU}-${Date.now()}`,
      }));
      wsMessagesSent.add(1);
    }, 1000);

    // Send periodic pings
    socket.setInterval(function() {
      socket.send(JSON.stringify({
        action: 'ping',
        timestamp: Date.now(),
      }));
      wsMessagesSent.add(1);
    }, 5000);

    // Close after test duration
    socket.setTimeout(function() {
      socket.close();
    }, 30000);
  });

  check(res, {
    'WebSocket connected successfully': () => connected,
    'Received at least one message': () => messagesReceived > 0,
  });

  if (!connected) {
    wsConnectionErrors.add(1);
  }

  sleep(1);
}
