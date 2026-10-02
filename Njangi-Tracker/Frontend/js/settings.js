(async () => {
  const me = await requireRole(user()?.role || 'admin').catch(() => null);
  if (!me) return;
  const role = me.role;

  // ----- navigation depends on who is signed in -----
  sideNav.innerHTML = role === 'admin'
    ? `<a href="dashboard.html"><span>▦</span> Dashboard</a>
       <a href="members.html"><span>MB</span> Members</a>
       <a href="cycles.html"><span>↻</span> Cycles</a>
       <a href="contributions.html"><span>₣</span> Contributions</a>
       <a href="history.html"><span>◷</span> History</a>
       <a href="loans.html"><span>LN</span> Emergency Loans</a>
       <a href="login-activity.html"><span>LG</span> Login Activity</a>`
    : `<a href="member-dashboard.html"><span>▦</span> My Dashboard</a>
       <a href="member-dashboard.html#loan-request"><span>LN</span> Request Loan</a>`;
  logoutButton.onclick = logout;
  mobileMenu.onclick = () => { sidebar.classList.toggle('open'); sidebarOverlay.classList.toggle('show'); };
  sidebarOverlay.onclick = () => { sidebar.classList.remove('open'); sidebarOverlay.classList.remove('show'); };

  function say(el, text, ok) { el.textContent = text; el.className = 'settings-msg ' + (ok ? 'ok' : 'err'); }

  async function load() {
    const d = await api('/settings');
    userName.textContent = d.user.name || me.name;
    userAvatar.textContent = (d.user.name || 'NG').split(/\s+/).map(x => x[0]).slice(0, 2).join('').toUpperCase();
    userRole.textContent = role === 'admin' ? 'Administrator' : 'Member';
    setName.value = d.user.name || '';
    setEmail.value = d.user.email || '';
    setPhone.value = d.user.phone || '';
    if (role === 'admin') {
      groupPanel.hidden = false;
      emailPanel.hidden = false;
      setGroupName.value = d.group.name || '';
      setAmount.value = d.group.contribution_amount || '';
      setFrequency.value = d.group.frequency || 'Monthly';
      emailStatus.textContent = d.email_configured ? 'Configured' : 'Not configured';
      emailStatus.className = 'pill ' + (d.email_configured ? 'ok' : 'bad');
      emailHelp.textContent = d.email_configured
        ? ''
        : 'Password-reset PINs cannot be sent until the server administrator sets NJANGI_SMTP_USERNAME and NJANGI_SMTP_PASSWORD in Backend/.env. Meanwhile you can give members a temporary password when you add or edit them.';
      settingsIntro.textContent = 'Manage your account, your njangi group and your password.';
    } else {
      setName.readOnly = true; setPhone.readOnly = true;
      profileSave.hidden = true;
      settingsIntro.textContent = 'Your account details are managed by your group administrator. You can change your password here.';
    }
  }

  profileForm.onsubmit = async (e) => {
    e.preventDefault();
    if (role !== 'admin') return;
    try {
      const d = await api('/settings', { method: 'PUT', body: JSON.stringify({ name: setName.value, phone: setPhone.value, group_name: setGroupName.value, contribution_amount: setAmount.value, frequency: setFrequency.value }) });
      say(profileMsg, d.message, true);
      const u = user() || {}; u.name = setName.value.trim(); localStorage.setItem('njangi_user', JSON.stringify(u));
      await load(); initShell();
    } catch (x) { say(profileMsg, x.message, false); }
  };

  groupForm.onsubmit = async (e) => {
    e.preventDefault();
    try {
      const d = await api('/settings', { method: 'PUT', body: JSON.stringify({ name: setName.value, phone: setPhone.value, group_name: setGroupName.value, contribution_amount: setAmount.value, frequency: setFrequency.value }) });
      say(groupMsg, d.message, true);
      await load(); initShell();
    } catch (x) { say(groupMsg, x.message, false); }
  };

  passwordForm.onsubmit = async (e) => {
    e.preventDefault();
    if (newPass.value !== newPass2.value) return say(passwordMsg, 'The new passwords do not match.', false);
    try {
      const d = await api('/auth/change-password', { method: 'POST', body: JSON.stringify({ current_password: curPassword.value, new_password: newPass.value }) });
      say(passwordMsg, d.message, true);
      passwordForm.reset();
    } catch (x) { say(passwordMsg, x.message, false); }
  };

  await load();
})().catch(e => alert(e.message));
