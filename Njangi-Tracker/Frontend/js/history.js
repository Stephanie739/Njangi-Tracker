(async () => {
  const me = await requireRole('admin');
  if (!me) return;
  userName.textContent = me.name;
  userAvatar.textContent = (me.name || 'NG').split(/\s+/).map(x => x[0]).slice(0, 2).join('').toUpperCase();
  logoutButton.onclick = logout;
  mobileMenu.onclick = () => { sidebar.classList.toggle('open'); sidebarOverlay.classList.toggle('show'); };
  sidebarOverlay.onclick = () => { sidebar.classList.remove('open'); sidebarOverlay.classList.remove('show'); };

  const rows = (await api('/history')).history;

  // Summary cards always describe the whole history.
  historyTotal.textContent = money(rows.reduce((a, x) => a + Number(x.amount), 0));
  historyCount.textContent = rows.length;
  historyMembers.textContent = new Set(rows.map(x => x.member_id)).size;
  historyCycles.textContent = new Set(rows.map(x => x.cycle_id)).size;

  // Member filter: one entry per member that has at least one payment.
  const people = [...new Map(rows.map(x => [String(x.member_id), x.member_name])).entries()].sort((a, b) => a[1].localeCompare(b[1]));
  memberFilter.innerHTML = '<option value="">All members</option>' + people.map(([id, name]) => `<option value="${id}">${esc(name)}</option>`).join('');

  function render() {
    const q = (historySearch.value || '').trim().toLowerCase();
    const member = memberFilter.value;
    const day = dateFilter.value;
    const list = rows.filter(x =>
      (!q || x.member_name.toLowerCase().includes(q)) &&
      (!member || String(x.member_id) === member) &&
      (!day || String(x.date).slice(0, 10) === day));
    historyBody.innerHTML = list.map(x => `<tr><td>${esc(x.member_name)}</td><td>${money(x.amount)}</td><td>${fmtDate(x.date)}</td><td>Cycle #${x.cycle_number}</td><td>${esc(x.status)}</td></tr>`).join('');
    emptyHistory.style.display = list.length ? 'none' : 'block';
  }

  historySearch.oninput = render;
  memberFilter.onchange = render;
  dateFilter.onchange = render;
  dateFilter.oninput = render;
  resetFilter.onclick = () => { historySearch.value = ''; memberFilter.value = ''; dateFilter.value = ''; render(); };
  render();
})().catch(e => alert(e.message));
