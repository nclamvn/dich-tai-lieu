/**
 * AI Provider Selector - Complete UI Component
 * AI Publisher Pro - Multi-Provider Support
 * 
 * This component provides a visual interface for selecting AI providers.
 * 
 * INTEGRATION:
 * 1. Add the CSS to your styles.css
 * 2. Add the HTML placeholder to your app.html
 * 3. Include this JS file
 * 4. Initialize: new AIProviderSelector('container-id')
 */

// =========================================
// Provider Data
// =========================================

const AI_PROVIDERS = {
  claude: {
    id: 'claude',
    name: 'Claude',
    company: 'Anthropic',
    icon: 'brain',
    color: '#9CA3AF',
    gradient: '#2A2A2A',
    description: 'Best for nuanced, thoughtful translation',
    supportsVision: true,
    supportsStreaming: true,
    models: [
      { id: 'claude-sonnet-4-20250514', name: 'Claude Sonnet 4', badge: '⭐ Recommended' },
      { id: 'claude-3-5-sonnet-20241022', name: 'Claude 3.5 Sonnet', badge: '' },
      { id: 'claude-3-5-haiku-20241022', name: 'Claude 3.5 Haiku', badge: '⚡ Fast' },
    ]
  },
  openai: {
    id: 'openai',
    name: 'ChatGPT',
    company: 'OpenAI',
    icon: 'message-square',
    color: '#9CA3AF',
    gradient: '#2A2A2A',
    description: 'Versatile, multimodal AI',
    supportsVision: true,
    supportsStreaming: true,
    models: [
      { id: 'gpt-4o', name: 'GPT-4o', badge: '⭐ Recommended' },
      { id: 'gpt-4o-mini', name: 'GPT-4o Mini', badge: '⚡ Fast' },
      { id: 'gpt-4-turbo', name: 'GPT-4 Turbo', badge: '' },
    ]
  },
  gemini: {
    id: 'gemini',
    name: 'Gemini',
    company: 'Google',
    icon: 'sparkles',
    color: '#9CA3AF',
    gradient: '#2A2A2A',
    description: 'Fast, multimodal AI from Google',
    supportsVision: true,
    supportsStreaming: true,
    models: [
      { id: 'gemini-2.0-flash-exp', name: 'Gemini 2.0 Flash', badge: '⭐ Recommended' },
      { id: 'gemini-1.5-pro', name: 'Gemini 1.5 Pro', badge: '' },
      { id: 'gemini-1.5-flash', name: 'Gemini 1.5 Flash', badge: '⚡ Fast' },
    ]
  },
  deepseek: {
    id: 'deepseek',
    name: 'DeepSeek',
    company: 'DeepSeek',
    icon: 'search',
    color: '#9CA3AF',
    gradient: '#2A2A2A',
    description: 'Cost-effective, strong multilingual',
    supportsVision: false,
    supportsStreaming: true,
    models: [
      { id: 'deepseek-chat', name: 'DeepSeek V3', badge: '⭐ Recommended' },
      { id: 'deepseek-reasoner', name: 'DeepSeek R1', badge: '🧠 Reasoning' },
    ]
  }
};

// =========================================
// AI Provider Selector Class
// =========================================

class AIProviderSelector {
  constructor(containerId, options = {}) {
    this.container = document.getElementById(containerId);
    if (!this.container) {
      console.error(`Container #${containerId} not found`);
      return;
    }
    
    this.options = {
      defaultProvider: 'claude',
      showModels: true,
      showCapabilities: true,
      compact: false,
      apiEndpoint: '/api/v2/providers',
      onProviderChange: null,
      onModelChange: null,
      onError: null,
      ...options
    };
    
    this.currentProvider = this.options.defaultProvider;
    this.currentModel = null;
    this.providerStatus = {};
    this.isLoading = false;
    
    this.init();
  }
  
  async init() {
    this.render();
    this.bindEvents();
    
    // Load provider status from API
    await this.loadProviderStatus();
    
    // Select default provider
    this.selectProvider(this.options.defaultProvider, false);
  }
  
  render() {
    const compact = this.options.compact;
    
    this.container.innerHTML = `
      <div class="ai-provider-selector ${compact ? 'compact' : ''}">
        <!-- Header -->
        <div class="provider-header">
          <div class="provider-title">
            <i data-lucide="cpu"></i>
            <span>AI Provider</span>
          </div>
          <div class="provider-status" id="provider-status">
            <span class="status-dot"></span>
            <span class="status-text">Checking...</span>
          </div>
        </div>
        
        <!-- Provider Cards -->
        <div class="provider-cards" id="provider-cards">
          ${Object.values(AI_PROVIDERS).map(p => this.renderProviderCard(p)).join('')}
        </div>
        
        <!-- Model Selector -->
        ${this.options.showModels ? `
          <div class="model-selector" id="model-selector">
            <label class="model-label">
              <i data-lucide="layers"></i>
              <span>Model</span>
            </label>
            <select id="model-select" class="model-select">
              <!-- Populated dynamically -->
            </select>
          </div>
        ` : ''}
        
        <!-- Capabilities -->
        ${this.options.showCapabilities ? `
          <div class="provider-capabilities" id="provider-capabilities">
            <!-- Populated dynamically -->
          </div>
        ` : ''}
      </div>
    `;
    
    // Initialize Lucide icons
    if (typeof lucide !== 'undefined') {
      lucide.createIcons();
    }
  }
  
  renderProviderCard(provider) {
    return `
      <div class="provider-card" data-provider="${provider.id}" title="${provider.description}">
        <div class="provider-icon" style="background: ${provider.gradient}">
          <i data-lucide="${provider.icon}"></i>
        </div>
        <div class="provider-name">${provider.name}</div>
        <div class="provider-company">${provider.company}</div>
        ${!provider.supportsVision ? '<div class="provider-badge no-vision">Text</div>' : ''}
        <div class="provider-check">
          <i data-lucide="check"></i>
        </div>
      </div>
    `;
  }
  
  bindEvents() {
    // Provider card clicks
    const cards = this.container.querySelectorAll('.provider-card');
    cards.forEach(card => {
      card.addEventListener('click', () => {
        if (!card.classList.contains('disabled')) {
          this.selectProvider(card.dataset.provider, true);
        }
      });
    });
    
    // Model select change
    const modelSelect = this.container.querySelector('#model-select');
    if (modelSelect) {
      modelSelect.addEventListener('change', (e) => {
        this.currentModel = e.target.value;
        this.saveToAPI();
        
        if (this.options.onModelChange) {
          this.options.onModelChange(this.currentModel, this.currentProvider);
        }
      });
    }
  }
  
  async loadProviderStatus() {
    try {
      const response = await fetch(`${this.options.apiEndpoint}/health`);
      if (response.ok) {
        const data = await response.json();
        this.providerStatus = data.providers || {};
        this.updateProviderAvailability();
        this.updateStatusIndicator(data.status);
      }
    } catch (error) {
      console.warn('Could not load provider status:', error);
      // Enable all providers as fallback
      Object.keys(AI_PROVIDERS).forEach(id => {
        this.providerStatus[id] = true;
      });
    }
  }
  
  updateProviderAvailability() {
    const cards = this.container.querySelectorAll('.provider-card');
    cards.forEach(card => {
      const providerId = card.dataset.provider;
      const isAvailable = this.providerStatus[providerId] !== false;
      
      card.classList.toggle('disabled', !isAvailable);
      card.classList.toggle('unavailable', !isAvailable);
      
      if (!isAvailable) {
        card.title = `${AI_PROVIDERS[providerId].name} - API key not configured`;
      }
    });
  }
  
  updateStatusIndicator(status) {
    const statusEl = this.container.querySelector('#provider-status');
    if (!statusEl) return;
    
    const dot = statusEl.querySelector('.status-dot');
    const text = statusEl.querySelector('.status-text');
    
    const statusConfig = {
      healthy: { color: 'var(--accent-success)', text: 'All systems online' },
      degraded: { color: 'var(--accent-warning)', text: 'Some providers unavailable' },
      unhealthy: { color: 'var(--accent-error)', text: 'Providers offline' }
    };
    
    const config = statusConfig[status] || statusConfig.degraded;
    dot.style.background = config.color;
    text.textContent = config.text;
  }
  
  selectProvider(providerId, saveToAPI = true) {
    const provider = AI_PROVIDERS[providerId];
    if (!provider) return;
    
    this.currentProvider = providerId;
    
    // Update card states
    const cards = this.container.querySelectorAll('.provider-card');
    cards.forEach(card => {
      card.classList.toggle('selected', card.dataset.provider === providerId);
    });
    
    // Update model selector
    if (this.options.showModels) {
      this.updateModelSelect(provider);
    }
    
    // Update capabilities
    if (this.options.showCapabilities) {
      this.updateCapabilities(provider);
    }
    
    // Save to API
    if (saveToAPI) {
      this.saveToAPI();
    }
    
    // Callback
    if (this.options.onProviderChange) {
      this.options.onProviderChange(providerId, provider);
    }
  }
  
  updateModelSelect(provider) {
    const select = this.container.querySelector('#model-select');
    if (!select) return;
    
    select.innerHTML = provider.models.map(m => `
      <option value="${m.id}">
        ${m.name} ${m.badge}
      </option>
    `).join('');
    
    this.currentModel = select.value;
  }
  
  updateCapabilities(provider) {
    const container = this.container.querySelector('#provider-capabilities');
    if (!container) return;
    
    container.innerHTML = `
      <div class="capability ${provider.supportsVision ? 'enabled' : 'disabled'}">
        <i data-lucide="${provider.supportsVision ? 'eye' : 'eye-off'}"></i>
        <span>Vision ${provider.supportsVision ? '✓' : '✗'}</span>
      </div>
      <div class="capability ${provider.supportsStreaming ? 'enabled' : 'disabled'}">
        <i data-lucide="zap"></i>
        <span>Streaming ${provider.supportsStreaming ? '✓' : '✗'}</span>
      </div>
    `;
    
    // Re-init icons
    if (typeof lucide !== 'undefined') {
      lucide.createIcons({ icons: container });
    }
  }
  
  async saveToAPI() {
    if (this.isLoading) return;
    
    this.isLoading = true;
    
    try {
      const response = await fetch(`${this.options.apiEndpoint}/set`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          provider: this.currentProvider,
          model: this.currentModel
        })
      });
      
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to set provider');
      }
      
      const data = await response.json();
      console.log('Provider set:', data);
      
    } catch (error) {
      console.error('Failed to save provider:', error);
      if (this.options.onError) {
        this.options.onError(error);
      }
    } finally {
      this.isLoading = false;
    }
  }
  
  // Public API
  getSelectedProvider() {
    return {
      provider: this.currentProvider,
      model: this.currentModel,
      info: AI_PROVIDERS[this.currentProvider]
    };
  }
  
  setProvider(providerId, model = null) {
    this.selectProvider(providerId, true);
    if (model) {
      const select = this.container.querySelector('#model-select');
      if (select) {
        select.value = model;
        this.currentModel = model;
      }
    }
  }
  
  async refresh() {
    await this.loadProviderStatus();
  }
}

// =========================================
// CSS Styles
// =========================================

const AI_PROVIDER_CSS = `
/* AI Provider Selector */
.ai-provider-selector {
  background: var(--bg-secondary, #1a1a2e);
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 16px;
}

.ai-provider-selector.compact {
  padding: 12px;
}

/* Header */
.provider-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.provider-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary, #fff);
}

.provider-title svg {
  width: 16px;
  height: 16px;
  color: var(--accent-primary, #6366f1);
}

.provider-status {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  color: var(--text-muted, #888);
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--accent-success, #10b981);
}

/* Provider Cards */
.provider-cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
  margin-bottom: 12px;
}

.compact .provider-cards {
  grid-template-columns: repeat(2, 1fr);
}

.provider-card {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 12px 8px;
  background: var(--bg-card, #242442);
  border: 2px solid transparent;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.provider-card:hover {
  background: var(--bg-card-hover, #2a2a4a);
  transform: translateY(-2px);
}

.provider-card.selected {
  border-color: var(--accent-primary, #6366f1);
  background: rgba(99, 102, 241, 0.1);
}

.provider-card.disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.provider-card.disabled:hover {
  transform: none;
}

.provider-icon {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 6px;
}

.provider-icon svg {
  width: 20px;
  height: 20px;
  color: white;
}

.provider-name {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-primary, #fff);
  margin-bottom: 2px;
}

.provider-company {
  font-size: 10px;
  color: var(--text-muted, #888);
}

.provider-badge {
  position: absolute;
  top: 4px;
  right: 4px;
  padding: 2px 6px;
  font-size: 9px;
  font-weight: 600;
  border-radius: 4px;
  background: var(--accent-warning, #f59e0b);
  color: white;
}

.provider-badge.no-vision {
  background: var(--text-muted, #666);
}

.provider-check {
  position: absolute;
  top: 4px;
  left: 4px;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: var(--accent-primary, #6366f1);
  display: none;
  align-items: center;
  justify-content: center;
}

.provider-check svg {
  width: 12px;
  height: 12px;
  color: white;
}

.provider-card.selected .provider-check {
  display: flex;
}

/* Model Selector */
.model-selector {
  margin-bottom: 12px;
}

.model-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  color: var(--text-muted, #888);
  margin-bottom: 6px;
}

.model-label svg {
  width: 12px;
  height: 12px;
}

.model-select {
  width: 100%;
  padding: 10px 12px;
  background: var(--bg-card, #242442);
  border: 1px solid var(--border-color, #333);
  border-radius: 8px;
  color: var(--text-primary, #fff);
  font-size: 13px;
  cursor: pointer;
  transition: border-color 0.2s;
}

.model-select:hover {
  border-color: var(--accent-primary, #6366f1);
}

.model-select:focus {
  outline: none;
  border-color: var(--accent-primary, #6366f1);
  box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.2);
}

/* Capabilities */
.provider-capabilities {
  display: flex;
  gap: 12px;
}

.capability {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  color: var(--text-muted, #888);
}

.capability svg {
  width: 12px;
  height: 12px;
}

.capability.enabled {
  color: var(--accent-success, #10b981);
}

.capability.disabled {
  color: var(--text-muted, #666);
  opacity: 0.6;
}

/* Dark mode support */
@media (prefers-color-scheme: light) {
  .ai-provider-selector {
    background: #f8f9fa;
  }
  
  .provider-card {
    background: #fff;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
  }
  
  .provider-card:hover {
    background: #f0f0f5;
  }
  
  .model-select {
    background: #fff;
  }
}
`;

// =========================================
// Auto-inject CSS
// =========================================

function injectProviderStyles() {
  if (document.getElementById('ai-provider-styles')) return;
  
  const style = document.createElement('style');
  style.id = 'ai-provider-styles';
  style.textContent = AI_PROVIDER_CSS;
  document.head.appendChild(style);
}

// Inject styles on load
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', injectProviderStyles);
} else {
  injectProviderStyles();
}

// =========================================
// Exports
// =========================================

window.AIProviderSelector = AIProviderSelector;
window.AI_PROVIDERS = AI_PROVIDERS;

// Export for ES modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { AIProviderSelector, AI_PROVIDERS };
}
