/**
 * NaySchool 3.0 – Authentication Helper
 * Dependency: window.NayAPI (api.js) must be loaded first.
 */

window.NayAuth = {
  /* ── State ─────────────────────────────────────────── */

  isLoggedIn() {
    return !!NayAPI.getToken();
  },

  /* ── Login / Register / Logout ─────────────────────── */

  async login(email, password) {
    const res = await NayAPI.auth.login({ email, password });
    NayAPI.setToken(res.access_token);
    if (res.user) localStorage.setItem('nayschool_user', JSON.stringify(res.user));
    return res;
  },

  async register(email, password, fullName) {
    const res = await NayAPI.auth.register({ email, password, full_name: fullName });
    NayAPI.setToken(res.access_token);
    if (res.user) localStorage.setItem('nayschool_user', JSON.stringify(res.user));
    return res;
  },

  logout() {
    NayAPI.clearToken();
    window.location.href = '/';
  },

  /* ── User helpers ──────────────────────────────────── */

  getCachedUser() {
    try {
      return JSON.parse(localStorage.getItem('nayschool_user'));
    } catch {
      return null;
    }
  },

  async getCurrentUser() {
    try {
      const user = await NayAPI.auth.me();
      localStorage.setItem('nayschool_user', JSON.stringify(user));
      return user;
    } catch {
      return null;
    }
  },

  /* ── Guards ────────────────────────────────────────── */

  requireAuth() {
    if (!this.isLoggedIn()) {
      window.location.href = '/';
      return false;
    }
    return true;
  },

  async ensureOnboarding() {
    // Check if user has completed onboarding, redirect if not
    try {
      const profile = await NayAPI.profile.get();
      if (!profile.onboarding_completed) {
        window.location.href = '/onboarding';
        return false;
      }
      return true;
    } catch {
      return true; // Don't block if profile check fails
    }
  },
};
