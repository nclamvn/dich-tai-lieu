/**
 * Thanh Điều Hướng - AI Publisher Pro
 * Dark Notion Theme - Thuần Khiết Cao Cấp
 */

const NavBar = {
  currentPage: '',

  init(page) {
    this.currentPage = page;
    this.render();
    this.bindEvents();
    if (typeof lucide !== 'undefined') {
      lucide.createIcons();
    }
  },

  render() {
    const nav = document.createElement('nav');
    nav.id = 'main-navbar';
    nav.innerHTML = `
      <div class="nav-container">
        <!-- Logo -->
        <a href="/ui/landing/" class="nav-logo">
          <i data-lucide="book-open" class="logo-icon"></i>
          <span class="logo-text">AI Translator</span>
        </a>

        <!-- Main Navigation -->
        <div class="nav-links">
          <a href="/ui/landing/" class="nav-link ${this.currentPage === 'landing' ? 'active' : ''}">
            <i data-lucide="home" class="nav-icon"></i>
            <span>Trang Chủ</span>
          </a>
          <a href="/app" class="nav-link ${this.currentPage === 'app' ? 'active' : ''}">
            <i data-lucide="file-text" class="nav-icon"></i>
            <span>Xưởng Xuất Bản</span>
          </a>
          <a href="/admin" class="nav-link ${this.currentPage === 'admin' ? 'active' : ''}">
            <i data-lucide="settings" class="nav-icon"></i>
            <span>Quản Trị</span>
          </a>
        </div>

        <!-- Right Actions -->
        <div class="nav-actions">
          <div class="nav-status" id="api-status">
            <span class="status-dot"></span>
            <span class="status-text">Đang kiểm tra...</span>
          </div>
          <button class="nav-btn nav-btn-primary" onclick="window.location.href='/app'">
            <i data-lucide="rocket" class="btn-icon"></i>
            Bắt Đầu
          </button>
        </div>

        <!-- Mobile Menu Button -->
        <button class="nav-mobile-toggle" id="mobile-menu-toggle">
          <span></span>
          <span></span>
          <span></span>
        </button>
      </div>

      <!-- Mobile Menu -->
      <div class="nav-mobile-menu" id="mobile-menu">
        <a href="/ui/landing/" class="mobile-link">
          <i data-lucide="home"></i> Trang Chủ
        </a>
        <a href="/app" class="mobile-link">
          <i data-lucide="file-text"></i> Xưởng Xuất Bản
        </a>
        <a href="/admin" class="mobile-link">
          <i data-lucide="settings"></i> Quản Trị
        </a>
      </div>
    `;

    document.body.prepend(nav);
    this.checkApiStatus();

    setTimeout(() => {
      if (typeof lucide !== 'undefined') {
        lucide.createIcons();
      }
    }, 0);
  },

  bindEvents() {
    const toggle = document.getElementById('mobile-menu-toggle');
    const menu = document.getElementById('mobile-menu');

    toggle?.addEventListener('click', () => {
      menu.classList.toggle('open');
      toggle.classList.toggle('open');
    });
  },

  async checkApiStatus() {
    const statusEl = document.getElementById('api-status');
    try {
      const res = await fetch('/api/v2/health');
      const data = await res.json();

      if (data.status === 'healthy') {
        statusEl.innerHTML = `
          <span class="status-dot online"></span>
          <span class="status-text">Hoạt động</span>
        `;
      } else {
        throw new Error('Unhealthy');
      }
    } catch (e) {
      statusEl.innerHTML = `
        <span class="status-dot offline"></span>
        <span class="status-text">Ngoại tuyến</span>
      `;
    }
  }
};

if (typeof module !== 'undefined') {
  module.exports = NavBar;
}
