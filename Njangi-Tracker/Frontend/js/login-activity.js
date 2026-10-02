(async () => {
  const me = await requireRole('admin');
  if (!me) return;
  userName.textContent = me.name;
  userAvatar.textContent = (me.name || 'NG').split(/\s+/).map(x => x[0]).slice(0, 2).join('').toUpperCase();
  logoutButton.onclick = logout;
  mobileMenu.onclick = () => { sidebar.classList.toggle('open'); sidebarOverlay.classList.toggle('show'); };
  sidebarOverlay.onclick = () => { sidebar.classList.remove('open'); sidebarOverlay.classList.remove('show'); };

  const rows = (await api('/login-activity')).activity || [];
  activityCount.textContent = rows.length;
  activityAdmins.textContent = rows.filter(x => x.user_type === 'admin').length;
  activityMembers.textContent = rows.filter(x => x.user_type === 'member').length;
  activityBody.innerHTML = rows.map(x =>
    `<tr><td>${esc(x.name)}</td><td>${esc(x.email)}</td><td>${esc(x.user_type)}</td><td>${fmtDate(x.login_at)} ${esc(String(x.login_at || '').slice(11, 16))}</td></tr>`
  ).join('');
  emptyActivity.style.display = rows.length ? 'none' : 'block';
})().catch(e => alert(e.message));
