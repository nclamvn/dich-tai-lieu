/**
 * Admin Dashboard - Provider Status Widget
 * AI Publisher Pro - Multi-Provider Support
 * 
 * Add this to your admin dashboard to show provider health status.
 */

// =========================================
// Provider Status Widget
// =========================================

class ProviderStatusWidget {
  constructor(containerId, options = {}) {
    this.container = document.getElementById(containerId);
    this.options = {
      apiEndpoint: '/api/v2/providers',
      refreshInterval: 30000, // 30 seconds
      ...options
    };
    
    this.providers = [];
    this.health = {};
    this.refreshTimer = null;
    
    this.init();
  }
  
  async init() {
    this.render();
    await this.loadData();
    this.startAutoRefresh();
  }
  
  render() {
    this.container.innerHTML = `
      <div class="admin-card provider-status-widget">
        <div class="card-header">
          <div class="card-title">
            <i data-lucide="cpu"></i>
            <span>AI Providers</span>
          </div>
          <button class="refresh-btn" id="refresh-providers" title="Refresh">
            <i data-lucide="refresh-cw"></i>
          </button>
        </div>
        <div class="card-content" id="provider-status-content">
          <div class="loading-state">
            <i data-lucide="loader"></i>
            <span>Loading providers...</span>
          </div>
        </div>
      </div>
    `;
    
    // Bind refresh button
    const refreshBtn = this.container.querySelector('#refresh-providers');
    refreshBtn?.addEventListener('click', () => this.loadData());
    
    // Init icons
    if (typeof lucide !== 'undefined') {
      lucide.createIcons();
    }
  }
  
  async loadData() {
    try {
      // Load providers list
      const providersRes = await fetch(`${this.options.apiEndpoint}`);
      const providersData = await providersRes.json();
      this.providers = providersData.providers || [];
      this.current = providersData.current;
      
      // Load health status
      const healthRes = await fetch(`${this.options.apiEndpoint}/health`);
      const healthData = await healthRes.json();
      this.health = healthData.providers || {};
      
      this.updateUI();
    } catch (error) {
      console.error('Failed to load provider data:', error);
      this.showError();
    }
  }
  
  updateUI() {
    const content = this.container.querySelector('#provider-status-content');
    if (!content) return;
    
    const providerColors = {
      claude: '#2A2A2A',
      openai: '#2A2A2A',
      gemini: '#2A2A2A',
      deepseek: '#2A2A2A'
    };
    
    const providerIcons = {
      claude: 'brain',
      openai: 'message-square',
      gemini: 'sparkles',
      deepseek: 'search'
    };
    
    content.innerHTML = `
      <div class="provider-list">
        ${this.providers.map(p => {
          const isOnline = this.health[p.id] === true;
          const isCurrent = this.current?.id === p.id;
          
          return `
            <div class="provider-status-item ${isCurrent ? 'current' : ''} ${!p.is_available ? 'unavailable' : ''}">
              <div class="provider-icon-small" style="background: ${providerColors[p.id] || '#666'}">
                <i data-lucide="${providerIcons[p.id] || 'cpu'}"></i>
              </div>
              <div class="provider-info">
                <div class="provider-name">${p.name}</div>
                <div class="provider-model">${p.default_model}</div>
              </div>
              <div class="provider-status-badge ${isOnline ? 'online' : 'offline'}">
                ${isOnline ? 'Online' : 'Offline'}
              </div>
              ${isCurrent ? '<div class="current-badge">Active</div>' : ''}
            </div>
          `;
        }).join('')}
      </div>
      
      <div class="provider-stats">
        <div class="stat">
          <span class="stat-value">${Object.values(this.health).filter(v => v).length}</span>
          <span class="stat-label">Online</span>
        </div>
        <div class="stat">
          <span class="stat-value">${this.providers.filter(p => p.is_available).length}</span>
          <span class="stat-label">Available</span>
        </div>
        <div class="stat">
          <span class="stat-value">${this.current?.name || 'None'}</span>
          <span class="stat-label">Current</span>
        </div>
      </div>
    `;
    
    // Re-init icons
    if (typeof lucide !== 'undefined') {
      lucide.createIcons();
    }
  }
  
  showError() {
    const content = this.container.querySelector('#provider-status-content');
    if (!content) return;
    
    content.innerHTML = `
      <div class="error-state">
        <i data-lucide="alert-circle"></i>
        <span>Failed to load providers</span>
        <button class="retry-btn" onclick="this.closest('.provider-status-widget').widget.loadData()">
          Retry
        </button>
      </div>
    `;
    
    if (typeof lucide !== 'undefined') {
      lucide.createIcons();
    }
  }
  
  startAutoRefresh() {
    if (this.refreshTimer) {
      clearInterval(this.refreshTimer);
    }
    
    this.refreshTimer = setInterval(() => {
      this.loadData();
    }, this.options.refreshInterval);
  }
  
  stopAutoRefresh() {
    if (this.refreshTimer) {
      clearInterval(this.refreshTimer);
      this.refreshTimer = null;
    }
  }
  
  destroy() {
    this.stopAutoRefresh();
    this.container.innerHTML = '';
  }
}

// =========================================
// CSS Styles
// =========================================

const PROVIDER_STATUS_CSS = `
/* Provider Status Widget */
.provider-status-widget {
  background: var(--bg-card);
  border-radius: 12px;
  overflow: hidden;
}

.provider-status-widget .card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  border-bottom: 1px solid var(--border-color);
}

.provider-status-widget .card-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 600;
}

.provider-status-widget .card-title svg {
  width: 18px;
  height: 18px;
  color: var(--accent-primary);
}

.provider-status-widget .refresh-btn {
  width: 32px;
  height: 32px;
  border: none;
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.provider-status-widget .refresh-btn:hover {
  background: var(--bg-secondary);
  color: var(--text-primary);
}

.provider-status-widget .refresh-btn svg {
  width: 16px;
  height: 16px;
}

.provider-status-widget .card-content {
  padding: 16px;
}

/* Provider List */
.provider-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 16px;
}

.provider-status-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  background: var(--bg-secondary);
  border-radius: 8px;
  position: relative;
}

.provider-status-item.current {
  border: 1px solid var(--accent-primary);
  background: rgba(99, 102, 241, 0.1);
}

.provider-status-item.unavailable {
  opacity: 0.5;
}

.provider-icon-small {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.provider-icon-small svg {
  width: 16px;
  height: 16px;
  color: white;
}

.provider-info {
  flex: 1;
}

.provider-info .provider-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}

.provider-info .provider-model {
  font-size: 11px;
  color: var(--text-muted);
}

.provider-status-badge {
  padding: 4px 8px;
  font-size: 10px;
  font-weight: 600;
  border-radius: 4px;
  text-transform: uppercase;
}

.provider-status-badge.online {
  background: rgba(16, 185, 129, 0.2);
  color: var(--accent-success);
}

.provider-status-badge.offline {
  background: rgba(239, 68, 68, 0.2);
  color: var(--accent-error);
}

.current-badge {
  position: absolute;
  top: -6px;
  right: 8px;
  padding: 2px 6px;
  font-size: 9px;
  font-weight: 600;
  background: var(--accent-primary);
  color: white;
  border-radius: 4px;
}

/* Stats */
.provider-stats {
  display: flex;
  gap: 16px;
  padding-top: 12px;
  border-top: 1px solid var(--border-color);
}

.provider-stats .stat {
  flex: 1;
  text-align: center;
}

.provider-stats .stat-value {
  display: block;
  font-size: 18px;
  font-weight: 700;
  color: var(--text-primary);
}

.provider-stats .stat-label {
  font-size: 11px;
  color: var(--text-muted);
}

/* Loading/Error States */
.loading-state,
.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 24px;
  color: var(--text-muted);
}

.loading-state svg,
.error-state svg {
  width: 24px;
  height: 24px;
  animation: spin 1s linear infinite;
}

.error-state svg {
  color: var(--accent-error);
  animation: none;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.retry-btn {
  padding: 6px 12px;
  background: var(--accent-primary);
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 12px;
}
`;

// Auto-inject CSS
function injectProviderStatusStyles() {
  if (document.getElementById('provider-status-styles')) return;
  
  const style = document.createElement('style');
  style.id = 'provider-status-styles';
  style.textContent = PROVIDER_STATUS_CSS;
  document.head.appendChild(style);
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', injectProviderStatusStyles);
} else {
  injectProviderStatusStyles();
}

// Export
window.ProviderStatusWidget = ProviderStatusWidget;
