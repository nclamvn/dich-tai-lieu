/**
 * Publisher Studio Main Application
 * AI Publisher Pro - Core Application Logic
 * With Lucide Icons Support
 */

const PublisherApp = {
  // State
  state: {
    file: null,
    files: [], // For batch mode
    profile: 'novel',
    sourceLang: 'en',
    targetLang: 'vi',
    outputFormats: ['docx', 'pdf'],
    useVision: true,
    mode: 'single', // single or batch
    job: null,
    pollInterval: null,
    aiProvider: 'claude', // AI provider: claude, openai, gemini, deepseek
    costMode: 'balanced', // economy, balanced, quality
  },

  // Cost mode configurations
  costModeConfig: {
    economy: {
      provider: 'gemini',
      model: 'gemini-1.5-flash',
      useVision: false,
      costPerPage: 0.001,  // $0.075/$0.30 per 1M tokens - cheapest
    },
    balanced: {
      provider: 'openai',
      model: 'gpt-4o-mini',
      useVision: true,
      costPerPage: 0.004,  // $0.15/$0.60 per 1M tokens - best balance
    },
    quality: {
      provider: 'claude',
      model: 'claude-sonnet-4-20250514',
      useVision: true,
      costPerPage: 0.05,
    },
  },
  
  // API Base
  API_BASE: '/api/v2',
  
  // Profiles data
  profiles: [],
  
  // Profile icons (Lucide icon names)
  profileIcons: {
    novel: 'book-open',
    arxiv_paper: 'flask-conical',
    business_report: 'bar-chart-3',
    legal_document: 'scale',
    medical_document: 'heart-pulse',
    technical_manual: 'code',
    news_article: 'newspaper',
    textbook: 'graduation-cap',
    marketing: 'megaphone',
    poetry: 'feather',
    screenplay: 'clapperboard',
    game_localization: 'gamepad-2',
  },
  
  // Format icons
  formatIcons: {
    docx: 'file-text',
    pdf: 'file-type',
    epub: 'book',
    html: 'globe',
  },

  // Language names for display
  languageNames: {
    en: 'Tiếng Anh',
    zh: 'Tiếng Trung',
    ja: 'Tiếng Nhật',
    ko: 'Tiếng Hàn',
    fr: 'Tiếng Pháp',
    de: 'Tiếng Đức',
    es: 'Tiếng Tây Ban Nha',
    ru: 'Tiếng Nga',
    vi: 'Tiếng Việt',
    auto: 'Tự động phát hiện',
  },
  
  // Initialize
  async init() {
    console.log('🚀 Publisher Studio initializing...');

    // Load profiles
    await this.loadProfiles();

    // Bind events
    this.bindEvents();

    // Refresh Lucide icons
    this.refreshIcons();

    // Check for running job and auto-reconnect
    await this.checkRunningJob();

    console.log('✅ Publisher Studio ready');
  },

  // Check for running job on page load
  async checkRunningJob() {
    // First try localStorage
    const savedJobId = localStorage.getItem('currentJobId');

    try {
      // Try to get current running job from server
      const res = await fetch(`${this.API_BASE}/jobs/current`);

      if (res.ok) {
        const job = await res.json();
        console.log('🔄 Found running job:', job.job_id);

        // Save to localStorage for future
        localStorage.setItem('currentJobId', job.job_id);

        this.state.job = job;

        // Show progress view
        this.switchTab('progress');

        // Update UI with current job info
        const fileNameEl = document.getElementById('selected-file-name');
        if (fileNameEl) fileNameEl.textContent = job.source_file || 'Unknown';

        // Start polling
        this.startPolling(job.job_id);
        this.updateJobProgress(job);

        this.showToast('Đã kết nối lại job đang chạy', 'success');
        return;
      }

      // No running job on server, check localStorage for completed job
      if (savedJobId) {
        const jobRes = await fetch(`${this.API_BASE}/jobs/${savedJobId}`);
        if (jobRes.ok) {
          const job = await jobRes.json();
          if (job.status === 'complete') {
            this.state.job = job;
            this.onJobComplete(job);
          }
        }
        localStorage.removeItem('currentJobId');
      }

    } catch (e) {
      console.error('Failed to check running job:', e);
      localStorage.removeItem('currentJobId');
    }
  },
  
  // Refresh Lucide icons
  refreshIcons() {
    if (typeof lucide !== 'undefined') {
      lucide.createIcons();
    }
  },
  
  // Load publishing profiles
  async loadProfiles() {
    try {
      const res = await fetch(`${this.API_BASE}/profiles`);
      const data = await res.json();
      this.profiles = data.profiles || [];
      this.renderProfiles();
    } catch (e) {
      console.error('Failed to load profiles:', e);
      // Use defaults
      this.profiles = [
        { id: 'novel', name: 'Novel / Fiction', description: 'Literary works with dialogue', genre: 'fiction' },
        { id: 'arxiv_paper', name: 'Academic Paper', description: 'Scientific papers with formulas', genre: 'academic' },
        { id: 'business_report', name: 'Business Report', description: 'Reports with tables and charts', genre: 'business' },
        { id: 'legal_document', name: 'Legal Document', description: 'Contracts and legal texts', genre: 'legal' },
        { id: 'technical_manual', name: 'Technical Manual', description: 'Technical documentation', genre: 'technical' },
        { id: 'news_article', name: 'News Article', description: 'Journalistic content', genre: 'news' },
        { id: 'textbook', name: 'Textbook', description: 'Educational materials', genre: 'education' },
        { id: 'marketing', name: 'Marketing', description: 'Promotional content', genre: 'marketing' },
      ];
      this.renderProfiles();
    }
  },
  
  // Render profile dropdown
  renderProfiles() {
    const dropdown = document.getElementById('profile-dropdown');
    if (!dropdown) return;
    
    dropdown.innerHTML = this.profiles.map(p => `
      <div class="profile-option ${p.id === this.state.profile ? 'selected' : ''}" 
           data-profile="${p.id}">
        <span class="profile-icon">
          <i data-lucide="${this.profileIcons[p.id] || 'file'}"></i>
        </span>
        <div class="profile-info">
          <span class="profile-name">${p.name}</span>
          <span class="profile-desc">${p.description}</span>
        </div>
      </div>
    `).join('');
    
    // Update selected display
    this.updateProfileDisplay();
    this.refreshIcons();
  },
  
  // Update profile display
  updateProfileDisplay() {
    const profile = this.profiles.find(p => p.id === this.state.profile);
    if (!profile) return;

    const selected = document.getElementById('profile-selected');
    if (selected) {
      selected.querySelector('.profile-icon').innerHTML = `<i data-lucide="${this.profileIcons[profile.id] || 'file'}"></i>`;
      selected.querySelector('.profile-name').textContent = profile.name;
      selected.querySelector('.profile-desc').textContent = profile.description;
      this.refreshIcons();
    }
  },

  // Provider display info
  providerDisplayInfo: {
    claude: { name: 'Claude Sonnet 4', company: 'Anthropic', icon: 'brain', bg: '#2A2A2A', vision: true, stream: true },
    openai: { name: 'GPT-4o', company: 'OpenAI', icon: 'message-square', bg: '#2A2A2A', vision: true, stream: true },
    gemini: { name: 'Gemini 2.0 Flash', company: 'Google', icon: 'sparkles', bg: '#2A2A2A', vision: true, stream: true },
    deepseek: { name: 'DeepSeek V3', company: 'DeepSeek', icon: 'search', bg: '#2A2A2A', vision: false, stream: true },
  },

  // Update provider display in the selected card
  updateProviderDisplay(provider, apiData = null) {
    const info = this.providerDisplayInfo[provider];
    if (!info) return;

    const selectedEl = document.getElementById('provider-selected');
    if (!selectedEl) return;

    // Update logo - monochrome
    const logoEl = selectedEl.querySelector('.provider-logo');
    if (logoEl) {
      logoEl.style.background = info.bg;
      logoEl.style.border = '1px solid #404040';
      logoEl.className = `provider-logo w-9 h-9 min-w-[36px] flex items-center justify-center rounded-lg`;
      logoEl.style.color = '#9CA3AF';
      logoEl.innerHTML = `<i data-lucide="${info.icon}" class="w-[18px] h-[18px]"></i>`;
    }

    // Update name and company
    const nameEl = selectedEl.querySelector('.provider-name');
    const companyEl = selectedEl.querySelector('.provider-company');
    if (nameEl) nameEl.textContent = apiData?.model || info.name;
    if (companyEl) companyEl.textContent = info.company;

    // Update badges - monochrome
    const badgesEl = selectedEl.querySelector('.provider-badges');
    if (badgesEl) {
      badgesEl.innerHTML = `
        ${info.vision ? `<span class="badge w-[22px] h-[22px] inline-flex items-center justify-center rounded text-gray-400" style="background:#2A2A2A;" title="Vision"><i data-lucide="eye" class="w-3 h-3"></i></span>` : ''}
        ${info.stream ? `<span class="badge w-[22px] h-[22px] inline-flex items-center justify-center rounded text-gray-400" style="background:#2A2A2A;" title="Streaming"><i data-lucide="zap" class="w-3 h-3"></i></span>` : ''}
      `;
    }

    this.refreshIcons();
  },

  // Load current AI provider state from server
  async loadProviderState() {
    try {
      const res = await fetch(`${this.API_BASE}/providers/current`);
      if (res.ok) {
        const data = await res.json();
        this.state.aiProvider = data.provider;

        // Update selected display
        this.updateProviderDisplay(data.provider, data);

        // Update dropdown options
        document.querySelectorAll('.provider-option').forEach(option => {
          const isActive = option.dataset.provider === data.provider;
          option.classList.toggle('active', isActive);
          const statusEl = option.querySelector('.provider-status');
          if (statusEl) {
            statusEl.innerHTML = isActive ? '<i data-lucide="check-circle"></i>' : '';
          }
        });

        this.refreshIcons();
      }
    } catch (e) {
      console.log('Provider state not available:', e.message);
    }

    // Also check which providers are available
    try {
      const res = await fetch(`${this.API_BASE}/providers`);
      if (res.ok) {
        const data = await res.json();
        const availableIds = data.providers
          .filter(p => p.is_available)
          .map(p => p.id);

        // Mark unavailable providers in dropdown
        document.querySelectorAll('.provider-option').forEach(option => {
          if (!availableIds.includes(option.dataset.provider)) {
            option.classList.add('unavailable');
          }
        });
      }
    } catch (e) {
      console.log('Provider list not available');
    }
  },

  // Bind events
  bindEvents() {
    // Mode toggle
    document.querySelectorAll('.mode-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const mode = btn.dataset.mode;
        this.setMode(mode);
      });
    });
    
    // Profile selector
    const profileSelected = document.getElementById('profile-selected');
    const profileDropdown = document.getElementById('profile-dropdown');
    
    profileSelected?.addEventListener('click', () => {
      profileDropdown?.classList.toggle('hidden');
    });
    
    profileDropdown?.addEventListener('click', (e) => {
      const option = e.target.closest('.profile-option');
      if (option) {
        this.state.profile = option.dataset.profile;
        this.updateProfileDisplay();
        profileDropdown.classList.add('hidden');
        
        // Update selected state
        document.querySelectorAll('.profile-option').forEach(o => {
          o.classList.toggle('selected', o.dataset.profile === this.state.profile);
        });
      }
    });
    
    // Close dropdown on outside click
    document.addEventListener('click', (e) => {
      if (!e.target.closest('.profile-selector')) {
        profileDropdown?.classList.add('hidden');
      }
    });

    // AI Provider - Load initial state only (handlers are in app.html)
    this.loadProviderState();

    // Cost mode selector (cost cards)
    document.querySelectorAll('.cost-card').forEach(card => {
      // Click handler
      card.addEventListener('click', () => {
        const mode = card.dataset.mode;
        this.setCostMode(mode);
      });

      // Hover effects - monochrome design
      card.addEventListener('mouseenter', () => {
        if (!card.classList.contains('active')) {
          card.style.border = '1px solid #4A4A4A';
          card.style.background = '#252525';
        }
      });
      card.addEventListener('mouseleave', () => {
        if (!card.classList.contains('active')) {
          card.style.border = '1px solid #333';
          card.style.background = '#1E1E1E';
        }
      });
    });

    // Dropzone (Single)
    const dropzone = document.getElementById('dropzone');
    const fileInput = document.getElementById('file-input');
    
    dropzone?.addEventListener('click', () => fileInput?.click());
    dropzone?.addEventListener('dragover', (e) => {
      e.preventDefault();
      dropzone.classList.add('drag-over');
    });
    dropzone?.addEventListener('dragleave', () => {
      dropzone.classList.remove('drag-over');
    });
    dropzone?.addEventListener('drop', (e) => {
      e.preventDefault();
      dropzone.classList.remove('drag-over');
      const files = e.dataTransfer.files;
      if (files.length > 0) this.handleFileSelect(files[0]);
    });
    
    fileInput?.addEventListener('change', (e) => {
      if (e.target.files.length > 0) {
        this.handleFileSelect(e.target.files[0]);
      }
    });
    
    // Batch dropzone
    const batchDropzone = document.getElementById('batch-dropzone');
    const batchInput = document.getElementById('batch-input');
    
    batchDropzone?.addEventListener('click', () => batchInput?.click());
    batchDropzone?.addEventListener('dragover', (e) => {
      e.preventDefault();
      batchDropzone.classList.add('drag-over');
    });
    batchDropzone?.addEventListener('dragleave', () => {
      batchDropzone.classList.remove('drag-over');
    });
    batchDropzone?.addEventListener('drop', (e) => {
      e.preventDefault();
      batchDropzone.classList.remove('drag-over');
      const files = Array.from(e.dataTransfer.files);
      this.handleBatchFiles(files);
    });
    
    batchInput?.addEventListener('change', (e) => {
      const files = Array.from(e.target.files);
      this.handleBatchFiles(files);
    });
    
    // File remove
    document.getElementById('file-remove')?.addEventListener('click', () => {
      this.clearFile();
    });
    
    // Language selects
    document.getElementById('source-lang')?.addEventListener('change', (e) => {
      this.state.sourceLang = e.target.value;
    });
    
    document.getElementById('target-lang')?.addEventListener('change', (e) => {
      this.state.targetLang = e.target.value;
    });
    
    // Format options
    document.querySelectorAll('.format-option input').forEach(input => {
      input.addEventListener('change', () => {
        this.state.outputFormats = Array.from(
          document.querySelectorAll('.format-option input:checked')
        ).map(i => i.value);
        this.updateStartButton();
      });
    });
    
    // Vision toggle
    document.getElementById('vision-toggle')?.addEventListener('click', (e) => {
      const btn = e.currentTarget;
      btn.classList.toggle('active');
      this.state.useVision = btn.classList.contains('active');
    });
    
    // Start button
    document.getElementById('btn-start')?.addEventListener('click', () => {
      this.startPublishing();
    });
    
    // Tab buttons
    document.querySelectorAll('.tab-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const tab = btn.dataset.tab;
        this.switchTab(tab);
      });
    });
  },
  
  // Handle file select (single)
  handleFileSelect(file) {
    const validTypes = ['.pdf', '.docx', '.txt', '.md', '.tex'];
    const ext = '.' + file.name.split('.').pop().toLowerCase();

    if (!validTypes.includes(ext)) {
      this.showToast('Định dạng file không được hỗ trợ', 'error');
      return;
    }

    this.state.file = file;

    // Update UI
    document.getElementById('dropzone')?.classList.add('hidden');
    const preview = document.getElementById('file-preview');
    preview?.classList.remove('hidden');

    document.getElementById('file-name').textContent = file.name;
    document.getElementById('file-size').textContent = this.formatFileSize(file.size);

    // Update icon based on type
    const iconMap = {
      '.pdf': 'file-type',
      '.docx': 'file-text',
      '.txt': 'file',
      '.md': 'file-code',
      '.tex': 'sigma',
    };
    const icon = document.getElementById('file-type-icon');
    if (icon) {
      icon.setAttribute('data-lucide', iconMap[ext] || 'file');
      this.refreshIcons();
    }

    // Auto-detect language
    this.detectLanguage(file);

    // Update cost estimate
    this.updateCostEstimate();

    this.updateStartButton();
  },

  // Detect language from file
  async detectLanguage(file) {
    const langDisplay = document.getElementById('source-lang-display');
    const langText = document.getElementById('detected-lang-text');
    const langBadge = document.getElementById('detected-badge');
    const langSelect = document.getElementById('source-lang');

    // Show detecting state
    if (langDisplay) langDisplay.classList.add('detecting');
    if (langText) langText.textContent = 'Đang phát hiện...';
    if (langBadge) langBadge.classList.add('hidden');

    try {
      // For text files, read directly
      const ext = file.name.split('.').pop().toLowerCase();
      let sampleText = '';

      if (['txt', 'md'].includes(ext)) {
        sampleText = await file.slice(0, 5000).text();
      } else {
        // For PDF/DOCX, we'll use the server to detect
        const formData = new FormData();
        formData.append('file', file);

        const res = await fetch(`${this.API_BASE}/detect-language`, {
          method: 'POST',
          body: formData
        });

        if (res.ok) {
          const data = await res.json();
          this.updateDetectedLanguage(data.language, data.confidence);
          return;
        }
      }

      // Client-side detection for text files
      if (sampleText) {
        const detected = this.detectLanguageFromText(sampleText);
        this.updateDetectedLanguage(detected.language, detected.confidence);
      } else {
        // Fallback to auto
        this.updateDetectedLanguage('en', 0.8);
      }
    } catch (error) {
      console.error('Language detection failed:', error);
      // Fallback
      this.updateDetectedLanguage('en', 0.5);
    }
  },

  // Client-side language detection using character patterns
  detectLanguageFromText(text) {
    const sample = text.slice(0, 3000);

    // Character pattern detection
    const patterns = {
      zh: /[\u4e00-\u9fff]/g,  // Chinese characters
      ja: /[\u3040-\u309f\u30a0-\u30ff]/g,  // Hiragana + Katakana
      ko: /[\uac00-\ud7af\u1100-\u11ff]/g,  // Korean Hangul
      ru: /[\u0400-\u04ff]/g,  // Cyrillic
      vi: /[àáảãạăắằẳẵặâấầẩẫậèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵđ]/gi,
    };

    // Count matches for each language
    const counts = {};
    for (const [lang, pattern] of Object.entries(patterns)) {
      const matches = sample.match(pattern);
      counts[lang] = matches ? matches.length : 0;
    }

    // Find dominant language
    const maxLang = Object.entries(counts).reduce((a, b) => b[1] > a[1] ? b : a, ['', 0]);

    if (maxLang[1] > 50) {
      return { language: maxLang[0], confidence: Math.min(0.95, maxLang[1] / 200) };
    }

    // Check for common European languages by word patterns
    const frenchWords = /\b(le|la|les|de|du|des|et|est|un|une|que|qui|dans|pour|sur|avec|ce|cette|sont|ont|été|être|avoir|fait|faire|plus|nous|vous|ils|elles)\b/gi;
    const germanWords = /\b(der|die|das|und|ist|ein|eine|zu|den|von|mit|für|auf|nicht|auch|sich|dem|dass|werden|wird|haben|hat|sein|sind|war|nach|bei|über|oder|wie|aber|nur|noch)\b/gi;
    const spanishWords = /\b(el|la|los|las|de|en|y|que|es|un|una|por|con|para|del|al|se|lo|como|más|pero|su|le|ya|o|sin|sobre|este|entre|cuando|muy|sin|donde|están|hay|sido|tiene|desde|todo)\b/gi;
    const englishWords = /\b(the|be|to|of|and|a|in|that|have|it|for|not|on|with|he|as|you|do|at|this|but|his|by|from|they|we|say|her|she|or|an|will|my|one|all|would|there|their|what|so|up|out|if|about|who|get|which|go|me|when|make|can|like|time|no|just|him|know|take|people|into|year|your|good|some|could|them|see|other|than|then|now|look|only|come|its|over|think|also|back|after|use|two|how|our|work|first|well|way|even|new|want|because|any|these|give|day|most|us)\b/gi;

    const frenchCount = (sample.match(frenchWords) || []).length;
    const germanCount = (sample.match(germanWords) || []).length;
    const spanishCount = (sample.match(spanishWords) || []).length;
    const englishCount = (sample.match(englishWords) || []).length;

    const euroLangs = { fr: frenchCount, de: germanCount, es: spanishCount, en: englishCount };
    const maxEuro = Object.entries(euroLangs).reduce((a, b) => b[1] > a[1] ? b : a, ['en', 0]);

    return { language: maxEuro[0], confidence: Math.min(0.9, maxEuro[1] / 100) };
  },

  // Update the detected language display
  updateDetectedLanguage(lang, confidence) {
    const langDisplay = document.getElementById('source-lang-display');
    const langText = document.getElementById('detected-lang-text');
    const langBadge = document.getElementById('detected-badge');
    const langSelect = document.getElementById('source-lang');

    // Remove detecting state
    if (langDisplay) langDisplay.classList.remove('detecting');

    // Update state
    this.state.sourceLang = lang;
    if (langSelect) langSelect.value = lang;

    // Update display
    const langName = this.languageNames[lang] || lang.toUpperCase();
    if (langText) langText.textContent = langName;

    // Show auto badge if confidence is good
    if (langBadge && confidence > 0.6) {
      langBadge.classList.remove('hidden');
      this.refreshIcons();
    }
  },

  // Set cost mode
  setCostMode(mode) {
    this.state.costMode = mode;

    // Update UI - cost cards with monochrome inline styles
    document.querySelectorAll('.cost-card').forEach(card => {
      const isActive = card.dataset.mode === mode;
      card.classList.toggle('active', isActive);

      // Update inline styles for active state - pure grayscale
      if (isActive) {
        card.style.background = '#252525';
        card.style.border = '1.5px solid #FFFFFF';
        // Update icon container
        const iconDiv = card.querySelector('div[style*="width: 40px"]');
        if (iconDiv) {
          iconDiv.style.background = '#333333';
          iconDiv.style.borderColor = '#FFFFFF';
          iconDiv.style.color = '#FFFFFF';
        }
        // Update text labels
        const labels = card.querySelectorAll('div[style*="font-size: 11px"]');
        labels.forEach(l => l.style.color = '#FFFFFF');
        const sublabels = card.querySelectorAll('div[style*="font-size: 9px"]');
        sublabels.forEach(l => l.style.color = '#9CA3AF');
      } else {
        card.style.background = '#1E1E1E';
        card.style.border = '1px solid #333';
        // Update icon container
        const iconDiv = card.querySelector('div[style*="width: 40px"]');
        if (iconDiv) {
          iconDiv.style.background = '#2A2A2A';
          iconDiv.style.borderColor = '#404040';
          iconDiv.style.color = '#9CA3AF';
        }
        // Update text labels
        const labels = card.querySelectorAll('div[style*="font-size: 11px"]');
        labels.forEach(l => l.style.color = '#9CA3AF');
        const sublabels = card.querySelectorAll('div[style*="font-size: 9px"]');
        sublabels.forEach(l => l.style.color = '#6B7280');
      }

      const radio = card.querySelector('input[type="radio"]');
      if (radio) radio.checked = isActive;
    });

    // Apply cost mode settings
    const config = this.costModeConfig[mode];
    if (config) {
      this.state.aiProvider = config.provider;
      this.state.useVision = config.useVision;

      // Update provider display
      this.updateProviderDisplay(config.provider);
    }

    // Update cost estimate
    this.updateCostEstimate();

    this.refreshIcons();
  },

  // Update cost estimate display
  updateCostEstimate() {
    // New cost estimate bar
    const valueEl = document.getElementById('cost-estimate-value');

    // Legacy support
    const legacyEl = document.getElementById('cost-estimate');

    const file = this.state.file;
    if (!file) {
      if (valueEl) {
        valueEl.textContent = '--';
        valueEl.className = 'cost-estimate-value';
      }
      if (legacyEl && !valueEl) {
        legacyEl.innerHTML = `<i data-lucide="calculator"></i><span>Ước tính: Chưa có file</span>`;
        legacyEl.classList.remove('expensive');
      }
      this.refreshIcons();
      return;
    }

    // Estimate pages based on file size (rough: 50KB per page)
    const estimatedPages = Math.ceil(file.size / 50000);

    // Get cost per page for selected mode
    const config = this.costModeConfig[this.state.costMode];
    const costPerPage = config?.costPerPage || 0.01;
    const estimatedCost = estimatedPages * costPerPage;

    // Format estimate
    let costText = `$${estimatedCost.toFixed(2)}`;
    let timeText = '';

    if (this.state.costMode === 'economy') {
      timeText = `${Math.ceil(estimatedPages / 15)}p`;
    } else if (this.state.costMode === 'balanced') {
      timeText = `${Math.ceil(estimatedPages / 10)}p`;
    } else {
      timeText = `${Math.ceil(estimatedPages / 3)}p`;
    }

    // Update new cost estimate bar
    if (valueEl) {
      valueEl.textContent = `${costText} · ~${timeText}`;
      valueEl.className = 'cost-estimate-value';
      if (estimatedCost > 10) {
        valueEl.classList.add('very-expensive');
      } else if (estimatedCost > 5) {
        valueEl.classList.add('expensive');
      }
    }

    // Legacy support
    if (legacyEl && !valueEl) {
      legacyEl.innerHTML = `<i data-lucide="calculator"></i><span>Ước tính: ${costText} · ~${timeText} (${estimatedPages} trang)</span>`;
      legacyEl.classList.toggle('expensive', estimatedCost > 5);
    }

    this.refreshIcons();
  },
  
  // Handle batch files
  handleBatchFiles(files) {
    const validTypes = ['.pdf', '.docx', '.txt', '.md', '.tex'];
    const validFiles = files.filter(f => {
      const ext = '.' + f.name.split('.').pop().toLowerCase();
      return validTypes.includes(ext);
    }).slice(0, 10); // Max 10 files
    
    this.state.files = validFiles;
    this.renderBatchFiles();
    this.updateStartButton();
  },
  
  // Render batch files
  renderBatchFiles() {
    const container = document.getElementById('batch-files');
    if (!container) return;
    
    container.innerHTML = this.state.files.map((file, i) => {
      const ext = '.' + file.name.split('.').pop().toLowerCase();
      const iconMap = {
        '.pdf': 'file-type',
        '.docx': 'file-text',
        '.txt': 'file',
        '.md': 'file-code',
        '.tex': 'sigma',
      };
      return `
        <div class="batch-file-item">
          <span class="file-icon"><i data-lucide="${iconMap[ext] || 'file'}"></i></span>
          <span class="file-name">${file.name}</span>
          <span class="file-size">${this.formatFileSize(file.size)}</span>
          <button class="file-remove" onclick="PublisherApp.removeBatchFile(${i})">
            <i data-lucide="x"></i>
          </button>
        </div>
      `;
    }).join('');
    
    this.refreshIcons();
  },
  
  // Remove batch file
  removeBatchFile(index) {
    this.state.files.splice(index, 1);
    this.renderBatchFiles();
    this.updateStartButton();
  },
  
  // Clear file
  clearFile() {
    this.state.file = null;
    
    document.getElementById('dropzone')?.classList.remove('hidden');
    document.getElementById('file-preview')?.classList.add('hidden');
    document.getElementById('file-input').value = '';
    
    this.updateStartButton();
  },
  
  // Set mode (single/batch)
  setMode(mode) {
    this.state.mode = mode;
    
    document.querySelectorAll('.mode-btn').forEach(btn => {
      btn.classList.toggle('active', btn.dataset.mode === mode);
    });
    
    document.getElementById('upload-section')?.classList.toggle('hidden', mode === 'batch');
    document.getElementById('batch-section')?.classList.toggle('hidden', mode === 'single');
    
    this.updateStartButton();
  },
  
  // Switch tab
  switchTab(tab) {
    document.querySelectorAll('.tab-btn').forEach(btn => {
      btn.classList.toggle('active', btn.dataset.tab === tab);
    });
    
    document.querySelectorAll('.tab-content').forEach(content => {
      content.classList.toggle('active', content.id === `tab-${tab}`);
    });
  },
  
  // Update start button state
  updateStartButton() {
    const btn = document.getElementById('btn-start');
    if (!btn) return;
    
    let canStart = false;
    
    if (this.state.mode === 'single') {
      canStart = this.state.file !== null && this.state.outputFormats.length > 0;
    } else {
      canStart = this.state.files.length > 0 && this.state.outputFormats.length > 0;
    }
    
    btn.disabled = !canStart;
  },
  
  // Start publishing
  async startPublishing() {
    if (this.state.mode === 'batch') {
      this.startBatchPublishing();
      return;
    }
    
    if (!this.state.file) {
      this.showToast('Vui lòng chọn file trước', 'error');
      return;
    }
    
    console.log('📚 Starting publishing...', this.state);
    
    // Update UI
    const btn = document.getElementById('btn-start');
    btn.disabled = true;
    btn.querySelector('.btn-text').textContent = 'Publishing...';
    
    // Reset agents
    this.resetAgents();
    
    // Switch to progress tab
    this.switchTab('progress');
    
    // Create form data
    const formData = new FormData();
    formData.append('file', this.state.file);
    formData.append('source_language', this.state.sourceLang);
    formData.append('target_language', this.state.targetLang);
    formData.append('profile_id', this.state.profile);
    formData.append('output_formats', this.state.outputFormats.join(','));
    formData.append('use_vision', this.state.useVision.toString());
    
    try {
      // Submit job
      const res = await fetch(`${this.API_BASE}/publish`, {
        method: 'POST',
        body: formData,
      });
      
      if (!res.ok) {
        throw new Error('Failed to submit job');
      }
      
      const job = await res.json();
      this.state.job = job;

      // Save job ID for auto-reconnect on refresh
      localStorage.setItem('currentJobId', job.job_id);

      console.log('✅ Job created:', job.job_id);
      this.showToast('Đã bắt đầu xử lý!', 'success');

      // Start polling
      this.startPolling(job.job_id);
      
    } catch (e) {
      console.error('Publishing error:', e);
      this.showToast('Không thể bắt đầu xuất bản: ' + e.message, 'error');
      
      btn.disabled = false;
      btn.querySelector('.btn-text').textContent = 'Bắt Đầu Xuất Bản';
    }
  },
  
  // Start batch publishing
  async startBatchPublishing() {
    console.log('📚 Starting batch publishing...', this.state.files);
    this.showToast('Đang bắt đầu xử lý hàng loạt...', 'success');
    this.switchTab('progress');
  },
  
  // Start polling job status
  startPolling(jobId) {
    this.stopPolling();
    
    this.state.pollInterval = setInterval(async () => {
      try {
        const res = await fetch(`${this.API_BASE}/jobs/${jobId}`);
        const job = await res.json();
        
        this.updateJobProgress(job);
        
        if (job.status === 'complete') {
          this.stopPolling();
          this.onJobComplete(job);
        } else if (job.status === 'failed') {
          this.stopPolling();
          this.onJobFailed(job);
        }
        
      } catch (e) {
        console.error('Poll error:', e);
      }
    }, 1000);
  },
  
  // Stop polling
  stopPolling() {
    if (this.state.pollInterval) {
      clearInterval(this.state.pollInterval);
      this.state.pollInterval = null;
    }
  },
  
  // Update job progress
  updateJobProgress(job) {
    // API returns progress as 0-1 decimal, convert to percentage
    // Handle edge cases where backend might return values > 1
    const rawProgress = job.progress || 0;
    let progress;
    if (rawProgress <= 1) {
      progress = rawProgress * 100;
    } else if (rawProgress <= 100) {
      progress = rawProgress;
    } else {
      // Backend bug: progress > 100, normalize it
      progress = Math.min(rawProgress, 100);
    }
    // Cap at 100%
    progress = Math.min(progress, 100);
    const status = job.status;

    // Update progress bar
    document.getElementById('overall-progress').style.width = `${progress}%`;
    document.getElementById('progress-text').textContent = `${progress.toFixed(0)}%`;

    // Update current task
    const taskDisplay = document.getElementById('current-task-display');
    if (taskDisplay) {
      taskDisplay.innerHTML = `
        <i data-lucide="loader-2" class="task-icon"></i>
        <span>${job.current_task || 'Processing...'}</span>
      `;
      this.refreshIcons();
    }

    // Get current stage from job.current_stage (more accurate) or fallback to status
    let rawStage = (job.current_stage || status || '').toLowerCase();

    // Map API stage descriptions to UI stage names
    // API sends descriptive text like "Claude Vision reading PDF...", "Extracting document DNA", etc.
    let currentStage = rawStage;

    // Pattern matching for API stage descriptions
    if (rawStage.includes('vision') || rawStage.includes('reading pdf')) {
      currentStage = 'vision_reading';
    } else if (rawStage.includes('dna') || rawStage.includes('extracting')) {
      currentStage = 'analyzing';
    } else if (rawStage.includes('chunk')) {
      currentStage = 'chunking';
    } else if (rawStage.includes('translat')) {
      currentStage = 'translating';
    } else if (rawStage.includes('assembl')) {
      currentStage = 'assembling';
    } else if (rawStage.includes('convert')) {
      currentStage = 'converting';
    } else if (rawStage.includes('verif') || rawStage.includes('quality')) {
      currentStage = 'verifying';
    } else if (rawStage === 'complete' || rawStage.includes('complete')) {
      currentStage = 'complete';
    }

    // Handle "running" or "pending" status by checking progress to estimate stage
    if (currentStage === 'running' || currentStage === 'pending' || !currentStage) {
      if (progress < 5) currentStage = 'vision_reading';
      else if (progress < 52) currentStage = 'analyzing';
      else if (progress < 55) currentStage = 'chunking';
      else if (progress < 92) currentStage = 'translating';
      else if (progress < 95) currentStage = 'assembling';
      else if (progress < 98) currentStage = 'converting';
      else if (progress < 100) currentStage = 'verifying';
      else currentStage = 'complete';
    }

    // Handle complete status
    if (status === 'complete' || currentStage === 'complete') {
      currentStage = 'complete';
    }

    // Update stages
    const stageOrder = ['vision_reading', 'analyzing', 'chunking', 'translating', 'assembling', 'converting', 'verifying', 'complete'];
    const currentIndex = stageOrder.indexOf(currentStage);

    document.querySelectorAll('.stage-item').forEach((el) => {
      const stage = el.dataset.stage;
      const stageIndex = stageOrder.indexOf(stage);

      if (stageIndex < currentIndex) {
        el.dataset.status = 'complete';
        el.querySelector('.stage-status').innerHTML = '<i data-lucide="check-circle"></i>';
      } else if (stageIndex === currentIndex) {
        el.dataset.status = 'active';
        el.querySelector('.stage-status').innerHTML = '<i data-lucide="loader-2"></i>';
      } else {
        el.dataset.status = 'pending';
        el.querySelector('.stage-status').innerHTML = '<i data-lucide="pause"></i>';
      }
    });

    this.refreshIcons();

    // Update agents
    this.updateAgentStatus(currentStage, progress);

    // Update usage stats
    this.updateUsageStats(job);

    // Update DNA if available
    if (job.dna) {
      this.showDNA(job.dna);
    }
  },

  // Format time duration
  formatDuration(seconds) {
    if (seconds < 60) {
      return `${Math.round(seconds)}s`;
    } else if (seconds < 3600) {
      const mins = Math.floor(seconds / 60);
      const secs = Math.round(seconds % 60);
      return `${mins}m ${secs}s`;
    } else {
      const hours = Math.floor(seconds / 3600);
      const mins = Math.floor((seconds % 3600) / 60);
      return `${hours}h ${mins}m`;
    }
  },

  // Format number with K/M suffix
  formatNumber(num) {
    if (num >= 1000000) {
      return (num / 1000000).toFixed(1) + 'M';
    } else if (num >= 1000) {
      return (num / 1000).toFixed(1) + 'K';
    }
    return num.toString();
  },

  // Update usage stats display
  updateUsageStats(job) {
    // Update elapsed time
    const elapsedEl = document.getElementById('stat-elapsed');
    if (elapsedEl) {
      const elapsed = job.elapsed_time_seconds || 0;
      elapsedEl.textContent = this.formatDuration(elapsed);
    }

    // Update from usage_stats if available
    const stats = job.usage_stats;
    if (stats) {
      const tokensEl = document.getElementById('stat-tokens');
      if (tokensEl) {
        tokensEl.textContent = this.formatNumber(stats.total_tokens || 0);
      }

      const callsEl = document.getElementById('stat-calls');
      if (callsEl) {
        callsEl.textContent = stats.total_calls || 0;
      }

      const costEl = document.getElementById('stat-cost');
      if (costEl) {
        const cost = stats.estimated_cost_usd || 0;
        costEl.textContent = cost < 0.01 ? '<$0.01' : `$${cost.toFixed(2)}`;
      }
    }
  },
  
  // Reset agents
  resetAgents() {
    ['editor', 'translator', 'publisher'].forEach(agent => {
      const el = document.getElementById(`agent-${agent}`);
      if (el) {
        el.dataset.status = 'idle';
        el.querySelector('.status-text').textContent = 'Chờ';
        el.querySelector('.progress-bar').style.width = '0%';
      }
    });
  },
  
  // Update agent status
  updateAgentStatus(currentStage, progress) {
    const editorStatuses = ['vision_reading', 'analyzing', 'chunking'];
    const translatorStatuses = ['translating'];
    const publisherStatuses = ['assembling', 'converting', 'verifying'];

    // Editor
    const editorEl = document.getElementById('agent-editor');
    if (editorEl) {
      if (editorStatuses.includes(currentStage)) {
        editorEl.dataset.status = 'active';
        editorEl.querySelector('.status-text').textContent = 'Đang xử lý...';
        // Update progress based on sub-stage
        const editorProgress = currentStage === 'vision_reading' ? 33 :
                              currentStage === 'analyzing' ? 66 :
                              currentStage === 'chunking' ? 100 : 0;
        editorEl.querySelector('.progress-bar').style.width = `${editorProgress}%`;
      } else if (['translating', 'assembling', 'converting', 'verifying', 'complete'].includes(currentStage)) {
        editorEl.dataset.status = 'complete';
        editorEl.querySelector('.status-text').textContent = 'Xong';
        editorEl.querySelector('.progress-bar').style.width = '100%';
      }
    }

    // Translator
    const translatorEl = document.getElementById('agent-translator');
    if (translatorEl) {
      if (translatorStatuses.includes(currentStage)) {
        translatorEl.dataset.status = 'active';
        translatorEl.querySelector('.status-text').textContent = 'Đang xử lý...';
        // Use overall progress for translation phase (55-92% from API)
        const translatorProgress = Math.min(100, Math.max(0, (progress - 55) * (100 / 37)));
        translatorEl.querySelector('.progress-bar').style.width = `${translatorProgress}%`;
      } else if (['assembling', 'converting', 'verifying', 'complete'].includes(currentStage)) {
        translatorEl.dataset.status = 'complete';
        translatorEl.querySelector('.status-text').textContent = 'Xong';
        translatorEl.querySelector('.progress-bar').style.width = '100%';
      }
    }

    // Publisher
    const publisherEl = document.getElementById('agent-publisher');
    if (publisherEl) {
      if (publisherStatuses.includes(currentStage)) {
        publisherEl.dataset.status = 'active';
        publisherEl.querySelector('.status-text').textContent = 'Đang xử lý...';
        // Update progress based on sub-stage
        const publisherProgress = currentStage === 'assembling' ? 33 :
                                 currentStage === 'converting' ? 66 :
                                 currentStage === 'verifying' ? 90 : 0;
        publisherEl.querySelector('.progress-bar').style.width = `${publisherProgress}%`;
      } else if (currentStage === 'complete') {
        publisherEl.dataset.status = 'complete';
        publisherEl.querySelector('.status-text').textContent = 'Xong';
        publisherEl.querySelector('.progress-bar').style.width = '100%';
      }
    }
  },
  
  // Job completed
  onJobComplete(job) {
    console.log('🎉 Job complete:', job);

    // Clear saved job ID
    localStorage.removeItem('currentJobId');

    const btn = document.getElementById('btn-start');
    btn.disabled = false;
    btn.querySelector('.btn-text').textContent = 'Bắt Đầu Xuất Bản';

    this.showToast('Xuất bản hoàn tất!', 'success');

    // Show downloads
    this.showDownloads(job);

    // Switch to downloads tab
    this.switchTab('downloads');
  },

  // Job failed
  onJobFailed(job) {
    console.error('❌ Job failed:', job.error);

    // Clear saved job ID
    localStorage.removeItem('currentJobId');

    const btn = document.getElementById('btn-start');
    btn.disabled = false;
    btn.querySelector('.btn-text').textContent = 'Bắt Đầu Xuất Bản';

    this.showToast('Xuất bản thất bại: ' + (job.error || 'Lỗi không xác định'), 'error');
  },
  
  // Show downloads
  showDownloads(job) {
    document.getElementById('downloads-placeholder')?.classList.add('hidden');
    const grid = document.getElementById('downloads-grid');
    grid?.classList.remove('hidden');

    // Always show these formats as download options
    const downloadFormats = [
      { fmt: 'docx', name: 'Word Document', ext: 'DOCX', icon: 'file-text', color: '#2B579A' },
      { fmt: 'pdf', name: 'PDF Document', ext: 'PDF', icon: 'file-type', color: '#FF0000' },
      { fmt: 'md', name: 'Markdown', ext: 'MD', icon: 'file-code', color: '#083FA1' },
    ];

    grid.innerHTML = downloadFormats.map(({ fmt, name, ext, icon, color }) => {
      const downloadUrl = `${this.API_BASE}/jobs/${job.job_id}/download/${fmt}`;
      return `
        <a href="${downloadUrl}" class="download-card" download style="--accent-color: ${color}">
          <span class="download-icon" style="background: ${color}20; color: ${color};">
            <i data-lucide="${icon}"></i>
          </span>
          <div class="download-info">
            <h4>${name}</h4>
            <p>Click to download ${ext}</p>
          </div>
        </a>
      `;
    }).join('');

    this.refreshIcons();
  },
  
  // Show DNA
  showDNA(dna) {
    document.getElementById('dna-placeholder')?.classList.add('hidden');
    const content = document.getElementById('dna-content');
    content?.classList.remove('hidden');
    
    content.innerHTML = `
      <div class="dna-section">
        <h4><i data-lucide="file-scan"></i> Document Info</h4>
        <div class="dna-grid">
          <div class="dna-item">
            <span class="label">Genre</span>
            <span class="value">${dna.detected_genre || 'Unknown'}</span>
          </div>
          <div class="dna-item">
            <span class="label">Language</span>
            <span class="value">${dna.detected_language || 'Unknown'}</span>
          </div>
          <div class="dna-item">
            <span class="label">Formulas</span>
            <span class="value">${dna.has_formulas ? '✓ Yes' : '✗ No'}</span>
          </div>
          <div class="dna-item">
            <span class="label">Tables</span>
            <span class="value">${dna.has_tables ? '✓ Yes' : '✗ No'}</span>
          </div>
          <div class="dna-item">
            <span class="label">Code</span>
            <span class="value">${dna.has_code ? '✓ Yes' : '✗ No'}</span>
          </div>
          <div class="dna-item">
            <span class="label">Citations</span>
            <span class="value">${dna.has_citations ? '✓ Yes' : '✗ No'}</span>
          </div>
        </div>
      </div>
      ${dna.terminology && dna.terminology.length > 0 ? `
        <div class="dna-section">
          <h4><i data-lucide="book-text"></i> Key Terms</h4>
          <div class="dna-tags">
            ${dna.terminology.slice(0, 10).map(t => `<span class="dna-tag">${t.term || t}</span>`).join('')}
          </div>
        </div>
      ` : ''}
    `;
    
    this.refreshIcons();
  },
  
  // Show toast notification
  showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;
    
    const iconMap = {
      success: 'check-circle',
      error: 'alert-circle',
      info: 'info',
    };
    
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
      <i data-lucide="${iconMap[type] || 'info'}"></i>
      <span class="toast-message">${message}</span>
    `;
    
    container.appendChild(toast);
    this.refreshIcons();
    
    setTimeout(() => {
      toast.remove();
    }, 4000);
  },
  
  // Utility: Format file size
  formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  }
};

// Export
window.PublisherApp = PublisherApp;
