(() => {
  const form = document.getElementById('memberLoginForm');
  if (!form) return;

  const emailInput = document.getElementById('memberCode');
  const passwordInput = document.getElementById('memberPassword');
  const message = document.getElementById('memberLoginMessage');
  const button = document.getElementById('memberLoginButton');
  const emailError = document.getElementById('memberCodeError');
  const passwordError = document.getElementById('memberPasswordError');

  document.querySelectorAll('.password-toggle').forEach((toggle) => {
    toggle.addEventListener('click', () => {
      const input = document.getElementById(toggle.dataset.target);
      if (!input) return;
      const visible = input.type === 'password';
      input.type = visible ? 'text' : 'password';
      toggle.textContent = visible ? 'Hide' : 'Show';
      toggle.setAttribute('aria-label', visible ? 'Hide password' : 'Show password');
    });
  });

  emailInput.addEventListener('input', () => { emailError.textContent = ''; });
  passwordInput.addEventListener('input', () => { passwordError.textContent = ''; });

  // If the same email belongs to several njangi groups, the backend asks which one.
  let groupSelect = null;
  function showGroupChoice(groups) {
    if (!groupSelect) {
      groupSelect = document.createElement('select');
      groupSelect.id = 'memberGroup';
      groupSelect.className = 'form-group';
      groupSelect.style.cssText = 'width:100%;margin:0 0 12px;padding:12px;border-radius:10px;border:1px solid #d1d5db';
      form.insertBefore(groupSelect, button);
    }
    groupSelect.innerHTML = groups
      .map((g) => `<option value="${g.group_id}">${esc(g.group_name)}</option>`)
      .join('');
    message.textContent = 'This email belongs to more than one group. Choose a group, then sign in again.';
    message.className = 'form-message';
  }

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    message.textContent = '';
    message.className = 'form-message';
    emailError.textContent = '';
    passwordError.textContent = '';

    const email = emailInput.value.trim().toLowerCase();
    const password = passwordInput.value;

    const emailHint = emailProblem(email);
    if (emailHint) {
      emailError.textContent = emailHint;
      emailInput.focus();
      return;
    }
    if (!password) {
      passwordError.textContent = 'Enter your password.';
      passwordInput.focus();
      return;
    }

    button.disabled = true;
    button.textContent = 'Signing in…';

    try {
      const payload = { email, password };
      if (groupSelect && groupSelect.value) payload.group_id = Number(groupSelect.value);

      const data = await api('/member/login', { method: 'POST', body: JSON.stringify(payload) });

      if (data.choose_group) {
        showGroupChoice(data.groups || []);
        return;
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
