/**
 * WebSocket Client for AI Publisher Pro
 *
 * Provides real-time updates with automatic reconnection,
 * heartbeat monitoring, and graceful fallback to polling.
 */

const WebSocketClient = {
  // Configuration
  config: {
    reconnectInterval: 3000,      // Initial reconnect delay (ms)
    maxReconnectInterval: 30000,  // Max reconnect delay (ms)
    reconnectDecay: 1.5,          // Exponential backoff factor
    heartbeatInterval: 25000,     // Heartbeat every 25s (server timeout is 30s)
    maxReconnectAttempts: 10,     // Max reconnect attempts before fallback
  },

  // State
  state: {
    ws: null,
    isConnected: false,
    reconnectAttempts: 0,
    reconnectTimer: null,
    heartbeatTimer: null,
    currentJobId: null,
    messageHandlers: new Map(),
    connectionStatusCallback: null,
    fallbackToPolling: false,
  },

  /**
   * Initialize WebSocket connection
   * @param {Function} onStatusChange - Callback for connection status changes
   */
  init(onStatusChange) {
    this.state.connectionStatusCallback = onStatusChange;
    this.connect();
  },

  /**
   * Connect to WebSocket server
   */
  connect() {
    // Don't reconnect if we've fallen back to polling
    if (this.state.fallbackToPolling) {
      console.log('[WS] Using polling fallback, not reconnecting');
      return;
    }

    // Build WebSocket URL
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;

    console.log(`[WS] Connecting to ${wsUrl}...`);
    this.updateStatus('connecting');

    try {
      this.state.ws = new WebSocket(wsUrl);
      this.setupEventHandlers();
    } catch (error) {
      console.error('[WS] Connection error:', error);
      this.handleDisconnect();
    }
  },

  /**
   * Setup WebSocket event handlers
   */
  setupEventHandlers() {
    const ws = this.state.ws;

    ws.onopen = () => {
      console.log('[WS] Connected successfully');
      this.state.isConnected = true;
      this.state.reconnectAttempts = 0;
      this.updateStatus('connected');
      this.startHeartbeat();

      // Subscribe to current job if exists
      if (this.state.currentJobId) {
        this.subscribeToJob(this.state.currentJobId);
      }
    };

    ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        this.handleMessage(message);
      } catch (error) {
        console.warn('[WS] Failed to parse message:', error);
      }
    };

    ws.onclose = (event) => {
      console.log(`[WS] Disconnected (code: ${event.code}, reason: ${event.reason})`);
      this.handleDisconnect();
    };

    ws.onerror = (error) => {
      console.error('[WS] Error:', error);
      // Error will trigger onclose, so we don't need to handle disconnect here
    };
  },

  /**
   * Handle incoming WebSocket messages
   * @param {Object} message - Parsed message object
   */
  handleMessage(message) {
    const { event, job_id } = message;

    // Log for debugging
    if (event !== 'stats_update') {
      console.log(`[WS] Received: ${event}`, message);
    }

    // Handle system events
    switch (event) {
      case 'connected':
        console.log('[WS] Server confirmed connection');
        break;

      case 'stats_update':
        // Queue stats update (heartbeat response)
        this.dispatchEvent('stats', message);
        break;

      case 'subscribed':
        console.log(`[WS] Subscribed to job: ${job_id}`);
        break;

      case 'pong':
        // Heartbeat response
        break;

      // Job-specific events
      case 'job_started':
      case 'job_progress':
      case 'job_updated':
      case 'job_completed':
      case 'job_failed':
      case 'chunk_translated':
      case 'batch_completed':
      case 'batch_exported':
        this.dispatchEvent(event, message);
        break;

      default:
        console.log(`[WS] Unknown event: ${event}`);
    }
  },

  /**
   * Dispatch event to registered handlers
   * @param {string} eventType - Event type
   * @param {Object} data - Event data
   */
  dispatchEvent(eventType, data) {
    const handlers = this.state.messageHandlers.get(eventType) || [];
    handlers.forEach(handler => {
      try {
        handler(data);
      } catch (error) {
        console.error(`[WS] Handler error for ${eventType}:`, error);
      }
    });

    // Also dispatch to 'all' handlers
    const allHandlers = this.state.messageHandlers.get('all') || [];
    allHandlers.forEach(handler => {
      try {
        handler(eventType, data);
      } catch (error) {
        console.error('[WS] All-handler error:', error);
      }
    });
  },

  /**
   * Register event handler
   * @param {string} eventType - Event type ('all' for all events)
   * @param {Function} handler - Handler function
   * @returns {Function} Unsubscribe function
   */
  on(eventType, handler) {
    if (!this.state.messageHandlers.has(eventType)) {
      this.state.messageHandlers.set(eventType, []);
    }
    this.state.messageHandlers.get(eventType).push(handler);

    // Return unsubscribe function
    return () => {
      const handlers = this.state.messageHandlers.get(eventType);
      const index = handlers.indexOf(handler);
      if (index > -1) {
        handlers.splice(index, 1);
      }
    };
  },

  /**
   * Remove all handlers for an event type
   * @param {string} eventType - Event type
   */
  off(eventType) {
    this.state.messageHandlers.delete(eventType);
  },

  /**
   * Subscribe to job updates
   * @param {string} jobId - Job ID to subscribe to
   */
  subscribeToJob(jobId) {
    this.state.currentJobId = jobId;

    if (this.state.isConnected && this.state.ws) {
      this.send({
        action: 'subscribe',
        job_id: jobId
      });
    }
  },

  /**
   * Unsubscribe from job updates
   */
  unsubscribeFromJob() {
    if (this.state.currentJobId && this.state.isConnected) {
      this.send({
        action: 'unsubscribe',
        job_id: this.state.currentJobId
      });
    }
    this.state.currentJobId = null;
  },

  /**
   * Send message to server
   * @param {Object} data - Message data
   */
  send(data) {
    if (this.state.ws && this.state.ws.readyState === WebSocket.OPEN) {
      this.state.ws.send(JSON.stringify(data));
    } else {
      console.warn('[WS] Cannot send - not connected');
    }
  },

  /**
   * Start heartbeat timer
   */
  startHeartbeat() {
    this.stopHeartbeat();

    this.state.heartbeatTimer = setInterval(() => {
      if (this.state.isConnected) {
        this.send({ action: 'ping', timestamp: Date.now() });
      }
    }, this.config.heartbeatInterval);
  },

  /**
   * Stop heartbeat timer
   */
  stopHeartbeat() {
    if (this.state.heartbeatTimer) {
      clearInterval(this.state.heartbeatTimer);
      this.state.heartbeatTimer = null;
    }
  },

  /**
   * Handle disconnection and attempt reconnect
   */
  handleDisconnect() {
    this.state.isConnected = false;
    this.stopHeartbeat();
    this.updateStatus('disconnected');

    // Check if we should fall back to polling
    if (this.state.reconnectAttempts >= this.config.maxReconnectAttempts) {
      console.log('[WS] Max reconnect attempts reached, falling back to polling');
      this.state.fallbackToPolling = true;
      this.updateStatus('polling');
      return;
    }

    // Calculate reconnect delay with exponential backoff
    const delay = Math.min(
      this.config.reconnectInterval * Math.pow(this.config.reconnectDecay, this.state.reconnectAttempts),
      this.config.maxReconnectInterval
    );

    console.log(`[WS] Reconnecting in ${delay}ms (attempt ${this.state.reconnectAttempts + 1})`);
    this.updateStatus('reconnecting');

    this.state.reconnectTimer = setTimeout(() => {
      this.state.reconnectAttempts++;
      this.connect();
    }, delay);
  },

  /**
   * Update connection status
   * @param {string} status - Status string
   */
  updateStatus(status) {
    if (this.state.connectionStatusCallback) {
      this.state.connectionStatusCallback(status, {
        isConnected: this.state.isConnected,
        reconnectAttempts: this.state.reconnectAttempts,
        fallbackToPolling: this.state.fallbackToPolling
      });
    }
  },

  /**
   * Check if WebSocket is connected
   * @returns {boolean}
   */
  isConnected() {
    return this.state.isConnected && this.state.ws?.readyState === WebSocket.OPEN;
  },

  /**
   * Check if using polling fallback
   * @returns {boolean}
   */
  isUsingPolling() {
    return this.state.fallbackToPolling;
  },

  /**
   * Force reconnect
   */
  reconnect() {
    this.state.fallbackToPolling = false;
    this.state.reconnectAttempts = 0;
    this.disconnect();
    this.connect();
  },

  /**
   * Disconnect WebSocket
   */
  disconnect() {
    this.stopHeartbeat();

    if (this.state.reconnectTimer) {
      clearTimeout(this.state.reconnectTimer);
      this.state.reconnectTimer = null;
    }

    if (this.state.ws) {
      this.state.ws.close();
      this.state.ws = null;
    }

    this.state.isConnected = false;
  },

  /**
   * Cleanup
   */
  destroy() {
    this.disconnect();
    this.state.messageHandlers.clear();
    this.state.connectionStatusCallback = null;
  }
};

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
  module.exports = WebSocketClient;
}
