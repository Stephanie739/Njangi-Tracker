const params = new URLSearchParams(location.search);
let token = sessionStorage.getItem('reset_token') || params.get('token') || '';

const roleSelect = document.getElementById('resetRole');
const memberCodeGroup = document.getElementById('resetMemberCodeGroup');
const memberCodeInput = document.getElementById('resetMemberCode');

if (roleSelect && memberCodeGroup) {
  const updateResetFields = () => {
    const member = roleSelect.value === 'member';
    memberCodeGroup.hidden = !member;
    memberCodeInput.required = member;
    if (!member) memberCodeInput.value = '';
  };
  roleSelect.addEventListener('change', updateResetFields);
  const roleFromUrl = new URLSearchParams(location.search).get('role');
  if (roleFromUrl === 'member' || roleFromUrl === 'admin') {
    roleSelect.value = roleFromUrl;
  }
  updateResetFields();
}

if (memberCodeInput) {
  memberCodeInput.addEventListener('input', () => {
    memberCodeInput.value = memberCodeInput.value.toUpperCase().replace(/\s/g, '');
  });
}

const forgotForm = document.getElementById('forgotForm');
if (forgotForm) {
  forgotForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    const message = document.getElementById('resetMessage');
    const button = document.getElementById('resetButton');
    message.textContent = '';

    const role = roleSelect.value;
    const email = document.getElementById('resetEmail').value.trim();
    const memberCode = memberCodeInput ? memberCodeInput.value.trim().toUpperCase() : '';

    if (!role) {
      message.textContent = 'Choose your account type.';
      message.className = 'form-message error';
      return;
    }
    if (role === 'member' && !/^MBR-\d{6}$/.test(memberCode)) {
      message.textContent = 'Enter your Member ID in this format: MBR-000123.';
      message.className = 'form-message error';
      return;
    }

    button.disabled = true;
    button.textContent = 'Sending…';

    try {
      const data = await api('/auth/forgot', {
        method: 'POST',
        body: JSON.stringify({
          account_type: role,
          member_code: role === 'member' ? memberCode : '',
          email
        })
      });
      sessionStorage.setItem('reset_token', data.reset_token || '');
      sessionStorage.setItem('reset_role', role);
      message.textContent = data.dev_pin
        ? 'Development PIN: ' + data.dev_pin
        : 'If the account exists, a 6-digit PIN has been sent to its email.';
      message.className = 'form-message success';
      setTimeout(() => location.href = 'verify-pin.html', 800);
    } catch (error) {
      message.textContent = error.message || 'Unable to start password reset.';
      message.className = 'form-message error';
    } finally {
      button.disabled = false;
      button.textContent = 'Send PIN';
    }
  });
}

const verifyForm = document.getElementById('verifyForm');
if (verifyForm) {
  verifyForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    const message = document.getElementById('resetMessage');
    try {
      const data = await api('/auth/verify-pin', {
        method: 'POST',
        body: JSON.stringify({
          reset_token: token,
          pin: document.getElementById('pin').value.trim()
        })
      });
      sessionStorage.setItem('reset_token', data.reset_token || token);
      sessionStorage.setItem('reset_role', data.role || sessionStorage.getItem('reset_role') || '');
      location.href = 'reset-password.html?token=' + encodeURIComponent(data.reset_token || token);
    } catch (error) {
      message.textContent = error.message || 'Invalid PIN.';
      message.className = 'form-message error';
    }
  });
}

const resetForm = document.getElementById('resetForm');
if (resetForm) {
  resetForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    const message = document.getElementById('resetMessage');
    const password = document.getElementById('newPassword').value;
    const confirm = document.getElementById('confirmPassword').value;

    if (password !== confirm) {
      message.textContent = 'Passwords do not match.';
      message.className = 'form-message error';
      return;
    }

    try {
      const data = await api('/auth/reset', {
        method: 'POST',
        body: JSON.stringify({ reset_token: token, password })
      });
      const role = data.role || sessionStorage.getItem('reset_role') || '';
      localStorage.removeItem('njangi_token');
      localStorage.removeItem('njangi_user');
      sessionStorage.removeItem('reset_token');
      sessionStorage.removeItem('reset_role');
      message.textContent = 'Password changed. Redirecting to sign in…';
      setTimeout(() => location.href = role === 'member' ? 'member-login.html' : 'login.html', 900);
    } catch (error) {
      message.textContent = error.message || 'Unable to change password.';
      message.className = 'form-message error';
    }
  });
}
