/* ============================================================
   NaySchool 3.0 — Centralized API Client
   ============================================================ */

(function () {
  'use strict';

  const TOKEN_KEY = 'nayschool_token';
  const USER_KEY = 'nayschool_user';

  // ── Token Management ──────────────────────────────────────

  function getToken() {
    return localStorage.getItem(TOKEN_KEY);
  }

  function setToken(token) {
    localStorage.setItem(TOKEN_KEY, token);
  }

  function clearToken() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  }

  // ── Core Request ───────────────────────────────────────────

  async function request(path, options = {}) {
    const headers = options.headers || {};
    const isFormData = options.body instanceof FormData;

    if (!isFormData) {
      headers['Content-Type'] = 'application/json';
    }

    const token = getToken();
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const url = `/api${path}`;

    const response = await fetch(url, {
      ...options,
      headers,
    });

    let body;
    const contentType = response.headers.get('content-type') || '';
    if (contentType.includes('application/json')) {
      body = await response.json();
    } else {
      body = await response.text();
    }

    if (response.status === 401) {
      const isAuthPath =
        path === '/auth/login' || path === '/auth/register';
      if (!isAuthPath) {
        clearToken();
        window.location.href = '/';
        return;
      }
    }

    if (
      response.status === 403 &&
      body &&
      typeof body === 'object' &&
      body.error === 'usage_limit_exceeded'
    ) {
      const err = new Error(body.message || 'Usage limit exceeded');
      err.name = 'UsageLimitError';
      err.plan = body.plan || null;
      err.detail = body;
      throw err;
    }

    if (!response.ok) {
      const message =
        (body && typeof body === 'object' && (body.detail || body.message)) ||
        (typeof body === 'string' && body) ||
        `Request failed with status ${response.status}`;
      const err = new Error(typeof message === 'object' ? JSON.stringify(message) : message);
      err.status = response.status;
      err.body = body;
      throw err;
    }

    return body;
  }

  // ── Convenience Methods ────────────────────────────────────

  function get(path) {
    return request(path, { method: 'GET' });
  }

  function post(path, body) {
    return request(path, { method: 'POST', body: JSON.stringify(body) });
  }

  function patch(path, body) {
    return request(path, { method: 'PATCH', body: JSON.stringify(body) });
  }

  function del(path) {
    return request(path, { method: 'DELETE' });
  }

  function upload(path, file) {
    const fd = new FormData();
    fd.append('file', file);
    return request(path, { method: 'POST', body: fd });
  }

  // ── Auth ───────────────────────────────────────────────────

  const auth = {
    register(data) {
      return post('/auth/register', data);
    },
    login(data) {
      return post('/auth/login', data);
    },
    me() {
      return get('/auth/me');
    },
  };

  // ── Profile ────────────────────────────────────────────────

  const profile = {
    get() {
      return get('/me/profile');
    },
    update(data) {
      return patch('/me/profile', data);
    },
    completeOnboarding(data) {
      return post('/me/onboarding/complete', data);
    },
  };

  // ── Student ────────────────────────────────────────────────

  const student = {
    home() {
      return get('/student/home');
    },
    activity(limit = 20) {
      return get(`/me/activity?limit=${limit}`);
    },
    streak() {
      return get('/me/streak');
    },
    plan() {
      return get('/me/plan');
    },
    usage() {
      return get('/me/usage');
    },
    updatePlanDev(plan) {
      return patch('/me/plan-dev', { plan });
    },
  };

  // ── Courses ────────────────────────────────────────────────

  const courses = {
    list() {
      return get('/courses');
    },
    create(data) {
      return post('/courses', data);
    },
    get(id) {
      return get(`/courses/${id}`);
    },
    delete(id) {
      return del(`/courses/${id}`);
    },
    search(id, data) {
      return post(`/courses/${id}/search`, data);
    },
    chunks(id) {
      return get(`/courses/${id}/chunks`);
    },
    embed(id, data = {}) {
      return post(`/courses/${id}/embed`, data);
    },
    embeddingStatus(id) {
      return get(`/courses/${id}/embedding-status`);
    },
    ingestionStatus(id) {
      return get(`/courses/${id}/ingestion-status`);
    },
  };

  // ── Assignments ────────────────────────────────────────────

  const assignments = {
    list(courseId) {
      return get(`/courses/${courseId}/assignments`);
    },
    create(courseId, data) {
      return post(`/courses/${courseId}/assignments`, data);
    },
    update(id, data) {
      return patch(`/assignments/${id}`, data);
    },
  };

  // ── Uploads ────────────────────────────────────────────────

  const uploads = {
    upload(courseId, file) {
      return upload(`/courses/${courseId}/upload`, file);
    },
    files(courseId) {
      return get(`/courses/${courseId}/files`);
    },
    fileStatus(courseId, fileId) {
      return get(`/courses/${courseId}/files/${fileId}/status`);
    },
    reprocess(courseId, fileId) {
      return post(`/courses/${courseId}/files/${fileId}/reprocess`);
    },
  };

  // ── Tutor ──────────────────────────────────────────────────

  const tutor = {
    ask(courseId, data) {
      return post(`/courses/${courseId}/tutor/ask`, data);
    },
    chatSessions(courseId) {
      return get(`/courses/${courseId}/chat-sessions`);
    },
    createChatSession(courseId, data = {}) {
      return post(`/courses/${courseId}/chat-sessions`, data);
    },
    getChatSession(courseId, sessionId) {
      return get(`/courses/${courseId}/chat-sessions/${sessionId}`);
    },
    deleteChatSession(courseId, sessionId) {
      return del(`/courses/${courseId}/chat-sessions/${sessionId}`);
    },
  };

  // ── Topics ─────────────────────────────────────────────────

  const topics = {
    list(courseId) {
      return get(`/courses/${courseId}/topics`);
    },
    create(courseId, data) {
      return post(`/courses/${courseId}/topics`, data);
    },
    extract(courseId, data = {}) {
      return post(`/courses/${courseId}/topics/extract`, data);
    },
    mapChunks(courseId) {
      return post(`/courses/${courseId}/topics/map-chunks`);
    },
    get(courseId, topicId) {
      return get(`/courses/${courseId}/topics/${topicId}`);
    },
  };

  // ── Practice ───────────────────────────────────────────────

  const practice = {
    generate(courseId, data) {
      return post(`/courses/${courseId}/practice/generate`, data);
    },
    list(courseId) {
      return get(`/courses/${courseId}/practice`);
    },
    attempt(courseId, questionId, data) {
      return post(`/courses/${courseId}/practice/${questionId}/attempt`, data);
    },
    attempts(courseId) {
      return get(`/courses/${courseId}/practice/attempts`);
    },
  };

  // ── Study Tasks ────────────────────────────────────────────

  const studyTasks = {
    list(courseId) {
      return get(`/courses/${courseId}/study-tasks`);
    },
    create(courseId, data) {
      return post(`/courses/${courseId}/study-tasks`, data);
    },
    generate(courseId, data = {}) {
      return post(`/courses/${courseId}/study-tasks/generate`, data);
    },
    update(taskId, data) {
      return patch(`/study-tasks/${taskId}`, data);
    },
  };

  // ── Exam Prep ──────────────────────────────────────────────

  const examPrep = {
    generate(courseId, data) {
      return post(`/courses/${courseId}/exam-prep`, data);
    },
  };

  // ── Flashcards ─────────────────────────────────────────────

  const flashcards = {
    generate(courseId, data) {
      return post(`/courses/${courseId}/flashcards/generate`, data);
    },
    list(courseId) {
      return get(`/courses/${courseId}/flashcards`);
    },
  };

  // ── Learning Dashboard ─────────────────────────────────────

  const learningDashboard = {
    get(courseId) {
      return get(`/courses/${courseId}/learning-dashboard`);
    },
  };

  // ── LMS ────────────────────────────────────────────────────

  const lms = {
    providers() {
      return get('/lms/providers');
    },
    connections() {
      return get('/lms/connections');
    },
    connect(provider, data) {
      return post(`/lms/${provider}/connect`, data);
    },
    sync(connectionId, data = {}) {
      return post(`/lms/${connectionId}/sync`, data);
    },
    syncLogs(connectionId) {
      return get(`/lms/${connectionId}/sync-logs`);
    },
    blackboardStatus() {
      return get('/lms/blackboard/status');
    },
  };

  // ── Notifications ──────────────────────────────────────────

  const notifications = {
    list() {
      return get('/notifications');
    },
    markRead(id) {
      return patch(`/notifications/${id}/read`, {});
    },
    generateReminders(courseId) {
      return post(`/courses/${courseId}/notifications/generate-study-reminders`);
    },
  };

  // ── Public API ─────────────────────────────────────────────

  window.NayAPI = {
    getToken,
    setToken,
    clearToken,
    request,
    get,
    post,
    patch,
    del,
    upload,
    auth,
    profile,
    student,
    courses,
    assignments,
    uploads,
    tutor,
    topics,
    practice,
    studyTasks,
    examPrep,
    flashcards,
    learningDashboard,
    lms,
    notifications,
  };
})();
