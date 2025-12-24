/**
 * Admin Dashboard Main Module
 * AI Publisher Pro - Admin Interface Logic
 * With Lucide Icons Support
 */

const AdminDashboard = {
  API_BASE: '/api/v2',
  currentSection: 'overview',
  
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
  
  // Refresh Lucide icons
  refreshIcons() {
    if (typeof lucide !== 'undefined') {
      lucide.createIcons();
    }
  },
  
  async init() {
    console.log('⚙️ Admin Dashboard initializing...');
    
    this.bindEvents();
    await this.loadHealthStatus();
    await this.loadCacheStats();
    await this.loadRecentJobs();
    await this.loadProfiles();
    
    this.refreshIcons();
    
    console.log('✅ Admin Dashboard ready');
  },
  
  bindEvents() {
    // Sidebar navigation
    document.querySelectorAll('.sidebar-link').forEach(link => {
      link.addEventListener('click', (e) => {
        e.preventDefault();
        const section = link.dataset.section;
        this.switchSection(section);
      });
    });
    
    // Search and filter
    document.getElementById('jobs-search')?.addEventListener('input', (e) => {
      this.filterJobs(e.target.value);
    });
    
    document.getElementById('jobs-filter')?.addEventListener('change', (e) => {
      this.loadAllJobs(e.target.value);
    });
  },
  
  switchSection(section) {
    this.currentSection = section;
    
    // Update sidebar
    document.querySelectorAll('.sidebar-link').forEach(link => {
      link.classList.toggle('active', link.dataset.section === section);
    });
    
    // Update sections
    document.querySelectorAll('.admin-section').forEach(sec => {
      sec.classList.toggle('active', sec.id === `section-${section}`);
    });
    
    // Load section data
    if (section === 'jobs') {
      this.loadAllJobs();
    }
  },
  
  // Load health status
  async loadHealthStatus() {
    try {
      const res = await fetch(`${this.API_BASE}/health`);
      const data = await res.json();
      
      this.updateStatusBadge('status-api', data.status === 'healthy');
      this.updateStatusBadge('status-pandoc', data.dependencies?.pandoc);
      this.updateStatusBadge('status-claude', data.dependencies?.anthropic);
      
    } catch (e) {
      console.error('Health check failed:', e);
      this.updateStatusBadge('status-api', false);
      this.updateStatusBadge('status-pandoc', false);
      this.updateStatusBadge('status-claude', false);
    }
  },
  
  updateStatusBadge(id, isOk) {
    const el = document.getElementById(id);
    if (!el) return;
    
    el.innerHTML = isOk 
      ? '<i data-lucide="check-circle" style="width:14px;height:14px;color:#22c55e;"></i>' 
      : '<i data-lucide="x-circle" style="width:14px;height:14px;color:#ef4444;"></i>';
    el.className = `status-badge ${isOk ? 'online' : 'offline'}`;
    this.refreshIcons();
  },
  
  // Load cache stats
  async loadCacheStats() {
    try {
      const res = await fetch(`${this.API_BASE}/cache/stats`);
      const data = await res.json();
      
      document.getElementById('stat-total-jobs').textContent = data.total_jobs || 0;
      document.getElementById('stat-completed').textContent = data.completed_jobs || 0;
      document.getElementById('stat-running').textContent = data.running_jobs || 0;
      document.getElementById('stat-failed').textContent = data.failed_jobs || 0;
      
      document.getElementById('cache-total').textContent = data.total_jobs || 0;
      document.getElementById('cache-size').textContent = this.formatSize(data.cache_size || 0);
      
    } catch (e) {
      console.error('Cache stats failed:', e);
      ['stat-total-jobs', 'stat-completed', 'stat-running', 'stat-failed', 'cache-total'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.textContent = '0';
      });
    }
  },
  
  // Load recent jobs
  async loadRecentJobs() {
    try {
      const res = await fetch(`${this.API_BASE}/jobs`);
      const data = await res.json();
      
      const tbody = document.getElementById('recent-jobs-body');
      if (!tbody) return;
      
      if (!data.jobs || data.jobs.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="text-center text-muted">Không có công việc nào</td></tr>';
        return;
      }
      
      tbody.innerHTML = data.jobs.slice(0, 5).map(job => this.renderJobRow(job)).join('');
      this.refreshIcons();
      
    } catch (e) {
      console.error('Load jobs failed:', e);
      const tbody = document.getElementById('recent-jobs-body');
      if (tbody) {
        tbody.innerHTML = '<tr><td colspan="7" class="text-center text-muted">Không thể tải công việc</td></tr>';
      }
    }
  },
  
  // Load all jobs (for jobs section)
  async loadAllJobs(filter = 'all') {
    try {
      const res = await fetch(`${this.API_BASE}/jobs`);
      const data = await res.json();
      
      const tbody = document.getElementById('all-jobs-body');
      if (!tbody) return;
      
      let jobs = data.jobs || [];
      
      // Apply filter
      if (filter !== 'all') {
        jobs = jobs.filter(j => j.status === filter);
      }
      
      if (jobs.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" class="text-center text-muted">Không có công việc nào</td></tr>';
        return;
      }
      
      tbody.innerHTML = jobs.map(job => this.renderFullJobRow(job)).join('');
      this.refreshIcons();
      
    } catch (e) {
      console.error('Load all jobs failed:', e);
    }
  },
  
  // Get status icon
  getStatusIcon(status) {
    const icons = {
      complete: 'check-circle',
      running: 'loader-2',
      translating: 'languages',
      analyzing: 'scan-search',
      failed: 'alert-circle',
      pending: 'clock',
    };
    return icons[status] || 'circle';
  },
  
  // Render job row (recent jobs)
  renderJobRow(job) {
    const statusIcon = this.getStatusIcon(job.status);
    return `
      <tr>
        <td><code>${(job.job_id || '').substring(0, 8)}</code></td>
        <td>${this.truncate(job.source_file || '-', 20)}</td>
        <td>${job.profile_id || '-'}</td>
        <td>
          <span class="status-pill ${job.status}">
            <i data-lucide="${statusIcon}"></i>
            ${job.status}
          </span>
        </td>
        <td>
          <div class="mini-progress">
            <div class="mini-progress-fill" style="width: ${job.progress || 0}%"></div>
          </div>
        </td>
        <td>${this.formatTime(job.created_at)}</td>
        <td>
          <button class="btn btn-xs" onclick="AdminDashboard.viewJob('${job.job_id}')">
            <i data-lucide="eye"></i>
          </button>
          ${job.status !== 'complete' && job.status !== 'failed' ? `
            <button class="btn btn-xs btn-danger" onclick="AdminDashboard.cancelJob('${job.job_id}')">
              <i data-lucide="x"></i>
            </button>
          ` : ''}
        </td>
      </tr>
    `;
  },
  
  // Render full job row (jobs section)
  renderFullJobRow(job) {
    const statusIcon = this.getStatusIcon(job.status);
    return `
      <tr>
        <td><code>${(job.job_id || '').substring(0, 8)}</code></td>
        <td>${this.truncate(job.source_file || '-', 25)}</td>
        <td>${job.profile_id || '-'}</td>
        <td>${job.source_language || '?'} → ${job.target_language || '?'}</td>
        <td>
          <span class="status-pill ${job.status}">
            <i data-lucide="${statusIcon}"></i>
            ${job.status}
          </span>
        </td>
        <td>
          <div class="mini-progress">
            <div class="mini-progress-fill" style="width: ${job.progress || 0}%"></div>
          </div>
        </td>
        <td>${this.formatTime(job.created_at)}</td>
        <td>
          <button class="btn btn-xs" onclick="AdminDashboard.viewJob('${job.job_id}')">
            <i data-lucide="eye"></i>
          </button>
          ${job.status === 'complete' && job.output_paths ? `
            <button class="btn btn-xs btn-primary" onclick="AdminDashboard.downloadJob('${job.job_id}')">
              <i data-lucide="download"></i>
            </button>
          ` : ''}
          <button class="btn btn-xs btn-danger" onclick="AdminDashboard.deleteJob('${job.job_id}')">
            <i data-lucide="trash-2"></i>
          </button>
        </td>
      </tr>
    `;
  },
  
  // Load profiles
  async loadProfiles() {
    try {
      const res = await fetch(`${this.API_BASE}/profiles`);
      const data = await res.json();
      
      const grid = document.getElementById('profiles-grid');
      if (!grid) return;
      
      const profiles = data.profiles || [];
      
      grid.innerHTML = profiles.map(p => `
        <div class="profile-card">
          <div class="profile-icon-wrap">
            <i data-lucide="${this.profileIcons[p.id] || 'file'}"></i>
          </div>
          <h4>${p.name}</h4>
          <p>${p.description}</p>
          <div class="profile-meta">
            <span>Thể loại: ${p.genre || '-'}</span>
            <span>Chunk: ${p.chunk_size || '-'}</span>
          </div>
        </div>
      `).join('');
      
      this.refreshIcons();
      
    } catch (e) {
      console.error('Load profiles failed:', e);
    }
  },
  
  // View job details
  async viewJob(jobId) {
    try {
      const res = await fetch(`${this.API_BASE}/jobs/${jobId}`);
      const job = await res.json();
      
      const details = `
Mã công việc: ${job.job_id}
Trạng thái: ${job.status}
Tiến trình: ${job.progress}%
File: ${job.source_file}
Hồ sơ: ${job.profile_id}
Ngôn ngữ: ${job.source_language} → ${job.target_language}
Ngày tạo: ${job.created_at}
Tác vụ hiện tại: ${job.current_task || '-'}
      `.trim();
      
      alert(details);
      
    } catch (e) {
      this.showToast('Không thể tải chi tiết công việc', 'error');
    }
  },
  
  // Download job outputs
  downloadJob(jobId) {
    window.open(`${this.API_BASE}/jobs/${jobId}/download`, '_blank');
  },
  
  // Delete job
  async deleteJob(jobId) {
    if (!confirm('Xóa công việc này?')) return;

    try {
      await fetch(`${this.API_BASE}/cache/${jobId}`, { method: 'DELETE' });
      this.showToast('Đã xóa công việc', 'success');
      this.refresh();
    } catch (e) {
      this.showToast('Không thể xóa công việc', 'error');
    }
  },
  
  // Cancel running job
  async cancelJob(jobId) {
    if (!confirm('Hủy công việc này?')) return;

    try {
      await fetch(`${this.API_BASE}/cache/${jobId}`, { method: 'DELETE' });
      this.showToast('Đã hủy công việc', 'success');
      this.refresh();
    } catch (e) {
      this.showToast('Không thể hủy công việc', 'error');
    }
  },
  
  // Clear all cache
  async clearCache() {
    if (!confirm('Bạn có chắc muốn xóa toàn bộ bộ nhớ đệm? Hành động này không thể hoàn tác.')) return;

    try {
      const res = await fetch(`${this.API_BASE}/cache`, { method: 'DELETE' });
      const data = await res.json();

      this.showToast(`Đã xóa bộ nhớ đệm! ${data.cleared_jobs || 0} công việc đã được xóa.`, 'success');
      this.refresh();

    } catch (e) {
      this.showToast('Không thể xóa bộ nhớ đệm', 'error');
    }
  },
  
  // Clear old jobs
  async clearOldJobs() {
    if (!confirm('Xóa tất cả công việc cũ hơn 7 ngày?')) return;

    try {
      const res = await fetch(`${this.API_BASE}/cache/old`, { method: 'DELETE' });
      const data = await res.json();

      this.showToast(`Đã xóa ${data.cleared_jobs || 0} công việc cũ.`, 'success');
      this.refresh();

    } catch (e) {
      this.showToast('Không thể xóa công việc cũ', 'error');
    }
  },
  
  // Filter jobs by search
  filterJobs(query) {
    const tbody = document.getElementById('all-jobs-body');
    if (!tbody) return;
    
    const rows = tbody.querySelectorAll('tr');
    const q = query.toLowerCase();
    
    rows.forEach(row => {
      const text = row.textContent.toLowerCase();
      row.style.display = text.includes(q) ? '' : 'none';
    });
  },
  
  // Refresh all data
  refresh() {
    this.loadHealthStatus();
    this.loadCacheStats();
    this.loadRecentJobs();
    
    if (this.currentSection === 'jobs') {
      this.loadAllJobs();
    }
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
  
  // Utility: Format time
  formatTime(isoString) {
    if (!isoString) return '-';
    const date = new Date(isoString);
    const now = new Date();
    const diff = (now - date) / 1000;

    if (diff < 60) return 'Vừa xong';
    if (diff < 3600) return `${Math.floor(diff / 60)} phút trước`;
    if (diff < 86400) return `${Math.floor(diff / 3600)} giờ trước`;
    return date.toLocaleDateString('vi-VN');
  },
  
  // Utility: Format size
  formatSize(bytes) {
    if (!bytes) return '0 B';
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    if (bytes < 1024 * 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
    return (bytes / (1024 * 1024 * 1024)).toFixed(1) + ' GB';
  },
  
  // Utility: Truncate text
  truncate(str, max) {
    if (!str) return '-';
    if (str.length <= max) return str;
    return str.substring(0, max - 3) + '...';
  }
};

// Export
window.AdminDashboard = AdminDashboard;
