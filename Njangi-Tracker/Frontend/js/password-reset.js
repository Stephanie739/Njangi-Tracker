/*
 * Password reset flow (talks to the backend):
 *   forgot-password.html  -> POST /auth/forgot      (email -> 6-digit PIN by e-mail)
 *   verify-pin.html       -> POST /auth/verify-pin   (reset_token + pin)
 *   reset-password.html   -> POST /auth/reset        (reset_token + new password)
 */
const params = new URLSearchParams(location.search);
let token = sessionStorage.getItem('reset_token') || params.get('token') || '';

// Which login page linked here (?role=member or ?role=admin) decides which account a
// shared email resolves to, when the same email is both an admin and a member.
let roleHint = sessionStorage.getItem('reset_role_hint') || params.get('role') || '';
if (roleHint) sessionStorage.setItem('reset_role_hint', roleHint);

function setResetMessage(text, ok) {
  const el = document.getElementById('resetMessage');
  if (!el) return;
  el.textContent = text;
  el.className = 'form-message' + (ok ? ' success' : ' error');
}

// ---- Step 1: request a PIN ------------------------------------------------
const forgotForm = document.getElementById('forgotForm');
if (forgotForm) {
  forgotForm.onsubmit = async (e) => {
    e.preventDefault();
    try {
      const d = await api('/auth/forgot', {
        method: 'POST',
        body: JSON.stringify({ email: resetEmail.value.trim(), role: roleHint || undefined })
      });
      sessionStorage.setItem('reset_token', d.reset_token || '');
      setResetMessage(d.dev_pin ? "Development PIN: " + d.dev_pin : "If this email is registered, a 6-digit PIN has been sent. It expires in 10 minutes.", true);
      setTimeout(() => (location.href = 'verify-pin.html'), d.dev_pin ? 4000 : 900);
    } catch (x) {
      setResetMessage(x.message, false);
    }
  };
}

// ---- Step 2: verify the PIN -----------------------------------------------
const verifyForm = document.getElementById('verifyForm');
if (verifyForm) {
  verifyForm.onsubmit = async (e) => {
    e.preventDefault();
    if (!token) {
      setResetMessage('No reset request found. Please request a new PIN.', false);
      return;
    }
    try {
      const d = await api('/auth/verify-pin', {
        method: 'POST',
        body: JSON.stringify({ reset_token: token, pin: pin.value.trim() })
      });
      sessionStorage.setItem('reset_token', d.reset_token || token);
      sessionStorage.setItem('reset_role', d.role || '');
      location.href = 'reset-password.html?token=' + encodeURIComponent(d.reset_token || token);
    } catch (x) {
      setResetMessage(x.message, false);
    }
  };
}

// ---- Step 3: choose a new password ----------------------------------------
const resetForm = document.getElementById('resetForm');
if (resetForm) {
  resetForm.onsubmit = async (e) => {
    e.preventDefault();
    if (newPassword.value !== confirmPassword.value) {
      setResetMessage('Passwords do not match', false);
      return;
    }
    try {
      const d = await api('/auth/reset', {
        method: 'POST',
        body: JSON.stringify({ reset_token: token, password: newPassword.value })
      });
      const role = d.role || sessionStorage.getItem('reset_role') || '';
      // A password reset invalidates all server sessions: clear stale browser auth too.
      localStorage.removeItem('njangi_token');
      localStorage.removeItem('njangi_user');
      sessionStorage.removeItem('reset_token');
      sessionStorage.removeItem('reset_role');
      sessionStorage.removeItem('reset_role_hint');
      setResetMessage('Password changed. Redirecting to login…', true);
      setTimeout(() => {
        location.href = role === 'member' ? 'member-login.html' : 'login.html';
      }, 900);
    } catch (x) {
      setResetMessage(x.message, false);
    }
  };
}
