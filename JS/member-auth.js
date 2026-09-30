(() => {
  const form = document.getElementById('memberLoginForm');
  if (!form) return;

  const codeInput = document.getElementById('memberCode');
  const passwordInput = document.getElementById('memberPassword');
  const message = document.getElementById('memberLoginMessage');
  const button = document.getElementById('memberLoginButton');

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

  codeInput.addEventListener('input', () => {
    codeInput.value = codeInput.value.toUpperCase().replace(/\s/g, '');
    document.getElementById('memberCodeError').textContent = '';
  });

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    message.textContent = '';
    message.className = 'form-message';

    const memberCode = codeInput.value.trim().toUpperCase();
    const password = passwordInput.value;

    if (!memberCode) {
      document.getElementById('memberCodeError').textContent =
        'Enter your Member ID (MBR-000123) or phone number.';
      codeInput.focus();
      return;
    }
    if (!password) {
      document.getElementById('memberPasswordError').textContent = 'Enter your password or 4-digit PIN.';
      passwordInput.focus();
      return;
    }

    button.disabled = true;
    button.textContent = 'Signing in…';

    try {
      // Prefer the new v1 phone/PIN endpoint. It also accepts member_code + PIN/password
      // so existing accounts continue to work without any HTML changes.
      const isMemberCode = /^MBR-\d{6}$/.test(memberCode);
      const isPin = /^\d{4}$/.test(password);

      let data;
      if (isPin || !isMemberCode) {
        // Phone + PIN  OR  Member-code + PIN  → v1 endpoint
        data = await api('/v1/auth/member-login', {
          method: 'POST',
          body: JSON.stringify({
            phone: isMemberCode ? undefined : memberCode,
            member_code: isMemberCode ? memberCode : undefined,
            pin: isPin ? password : undefined,
            password: isPin ? undefined : password
          })
        });
      } else {
        // Classic Member ID + password path (legacy)
        data = await api('/member/login', {
          method: 'POST',
          body: JSON.stringify({ member_code: memberCode, password })
        });
      }

      saveSession(data);
      window.location.replace('member-dashboard.html');
    } catch (error) {
      message.textContent = error.message || 'Unable to sign in. Check your credentials.';
      message.className = 'form-message error';
    } finally {
      button.disabled = false;
      button.innerHTML = 'Sign in <span>→</span>';
    }
  });
})();
