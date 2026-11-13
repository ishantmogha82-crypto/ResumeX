/**
 * ResumeX — Authentication Logic (auth.js)
 */

document.addEventListener('DOMContentLoaded', () => {
  const loginForm = document.getElementById('login-form');
  const registerForm = document.getElementById('register-form');
  const errorBox = document.getElementById('auth-error');
  const submitBtn = document.getElementById('btn-submit');

  function showError(msg) {
    if (errorBox) {
      errorBox.textContent = msg;
      errorBox.style.display = 'block';
    } else {
      showToast(msg, 'error');
    }
  }

  function clearError() {
    if (errorBox) {
      errorBox.textContent = '';
      errorBox.style.display = 'none';
    }
  }

  // ─────────────────────────────────────────────────────────────
  // LOGIN FORM
  // ─────────────────────────────────────────────────────────────
  if (loginForm) {
    loginForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      clearError();

      const email = document.getElementById('email').value.trim();
      const password = document.getElementById('password').value;

      if (!email || !password) {
        showError('Please enter both email and password.');
        return;
      }

      if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.innerHTML = `<span class="spinner"></span> Signing In...`;
      }

      try {
        const response = await fetch(`${API_BASE}/auth/login`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify({ email, password })
        });

        const data = await response.json();

        if (response.ok) {
          showToast('Sign in successful. Redirecting...', 'success');
          // Check for redirect param
          const params = new URLSearchParams(window.location.search);
          const redirectUrl = params.get('redirect') || '/dashboard.html';
          setTimeout(() => {
            window.location.href = redirectUrl;
          }, 400);
        } else {
          showError(data.error || 'Invalid email or password.');
          if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.innerHTML = `<span>Sign In</span>`;
          }
        }
      } catch (err) {
        console.error('Login error:', err);
        showError('Unable to connect to the authentication server. Please try again.');
        if (submitBtn) {
          submitBtn.disabled = false;
          submitBtn.innerHTML = `<span>Sign In</span>`;
        }
      }
    });
  }

  // ─────────────────────────────────────────────────────────────
  // REGISTRATION FORM
  // ─────────────────────────────────────────────────────────────
  if (registerForm) {
    registerForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      clearError();

      const name = document.getElementById('name').value.trim();
      const email = document.getElementById('email').value.trim();
      const password = document.getElementById('password').value;
      const confirmPassword = document.getElementById('confirm-password').value;

      if (!name || !email || !password) {
        showError('All fields are required.');
        return;
      }

      if (password.length < 6) {
        showError('Password must be at least 6 characters long.');
        return;
      }

      if (password !== confirmPassword) {
        showError('Passwords do not match. Please re-enter.');
        return;
      }

      if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.innerHTML = `<span class="spinner"></span> Creating Account...`;
      }

      try {
        const response = await fetch(`${API_BASE}/auth/register`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify({ name, email, password })
        });

        const data = await response.json();

        if (response.ok) {
          showToast('Account created successfully!', 'success');
          setTimeout(() => {
            window.location.href = '/dashboard.html';
          }, 500);
        } else {
          showError(data.error || 'Registration failed. Please try again.');
          if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.innerHTML = `<span>Create Free Account</span>`;
          }
        }
      } catch (err) {
        console.error('Registration error:', err);
        showError('Unable to connect to registration server. Please try again.');
        if (submitBtn) {
          submitBtn.disabled = false;
          submitBtn.innerHTML = `<span>Create Free Account</span>`;
        }
      }
    });
  }
});

