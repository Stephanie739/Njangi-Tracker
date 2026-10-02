(async () => {
  const me = await requireRole('admin');
  if (!me) return;
  userName.textContent = me.name;
  userAvatar.textContent = (me.name || 'NG').split(/\s+/).map(x => x[0]).slice(0, 2).join('').toUpperCase();
  logoutButton.onclick = logout;
  mobileMenu.onclick = () => { sidebar.classList.toggle('open'); sidebarOverlay.classList.toggle('show'); };

  let data = [];
  let defaultAmount = '';

  async function load() {
    data = (await api('/members')).members;
    render();
  }

  function reliabilityCell(m) {
    const r = m.reliability;
    return r && r.completed_cycles ? `${r.score}%` : '<span title="Shown after the first closed cycle">—</span>';
  }

  function render() {
    const q = (searchMember.value || memberSearchTop.value || '').toLowerCase();
    const st = statusFilter.value, en = enrollmentFilter.value;
    const rows = data.filter(m =>
      (m.name.toLowerCase().includes(q) || (m.phone || '').toLowerCase().includes(q) || (m.email || '').toLowerCase().includes(q)) &&
      (st === 'all' || m.status.toLowerCase() === st) &&
      (en === 'all' || (en === 'enrolled' ? m.enrolled : !m.enrolled)));
    memberTable.innerHTML = rows.map(m => `<tr>
      <td>#${m.rotation_position}</td>
      <td><strong>${esc(m.name)}</strong><br><small>${esc(m.email || '')}</small>${m.enrolled ? '' : '<br><small>Not enrolled</small>'}</td>
      <td>${esc(m.phone)}</td>
      <td>${money(m.expected)}</td>
      <td>${money(m.paid)}</td>
      <td>${money(Math.max(m.expected - m.paid, 0))}</td>
      <td><span class="status ${m.status.toLowerCase()}">${m.status}</span></td>
      <td>${reliabilityCell(m)}</td>
      <td><button onclick="editMember(${m.id})">Edit</button> <button onclick="deleteMember(${m.id})">Delete</button></td>
    </tr>`).join('') || '<tr><td colspan="9" style="text-align:center;padding:24px">No members found.</td></tr>';
    const enrolled = data.filter(m => m.enrolled);
    totalMembers.textContent = data.length;
    fullyPaid.textContent = enrolled.filter(m => m.status === 'Paid').length;
    outstandingCount.textContent = enrolled.filter(m => m.status !== 'Paid').length;
    totalExpected.textContent = money(enrolled.reduce((a, m) => a + Number(m.expected || 0), 0));
    enrollmentSummary.textContent = enrolled.length + ' enrolled';
  }

  openMemberModal.onclick = () => {
    modalTitle.textContent = 'Add Member';
    memberForm.reset();
    memberId.value = '';
    memberEnrolled.checked = true;
    memberExpected.value = defaultAmount || '';
    memberPosition.value = data.reduce((mx, m) => Math.max(mx, m.rotation_position), 0) + 1;
    memberPassword.placeholder = 'At least 8 characters';
    memberModal.classList.add('show');
  };
  closeMemberModal.onclick = cancelMember.onclick = () => memberModal.classList.remove('show');

  memberForm.onsubmit = async (e) => {
    e.preventDefault();
    const payload = {
      name: memberName.value.trim(),
      phone: memberPhone.value.trim(),
      email: memberEmail.value.trim(),
      expected: memberExpected.value,
      rotation_position: memberPosition.value,
      enrolled: memberEnrolled.checked,
    };
    if (memberPassword.value.trim()) payload.password = memberPassword.value.trim();
    try {
      if (memberId.value) {
        await api('/members/' + memberId.value, { method: 'PUT', body: JSON.stringify(payload) });
        memberModal.classList.remove('show');
        await load();
      } else {
        const d = await api('/members', { method: 'POST', body: JSON.stringify(payload) });
        memberModal.classList.remove('show');
        await load();
        alert(d.needs_activation
          ? `${payload.name} was added.\n\nThey can choose their own password: member login page > "Forgot password?" > enter ${payload.email}.`
          : `${payload.name} was added.\n\nThey can sign in with ${payload.email} and the temporary password you set.`);
      }
    } catch (x) { alert(x.message); }
  };

  window.editMember = (id) => {
    const m = data.find(x => x.id === id);
    if (!m) return;
    modalTitle.textContent = 'Edit Member';
    memberForm.reset();
    memberId.value = m.id;
    memberName.value = m.name;
    memberPhone.value = m.phone;
    memberEmail.value = m.email || '';
    memberExpected.value = m.expected;
    memberPosition.value = m.rotation_position;
    memberEnrolled.checked = !!m.enrolled;
    memberPassword.placeholder = 'Leave empty to keep the current password';
    memberModal.classList.add('show');
  };

  window.deleteMember = async (id) => {
    const m = data.find(x => x.id === id);
    if (!m || !confirm(`Delete ${m.name}? This cannot be undone.`)) return;
    try { await api('/members/' + id, { method: 'DELETE' }); await load(); }
    catch (x) { alert(x.message); }
  };

  [searchMember, memberSearchTop, statusFilter, enrollmentFilter].forEach(x => x.addEventListener('input', render));

  try { const st = await api('/settings'); defaultAmount = st.group.contribution_amount || ''; activeGroupName.textContent = st.group.name || 'Njangi Group'; } catch { /* optional */ }
  await load();
})().catch(e => alert(e.message));
