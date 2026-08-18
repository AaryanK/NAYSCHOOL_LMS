// API Client Interface
const App = {
  getToken() {
    return localStorage.getItem('nayschool_token');
  },
  setToken(token) {
    localStorage.setItem('nayschool_token', token);
  },
  clearToken() {
    localStorage.removeItem('nayschool_token');
    localStorage.removeItem('nayschool_user');
  },
  getHeaders() {
    const headers = { 'Content-Type': 'application/json' };
    const token = this.getToken();
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    return headers;
  },
  async request(endpoint, options = {}) {
    options.headers = { ...this.getHeaders(), ...options.headers };
    try {
      const response = await fetch(`/api${endpoint}`, options);
      const data = await response.json();
      if (!response.ok) {
        if (response.status === 401 && endpoint !== '/auth/login' && endpoint !== '/auth/register') {
          this.clearToken();
          window.location.href = 'dashboard.html';
        }
        if (response.status === 403 && data.error === 'usage_limit_exceeded') {
          showUsageLimitOverlay(data.message, data.plan);
          throw new Error('usage_limit_exceeded');
        }
        throw new Error(data.detail || 'Request failed.');
      }
      return data;
    } catch (e) {
      console.error(e);
      throw e;
    }
  },

  // Auth Operations
  async register(email, password, fullName) {
    const res = await this.request('/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, password, full_name: fullName })
    });
    this.setToken(res.access_token);
    localStorage.setItem('nayschool_user', JSON.stringify(res.user));
    return res;
  },
  async login(email, password) {
    const res = await this.request('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password })
    });
    this.setToken(res.access_token);
    localStorage.setItem('nayschool_user', JSON.stringify(res.user));
    return res;
  },
  logout() {
    this.clearToken();
    window.location.href = 'index.html';
  },
  async getMe() {
    return this.request('/auth/me');
  },

  // Courses Operations
  async getCourses() {
    return this.request('/courses');
  },
  async getCourse(id) {
    return this.request(`/courses/${id}`);
  },
  async createCourse(name, code, instructor, description) {
    return this.request('/courses', {
      method: 'POST',
      body: JSON.stringify({ name, code, instructor, description })
    });
  },
  async deleteCourse(id) {
    return this.request(`/courses/${id}`, { method: 'DELETE' });
  },

  // Assignments Operations
  async getAssignments(courseId) {
    return this.request(`/courses/${courseId}/assignments`);
  },
  async createAssignment(courseId, title, description, dueDate) {
    return this.request(`/courses/${courseId}/assignments`, {
      method: 'POST',
      body: JSON.stringify({ title, description, due_date: dueDate })
    });
  },
  async updateAssignmentStatus(id, status) {
    return this.request(`/assignments/${id}`, {
      method: 'PATCH',
      body: JSON.stringify({ status })
    });
  },

  // Files Operations
  async getFiles(courseId) {
    return this.request(`/courses/${courseId}/files`);
  },
  async uploadFile(courseId, fileInput) {
    const file = fileInput.files[0];
    if (!file) throw new Error('No file selected.');
    
    const formData = new FormData();
    formData.append('file', file);
    
    const token = this.getToken();
    const headers = {};
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    
    const response = await fetch(`/api/courses/${courseId}/upload`, {
      method: 'POST',
      headers,
      body: formData
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || 'Upload failed.');
    }
    return data;
  },

  // AI Tutor & Exam/Flashcard Generation Operations
  async askTutor(courseId, question, provider, model, sessionId = null) {
    return this.request(`/courses/${courseId}/tutor/ask`, {
      method: 'POST',
      body: JSON.stringify({ question, provider, model, session_id: sessionId })
    });
  },
  async generateExamPrep(courseId, examTitle, examDate, topics, provider, model) {
    return this.request(`/courses/${courseId}/exam-prep`, {
      method: 'POST',
      body: JSON.stringify({ exam_title: examTitle, exam_date: examDate, topics, provider, model })
    });
  },
  async generateFlashcards(courseId, topic, count, provider, model) {
    return this.request(`/courses/${courseId}/flashcards/generate`, {
      method: 'POST',
      body: JSON.stringify({ topic, count: parseInt(count), provider, model })
    });
  },
  async getFlashcards(courseId) {
    return this.request(`/courses/${courseId}/flashcards`);
  },
  async searchCourseMaterials(courseId, query, mode = 'hybrid') {
    return this.request(`/courses/${courseId}/search`, {
      method: 'POST',
      body: JSON.stringify({ query, mode })
    });
  },
  async getEmbeddingStatus(courseId) {
    return this.request(`/courses/${courseId}/embedding-status`);
  },
  async generateEmbeddings(courseId, force = false) {
    return this.request(`/courses/${courseId}/embed`, {
      method: 'POST',
      body: JSON.stringify({ force })
    });
  },
  async getIngestionStatus(courseId) {
    return this.request(`/courses/${courseId}/ingestion-status`);
  },
  async getFileStatus(courseId, fileId) {
    return this.request(`/courses/${courseId}/files/${fileId}/status`);
  },
  async reprocessFile(courseId, fileId, forceEmbeddings = false) {
    return this.request(`/courses/${courseId}/files/${fileId}/reprocess`, {
      method: 'POST',
      body: JSON.stringify({ force_embeddings: forceEmbeddings })
    });
  },
  async getCourseChunks(courseId) {
    return this.request(`/courses/${courseId}/chunks`);
  },

  // Blackboard Placeholder integration
  async getBlackboardStatus() {
    return this.request('/lms/blackboard/status');
  },
  async connectBlackboardPlaceholder() {
    return this.request('/lms/blackboard/connect-placeholder', { method: 'POST' });
  },
  async syncBlackboardPlaceholder() {
    return this.request('/lms/blackboard/sync-placeholder', { method: 'POST' });
  },

  // Unified LMS API operations
  async getLMSProviders() {
    return this.request('/lms/providers');
  },
  async getLMSConnections() {
    return this.request('/lms/connections');
  },
  async connectLMSProvider(provider, schoolDomain) {
    return this.request(`/lms/${provider}/connect`, {
      method: 'POST',
      body: JSON.stringify({ school_domain: schoolDomain })
    });
  },
  async syncLMSConnection(connectionId, options = {}) {
    return this.request(`/lms/${connectionId}/sync`, {
      method: 'POST',
      body: JSON.stringify(options)
    });
  },
  async getLMSSyncLogs(connectionId) {
    return this.request(`/lms/${connectionId}/sync-logs`);
  },
  async probeLMSConnection(connectionId) {
    return this.request(`/lms/${connectionId}/probe`);
  },

  // Phase 5 Operations
  async getTopics(courseId) {
    return this.request(`/courses/${courseId}/topics`);
  },
  async createTopic(courseId, name, description) {
    return this.request(`/courses/${courseId}/topics`, {
      method: 'POST',
      body: JSON.stringify({ name, description })
    });
  },
  async extractTopics(courseId, provider, model) {
    return this.request(`/courses/${courseId}/topics/extract`, {
      method: 'POST',
      body: JSON.stringify({ provider, model })
    });
  },
  async mapChunks(courseId) {
    return this.request(`/courses/${courseId}/topics/map-chunks`, {
      method: 'POST'
    });
  },
  async generatePractice(courseId, topicId, count, difficulty, provider, model) {
    return this.request(`/courses/${courseId}/practice/generate`, {
      method: 'POST',
      body: JSON.stringify({ topic_id: topicId ? parseInt(topicId) : null, count: parseInt(count), difficulty, provider, model })
    });
  },
  async getPracticeQuestions(courseId, topicId = null) {
    let url = `/courses/${courseId}/practice`;
    if (topicId) url += `?topic_id=${topicId}`;
    return this.request(url);
  },
  async gradePracticeAttempt(courseId, questionId, studentAnswer, provider, model) {
    return this.request(`/courses/${courseId}/practice/${questionId}/attempt`, {
      method: 'POST',
      body: JSON.stringify({ student_answer: studentAnswer, provider, model })
    });
  },
  async getPracticeAttempts(courseId) {
    return this.request(`/courses/${courseId}/practice/attempts`);
  },
  async getStudyTasks(courseId) {
    return this.request(`/courses/${courseId}/study-tasks`);
  },
  async generateStudyTasks(courseId, days = 7) {
    return this.request(`/courses/${courseId}/study-tasks/generate`, {
      method: 'POST',
      body: JSON.stringify({ days: parseInt(days) })
    });
  },
  async updateStudyTaskStatus(taskId, status) {
    return this.request(`/study-tasks/${taskId}`, {
      method: 'PATCH',
      body: JSON.stringify({ status })
    });
  },
  async getLearningDashboard(courseId) {
    return this.request(`/courses/${courseId}/learning-dashboard`);
  }
};

// Alert display utility
function showAlert(message, type = 'danger', containerId = 'alert-container') {
  const container = document.getElementById(containerId);
  if (!container) return;
  
  const alert = document.createElement('div');
  alert.className = `alert alert-${type}`;
  alert.textContent = message;
  container.innerHTML = '';
  container.appendChild(alert);
  
  // Auto dismiss in 5s
  setTimeout(() => alert.remove(), 6000);
}

function showUsageLimitOverlay(message, currentPlan) {
  let overlay = document.getElementById('usage-limit-overlay');
  if (overlay) overlay.remove();

  overlay = document.createElement('div');
  overlay.id = 'usage-limit-overlay';
  overlay.style = `
    position: fixed;
    top: 0; left: 0; width: 100vw; height: 100vh;
    background: rgba(5, 7, 12, 0.9);
    display: flex; justify-content: center; align-items: center;
    z-index: 9999; backdrop-filter: blur(10px);
  `;
  
  overlay.innerHTML = `
    <div class="card" style="max-width: 500px; padding: 2.5rem; text-align: center; border-color: #6366f1; box-shadow: 0 0 30px rgba(99, 102, 241, 0.3);">
      <div style="font-size: 3rem; margin-bottom: 1rem;">⚡</div>
      <h2 style="font-size: 1.8rem; margin-bottom: 0.75rem;" class="text-gradient">Usage Limit Exceeded</h2>
      <p style="color: var(--text-white); margin-bottom: 1.5rem; line-height: 1.5;">${message}</p>
      <div style="background: rgba(255,255,255,0.03); border: 1px solid var(--border-color); padding: 0.75rem; border-radius: 6px; font-size: 0.85rem; color: var(--text-gray); margin-bottom: 2rem;">
        Current Plan: <strong style="color: var(--accent-cyan);">${currentPlan.toUpperCase()}</strong>
      </div>
      <div style="display: flex; gap: 1rem; justify-content: center;">
        <a href="pricing.html" class="btn btn-primary">Upgrade Plan</a>
        <button onclick="document.getElementById('usage-limit-overlay').remove()" class="btn btn-secondary">Close</button>
      </div>
    </div>
  `;
  document.body.appendChild(overlay);
}

// Global page initialization
document.addEventListener('DOMContentLoaded', () => {
  setupNavbar();
  
  const path = window.location.pathname;
  if (path.includes('dashboard.html')) {
    initDashboard();
  } else if (path.includes('course.html')) {
    initCourse();
  } else if (path.includes('lms.html') || path === '/lms') {
    initLMSPage();
  } else {
    initIndex();
  }
});

// Setup dynamic elements in Navbar
function setupNavbar() {
  const navContainer = document.querySelector('.nav-links');
  if (!navContainer) return;
  
  const token = App.getToken();
  if (token) {
    const userStr = localStorage.getItem('nayschool_user');
    const user = userStr ? JSON.parse(userStr) : null;
    const name = user ? user.full_name || user.email : 'User';
    
    navContainer.innerHTML = `
      <a href="dashboard.html" class="nav-link">Dashboard</a>
      <a href="lms.html" class="nav-link">LMS Integrations</a>
      <a href="pricing.html" class="nav-link">Pricing</a>
      <a href="notifications.html" class="nav-link" id="nav-notif-link">
        Notifications <span class="badge" id="nav-notif-badge" style="display: none; background: #ef4444; color: white; padding: 0.1rem 0.4rem; font-size: 0.65rem; border: none; margin-left: 0.25rem;">0</span>
      </a>
      <span class="nav-link" style="color: var(--text-white); margin-left: 1rem;">Hi, ${name}</span>
      <button onclick="App.logout()" class="btn btn-secondary" style="padding: 0.4rem 1rem; font-size: 0.85rem; margin-left: 0.5rem;">Logout</button>
    `;

    // Fetch unread notifications count
    App.request('/notifications').then(notifs => {
      const unread = notifs.filter(n => n.read_at === null).length;
      const badge = document.getElementById('nav-notif-badge');
      if (badge) {
        if (unread > 0) {
          badge.textContent = unread;
          badge.style.display = 'inline-block';
        } else {
          badge.style.display = 'none';
        }
      }
    }).catch(e => console.error("Error reading notifications count:", e));

  } else {
    navContainer.innerHTML = `
      <a href="dashboard.html" class="nav-link btn btn-primary" style="padding: 0.4rem 1.2rem; font-size: 0.85rem; color: white;">Get Started</a>
    `;
  }
}

// Landing page logic
function initIndex() {
  const ctaBtn = document.getElementById('cta-btn');
  if (!ctaBtn) return;
  const token = App.getToken();
  ctaBtn.href = token ? 'dashboard.html' : 'dashboard.html';
}

// Dashboard Page logic
function initDashboard() {
  const token = App.getToken();
  const authSection = document.getElementById('auth-section');
  const appSection = document.getElementById('app-section');
  
  if (!token) {
    if (authSection) authSection.style.display = 'block';
    if (appSection) appSection.style.display = 'none';
    setupAuthForms();
  } else {
    if (authSection) authSection.style.display = 'none';
    if (appSection) appSection.style.display = 'block';
    
    // Check user profile onboarding completion
    App.request('/me/profile').then(profile => {
      if (!profile.onboarding_completed) {
        window.location.href = 'onboarding.html';
      } else {
        loadStudentHomeDashboard();
      }
    }).catch(err => {
      console.error("Profile check failed:", err);
      loadStudentHomeDashboard();
    });

    setupCourseCreationForm();
    
    // Toggles for course creator card
    const btnShowAdd = document.getElementById('btn-show-add-course');
    const btnCancelAdd = document.getElementById('btn-cancel-add-course');
    const addCardContainer = document.getElementById('add-course-container');
    
    if (btnShowAdd && addCardContainer) {
      btnShowAdd.addEventListener('click', () => {
        addCardContainer.style.display = 'block';
        btnShowAdd.style.display = 'none';
      });
    }
    if (btnCancelAdd && addCardContainer) {
      btnCancelAdd.addEventListener('click', () => {
        addCardContainer.style.display = 'none';
        if (btnShowAdd) btnShowAdd.style.display = 'block';
      });
    }
  }
}

function setupAuthForms() {
  const loginForm = document.getElementById('login-form');
  const registerForm = document.getElementById('register-form');
  
  if (loginForm) {
    loginForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const email = document.getElementById('login-email').value;
      const pass = document.getElementById('login-password').value;
      try {
        await App.login(email, pass);
        window.location.reload();
      } catch (err) {
        showAlert(err.message, 'danger', 'auth-alert-container');
      }
    });
  }
  
  if (registerForm) {
    registerForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const name = document.getElementById('reg-name').value;
      const email = document.getElementById('reg-email').value;
      const pass = document.getElementById('reg-password').value;
      try {
        await App.register(email, pass, name);
        window.location.reload();
      } catch (err) {
        showAlert(err.message, 'danger', 'auth-alert-container');
      }
    });
  }
}

async function loadStudentHomeDashboard() {
  const alertContainer = 'dashboard-alert-container';
  try {
    const data = await App.request('/student/home');
    
    // Streak
    const streakDays = document.getElementById('streak-days');
    if (streakDays) {
      streakDays.textContent = data.streak.current_streak_days;
    }
    
    // Student Name & Onboarding Summary
    const studentName = document.getElementById('student-name');
    if (studentName) {
      studentName.textContent = data.user.full_name || 'Student';
    }
    
    const summaryEl = document.getElementById('onboarding-summary');
    if (summaryEl && data.profile) {
      const edLevel = data.profile.education_level ? data.profile.education_level.replace('_', ' ') : 'Self Learner';
      const majorStr = data.profile.major ? ` studying ${data.profile.major}` : '';
      const goalStr = data.profile.study_goal ? `. Goal: ${data.profile.study_goal}` : '';
      summaryEl.textContent = `${edLevel.charAt(0).toUpperCase() + edLevel.slice(1)}${majorStr}${goalStr}`;
    }
    
    // Recommended Actions
    const recContainer = document.getElementById('recommendations-container');
    if (recContainer) {
      if (data.recommended_actions && data.recommended_actions.length > 0) {
        const actionsHtml = data.recommended_actions.map(action => `
          <div style="background: rgba(255, 255, 255, 0.04); border: 1px solid var(--border-color); border-radius: 8px; padding: 0.6rem 1rem; margin-top: 0.5rem; display: flex; justify-content: space-between; align-items: center; font-size: 0.85rem;">
            <span>💡 ${action}</span>
          </div>
        `).join('');
        recContainer.innerHTML = `
          <div style="margin-top: 0.75rem;">
            <span style="font-size: 0.72rem; text-transform: uppercase; font-weight: 700; color: var(--text-gray); letter-spacing: 0.05em; display: block; margin-bottom: 0.25rem;">Recommended Next Steps</span>
            ${actionsHtml}
          </div>
        `;
      } else {
        recContainer.innerHTML = '';
      }
    }

    // Today's agenda tasks
    const agendaList = document.getElementById('agenda-list');
    const agendaCount = document.getElementById('agenda-count');
    if (agendaList) {
      agendaCount.textContent = `${data.study_tasks_today.length} tasks`;
      if (data.study_tasks_today.length === 0) {
        agendaList.innerHTML = `
          <div class="empty-state">
            <h4>No study tasks today!</h4>
            <p>Generate a study plan inside your courses to get daily tasks.</p>
          </div>
        `;
      } else {
        agendaList.innerHTML = data.study_tasks_today.map(t => {
          const isCompleted = t.status === 'completed';
          const checkedAttr = isCompleted ? 'checked' : '';
          const lineThrough = isCompleted ? 'text-decoration: line-through; color: var(--text-gray);' : 'color: var(--text-white);';
          return `
            <div class="agenda-item">
              <div style="display: flex; gap: 0.75rem; align-items: start;">
                <input type="checkbox" ${checkedAttr} onchange="toggleDashboardTaskStatus(${t.id}, this.checked)" style="margin-top: 0.25rem; cursor: pointer;">
                <div>
                  <strong style="${lineThrough}">${t.title}</strong>
                  <div style="font-size: 0.75rem; color: var(--text-gray); margin-top: 0.15rem;">${t.description || 'Study session'}</div>
                </div>
              </div>
              <span class="badge" style="background: rgba(139, 92, 246, 0.15); color: #8b5cf6;">${t.priority.toUpperCase()}</span>
            </div>
          `;
        }).join('');
      }
    }

    // Due soon assignments
    const dueList = document.getElementById('due-soon-list');
    const dueCount = document.getElementById('due-count');
    if (dueList) {
      dueCount.textContent = `${data.assignments_due_soon.length} due`;
      if (data.assignments_due_soon.length === 0) {
        dueList.innerHTML = `
          <div class="empty-state">
            <h4>No assignments due soon</h4>
            <p>You have no pending assignments in the next 7 days.</p>
          </div>
        `;
      } else {
        dueList.innerHTML = data.assignments_due_soon.map(a => `
          <div class="agenda-item">
            <div>
              <strong>${a.title}</strong>
              <div style="font-size: 0.75rem; color: var(--text-gray); margin-top: 0.15rem;">Due on: ${a.due_date || 'Soon'}</div>
            </div>
            <span class="badge" style="background: rgba(239, 68, 68, 0.15); color: var(--accent-rose); border: 1px solid rgba(239, 68, 68, 0.3);">Due Soon</span>
          </div>
        `).join('');
      }
    }

    // Weak topics
    const weakList = document.getElementById('weak-topics-list');
    if (weakList) {
      if (data.weak_topics.length === 0) {
        weakList.innerHTML = `
          <div class="empty-state">
            <p>Mastery stats will appear once you solve practice attempts.</p>
          </div>
        `;
      } else {
        weakList.innerHTML = data.weak_topics.map(t => `
          <div class="weak-item">
            <div>
              <strong>${t.topic_name}</strong>
              <div style="font-size: 0.75rem; color: var(--text-gray); margin-top: 0.15rem;">Course: ${t.course_name}</div>
            </div>
            <div style="display: flex; align-items: center; gap: 0.5rem;">
              <span class="badge" style="background: rgba(244, 63, 94, 0.15); color: var(--accent-rose);">${Math.round(t.mastery_score * 100)}%</span>
              <a href="course.html?course_id=${t.course_id}&tab=practice" class="btn btn-secondary" style="padding: 0.25rem 0.6rem; font-size: 0.75rem; min-width: auto;">Practice</a>
            </div>
          </div>
        `).join('');
      }
    }

    // Recent chats
    const recentChats = document.getElementById('recent-chats-list');
    if (recentChats) {
      if (data.recent_chat_sessions.length === 0) {
        recentChats.innerHTML = `
          <div class="empty-state">
            <p>Ask a question to the tutor inside a course space to save chats.</p>
          </div>
        `;
      } else {
        recentChats.innerHTML = data.recent_chat_sessions.map(s => `
          <div class="chat-session-item">
            <div style="flex: 1; min-width: 0; padding-right: 0.5rem;">
              <strong style="display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${s.title}</strong>
            </div>
            <a href="course.html?course_id=${s.course_id}&tab=tutor&session_id=${s.id}" class="btn btn-secondary" style="padding: 0.25rem 0.6rem; font-size: 0.75rem; min-width: auto;">Resume</a>
          </div>
        `).join('');
      }
    }

    // Courses List
    const coursesList = document.getElementById('courses-list');
    if (coursesList) {
      const courses = data.recent_courses;
      if (courses.length === 0) {
        coursesList.innerHTML = `
          <div class="empty-state" style="grid-column: 1 / -1; padding: 4rem 2rem;">
            <h3>Start by creating a course space</h3>
            <p style="margin-bottom: 1.5rem;">Upload your syllabus, lecture notes, or textbooks, and AI will prepare quizzes, schedules, and study guides for you.</p>
            <button class="btn btn-primary" onclick="document.getElementById('add-course-container').style.display='block'; document.getElementById('btn-show-add-course').style.display='none';">Create Course Now</button>
          </div>
        `;
      } else {
        coursesList.innerHTML = courses.map(c => `
          <div class="card course-item" onclick="window.location.href='course.html?course_id=${c.id}'">
            <div class="course-code">${c.code || 'NO CODE'}</div>
            <h3 style="margin-bottom: 0.5rem;">${c.name}</h3>
            <p style="color: var(--text-gray); font-size: 0.9rem; margin-bottom: 1rem;">Instructor: ${c.instructor || 'Not Specified'}</p>
            <p style="color: var(--text-dark); font-size: 0.85rem;">${c.description || 'No description provided.'}</p>
          </div>
        `).join('');
      }
    }

  } catch (err) {
    showAlert('Failed to load dashboard: ' + err.message, 'danger', alertContainer);
  }
}

window.toggleDashboardTaskStatus = async function(taskId, isChecked) {
  try {
    const status = isChecked ? 'completed' : 'pending';
    await App.updateStudyTaskStatus(taskId, status);
    loadStudentHomeDashboard();
  } catch (err) {
    showAlert('Failed to update task: ' + err.message, 'danger', 'dashboard-alert-container');
  }
};

function setupCourseCreationForm() {
  const form = document.getElementById('create-course-form');
  if (!form) return;
  
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const name = document.getElementById('course-name').value;
    const code = document.getElementById('course-code').value;
    const inst = document.getElementById('course-instructor').value;
    const desc = document.getElementById('course-desc').value;
    
    try {
      await App.createCourse(name, code, inst, desc);
      form.reset();
      
      const addCardContainer = document.getElementById('add-course-container');
      const btnShowAdd = document.getElementById('btn-show-add-course');
      if (addCardContainer) addCardContainer.style.display = 'none';
      if (btnShowAdd) btnShowAdd.style.display = 'block';

      loadStudentHomeDashboard();
      showAlert('Course created successfully!', 'success', 'dashboard-alert-container');
    } catch (err) {
      showAlert(err.message, 'danger', 'dashboard-alert-container');
    }
  });
}

// Course details page logic
let currentCourseId = null;
let activeChatSessionId = null;

async function initCourse() {
  const token = App.getToken();
  if (!token) {
    window.location.href = 'dashboard.html';
    return;
  }
  
  const params = new URLSearchParams(window.location.search);
  currentCourseId = params.get('course_id');
  if (!currentCourseId) {
    window.location.href = 'dashboard.html';
    return;
  }

  setupWorkspaceTabs();
  
  await loadCourseDetails();
  await loadAssignments();
  await loadFiles();
  await loadFlashcards();
  await updateIngestionStatusSummary();
  await loadLearningDashboard();
  await loadTopics();
  await loadStudyTasks();
  
  setupCoursePageForms();
  setupBlackboardScaffold();
  await loadChatSessions();
  setupQuickAskForm();
  setupCompileRemindersButton();
  handleUrlQueryParams();

  const refreshBtn = document.getElementById('refresh-ingestion-btn');
  if (refreshBtn) {
    refreshBtn.addEventListener('click', async () => {
      refreshBtn.disabled = true;
      try {
        await updateIngestionStatusSummary();
        await loadFiles();
        await updateEmbeddingStatus();
        showAlert('Ingestion status refreshed.', 'success');
      } catch (err) {
        showAlert('Failed to refresh: ' + err.message, 'danger');
      } finally {
        refreshBtn.disabled = false;
      }
    });
  }
}

async function loadCourseDetails() {
  try {
    const course = await App.getCourse(currentCourseId);
    document.getElementById('course-title-header').textContent = course.name;
    document.getElementById('course-code-header').textContent = course.code || 'NO CODE';
    document.getElementById('course-instructor-text').textContent = course.instructor || 'Unknown';
    document.getElementById('course-desc-text').textContent = course.description || 'No description provided.';
    await updateEmbeddingStatus();
  } catch (e) {
    showAlert('Error loading course details: ' + e.message, 'danger');
  }
}

async function updateEmbeddingStatus() {
  try {
    const status = await App.getEmbeddingStatus(currentCourseId);
    document.getElementById('embed-total-chunks').textContent = status.chunks_total;
    document.getElementById('embed-embedded-chunks').textContent = status.chunks_with_embeddings;
    document.getElementById('embed-missing-chunks').textContent = status.chunks_without_embeddings;
    document.getElementById('embed-model-name').textContent = status.embedding_model || 'None';
  } catch (e) {
    console.error('Error fetching embedding status:', e);
  }
}

async function loadAssignments() {
  const listEl = document.getElementById('assignments-list');
  if (!listEl) return;
  try {
    const assigns = await App.getAssignments(currentCourseId);
    if (assigns.length === 0) {
      listEl.innerHTML = '<p style="color: var(--text-dark);">No assignments added yet.</p>';
      return;
    }
    
    listEl.innerHTML = assigns.map(a => {
      const isDone = a.status === 'completed';
      const statusBtn = isDone 
        ? `<span class="badge badge-allowed" style="cursor: pointer;" onclick="toggleAssignmentStatus(${a.id}, 'todo')">✓ Done</span>`
        : `<span class="badge badge-caution" style="cursor: pointer;" onclick="toggleAssignmentStatus(${a.id}, 'completed')">☐ ToDo</span>`;
      
      return `
        <div class="assignment-item">
          <div>
            <h4 style="${isDone ? 'text-decoration: line-through; color: var(--text-dark);' : ''}">${a.title}</h4>
            <p class="assignment-meta">${a.description || ''} ${a.due_date ? `| Due: ${a.due_date}` : ''}</p>
          </div>
          <div>${statusBtn}</div>
        </div>
      `;
    }).join('');
  } catch (e) {
    showAlert('Error loading assignments: ' + e.message, 'danger');
  }
}

async function toggleAssignmentStatus(id, newStatus) {
  try {
    await App.updateAssignmentStatus(id, newStatus);
    loadAssignments();
  } catch (e) {
    showAlert('Error updating assignment: ' + e.message, 'danger');
  }
}

function getStatusBg(status) {
  switch (status) {
    case 'completed':
    case 'success':
      return 'rgba(16, 185, 129, 0.15)';
    case 'uploaded':
    case 'extracting':
    case 'chunking':
    case 'embedding':
    case 'pending':
      return 'rgba(6, 182, 212, 0.15)';
    case 'skipped':
    case 'unsupported':
      return 'rgba(234, 179, 8, 0.15)';
    case 'failed':
      return 'rgba(244, 63, 94, 0.15)';
    case 'partial':
      return 'rgba(139, 92, 246, 0.15)';
    default:
      return 'rgba(255, 255, 255, 0.05)';
  }
}

function getStatusColor(status) {
  switch (status) {
    case 'completed':
    case 'success':
      return 'var(--accent-emerald)';
    case 'uploaded':
    case 'extracting':
    case 'chunking':
    case 'embedding':
    case 'pending':
      return 'var(--accent-cyan)';
    case 'skipped':
    case 'unsupported':
      return 'var(--accent-yellow)';
    case 'failed':
      return 'var(--accent-rose)';
    case 'partial':
      return 'var(--accent-purple)';
    default:
      return 'var(--text-gray)';
  }
}

const activePolls = new Set();

function startPollingFile(fileId) {
  if (activePolls.has(fileId)) return;
  activePolls.add(fileId);
  
  const intervalId = setInterval(async () => {
    try {
      const status = await App.getFileStatus(currentCourseId, fileId);
      
      await loadFiles();
      await updateIngestionStatusSummary();
      await updateEmbeddingStatus();
      
      const finishedStates = ['completed', 'failed', 'partial'];
      if (finishedStates.includes(status.processing_status)) {
        clearInterval(intervalId);
        activePolls.delete(fileId);
        
        if (status.processing_status === 'completed') {
          showAlert(`File "${status.filename}" processed successfully!`, 'success');
        } else if (status.processing_status === 'failed') {
          showAlert(`File "${status.filename}" processing failed: ${status.processing_error || 'unknown error'}`, 'danger');
        } else if (status.processing_status === 'partial') {
          showAlert(`File "${status.filename}" processed with partial success. Check errors.`, 'warning');
        }
      }
    } catch (err) {
      console.error(`Polling error for file ${fileId}:`, err);
      clearInterval(intervalId);
      activePolls.delete(fileId);
    }
  }, 3000);
}

async function updateIngestionStatusSummary() {
  try {
    const summary = await App.getIngestionStatus(currentCourseId);
    document.getElementById('ingest-total-files').textContent = summary.files_total;
    document.getElementById('ingest-completed').textContent = summary.completed;
    document.getElementById('ingest-processing').textContent = summary.processing;
    document.getElementById('ingest-failed').textContent = summary.failed;
    document.getElementById('ingest-total-chunks').textContent = summary.chunks_total;
    document.getElementById('ingest-embedded-chunks').textContent = summary.embedded_total;
  } catch (e) {
    console.error('Error loading ingestion summary:', e);
  }
}

window.triggerReprocess = async function(fileId) {
  try {
    showAlert('Reprocessing started in the background.', 'success');
    await App.reprocessFile(currentCourseId, fileId, false);
    await loadFiles();
    await updateIngestionStatusSummary();
    startPollingFile(fileId);
  } catch (err) {
    showAlert('Reprocess failed: ' + err.message, 'danger');
  }
};

async function loadFiles() {
  const listEl = document.getElementById('files-list');
  if (!listEl) return;
  try {
    const files = await App.getFiles(currentCourseId);
    if (files.length === 0) {
      listEl.innerHTML = '<p style="color: var(--text-dark);">No files uploaded yet.</p>';
      return;
    }
    
    // Auto-start polling for files that are in transition
    files.forEach(f => {
      const processingStates = ['uploaded', 'extracting', 'chunking', 'embedding'];
      if (processingStates.includes(f.processing_status)) {
        startPollingFile(f.id);
      }
    });

    listEl.innerHTML = files.map(f => {
      const date = new Date(f.uploaded_at).toLocaleDateString();
      return `
        <li class="file-item" style="display: flex; flex-direction: column; gap: 0.5rem; align-items: stretch; border: 1px solid var(--border-color); border-radius: 6px; padding: 0.75rem; background: rgba(255,255,255,0.02); margin-bottom: 0.75rem; list-style: none;">
          <div style="display: flex; justify-content: space-between; align-items: start;">
            <div class="file-info" style="display: flex; gap: 0.5rem; align-items: center;">
              <span style="color: var(--accent-cyan); font-size: 1.2rem;">📁</span>
              <div>
                <div style="font-weight: 500; font-size: 0.9rem; color: var(--text-white);">${f.original_filename}</div>
                <div class="file-meta" style="font-size: 0.75rem; color: var(--text-gray);">Uploaded on ${date}</div>
              </div>
            </div>
            <span class="badge" style="background: rgba(255,255,255,0.05); color: var(--text-gray); border: 1px solid var(--border-color); font-size: 0.75rem;">${f.file_type || 'Unknown'}</span>
          </div>
          
          <div style="display: flex; flex-wrap: wrap; gap: 0.4rem; font-size: 0.75rem; align-items: center; margin-top: 0.25rem;">
            <span class="badge" style="background: ${getStatusBg(f.processing_status)}; color: ${getStatusColor(f.processing_status)}; border: 1px solid rgba(255,255,255,0.1);">Proc: ${f.processing_status}</span>
            <span class="badge" style="background: ${getStatusBg(f.extraction_status)}; color: ${getStatusColor(f.extraction_status)}; border: 1px solid rgba(255,255,255,0.1);">Ext: ${f.extraction_status || 'pending'}</span>
            <span class="badge" style="background: ${getStatusBg(f.embedding_status)}; color: ${getStatusColor(f.embedding_status)}; border: 1px solid rgba(255,255,255,0.1);">Embed: ${f.embedding_status || 'pending'}</span>
          </div>

          <div style="display: flex; justify-content: space-between; align-items: center; font-size: 0.8rem; color: var(--text-gray); margin-top: 0.25rem;">
            <div>
              <span>Chunks: <strong>${f.chunk_count || 0}</strong></span> | 
              <span>Embedded: <strong>${f.embedded_count || 0}</strong></span>
            </div>
            <button onclick="triggerReprocess(${f.id})" class="btn btn-secondary" style="font-size: 0.7rem; padding: 0.2rem 0.5rem; min-width: auto; background: rgba(255,255,255,0.05); border: 1px solid var(--border-color); color: var(--text-white); cursor: pointer;">Reprocess</button>
          </div>
          
          ${f.processing_error ? `
            <div style="font-size: 0.75rem; color: var(--accent-rose); background: rgba(244,63,94,0.1); border-left: 2px solid var(--accent-rose); padding: 0.25rem 0.5rem; margin-top: 0.25rem; border-radius: 2px; word-break: break-all;">
              Error: ${f.processing_error}
            </div>
          ` : ''}
        </li>
      `;
    }).join('');
  } catch (e) {
    showAlert('Error loading files: ' + e.message, 'danger');
  }
}

async function loadFlashcards() {
  const container = document.getElementById('flashcards-list');
  if (!container) return;
  try {
    const cards = await App.getFlashcards(currentCourseId);
    if (cards.length === 0) {
      container.innerHTML = '<p style="color: var(--text-dark);">No flashcards generated yet. Create them in the sidebar.</p>';
      return;
    }
    
    container.innerHTML = cards.map(c => `
      <div class="flashcard" onclick="this.classList.toggle('flipped')">
        <div class="flashcard-inner">
          <div class="flashcard-front">
            <div class="flashcard-topic">${c.topic || 'General'}</div>
            <div style="font-weight: 500; font-size: 1.05rem;">${c.front}</div>
            <div style="position: absolute; bottom: 10px; font-size: 0.7rem; color: var(--text-dark);">Click to flip</div>
          </div>
          <div class="flashcard-back">
            <div style="font-size: 0.95rem;">${c.back}</div>
          </div>
        </div>
      </div>
    `).join('');
  } catch (e) {
    showAlert('Error loading flashcards: ' + e.message, 'danger');
  }
}

function setupCoursePageForms() {
  // 1. File Upload Form
  const uploadForm = document.getElementById('upload-file-form');
  if (uploadForm) {
    uploadForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const fileInput = document.getElementById('file-input');
      const submitBtn = uploadForm.querySelector('button[type="submit"]');
      submitBtn.disabled = true;
      submitBtn.innerHTML = '<div class="spinner"></div> Uploading...';
      
      try {
        const res = await App.uploadFile(currentCourseId, fileInput);
        uploadForm.reset();
        showAlert('Processing started.', 'info');
        await loadFiles();
        await updateIngestionStatusSummary();
        if (res.file && res.file.id) {
          startPollingFile(res.file.id);
        }
      } catch (err) {
        showAlert(err.message, 'danger');
      } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Upload File';
      }
    });
  }


  // 2. Assignment Form
  const assignForm = document.getElementById('add-assignment-form');
  if (assignForm) {
    assignForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const title = document.getElementById('assign-title').value;
      const desc = document.getElementById('assign-desc').value;
      const date = document.getElementById('assign-date').value;
      
      try {
        await App.createAssignment(currentCourseId, title, desc, date);
        assignForm.reset();
        showAlert('Assignment created!', 'success');
        loadAssignments();
      } catch (err) {
        showAlert(err.message, 'danger');
      }
    });
  }

  // Search Materials Form
  const searchForm = document.getElementById('search-materials-form');
  if (searchForm) {
    searchForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const query = document.getElementById('search-query').value;
      const mode = document.getElementById('search-mode').value;
      const submitBtn = searchForm.querySelector('button[type="submit"]');
      submitBtn.disabled = true;
      submitBtn.innerHTML = '<div class="spinner"></div> Searching...';
      
      const resultsBox = document.getElementById('search-results-box');
      const resultsList = document.getElementById('search-results-list');
      resultsBox.style.display = 'none';
      resultsList.innerHTML = '';
      
      try {
        const res = await App.searchCourseMaterials(currentCourseId, query, mode);
        resultsBox.style.display = 'block';
        if (res.results.length === 0) {
          resultsList.innerHTML = '<p style="color: var(--text-dark); padding: 0.5rem;">No matching text passages found in your materials.</p>';
          return;
        }
        
        resultsList.innerHTML = res.results.map(r => {
          const finalScore = r.final_score !== null && r.final_score !== undefined ? r.final_score.toFixed(3) : r.score.toFixed(1);
          const semScore = r.semantic_score !== null && r.semantic_score !== undefined ? r.semantic_score.toFixed(3) : 'N/A';
          const kwScore = r.keyword_score !== null && r.keyword_score !== undefined ? r.keyword_score.toFixed(3) : 'N/A';
          
          return `
            <div style="background: rgba(0, 0, 0, 0.2); border: 1px solid var(--border-color); border-radius: 6px; padding: 1rem; border-left: 3px solid var(--accent-cyan);">
              <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem; font-size: 0.8rem; color: var(--text-gray); flex-wrap: wrap; gap: 0.5rem;">
                <span><strong>Chunk ID:</strong> ${r.chunk_id} | <strong>File ID:</strong> ${r.course_file_id}</span>
                <div style="display: flex; gap: 0.4rem; font-size: 0.75rem;">
                  <span class="badge" style="background: rgba(99, 102, 241, 0.15); color: var(--accent-indigo); border: 1px solid rgba(99, 102, 241, 0.3);">Final Score: ${finalScore}</span>
                  <span class="badge" style="background: rgba(6, 182, 212, 0.15); color: var(--accent-cyan); border: 1px solid rgba(6, 182, 212, 0.3);">Semantic: ${semScore}</span>
                  <span class="badge" style="background: rgba(234, 179, 8, 0.15); color: var(--accent-yellow); border: 1px solid rgba(234, 179, 8, 0.3);">Keyword: ${kwScore}</span>
                </div>
              </div>
              <p style="font-size: 0.9rem; line-height: 1.5; color: var(--text-white); white-space: pre-line;">${r.content}</p>
            </div>
          `;
        }).join('');
      } catch (err) {
        showAlert('Search error: ' + err.message, 'danger');
      } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Search';
      }
    });
  }

  // 3. AI Tutor Ask
  const tutorForm = document.getElementById('ask-tutor-form');
  if (tutorForm) {
    tutorForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const questionEl = document.getElementById('tutor-question');
      const question = questionEl.value;
      const provider = document.getElementById('provider-select').value;
      const submitBtn = tutorForm.querySelector('button[type="submit"]');
      
      if (!question.trim()) return;
      
      // Append user message immediately
      const historyBox = document.getElementById('chat-message-history');
      if (historyBox) {
        // Clear initial guide if it is the only child or first message
        if (historyBox.innerHTML.includes("Hello! I am your NaySchool Course Tutor")) {
          historyBox.innerHTML = '';
        }
        historyBox.innerHTML += `<div class="chat-msg user">${question}</div>`;
        historyBox.scrollTop = historyBox.scrollHeight;
      }
      
      // Clear input and show sending state
      questionEl.value = '';
      submitBtn.disabled = true;
      submitBtn.innerHTML = '<div class="spinner"></div> Sending...';
      
      const responseContainer = document.getElementById('ai-tutor-response-box');
      
      try {
        const res = await App.askTutor(currentCourseId, question, provider, null, activeChatSessionId);
        
        // Update active session
        activeChatSessionId = res.session_id;
        loadChatSessions(); // refresh sidebar list
        
        // Handle Integrity
        const integrityEl = document.getElementById('tutor-integrity-badge');
        if (integrityEl) {
          integrityEl.className = `badge badge-${res.integrity.classification}`;
          integrityEl.textContent = `Safety: ${res.integrity.classification.toUpperCase()}`;
        }
        
        // Handle Search Mode
        const searchModeEl = document.getElementById('tutor-search-mode-badge');
        if (searchModeEl) {
          searchModeEl.textContent = `Mode: ${res.search_mode || 'hybrid'}`;
        }
        
        // Handle Context Used
        const contextEl = document.getElementById('tutor-context-badge');
        if (contextEl) {
          contextEl.textContent = res.context_used ? 'Context: Yes' : 'Context: No';
        }

        let assistantHtml = '';
        if (res.integrity.classification === 'blocked') {
          assistantHtml = `<span style="color: var(--accent-rose);">Blocked request.</span> Reason: ${res.integrity.reason}<br><br><strong>Safe Alternative:</strong> ${res.integrity.safe_alternative}`;
        } else {
          const detail = res.tutor_response;
          assistantHtml = detail.answer;
          
          if (detail.steps && detail.steps.length > 0) {
            assistantHtml += `
              <h5 style="margin-top: 1rem;">Guided Concept Steps:</h5>
              <ol class="step-list">
                ${detail.steps.map(s => `<li>${s}</li>`).join('')}
              </ol>
            `;
          }
          
          if (detail.follow_up_question) {
            assistantHtml += `
              <div style="margin-top: 1rem; border-top: 1px dashed var(--border-color); padding-top: 0.75rem;">
                <strong style="color: var(--accent-cyan);">Concept Check:</strong> ${detail.follow_up_question}
              </div>
            `;
          }
        }
        
        if (historyBox) {
          historyBox.innerHTML += `<div class="chat-msg assistant">${assistantHtml}</div>`;
          historyBox.scrollTop = historyBox.scrollHeight;
        }

        // Show metadata box if needed (for debug panel/chunks listing)
        if (responseContainer) {
          responseContainer.style.display = 'block';
          const debugEl = document.getElementById('tutor-debug');
          if (debugEl && res.tutor_response) {
            debugEl.style.display = 'block';
            debugEl.textContent = `Provider: ${res.tutor_response.provider_used} | Model: ${res.tutor_response.model_used}`;
          }
          
          const chunksSection = document.getElementById('tutor-retrieved-chunks-section');
          const chunksList = document.getElementById('tutor-retrieved-chunks-list');
          if (chunksSection && chunksList && res.retrieved_chunks && res.retrieved_chunks.length > 0) {
            chunksSection.style.display = 'block';
            chunksList.innerHTML = res.retrieved_chunks.map((c, idx) => `
              <div style="background: rgba(0, 0, 0, 0.2); border: 1px solid var(--border-color); border-radius: 6px; padding: 0.75rem; font-size: 0.85rem; margin-top: 0.5rem;">
                <div style="font-size: 0.75rem; color: var(--text-gray);">Chunk #${idx+1} (ID: ${c.chunk_id})</div>
                <div style="color: var(--text-white); font-style: italic; margin-top: 0.25rem;">"${c.content}"</div>
              </div>
            `).join('');
          }
        }
      } catch (err) {
        showAlert('Tutor error: ' + err.message, 'danger');
        if (historyBox) {
          historyBox.innerHTML += `<div class="chat-msg assistant" style="color: var(--accent-rose);">Tutor failed to respond: ${err.message}</div>`;
          historyBox.scrollTop = historyBox.scrollHeight;
        }
      } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Send';
      }
    });
  }

  // 6. Generate Embeddings Button Handler
  const generateEmbeddingsBtn = document.getElementById('generate-embeddings-btn');
  if (generateEmbeddingsBtn) {
    generateEmbeddingsBtn.addEventListener('click', async () => {
      generateEmbeddingsBtn.disabled = true;
      generateEmbeddingsBtn.innerHTML = '<div class="spinner"></div> Processing...';
      try {
        const res = await App.generateEmbeddings(currentCourseId, false);
        const detail = `Total: ${res.chunks_total}, Embedded: ${res.chunks_embedded}, Skipped: ${res.chunks_skipped}`;
        showAlert(`Embedding Generation Complete!\n${detail}`, 'success');
        await updateEmbeddingStatus();
      } catch (err) {
        showAlert('Embedding Generation Error: ' + err.message, 'danger');
      } finally {
        generateEmbeddingsBtn.disabled = false;
        generateEmbeddingsBtn.textContent = 'Generate Embeddings';
      }
    });
  }

  // 4. Generate Exam Prep
  const prepForm = document.getElementById('generate-examprep-form');
  if (prepForm) {
    prepForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const examTitle = document.getElementById('exam-title').value;
      const examDate = document.getElementById('exam-date').value;
      const topicsStr = document.getElementById('exam-topics').value;
      const provider = document.getElementById('provider-select').value;
      const submitBtn = prepForm.querySelector('button[type="submit"]');
      
      submitBtn.disabled = true;
      submitBtn.innerHTML = '<div class="spinner"></div> Generating Plan...';
      
      const responseContainer = document.getElementById('ai-examprep-response-box');
      responseContainer.style.display = 'none';
      
      const topics = topicsStr.split(',').map(t => t.strip ? t.strip() : t.trim()).filter(Boolean);

      try {
        const res = await App.generateExamPrep(currentCourseId, examTitle, examDate, topics, provider, null);
        responseContainer.style.display = 'block';
        
        document.getElementById('prep-title').textContent = res.title;
        
        // Render Warning if any
        const warningAlert = document.getElementById('prep-warning-alert');
        if (res.plan.warning) {
          warningAlert.style.display = 'block';
          warningAlert.textContent = res.plan.warning;
        } else {
          warningAlert.style.display = 'none';
        }

        // Render Priority Topics
        const weakEl = document.getElementById('prep-weaktopics');
        if (res.plan.priority_topics && res.plan.priority_topics.length > 0) {
          weakEl.innerHTML = res.plan.priority_topics.map(pt => `
            <span class="badge badge-caution" style="margin-right: 0.5rem; margin-bottom: 0.5rem; font-size: 0.8rem; display: inline-flex; flex-direction: column; align-items: start; padding: 0.4rem 0.6rem;">
              <strong>${pt.topic}</strong>
              <span style="font-size: 0.7rem; opacity: 0.8;">Mastery: ${Math.round(pt.mastery_score * 100)}% - ${pt.reason}</span>
            </span>
          `).join('');
        } else if (res.plan.weak_topics && res.plan.weak_topics.length > 0) {
          weakEl.innerHTML = res.plan.weak_topics.map(w => `<span class="badge badge-caution" style="margin-right: 0.5rem; margin-bottom: 0.5rem;">${w}</span>`).join('');
        } else {
          weakEl.innerHTML = 'None';
        }

        // Render Schedule
        const planEl = document.getElementById('prep-studyplan');
        if (res.plan.daily_plan && res.plan.daily_plan.length > 0) {
          planEl.innerHTML = res.plan.daily_plan.map(p => `
            <div style="margin-bottom: 1rem; padding: 0.75rem; background: rgba(0,0,0,0.2); border-left: 3px solid var(--accent-purple); border-radius: 4px;">
              <strong>Day ${p.day}</strong>
              <ul style="margin-top: 0.5rem; padding-left: 1rem;">
                ${p.tasks.map(t => `<li>${t}</li>`).join('')}
              </ul>
            </div>
          `).join('');
        } else if (res.plan.study_plan && res.plan.study_plan.length > 0) {
          planEl.innerHTML = res.plan.study_plan.map(p => `
            <div style="margin-bottom: 1rem; padding: 0.75rem; background: rgba(0,0,0,0.2); border-left: 3px solid var(--accent-purple); border-radius: 4px;">
              <strong>${p.phase}</strong> (${p.focus})
              <ul style="margin-top: 0.5rem; padding-left: 1rem;">
                ${p.tasks.map(t => `<li>${t}</li>`).join('')}
              </ul>
            </div>
          `).join('');
        } else {
          planEl.innerHTML = '<p>No tasks returned.</p>';
        }

        // Render Practice Plan
        const practicePlanEl = document.getElementById('prep-practice-plan');
        if (res.plan.practice_plan && res.plan.practice_plan.length > 0) {
          practicePlanEl.innerHTML = `
            <ul style="padding-left: 1rem;">
              ${res.plan.practice_plan.map(p => `<li>${p}</li>`).join('')}
            </ul>
          `;
        } else {
          practicePlanEl.innerHTML = '<p>No practice items generated.</p>';
        }

        // Render Review Strategy
        const reviewStrategyEl = document.getElementById('prep-review-strategy');
        reviewStrategyEl.textContent = res.plan.review_strategy || 'No specific strategy returned.';

      } catch (err) {
        showAlert('Exam Prep error: ' + err.message, 'danger');
      } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Generate Prep Plan';
      }
    });
  }

  // 5. Generate Flashcards
  const flashcardForm = document.getElementById('generate-flashcards-form');
  if (flashcardForm) {
    flashcardForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const topic = document.getElementById('flashcard-topic').value;
      const count = document.getElementById('flashcard-count').value;
      const provider = document.getElementById('provider-select').value;
      const submitBtn = flashcardForm.querySelector('button[type="submit"]');
      
      submitBtn.disabled = true;
      submitBtn.innerHTML = '<div class="spinner"></div> Generating Cards...';

      try {
        await App.generateFlashcards(currentCourseId, topic, count, provider, null);
        flashcardForm.reset();
        showAlert('Flashcards generated successfully!', 'success');
        loadFlashcards();
      } catch (err) {
        showAlert('Flashcard generation error: ' + err.message, 'danger');
      } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Generate Flashcards';
      }
    });
  }

  // 6. Refresh Dashboard Button
  const refreshDashBtn = document.getElementById('refresh-dashboard-btn');
  if (refreshDashBtn) {
    refreshDashBtn.addEventListener('click', async () => {
      refreshDashBtn.disabled = true;
      try {
        await loadLearningDashboard();
        showAlert('Dashboard refreshed.', 'success');
      } catch (err) {
        showAlert('Failed to refresh dashboard: ' + err.message, 'danger');
      } finally {
        refreshDashBtn.disabled = false;
      }
    });
  }

  // 7. Extract Topics Button
  const extractTopicsBtn = document.getElementById('extract-topics-btn');
  if (extractTopicsBtn) {
    extractTopicsBtn.addEventListener('click', async () => {
      extractTopicsBtn.disabled = true;
      extractTopicsBtn.innerHTML = '<div class="spinner"></div> Extracting...';
      const provider = document.getElementById('provider-select').value;
      try {
        const summary = await App.extractTopics(currentCourseId, provider, null);
        const detail = `Created: ${summary.topics_created}, Mapped chunks: ${summary.chunk_maps_created}`;
        
        const summaryBox = document.getElementById('extracted-topics-summary');
        if (summaryBox) {
          summaryBox.style.display = 'block';
          summaryBox.textContent = `Extraction complete! ${detail}`;
        }
        
        await loadTopics();
        await loadLearningDashboard();
        showAlert('Topics extracted successfully!', 'success');
      } catch (err) {
        showAlert('Extraction failed: ' + err.message, 'danger');
      } finally {
        extractTopicsBtn.disabled = false;
        extractTopicsBtn.textContent = 'Extract Topics (AI)';
      }
    });
  }

  // 8. Map Chunks Button
  const mapChunksBtn = document.getElementById('map-chunks-btn');
  if (mapChunksBtn) {
    mapChunksBtn.addEventListener('click', async () => {
      mapChunksBtn.disabled = true;
      try {
        const res = await App.mapChunks(currentCourseId);
        showAlert(`Successfully updated mappings! Mapped ${res.chunk_maps_created} chunks.`, 'success');
        await loadLearningDashboard();
      } catch (err) {
        showAlert('Failed to map chunks: ' + err.message, 'danger');
      } finally {
        mapChunksBtn.disabled = false;
      }
    });
  }

  // 9. Add Topic Form
  const addTopicForm = document.getElementById('add-topic-form');
  if (addTopicForm) {
    addTopicForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const name = document.getElementById('manual-topic-name').value;
      const desc = document.getElementById('manual-topic-desc').value;
      try {
        await App.createTopic(currentCourseId, name, desc);
        addTopicForm.reset();
        showAlert('Topic created manually!', 'success');
        await loadTopics();
        await loadLearningDashboard();
      } catch (err) {
        showAlert('Failed to create topic: ' + err.message, 'danger');
      }
    });
  }

  // 10. Generate Practice Form
  const generatePracticeForm = document.getElementById('generate-practice-form');
  if (generatePracticeForm) {
    generatePracticeForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const topicId = document.getElementById('practice-topic-select').value;
      const difficulty = document.getElementById('practice-difficulty').value;
      const count = document.getElementById('practice-count').value;
      const provider = document.getElementById('provider-select').value;
      const submitBtn = generatePracticeForm.querySelector('button[type="submit"]');

      submitBtn.disabled = true;
      submitBtn.innerHTML = '<div class="spinner"></div> Generating Questions...';
      
      const quizArea = document.getElementById('practice-quiz-area');
      const questionsList = document.getElementById('quiz-questions-list');
      if (quizArea) quizArea.style.display = 'none';
      if (questionsList) questionsList.innerHTML = '';

      try {
        const questions = await App.generatePractice(currentCourseId, topicId, count, difficulty, provider, null);
        if (quizArea) quizArea.style.display = 'block';
        
        if (questionsList) {
          questionsList.innerHTML = questions.map((q, idx) => `
            <div class="quiz-question-card" style="background: rgba(255,255,255,0.03); border: 1px solid var(--border-color); padding: 1.25rem; border-radius: 8px; margin-bottom: 1.5rem;" id="quiz-card-${q.id}">
              <div style="font-weight: bold; font-size: 1rem; margin-bottom: 0.5rem; color: var(--text-white);">Q${idx+1}: ${q.question_text}</div>
              <div style="display: flex; gap: 0.5rem; margin-bottom: 1rem; font-size: 0.75rem;">
                <span class="badge badge-secondary">${q.difficulty.toUpperCase()}</span>
              </div>
              
              <form onsubmit="submitQuizAnswer(event, ${q.id})">
                <div class="form-group">
                  <textarea class="form-control" id="quiz-answer-${q.id}" placeholder="Type your answer here..." rows="3" required style="width: 100%; border-radius: 6px; padding: 0.5rem; background: var(--bg-card); color: var(--text-white); border: 1px solid var(--border-color);"></textarea>
                </div>
                <button type="submit" class="btn btn-secondary" style="font-size: 0.85rem; padding: 0.4rem 0.8rem; margin-top: 0.5rem;">Grade Answer</button>
              </form>
              
              <div id="quiz-feedback-${q.id}" style="display: none; margin-top: 1rem; padding: 0.75rem; border-radius: 6px; font-size: 0.9rem; line-height: 1.5;"></div>
            </div>
          `).join('');
        }
      } catch (err) {
        showAlert('Practice generation failed: ' + err.message, 'danger');
      } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Generate Quiz Questions';
      }
    });
  }

  // 11. Generate Study Tasks Button
  const generateStudyTasksBtn = document.getElementById('generate-study-tasks-btn');
  if (generateStudyTasksBtn) {
    generateStudyTasksBtn.addEventListener('click', async () => {
      generateStudyTasksBtn.disabled = true;
      generateStudyTasksBtn.innerHTML = '<div class="spinner"></div> Generating...';
      try {
        await App.generateStudyTasks(currentCourseId, 7);
        showAlert('Successfully generated weekly study tasks based on weaknesses!', 'success');
        await loadStudyTasks();
        await loadLearningDashboard();
      } catch (err) {
        showAlert('Failed to generate study tasks: ' + err.message, 'danger');
      } finally {
        generateStudyTasksBtn.disabled = false;
        generateStudyTasksBtn.textContent = 'Generate 7-Day Plan';
      }
    });
  }
}

function setupBlackboardScaffold() {
  const statusBtn = document.getElementById('bb-status-btn');
  const connBtn = document.getElementById('bb-connect-btn');
  const syncBtn = document.getElementById('bb-sync-btn');
  const outputEl = document.getElementById('blackboard-scaffold-output');

  if (statusBtn) {
    statusBtn.addEventListener('click', async () => {
      outputEl.style.display = 'block';
      outputEl.innerHTML = 'Fetching status...';
      try {
        const res = await App.getBlackboardStatus();
        outputEl.innerHTML = `
          <strong>Provider:</strong> ${res.provider}<br>
          <strong>Status:</strong> ${res.status}<br>
          <strong>Implemented:</strong> ${res.implemented}<br><br>
          <strong>Required Steps for Blackboard API integration:</strong>
          <ul style="padding-left: 1rem; margin-top: 0.5rem;">
            ${res.next_steps.map(s => `<li>${s}</li>`).join('')}
          </ul>
        `;
      } catch (err) {
        outputEl.innerHTML = 'Error: ' + err.message;
      }
    });
  }

  if (connBtn) {
    connBtn.addEventListener('click', async () => {
      outputEl.style.display = 'block';
      outputEl.innerHTML = 'Attempting connection...';
      try {
        const res = await App.connectBlackboardPlaceholder();
        outputEl.innerHTML = `
          <strong>Status:</strong> ${res.status}<br><br>
          <strong>Details:</strong> ${res.message}<br><br>
          <strong>Next actions:</strong>
          <ul style="padding-left: 1rem; margin-top: 0.5rem;">
            ${res.next_actions.map(a => `<li>${a}</li>`).join('')}
          </ul>
        `;
      } catch (err) {
        outputEl.innerHTML = 'Error: ' + err.message;
      }
    });
  }

  if (syncBtn) {
    syncBtn.addEventListener('click', async () => {
      outputEl.style.display = 'block';
      outputEl.innerHTML = 'Syncing...';
      try {
        const res = await App.syncBlackboardPlaceholder();
        outputEl.innerHTML = `
          <strong>Status:</strong> ${res.status}<br>
          <strong>Detail:</strong> ${res.message}<br>
          <strong>Synced Courses:</strong> ${res.synced_courses_count}<br>
          <strong>Synced Assignments:</strong> ${res.synced_assignments_count}<br><br>
          <strong>Sample Synced Class:</strong> "${res.detail.courses[0].name}" (${res.detail.courses[0].code})
        `;
        // Refresh assignments list
        loadAssignments();
      } catch (err) {
        outputEl.innerHTML = 'Error: ' + err.message;
      }
    });
  }
}

async function initLMSPage() {
  const token = App.getToken();
  if (!token) {
    window.location.href = 'dashboard.html';
    return;
  }
  
  await loadProviders();
  await loadConnections();
  const params = new URLSearchParams(window.location.search);
  if (params.get('oauth') === 'success' && params.get('connection_id')) {
    showAlert('Blackboard connected. Verifying the saved authorization…', 'success', 'lms-alert-container');
    await probeLMSConnection(Number(params.get('connection_id')));
  } else if (params.get('oauth') === 'error') {
    showAlert(`Blackboard authorization failed: ${params.get('reason') || 'unknown error'}.`, 'danger', 'lms-alert-container');
  }
  if (params.has('oauth')) window.history.replaceState({}, '', '/lms');
}

async function loadProviders() {
  const container = document.getElementById('providers-list');
  if (!container) return;
  
  container.innerHTML = '<div class="spinner"></div> Loading providers...';
  
  try {
    const res = await App.getLMSProviders();
    container.innerHTML = res.providers.map(p => {
      const configClass = p.configured ? 'badge-allowed' : 'badge-caution';
      const configText = p.configured ? 'Configured' : 'Missing Env Configurations';
      const statusClass = p.enabled ? 'badge-allowed' : 'badge-caution';
      const statusText = p.enabled ? 'Enabled' : 'Disabled';
      
      let actionHtml = '';
      if (p.configured && p.enabled) {
        actionHtml = `
          <form onsubmit="handleLMSConnect(event, '${p.name}')" style="margin-top: 1rem; display: flex; gap: 0.5rem; flex-wrap: wrap;">
            <input type="text" id="domain-${p.name}" class="form-control" placeholder="e.g. blackboard.university.edu" required style="flex: 1; min-width: 200px; font-size: 0.85rem; padding: 0.4rem 0.75rem;">
            <button type="submit" class="btn btn-primary" style="font-size: 0.85rem; padding: 0.4rem 1rem;">Connect ${p.name.toUpperCase()}</button>
          </form>
        `;
      } else {
        actionHtml = `
          <div style="margin-top: 1rem; background: rgba(234, 179, 8, 0.08); border: 1px solid rgba(234, 179, 8, 0.2); border-radius: 6px; padding: 0.75rem; font-size: 0.8rem; color: var(--text-gray);">
            <strong>Setup Instructions:</strong>
            <ul style="margin-top: 0.25rem; padding-left: 1.25rem; display: flex; flex-direction: column; gap: 0.25rem; list-style-type: disc;">
              <li>Enable in environment: set <code>${p.name.toUpperCase()}_ENABLED=true</code></li>
              <li>Provide the Developer Portal OAuth Key/client ID and OAuth Secret</li>
              <li>For Blackboard, ensure your App ID is approved in the university system</li>
            </ul>
          </div>
        `;
      }

      return `
        <div class="card" style="padding: 1.5rem; margin-bottom: 1rem;">
          <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 0.5rem;">
            <h3 style="margin: 0; font-size: 1.2rem;">${p.name.charAt(0).toUpperCase() + p.name.slice(1)} Integration</h3>
            <div style="display: flex; gap: 0.4rem;">
              <span class="badge ${statusClass}">${statusText}</span>
              <span class="badge ${configClass}">${configText}</span>
            </div>
          </div>
          <p style="color: var(--text-gray); font-size: 0.85rem; margin-top: 0.5rem;">
            Sync and map your LMS courses directly into NaySchool to access AI concept tutoring, homework prep, and flashcard generators automatically.
          </p>
          ${actionHtml}
        </div>
      `;
    }).join('');
  } catch (err) {
    showAlert('Error loading providers: ' + err.message, 'danger', 'lms-alert-container');
  }
}

async function loadConnections() {
  const container = document.getElementById('connections-list');
  if (!container) return;
  
  container.innerHTML = '<p style="color: var(--text-dark);">Loading active integrations...</p>';
  
  try {
    const conns = await App.getLMSConnections();
    if (conns.length === 0) {
      container.innerHTML = '<p style="color: var(--text-dark);">No LMS accounts connected yet. Link an enabled LMS above.</p>';
      return;
    }
    
    container.innerHTML = conns.map(c => {
      const date = c.last_synced_at ? new Date(c.last_synced_at).toLocaleString() : 'Never';
      const statusClass = c.status === 'connected' ? 'badge-allowed' : 'badge-caution';
      
      return `
        <div class="card" style="padding: 1.5rem; margin-bottom: 1rem; border-left: 3px solid ${c.status === 'connected' ? 'var(--accent-emerald)' : 'var(--accent-yellow)'}">
          <div style="display: flex; justify-content: space-between; align-items: start; flex-wrap: wrap; gap: 0.5rem;">
            <div>
              <h3 style="margin: 0; font-size: 1.15rem; color: var(--text-white);">${c.provider.toUpperCase()} Connection</h3>
              <div style="font-size: 0.85rem; color: var(--text-gray); margin-top: 0.25rem;">
                <strong>Domain:</strong> ${c.school_domain || 'Not Specified'} | 
                <strong>User ID:</strong> ${c.external_user_id || 'Not Mapped'}
              </div>
            </div>
            <span class="badge ${statusClass}">${c.status}</span>
          </div>
          
          <div style="font-size: 0.8rem; color: var(--text-dark); margin-top: 0.75rem;">
            Last Synchronized: <strong>${date}</strong>
          </div>
          
          <div style="margin-top: 1rem; display: flex; gap: 0.75rem; flex-wrap: wrap;">
            <button onclick="triggerLMSSync(${c.id})" class="btn btn-primary" style="font-size: 0.8rem; padding: 0.4rem 0.8rem; cursor: pointer;">Sync Content</button>
            <button onclick="probeLMSConnection(${c.id})" class="btn btn-secondary" style="font-size: 0.8rem; padding: 0.4rem 0.8rem; cursor: pointer;">Verify Connection</button>
            <button onclick="viewSyncLogs(${c.id})" class="btn btn-secondary" style="font-size: 0.8rem; padding: 0.4rem 0.8rem; cursor: pointer;">Sync Logs</button>
          </div>
        </div>
      `;
    }).join('');
  } catch (err) {
    showAlert('Error loading connections: ' + err.message, 'danger', 'lms-alert-container');
  }
}

window.handleLMSConnect = async function(event, provider) {
  event.preventDefault();
  const domainInput = document.getElementById(`domain-${provider}`);
  if (!domainInput) return;
  
  const domain = domainInput.value.trim();
  try {
    showAlert('Initiating integration connection...', 'info', 'lms-alert-container');
    const res = await App.connectLMSProvider(provider, domain);
    
    if (res.status === 'not_configured') {
      let msg = res.message + '\n\nRequired actions:\n';
      res.next_steps.forEach(s => { msg += `- ${s}\n`; });
      alert(msg);
    } else if (res.status === 'configured' && res.authorization_url) {
      window.location.href = res.authorization_url;
    }
  } catch (err) {
    showAlert('Failed to link LMS: ' + err.message, 'danger', 'lms-alert-container');
  }
};

window.probeLMSConnection = async function(connectionId) {
  const container = document.getElementById('probe-status-box');
  if (container) {
    container.style.display = 'block';
    container.textContent = 'Verifying the encrypted Blackboard authorization…';
  }
  try {
    const result = await App.probeLMSConnection(connectionId);
    if (container) {
      container.innerHTML = `<strong>Blackboard connected</strong><br>Site: ${result.blackboard_site}<br>Authenticated user: ${result.authenticated_user_id}<br>API reachable: ${result.api_reachable ? 'Yes' : 'No'}<br>Token expires: ${result.token_expires_at ? new Date(result.token_expires_at).toLocaleString() : 'Not supplied'}`;
    }
  } catch (err) {
    if (container) container.textContent = `Connection verification failed: ${err.message}`;
    showAlert(`Blackboard verification failed: ${err.message}`, 'danger', 'lms-alert-container');
  }
};

window.triggerLMSSync = async function(connectionId) {
  const container = document.getElementById('sync-status-box');
  if (container) {
    container.style.display = 'block';
    container.innerHTML = '<div class="spinner"></div> Synchronizing LMS data (mapping courses & assignments)...';
  }
  
  try {
    const res = await App.syncLMSConnection(connectionId, {
      sync_courses: true,
      sync_assignments: true,
      sync_content: false,
      sync_announcements: true,
      sync_grades: false
    });
    
    if (res.status === 'not_configured') {
      showAlert('Sync Failed: Blackboard credentials are not configured.', 'danger', 'lms-alert-container');
      if (container) {
        container.innerHTML = `
          <div style="color: var(--accent-rose);"><strong>Status: Configuration Missing</strong></div>
          <div style="margin-top: 0.25rem; font-size: 0.9rem;">${res.message}</div>
          <ul style="margin-top: 0.5rem; padding-left: 1.25rem; list-style-type: disc; font-size: 0.85rem; color: var(--text-gray);">
            ${res.next_steps.map(s => `<li>${s}</li>`).join('')}
          </ul>
        `;
      }
    } else {
      showAlert('LMS synchronized successfully!', 'success', 'lms-alert-container');
      if (container) {
        container.innerHTML = `
          <div style="color: var(--accent-emerald);"><strong>Status: Successful</strong></div>
          <div>Synced courses count: <strong>${res.synced_courses_count}</strong></div>
          <div>Synced assignments count: <strong>${res.synced_assignments_count}</strong></div>
          <div style="margin-top: 0.5rem; font-size: 0.8rem; color: var(--text-gray);">${res.message}</div>
        `;
      }
      loadConnections();
    }
  } catch (err) {
    showAlert('Sync failed: ' + err.message, 'danger', 'lms-alert-container');
    if (container) {
      container.innerHTML = `<div style="color: var(--accent-rose);"><strong>Sync Error:</strong> ${err.message}</div>`;
    }
  }
};

window.viewSyncLogs = async function(connectionId) {
  const box = document.getElementById('sync-logs-box');
  const list = document.getElementById('sync-logs-list');
  if (!box || !list) return;
  
  box.style.display = 'block';
  list.innerHTML = '<p style="color: var(--text-dark);">Fetching sync execution history logs...</p>';
  
  try {
    const logs = await App.getLMSSyncLogs(connectionId);
    if (logs.length === 0) {
      list.innerHTML = '<p style="color: var(--text-dark); padding: 0.5rem;">No logs found for this connection.</p>';
      return;
    }
    
    list.innerHTML = logs.map(l => {
      const started = new Date(l.started_at).toLocaleString();
      const duration = l.finished_at ? Math.round((new Date(l.finished_at) - new Date(l.started_at)) / 100) / 10 + 's' : 'N/A';
      const statusClass = l.status === 'success' ? 'badge-allowed' : 'badge-caution';
      
      return `
        <div style="background: rgba(0, 0, 0, 0.2); border: 1px solid var(--border-color); border-radius: 6px; padding: 0.75rem; display: flex; flex-direction: column; gap: 0.25rem; margin-bottom: 0.5rem;">
          <div style="display: flex; justify-content: space-between; align-items: center; font-size: 0.8rem;">
            <span style="color: var(--text-gray); font-family: monospace;">Sync Log ID: #${l.id}</span>
            <span class="badge ${statusClass}">${l.status}</span>
          </div>
          <div style="font-size: 0.85rem; color: var(--text-white);">
            <strong>Started:</strong> ${started} | <strong>Duration:</strong> ${duration}
          </div>
          ${l.message ? `<div style="font-size: 0.8rem; color: var(--accent-rose); margin-top: 0.25rem;">${l.message}</div>` : ''}
          ${l.raw_summary_json ? `<div style="font-size: 0.75rem; color: var(--text-dark); font-family: monospace; background: rgba(0,0,0,0.1); padding: 0.25rem; border-radius: 4px; margin-top: 0.25rem;">Summary: ${l.raw_summary_json}</div>` : ''}
        </div>
      `;
    }).join('');
  } catch (err) {
    showAlert('Failed to fetch logs: ' + err.message, 'danger', 'lms-alert-container');
    list.innerHTML = `<p style="color: var(--accent-rose);">Error: ${err.message}</p>`;
  }
};

async function loadLearningDashboard() {
  try {
    const dash = await App.getLearningDashboard(currentCourseId);
    
    document.getElementById('dashboard-avg-mastery').textContent = `${Math.round(dash.average_mastery * 100)}%`;
    document.getElementById('dashboard-topics-count').textContent = dash.topics_count;
    document.getElementById('dashboard-attempts-count').textContent = `${dash.attempts_count} (${dash.practice_questions_count} Qs)`;
    
    const weakList = document.getElementById('dashboard-weak-topics');
    if (dash.weak_topics && dash.weak_topics.length > 0) {
      weakList.innerHTML = dash.weak_topics.map(t => `
        <li style="display: flex; justify-content: space-between; align-items: center; background: rgba(239, 68, 68, 0.05); border: 1px solid rgba(239, 68, 68, 0.1); padding: 0.4rem 0.75rem; border-radius: 6px;">
          <span>${t.name}</span>
          <span class="badge badge-caution">${Math.round(t.mastery_score * 100)}% Mastery</span>
        </li>
      `).join('');
    } else {
      weakList.innerHTML = '<li style="color: var(--text-gray);">No weak topics detected.</li>';
    }

    const strongList = document.getElementById('dashboard-strong-topics');
    if (dash.strong_topics && dash.strong_topics.length > 0) {
      strongList.innerHTML = dash.strong_topics.map(t => `
        <li style="display: flex; justify-content: space-between; align-items: center; background: rgba(16, 185, 129, 0.05); border: 1px solid rgba(16, 185, 129, 0.1); padding: 0.4rem 0.75rem; border-radius: 6px;">
          <span>${t.name}</span>
          <span class="badge badge-success">${Math.round(t.mastery_score * 100)}% Mastery</span>
        </li>
      `).join('');
    } else {
      strongList.innerHTML = '<li style="color: var(--text-gray);">No strong topics detected.</li>';
    }
  } catch (e) {
    console.error('Failed to load learning dashboard:', e);
  }
}

async function loadTopics() {
  try {
    const topics = await App.getTopics(currentCourseId);
    
    const container = document.getElementById('topics-list-container');
    if (topics.length === 0) {
      container.innerHTML = `<span style="color: var(--text-gray); font-size: 0.9rem;">No topics extracted yet. Click 'Extract Topics (AI)' to start.</span>`;
    } else {
      container.innerHTML = topics.map(t => `
        <div style="background: rgba(255,255,255,0.03); border: 1px solid var(--border-color); padding: 0.75rem; border-radius: 6px; display: flex; justify-content: space-between; align-items: start; margin-bottom: 0.5rem;">
          <div style="flex: 1; padding-right: 0.5rem;">
            <strong style="color: var(--text-white);">${t.name}</strong>
            <div style="font-size: 0.8rem; color: var(--text-gray); margin-top: 0.25rem;">${t.description || 'No description.'}</div>
            <div style="font-size: 0.75rem; color: var(--accent-cyan); margin-top: 0.25rem;"><em>Source:</em> ${t.source}</div>
          </div>
          <span class="badge badge-info">${t.confidence ? (t.confidence * 100).toFixed(0) : 100}% Conf</span>
        </div>
      `).join('');
    }

    const select = document.getElementById('practice-topic-select');
    if (select) {
      const prevVal = select.value;
      select.innerHTML = '<option value="">-- Choose a Topic --</option>' + topics.map(t => `
        <option value="${t.id}">${t.name}</option>
      `).join('');
      if (prevVal) select.value = prevVal;
    }
  } catch (e) {
    console.error('Failed to load topics:', e);
  }
}

async function loadStudyTasks() {
  try {
    const tasks = await App.getStudyTasks(currentCourseId);
    const container = document.getElementById('study-tasks-list-container');
    
    if (tasks.length === 0) {
      container.innerHTML = `<span style="color: var(--text-gray); font-size: 0.9rem;">No tasks generated yet. Click 'Generate 7-Day Plan' to create tasks targeted to your weaknesses.</span>`;
      return;
    }
    
    container.innerHTML = tasks.map(t => {
      const isCompleted = t.status === 'completed';
      const dateStr = t.due_at ? new Date(t.due_at).toLocaleDateString() : 'N/A';
      const checkedAttr = isCompleted ? 'checked' : '';
      const lineThrough = isCompleted ? 'text-decoration: line-through; color: var(--text-gray);' : 'color: var(--text-white);';
      
      let badgeClass = 'badge-info';
      if (t.priority === 'urgent') badgeClass = 'badge-danger';
      else if (t.priority === 'high') badgeClass = 'badge-caution';
      else if (t.priority === 'low') badgeClass = 'badge-secondary';

      return `
        <div style="background: rgba(255,255,255,0.03); border: 1px solid var(--border-color); padding: 0.75rem 1rem; border-radius: 6px; display: flex; align-items: start; gap: 0.75rem; margin-bottom: 0.5rem;">
          <input type="checkbox" ${checkedAttr} onchange="toggleStudyTaskStatus(${t.id}, this.checked)" style="margin-top: 0.3rem; cursor: pointer;">
          <div style="flex: 1;">
            <div style="font-weight: bold; ${lineThrough}">${t.title}</div>
            <div style="font-size: 0.8rem; color: var(--text-gray); margin-top: 0.25rem;">${t.description || ''}</div>
            <div style="display: flex; gap: 0.5rem; margin-top: 0.4rem; font-size: 0.75rem; flex-wrap: wrap;">
              <span class="badge ${badgeClass}">${t.priority.toUpperCase()}</span>
              <span style="color: var(--text-dark);">Due: ${dateStr}</span>
            </div>
          </div>
        </div>
      `;
    }).join('');
  } catch (e) {
    console.error('Failed to load study tasks:', e);
  }
}

window.toggleStudyTaskStatus = async function(taskId, isChecked) {
  try {
    const status = isChecked ? 'completed' : 'pending';
    await App.updateStudyTaskStatus(taskId, status);
    showAlert('Study task updated!', 'success');
    await loadStudyTasks();
    await loadLearningDashboard();
  } catch (err) {
    showAlert('Failed to update task: ' + err.message, 'danger');
  }
};

window.submitQuizAnswer = async function(event, questionId) {
  event.preventDefault();
  const answerText = document.getElementById(`quiz-answer-${questionId}`).value;
  const provider = document.getElementById('provider-select').value;
  const form = event.target;
  const btn = form.querySelector('button[type="submit"]');
  
  btn.disabled = true;
  btn.innerHTML = '<div class="spinner"></div> Grading...';
  
  const feedbackBox = document.getElementById(`quiz-feedback-${questionId}`);
  feedbackBox.style.display = 'none';

  try {
    const attempt = await App.gradePracticeAttempt(currentCourseId, questionId, answerText, provider, null);
    feedbackBox.style.display = 'block';
    
    const isCorrect = attempt.is_correct;
    const score = Math.round(attempt.score * 100);
    const bg = isCorrect ? 'rgba(16, 185, 129, 0.1)' : 'rgba(239, 68, 68, 0.1)';
    const border = isCorrect ? 'var(--accent-emerald)' : 'var(--accent-rose)';
    const color = isCorrect ? 'var(--accent-emerald)' : 'var(--accent-rose)';
    
    feedbackBox.style.background = bg;
    feedbackBox.style.border = `1px solid ${border}`;
    feedbackBox.style.color = 'var(--text-white)';
    feedbackBox.innerHTML = `
      <div style="font-weight: bold; color: ${color}; margin-bottom: 0.25rem;">Score: ${score}% (${isCorrect ? 'Pass' : 'Requires Review'})</div>
      <div><strong>Feedback:</strong> ${attempt.feedback}</div>
    `;
    
    form.querySelector('textarea').disabled = true;
    btn.style.display = 'none';
    
    await loadLearningDashboard();
  } catch (err) {
    showAlert('Grading failed: ' + err.message, 'danger');
    btn.disabled = false;
    btn.textContent = 'Grade Answer';
  }
};

// Phase 6A helper functions
function setupWorkspaceTabs() {
  const tabButtons = document.querySelectorAll('.tab-btn');
  tabButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      const tabName = btn.dataset.tab;
      switchTab(tabName);
    });
  });
}

function switchTab(tabName) {
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  const activeBtn = document.querySelector(`.tab-btn[data-tab="${tabName}"]`);
  if (activeBtn) activeBtn.classList.add('active');

  document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
  const activeContent = document.getElementById(`tab-${tabName}`);
  if (activeContent) activeContent.classList.add('active');
}

function handleUrlQueryParams() {
  const params = new URLSearchParams(window.location.search);
  const tab = params.get('tab');
  const sessionId = params.get('session_id');
  
  if (tab) {
    switchTab(tab);
    if (tab === 'tutor' && sessionId) {
      loadChatSessionHistory(parseInt(sessionId));
    }
  }
}

function setupQuickAskForm() {
  const form = document.getElementById('quick-ask-form');
  if (!form) return;
  form.addEventListener('submit', (e) => {
    e.preventDefault();
    const q = document.getElementById('quick-ask-question').value;
    if (!q.trim()) return;
    
    switchTab('tutor');
    
    const tutorInput = document.getElementById('tutor-question');
    if (tutorInput) {
      tutorInput.value = q;
      const askForm = document.getElementById('ask-tutor-form');
      if (askForm) {
        activeChatSessionId = null;
        document.getElementById('active-chat-title').textContent = "New Tutor Chat";
        const historyBox = document.getElementById('chat-message-history');
        if (historyBox) {
          historyBox.innerHTML = `<div class="chat-msg assistant">Let's answer your question...</div>`;
        }
        const submitEvent = new Event('submit', { cancelable: true });
        askForm.dispatchEvent(submitEvent);
      }
    }
    form.reset();
  });
}

function setupCompileRemindersButton() {
  const btn = document.getElementById('btn-generate-reminders');
  if (!btn) return;
  btn.addEventListener('click', async () => {
    btn.disabled = true;
    btn.textContent = "Compiling...";
    try {
      const res = await App.request(`/courses/${currentCourseId}/notifications/generate-study-reminders`, {
        method: 'POST'
      });
      showAlert(`Compiled ${res.length} alerts and reminders!`, 'success');
      setupNavbar();
    } catch (e) {
      showAlert('Failed to compile reminders: ' + e.message, 'danger');
    } finally {
      btn.disabled = false;
      btn.textContent = "Compile Alerts";
    }
  });
}

async function loadChatSessions() {
  const list = document.getElementById('chat-sessions-list');
  if (!list) return;
  try {
    const sessions = await App.request(`/courses/${currentCourseId}/chat-sessions`);
    if (sessions.length === 0) {
      list.innerHTML = '<div style="font-size: 0.8rem; color: var(--text-dark); padding: 0.5rem;">No saved chats.</div>';
      return;
    }
    
    list.innerHTML = sessions.map(s => {
      const activeClass = activeChatSessionId === s.id ? 'active' : '';
      return `
        <div class="chat-session-btn ${activeClass}" id="session-btn-${s.id}" onclick="selectChatSession(${s.id})">
          <span style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap; flex: 1;">${s.title}</span>
          <button class="chat-session-delete" onclick="handleDeleteChatSession(event, ${s.id})">×</button>
        </div>
      `;
    }).join('');
  } catch (e) {
    console.error("Failed to load chat sessions:", e);
  }
}

window.selectChatSession = function(sessionId) {
  loadChatSessionHistory(sessionId);
};

window.handleDeleteChatSession = async function(event, sessionId) {
  event.stopPropagation();
  if (!confirm("Are you sure you want to delete this chat session?")) return;
  
  try {
    await App.request(`/courses/${currentCourseId}/chat-sessions/${sessionId}`, {
      method: 'DELETE'
    });
    showAlert("Chat session deleted successfully.", "success");
    if (activeChatSessionId === sessionId) {
      activeChatSessionId = null;
      document.getElementById('active-chat-title').textContent = "Tutor Chat";
      document.getElementById('chat-message-history').innerHTML = `
        <div class="chat-msg assistant">
          Hello! I am your NaySchool Course Tutor. Ask me any question about the uploaded materials, assignments, or study plans. I'll guide you step-by-step!
        </div>
      `;
    }
    loadChatSessions();
  } catch (e) {
    showAlert("Failed to delete chat: " + e.message, "danger");
  }
};

async function loadChatSessionHistory(sessionId) {
  activeChatSessionId = sessionId;
  
  document.querySelectorAll('.chat-session-btn').forEach(btn => btn.classList.remove('active'));
  const btn = document.getElementById(`session-btn-${sessionId}`);
  if (btn) btn.classList.add('active');

  const historyBox = document.getElementById('chat-message-history');
  if (!historyBox) return;
  
  historyBox.innerHTML = '<div style="font-size: 0.85rem; color: var(--text-gray); padding: 0.5rem;">Loading chat messages...</div>';
  
  try {
    const detail = await App.request(`/courses/${currentCourseId}/chat-sessions/${sessionId}`);
    document.getElementById('active-chat-title').textContent = detail.title;
    
    if (detail.messages.length === 0) {
      historyBox.innerHTML = '<div style="font-size: 0.85rem; color: var(--text-gray); padding: 0.5rem;">No messages in this chat. Ask a question below to start!</div>';
    } else {
      historyBox.innerHTML = detail.messages.map(m => {
        const roleClass = m.role === 'user' ? 'user' : 'assistant';
        return `<div class="chat-msg ${roleClass}">${m.content}</div>`;
      }).join('');
      historyBox.scrollTop = historyBox.scrollHeight;
    }
  } catch (e) {
    historyBox.innerHTML = `<div style="font-size: 0.85rem; color: var(--accent-rose); padding: 0.5rem;">Error loading history: ${e.message}</div>`;
  }
}

// Sidebar new chat trigger
const btnNewChat = document.getElementById('btn-new-chat');
if (btnNewChat) {
  btnNewChat.addEventListener('click', () => {
    activeChatSessionId = null;
    document.getElementById('active-chat-title').textContent = "New Tutor Chat";
    document.querySelectorAll('.chat-session-btn').forEach(btn => btn.classList.remove('active'));
    const historyBox = document.getElementById('chat-message-history');
    if (historyBox) {
      historyBox.innerHTML = `
        <div class="chat-msg assistant">
          Hello! I am your NaySchool Course Tutor. Ask me any question about the uploaded materials, assignments, or study plans. I'll guide you step-by-step!
        </div>
      `;
    }
  });
}
