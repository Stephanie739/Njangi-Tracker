document.querySelectorAll('.password-toggle').forEach(b => b.onclick = () => {
  const i = document.getElementById(b.dataset.target);
  i.type = i.type === 'password' ? 'text' : 'password';
  b.textContent = i.type === 'password' ? 'Show' : 'Hide';
});

const lf = document.getElementById('loginForm');
if (lf) lf.onsubmit = async e => {
  e.preventDefault();
  const msg = document.getElementById('loginMessage');
  try {
    const d = await api('/auth/login', {
      method: 'POST',
      body: JSON.stringify({
        email: loginEmail.value,
        password: loginPassword.value
      })
    });
    saveSession(d);
    location.href = 'dashboard.html';
  } catch (x) {
    msg.textContent = x.message;
    msg.className = 'form-message error';
  }
};

const rf = document.getElementById('registerForm');
if (rf) rf.onsubmit = async e => {
  e.preventDefault();
  const msg = document.getElementById('registerMessage');

  if (registerPassword.value !== registerConfirm.value) {
    msg.textContent = 'Passwords do not match';
    return;
  }

  if (!agreeTerms.checked) {
    msg.textContent = 'Please agree to use Njangi Tracker responsibly';
    return;
  }

  try {
    const d = await api('/auth/register', {
      method: 'POST',
      body: JSON.stringify({
        name: registerName.value,
        email: registerEmail.value,
        phone: registerPhone.value,
        password: registerPassword.value
      })
    });
    saveSession(d);
    location.href = 'dashboard.html';
  } catch (x) {
    msg.textContent = x.message;
    msg.className = 'form-message error';
  }
};

const fp = document.getElementById('forgotPassword');
if (fp) fp.onclick = e => {
  e.preventDefault();
  location.href = 'forgot-password.html?role=admin';
};