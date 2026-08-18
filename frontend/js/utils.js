/* ──────────────────────────────────────────────────────────────
   NaySchool 3.0 — Utility Functions
   Pure vanilla JS, zero dependencies.
   ────────────────────────────────────────────────────────────── */

window.NayUtils = {

  /* ── Date / Time ─────────────────────────────────────────── */

  formatDate(value) {
    if (!value) return '—';
    const d = new Date(value);
    if (isNaN(d)) return '—';
    return d.toLocaleDateString('en-US', {
      month: 'short', day: 'numeric', year: 'numeric',
    });
  },

  formatDateTime(value) {
    if (!value) return '—';
    const d = new Date(value);
    if (isNaN(d)) return '—';
    return d.toLocaleString('en-US', {
      month: 'short', day: 'numeric', year: 'numeric',
      hour: 'numeric', minute: '2-digit',
    });
  },

  timeAgo(value) {
    if (!value) return '—';
    const d = new Date(value);
    const now = new Date();
    const diff = Math.floor((now - d) / 1000);
    if (diff < 60)     return 'just now';
    if (diff < 3600)   return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400)  return `${Math.floor(diff / 3600)}h ago`;
    if (diff < 604800) return `${Math.floor(diff / 86400)}d ago`;
    return this.formatDate(value);
  },

  /* ── URL / Text ──────────────────────────────────────────── */

  getQueryParam(name) {
    return new URLSearchParams(window.location.search).get(name);
  },

  escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text || '';
    return div.innerHTML;
  },

  truncateText(text, maxLength = 100) {
    if (!text) return '';
    if (text.length <= maxLength) return text;
    return text.slice(0, maxLength) + '…';
  },

  /* ── HTML Generators ─────────────────────────────────────── */

  badge(label, type = 'brand') {
    return `<span class="nay-badge nay-badge-${type}">${this.escapeHtml(label)}</span>`;
  },

  progressBar(value, max = 100) {
    const pct = Math.min(100, Math.max(0, (value / max) * 100));
    return `<div class="nay-progress"><div class="nay-progress-fill" style="width:${pct}%"></div></div>`;
  },

  statusBadge(status) {
    const map = {
      completed: 'success', done: 'success', active: 'success', connected: 'success',
      pending: 'warning', in_progress: 'warning', processing: 'warning',
      extracting: 'warning', chunking: 'warning', embedding: 'warning', uploaded: 'warning',
      failed: 'danger', error: 'danger', skipped: 'danger', disconnected: 'danger',
      todo: 'info',
    };
    const type = map[status] || 'mono';
    return this.badge(status.replace(/_/g, ' '), type);
  },

  priorityBadge(priority) {
    const map = { urgent: 'danger', high: 'warning', medium: 'brand', low: 'info' };
    return this.badge(priority, map[priority] || 'mono');
  },

  /* ── Scores ──────────────────────────────────────────────── */

  scorePercent(value) {
    if (value === null || value === undefined) return '—';
    return Math.round(value * 100) + '%';
  },

  scoreColor(value) {
    if (value >= 0.8) return 'success';
    if (value >= 0.5) return 'warning';
    return 'danger';
  },

  /* ── Functional Helpers ──────────────────────────────────── */

  debounce(fn, delay = 300) {
    let timer;
    return (...args) => {
      clearTimeout(timer);
      timer = setTimeout(() => fn(...args), delay);
    };
  },

  clamp(value, min, max) {
    return Math.min(max, Math.max(min, value));
  },

  /* ── DOM Helpers ─────────────────────────────────────────── */

  createEl(tag, attrs = {}, children = '') {
    const el = document.createElement(tag);
    for (const [key, val] of Object.entries(attrs)) {
      if (key === 'className')        el.className = val;
      else if (key === 'innerHTML')   el.innerHTML = val;
      else if (key === 'textContent') el.textContent = val;
      else if (key.startsWith('on'))  el.addEventListener(key.slice(2).toLowerCase(), val);
      else                            el.setAttribute(key, val);
    }
    if (typeof children === 'string') el.innerHTML = children;
    return el;
  },

  $(selector) {
    return document.querySelector(selector);
  },

  $$(selector) {
    return document.querySelectorAll(selector);
  },
};
