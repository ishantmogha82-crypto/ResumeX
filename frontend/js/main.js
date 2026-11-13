/**
 * ResumeX — Shared Frontend Utilities (main.js)
 */

const API_BASE = '/api';

/**
 * Display a minimalist monochrome toast notification
 * @param {string} message 
 * @param {'success'|'error'|'info'} type 
 */
function showToast(message, type = 'info') {
  let container = document.getElementById('toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    document.body.appendChild(container);
  }

  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  
  const icon = type === 'error' ? '✕' : (type === 'success' ? '✓' : 'ℹ');
  toast.innerHTML = `<span style="font-weight:700;">${icon}</span><span>${escapeHtml(message)}</span>`;
  
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(10px)';
    toast.style.transition = 'all 0.25s ease';
    setTimeout(() => toast.remove(), 250);
  }, 4000);
}

/**
 * Escape raw HTML to prevent XSS
 */
function escapeHtml(str) {
  if (!str) return '';
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

/**
 * Format ISO date string to readable format (e.g., Nov 13, 2026)
 */
function formatDate(isoStr) {
  if (!isoStr) return '—';
  try {
    const d = new Date(isoStr);
    return d.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  } catch (e) {
    return isoStr;
  }
}

/**
 * Format bytes to readable size
 */
function formatBytes(bytes, decimals = 1) {
  if (!+bytes) return '0 B';
  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(dm))} ${sizes[i]}`;
}

/**
 * Verify current user authentication status
 * @returns {Promise<object|null>} user object or null
 */
async function checkAuth() {
  try {
    const res = await fetch(`${API_BASE}/auth/me`, {
      method: 'GET',
      credentials: 'include'
    });
    if (res.ok) {
      const data = await res.json();
      return data.user || null;
    }
    return null;
  } catch (err) {
    console.error('Auth verification error:', err);
    return null;
  }
}

/**
 * Handle user logout
 */
async function handleLogout() {
  try {
    await fetch(`${API_BASE}/auth/logout`, {
      method: 'POST',
      credentials: 'include'
    });
  } catch (err) {
    console.warn('Logout network error:', err);
  } finally {
    window.location.href = '/login.html';
  }
}

// ─────────────────────────────────────────────────────────────
// Page Initialization
// ─────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
  // Mobile Nav Toggle
  const toggleBtn = document.getElementById('nav-toggle');
  const navMenu = document.getElementById('nav-menu');
  if (toggleBtn && navMenu) {
    toggleBtn.addEventListener('click', () => {
      navMenu.classList.toggle('open');
    });
  }

  // Bind Logout Button if present in sidebar
  const logoutBtn = document.getElementById('btn-logout');
  if (logoutBtn) {
    logoutBtn.addEventListener('click', (e) => {
      e.preventDefault();
      handleLogout();
    });
  }

  // Update dynamic user info in sidebar if present
  const userAvatar = document.getElementById('user-avatar');
  const userName = document.getElementById('user-name');
  const userEmail = document.getElementById('user-email');
  const welcomeHeading = document.getElementById('welcome-heading');

  const protectedPages = ['/dashboard.html', '/analyze.html', '/results.html', '/history.html'];
  const currentPath = window.location.pathname;

  if (protectedPages.some(p => currentPath.endsWith(p))) {
    const user = await checkAuth();
    if (!user) {
      // User is not signed in, redirect to login
      window.location.href = `/login.html?redirect=${encodeURIComponent(window.location.pathname + window.location.search)}`;
      return;
    }

    if (userAvatar) userAvatar.textContent = user.name ? user.name[0].toUpperCase() : 'U';
    if (userName) userName.textContent = user.name || 'User';
    if (userEmail) userEmail.textContent = user.email || '';
    if (welcomeHeading) welcomeHeading.textContent = `Welcome, ${user.name.split(' ')[0]}`;
  } else if (currentPath === '/' || currentPath.endsWith('/index.html')) {
    // If on landing page, check if user is already logged in to customize nav actions
    const user = await checkAuth();
    const navAuthActions = document.getElementById('nav-auth-actions');
    if (user && navAuthActions) {
      navAuthActions.innerHTML = `
        <a href="/dashboard.html" class="btn btn-secondary btn-sm">Dashboard</a>
        <a href="/analyze.html" class="btn btn-primary btn-sm">Analyze Resume</a>
      `;
    }
  }
});
