(() => {
  document.querySelectorAll('.password-toggle').forEach((button) => {
    button.addEventListener('click', () => {
      const input = document.getElementById(button.dataset.target);
      if (!input) return;
      const visible = input.type === 'password';
      input.type = visible ? 'text' : 'password';
      button.textContent = visible ? 'Hide' : 'Show';
      button.setAttribute('aria-label', visible ? 'Hide password' : 'Show password');
    });
  });

  const loginForm = document.getElementById('loginForm');
  if (loginForm) {
    loginForm.addEventListener('submit', async (event) => {
      event.preventDefault();
      const email = document.getElementById('loginEmail');
      const password = document.getElementById('loginPassword');
      const message = document.getElementById('loginMessage');

      message.textContent = '';
      message.className = 'form-message';

      if (!email.value.trim() || !email.validity.valid) {
        message.textContent = 'Enter a valid administrator email address.';
        message.className = 'form-message error';
        email.focus();
        return;
      }
      if (!password.value) {
        message.textContent = 'Enter your password.';
        message.className = 'form-message error';
        password.focus();
        return;
      }

      const button = loginForm.querySelector('button[type="submit"]');
      button.disabled = true;
      button.innerHTML = 'Signing in…';

      try {
        const data = await api('/auth/login', {
          method: 'POST',
          body: JSON.stringify({ email: email.value.trim(), password: password.value })
        });
        saveSession(data);
        location.replace('dashboard.html');
      } catch (error) {
        message.textContent = error.message || 'Unable to sign in.';
        message.className = 'form-message error';
      } finally {
        button.disabled = false;
        button.innerHTML = 'Sign in <span>→</span>';
      }
    });
  }

  const registerForm = document.getElementById('registerForm');
  if (registerForm) {
    registerForm.addEventListener('submit', async (event) => {
      event.preventDefault();
      const message = document.getElementById('registerMessage');
      const password = document.getElementById('registerPassword').value;
      const confirm = document.getElementById('registerConfirm').value;

      if (password.length < 8) {
        message.textContent = 'Password must be at least 8 characters.';
        message.className = 'form-message error';
        return;
      }
      if (password !== confirm) {
        message.textContent = 'Passwords do not match.';
        message.className = 'form-message error';
        return;
      }
      if (!document.getElementById('agreeTerms').checked) {
        message.textContent = 'Please agree to use Njangi Tracker responsibly.';
        message.className = 'form-message error';
        return;
      }

      const button = registerForm.querySelector('button[type="submit"]');
      button.disabled = true;
      button.innerHTML = 'Creating account…';

      try {
        const data = await api('/auth/register', {
          method: 'POST',
          body: JSON.stringify({
            name: document.getElementById('registerName').value.trim(),
            email: document.getElementById('registerEmail').value.trim(),
            phone: document.getElementById('registerPhone').value.trim(),
            password
          })
        });
        saveSession(data);
        location.replace('dashboard.html');
      } catch (error) {
        message.textContent = error.message || 'Unable to create account.';
        message.className = 'form-message error';
      } finally {
        button.disabled = false;
        button.innerHTML = 'Create Account <span>→</span>';
      }
    });
  }

  const forgotPassword = document.getElementById('forgotPassword');
  if (forgotPassword) {
    forgotPassword.addEventListener('click', (event) => {
      event.preventDefault();
      location.href = 'forgot-password.html?role=admin';
    });
  }
})();
