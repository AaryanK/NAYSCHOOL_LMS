/**
 * NaySchool 3.0 — Layout Manager
 * Renders navbar, footer, toasts, loading overlays, and empty states.
 * Depends on: window.NayAuth, window.NayAPI
 */
window.NayLayout = {

  /* ── Navbar ─────────────────────────────────────────────── */

  renderNavbar(activePage) {
    const loggedIn = NayAuth.isLoggedIn();

    const link = (href, label, page, extra = '') => {
      const cls = activePage === page ? 'nay-nav-link active' : 'nay-nav-link';
      return `<li><a href="${href}" class="${cls}" ${extra}>${label}</a></li>`;
    };

    let links = '';

    if (loggedIn) {
      links = [
        link('/dashboard', 'Dashboard', 'dashboard'),
        link('/dashboard#courses', 'Courses', 'course'),
        link('/lms', 'LMS', 'lms'),
        `<li>
          <a href="/notifications" class="nay-nav-link${activePage === 'notifications' ? ' active' : ''}">
            Notifications
            <span class="nay-notif-badge" id="nay-notif-badge" style="display:none"></span>
          </a>
        </li>`,
        link('/pricing', 'Pricing', 'pricing'),
        link('/docs', 'API Docs', 'docs', 'target="_blank"'),
        `<li><a href="#" class="nay-nav-link" onclick="NayAuth.logout();return false;">Logout</a></li>`,
      ].join('\n');
    } else {
      links = [
        link('/', 'Home', 'home'),
        link('/#features', 'Features', 'features'),
        link('/pricing', 'Pricing', 'pricing'),
        link('/docs', 'API Docs', 'docs', 'target="_blank"'),
        `<li><a href="/onboarding" class="nay-nav-link nay-nav-cta${activePage === 'onboarding' ? ' active' : ''}">Login / Register</a></li>`,
      ].join('\n');
    }

    const nav = document.createElement('nav');
    nav.className = 'nay-navbar';
    nav.innerHTML = `
      <div class="nay-navbar-inner">
        <a href="/" class="nay-logo">
          <div class="nay-logo-icon">N</div>
          <span class="nay-logo-text">NaySchool</span>
        </a>
        <button class="nay-nav-toggle" onclick="NayLayout.toggleMobileNav()" aria-label="Menu">☰</button>
        <ul class="nay-nav-links" id="nay-nav-links">
          ${links}
        </ul>
      </div>`;

    document.body.insertBefore(nav, document.body.firstChild);

    if (loggedIn) this._loadNotificationBadge();
  },

  /* ── Notification badge (async) ─────────────────────────── */

  async _loadNotificationBadge() {
    try {
      const notifs = await NayAPI.notifications.list();
      const unread = notifs.filter(n => !n.read_at).length;
      const badge = document.getElementById('nay-notif-badge');
      if (badge && unread > 0) {
        badge.textContent = unread > 9 ? '9+' : unread;
        badge.style.display = 'inline-flex';
      }
    } catch { /* silent — badge stays hidden */ }
  },

  /* ── Mobile nav toggle ──────────────────────────────────── */

  toggleMobileNav() {
    const links = document.getElementById('nay-nav-links');
    if (links) links.classList.toggle('open');
  },

  /* ── Footer ─────────────────────────────────────────────── */

  renderFooter() {
    const footer = document.createElement('footer');
    footer.className = 'nay-footer';
    footer.innerHTML = `
      <div class="nay-footer-inner">
        <div class="nay-footer-brand">NaySchool 3.0</div>
        <p class="nay-footer-text">Student learning operating system — built for academic excellence</p>
        <div class="nay-footer-links">
          <a href="/dashboard">Dashboard</a>
          <a href="/pricing">Pricing</a>
          <a href="/docs" target="_blank">API Docs</a>
        </div>
      </div>`;
    document.body.appendChild(footer);
  },

  /* ── Auth guard ─────────────────────────────────────────── */

  protectPage() {
    return NayAuth.requireAuth();
  },

  /* ── Page title ─────────────────────────────────────────── */

  setPageTitle(title) {
    document.title = `${title} | NaySchool 3.0`;
  },

  /* ── Toast notifications ────────────────────────────────── */

  showToast(message, type = 'info') {
    let container = document.getElementById('nay-toast-container');
    if (!container) {
      container = document.createElement('div');
      container.id = 'nay-toast-container';
      container.className = 'nay-toast-container';
      document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.className = `nay-toast ${type}`;
    toast.textContent = message;
    container.appendChild(toast);

    setTimeout(() => {
      toast.style.animation = 'fadeOut 0.3s ease forwards';
      setTimeout(() => toast.remove(), 300);
    }, 4000);
  },

  /* ── Loading overlay ────────────────────────────────────── */

  showLoading(target) {
    if (!target) return;
    target.style.position = 'relative';
    const overlay = document.createElement('div');
    overlay.className = 'nay-loading-overlay';
    overlay.innerHTML = '<div class="nay-spinner"></div>';
    overlay.dataset.loadingOverlay = 'true';
    target.appendChild(overlay);
  },

  hideLoading(target) {
    if (!target) return;
    const overlay = target.querySelector('[data-loading-overlay]');
    if (overlay) overlay.remove();
  },

  /* ── Empty state ────────────────────────────────────────── */

  renderEmptyState(container, config) {
    container.innerHTML = `
      <div class="nay-empty">
        <div class="nay-empty-icon">${config.icon || '📭'}</div>
        <div class="nay-empty-title">${config.title || 'Nothing here yet'}</div>
        <div class="nay-empty-text">${config.text || ''}</div>
        ${config.actionText
          ? `<button class="nay-btn nay-btn-primary" id="nay-empty-action">${config.actionText}</button>`
          : ''}
      </div>`;

    const btn = container.querySelector('#nay-empty-action');
    if (!btn) return;

    if (config.onClick) {
      btn.addEventListener('click', config.onClick);
    } else if (config.actionHref) {
      btn.addEventListener('click', () => { window.location.href = config.actionHref; });
    }
  }
};
