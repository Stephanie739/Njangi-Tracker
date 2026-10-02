(async () => {
  await requireRole('admin');
  logoutButton.onclick = logout;

  let rows = [], members = [], frequency = 'Monthly';

  const pad = (n) => String(n).padStart(2, '0');
  const ymd = (d) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
  function endFor(start) {
    const d = new Date(start + 'T00:00:00');
    if (frequency === 'Weekly') d.setDate(d.getDate() + 7);
    else if (frequency === 'Biweekly') d.setDate(d.getDate() + 14);
    else d.setMonth(d.getMonth() + 1);
    return ymd(d);
  }

  async function load() {
    rows = (await api('/cycles')).cycles;
    members = (await api('/members')).members;
    render();
  }

  function render() {
    const a = rows.find(c => c.status === 'OPEN');
    const recipient = a ? members.find(m => m.id === a.recipient_id) : null;
    activeCycleName.textContent = a ? `#${a.number}` : 'None';
    activeCycleDates.textContent = a ? `${fmtDate(a.start_date)} - ${fmtDate(a.end_date)}` : '-';
    cycleTarget.textContent = 'Target: ' + money(a?.target || 0);
    recipientName.textContent = a ? (recipient?.name || '-') : '-';
    recipientPosition.textContent = a ? `Rotation position: ${recipient?.rotation_position || '-'}` : 'Rotation position: -';
    activeTitle.textContent = a ? `Cycle #${a.number}` : 'No active cycle';
    closeCycleButton.disabled = !a;
    openCycle.disabled = !!a;
    openCycle.title = a ? 'Close the active cycle first' : '';
    const term = (document.getElementById('topSearch')?.value || '').trim().toLowerCase();
    const shown = rows.filter(c => !term || String(c.recipient_name || '').toLowerCase().includes(term) || ('#' + c.number).includes(term) || String(c.number) === term);
    cycleTable.innerHTML = shown.map(c => `<tr><td>#${c.number}</td><td>${fmtDate(c.start_date)} - ${fmtDate(c.end_date)}</td><td>${money(c.target)}</td><td>${money(c.collected || 0)}</td><td>${esc(c.recipient_name || '-')}</td><td><span class="status ${c.status.toLowerCase()}">${c.status}</span></td></tr>`).join('')
      || '<tr><td colspan="6" style="text-align:center;padding:24px">No cycles yet. Click "New Cycle" to start the first one.</td></tr>';
    sideCycle.textContent = a ? `Cycle #${a.number}` : 'No active cycle';

    // Active-cycle cards and progress bar
    const collected = Number(a?.collected || 0), target = Number(a?.target || 0);
    const percent = target ? Math.min(100, Math.round(collected / target * 100)) : 0;
    const enrolled = members.filter(m => m.enrolled);
    cyclePool.textContent = money(collected);
    cyclePercent.textContent = percent + '%';
    cycleProgress.textContent = percent + '%';
    progressBar.style.width = percent + '%';
    progressCollected.textContent = money(collected) + ' collected';
    progressPercent.textContent = percent + '%';
    startDate.textContent = a ? fmtDate(a.start_date) : '-';
    endDate.textContent = a ? fmtDate(a.end_date) : '-';
    paidMembers.textContent = a ? `${enrolled.filter(m => m.status === 'Paid').length} / ${enrolled.length}` : '0 / 0';
    recipientDetail.textContent = recipient?.name || '-';
  }

  // The next recipient is the first enrolled member (by rotation position) who has not received yet;
  // once everyone has received, the rotation starts again from position 1.
  function suggestedRecipientId(enrolled) {
    const received = new Set(rows.map(c => c.recipient_id).filter(Boolean));
    const next = enrolled.find(m => !received.has(m.id)) || enrolled[0];
    return next ? next.id : null;
  }

  openCycle.onclick = () => {
    const enrolled = members.filter(m => m.enrolled).sort((a, b) => a.rotation_position - b.rotation_position);
    if (!enrolled.length) { alert('Add at least one enrolled member before creating a cycle.'); return; }
    const suggested = suggestedRecipientId(enrolled);
    cycleRecipient.innerHTML = enrolled.map(m => `<option value="${m.id}" ${m.id === suggested ? 'selected' : ''}>#${m.rotation_position} — ${esc(m.name)}</option>`).join('');
    cycleNumber.value = Math.max(0, ...rows.map(x => x.number)) + 1;
    // The target is the sum of what every enrolled member is expected to pay; the server uses the same rule.
    const target = enrolled.reduce((sum, m) => sum + Number(m.expected || 0), 0);
    cycleTargetInput.value = money(target);
    cycleStart.value = ymd(new Date());
    cycleEnd.value = endFor(cycleStart.value);
    cycleModal.classList.add('show');
  };
  cycleStart.onchange = () => { if (cycleStart.value) cycleEnd.value = endFor(cycleStart.value); };
  closeCycleModal.onclick = cancelCycle.onclick = () => cycleModal.classList.remove('show');

  cycleForm.onsubmit = async (e) => {
    e.preventDefault();
    try {
      await api('/cycles', { method: 'POST', body: JSON.stringify({ number: cycleNumber.value, start_date: cycleStart.value, end_date: cycleEnd.value, recipient_id: cycleRecipient.value }) });
      cycleModal.classList.remove('show');
      await load();
      alert('Cycle created');
    } catch (x) { alert(x.message); }
  };

  closeCycleButton.onclick = async () => {
    const a = rows.find(c => c.status === 'OPEN');
    if (!a || !confirm(`Close cycle #${a.number}? Members who have not paid in full will be recorded as missed.`)) return;
    try {
      await api('/cycles/close', { method: 'POST', body: '{}' });
      await load();
      alert('Cycle closed successfully');
    } catch (x) { alert(x.message); }
  };

  const cycleSearch = document.getElementById('topSearch');
  if (cycleSearch) cycleSearch.oninput = render;
  try { frequency = (await api('/settings')).group.frequency || 'Monthly'; } catch { /* default */ }
  await load();
})().catch(e => alert(e.message));
