(async () => {
  await requireRole('admin');
  logoutButton.onclick = logout;

  let members = [], cycles = [], rows = [];
  const pad = (n) => String(n).padStart(2, '0');
  const today = () => { const d = new Date(); return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`; };

  async function load() {
    members = (await api('/members')).members;
    cycles = (await api('/cycles')).cycles;
    rows = (await api('/contributions')).contributions;
    memberSelect.innerHTML = members.filter(m => m.enrolled).map(m => `<option value="${m.id}">${esc(m.name)}</option>`).join('');
    const keep = cycleFilter.value || 'all';
    cycleFilter.innerHTML = '<option value="all">All cycles</option>' + cycles.map(c => `<option value="${c.id}">Cycle #${c.number}</option>`).join('');
    cycleFilter.value = [...cycleFilter.options].some(o => o.value === keep) ? keep : 'all';
    render();
  }

  function render() {
    const q = (searchContribution.value || document.getElementById('topSearch')?.value || '').toLowerCase();
    const cf = cycleFilter.value;
    const list = rows.filter(p => (!q || p.member_name.toLowerCase().includes(q)) && (cf === 'all' || String(p.cycle_id) === cf));
    const active = cycles.find(c => c.status === 'OPEN');
    contributionTable.innerHTML = list.map(p => {
      const open = active && p.cycle_id === active.id;
      return `<tr><td><strong>${esc(p.member_name)}</strong></td><td>${money(p.amount)}</td><td>${fmtDate(p.date)}</td><td>Cycle #${p.cycle_number}</td><td><span class="status ${p.status.toLowerCase()}">${p.status}</span></td><td>${open ? `<button onclick="delContribution(${p.id})">Delete</button>` : ''}</td></tr>`;
    }).join('') || '<tr><td colspan="6" style="text-align:center;padding:24px">No payments found.</td></tr>';

    const total = rows.filter(x => active && x.cycle_id === active.id).reduce((a, x) => a + Number(x.amount), 0);
    totalCollected.textContent = money(total);
    paymentCount.textContent = rows.length;
    outstandingCount.textContent = members.filter(m => m.enrolled && m.status !== 'Paid').length;
    cycleProgress.textContent = (active ? Math.min(100, Math.round(total / Math.max(Number(active.target), 1) * 100)) : 0) + '%';
    cycleTargetText.textContent = 'Target: ' + money(active?.target || 0);
    sideCycle.textContent = active ? `Cycle #${active.number}` : 'No active cycle';
  }

  openContribution.onclick = () => {
    if (!cycles.find(c => c.status === 'OPEN')) { alert('Create an active cycle first (Cycles page).'); return; }
    if (!members.some(m => m.enrolled)) { alert('Add at least one enrolled member first.'); return; }
    dateInput.value = today();
    dateInput.max = today();
    contributionModal.classList.add('show');
  };
  closeContribution.onclick = cancelContribution.onclick = () => contributionModal.classList.remove('show');

  contributionForm.onsubmit = async (e) => {
    e.preventDefault();
    const cy = cycles.find(c => c.status === 'OPEN');
    try {
      if (!cy) throw Error('Create an active cycle first');
      await api('/contributions', { method: 'POST', body: JSON.stringify({ member_id: memberSelect.value, cycle_id: cy.id, amount: amountInput.value, date: dateInput.value }) });
      contributionModal.classList.remove('show');
      contributionForm.reset();
      await load();
      alert('Payment recorded successfully');
    } catch (x) { alert(x.message); }
  };

  window.delContribution = async (id) => {
    if (!confirm('Delete this payment?')) return;
    try { await api('/contributions/' + id, { method: 'DELETE' }); await load(); }
    catch (x) { alert(x.message); }
  };

  searchContribution.oninput = render;
  const topSearchBox = document.getElementById('topSearch');
  if (topSearchBox) topSearchBox.oninput = render;
  cycleFilter.onchange = render;
  dateInput.value = today();
  await load();
})().catch(e => alert(e.message));
