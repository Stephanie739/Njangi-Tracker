(async () => {
  await requireRole('admin');
  let rows = [], members = [];

  async function load() {
    rows = (await api('/loans')).loans;
    members = (await api('/members')).members;
    loanMember.innerHTML = members
      .filter((m) => m.enrolled)
      .map((m) => `<option value="${m.id}">${esc(m.name)}</option>`)
      .join('');
    render();
  }

  function render() {
    const filter = statusFilter.value;
    const visible = rows.filter((x) => filter === 'all' || x.status.toLowerCase() === filter);
    loanTableBody.innerHTML = visible
      .map((x) => {
        const r = x.reliability || { score: 0, completed_cycles: 0, on_time: 0, late: 0, missed: 0 };
        const balance = Number(
          x.balance ?? Math.max(Number(x.total_due || x.amount) - Number(x.amount_repaid || 0), 0)
        );
        const action =
          x.status === 'PENDING'
            ? `<button onclick="loanAction(${x.id},'approve')">Approve</button> <button onclick="loanAction(${x.id},'reject')">Reject</button>`
            : ['APPROVED', 'ACTIVE'].includes(x.status)
              ? `<button onclick="repay(${x.id},${balance})">Repay</button>`
              : '';
        return `<tr>
        <td>${esc(x.member_name)}</td>
        <td>${money(x.amount)}</td>
        <td>${esc(x.reason)}</td>
        <td>${fmtDate(x.date_requested)}</td>
        <td>${money(balance)}</td>
        <td>${r.score}%</td>
        <td>${x.status}</td>
        <td>${action}</td>
      </tr>`;
      })
      .join('');
    emptyState.style.display = visible.length ? 'none' : 'block';
    pendingCount.textContent = rows.filter((x) => x.status === 'PENDING').length;
    borrowerCount.textContent = rows.filter((x) => ['APPROVED', 'ACTIVE'].includes(x.status)).length;
    activeBalance.textContent = money(
      rows
        .filter((x) => ['APPROVED', 'ACTIVE'].includes(x.status))
        .reduce((sum, x) => sum + Number(x.balance || 0), 0)
    );

    const scored = members.map((m) => m.reliability).filter((r) => r && r.completed_cycles > 0);
    const avg = scored.length
      ? Math.round(scored.reduce((sum, r) => sum + Number(r.score), 0) / scored.length)
      : 0;
    averageReliability.textContent = avg + '%';
    reliabilityGrid.innerHTML = members
      .map((m) => {
        const r = m.reliability || { score: 0, completed_cycles: 0, on_time: 0, late: 0, missed: 0 };
        return `<div class="reliability-card">
        <strong>${esc(m.name)}</strong>
        <span>${r.score}%</span>
        <small>${r.completed_cycles} cycle(s): ${r.on_time} on-time, ${r.late} late, ${r.missed} missed</small>
      </div>`;
      })
      .join('');
  }

  // Admin approve / reject → prefer v1 endpoint, fall back to legacy PATCH
  window.loanAction = async (id, action) => {
    const loan = rows.find((x) => x.id === id);
    if (action === 'approve' && loan) {
      const total = Math.round(Number(loan.amount) * (1 + Number(loan.interest_rate || 0) / 100));
      if (
        !confirm(
          `Approve ${money(loan.amount)} for ${loan.member_name} at ${loan.interest_rate}% interest?\nTotal to repay: ${money(total)}`
        )
      )
        return;
    }
    if (action === 'reject' && !confirm('Reject this loan request?')) return;
    try {
      let result;
      try {
        result = await api('/v1/loans/' + id + '/approve', {
          method: 'POST',
          body: JSON.stringify({ action })
        });
      } catch (v1err) {
        // Fall back to legacy PATCH if v1 rejects (e.g. missing guarantors) — admin can force
        if (action === 'approve' && /guarantor/i.test(v1err.message || '')) {
          if (!confirm(v1err.message + '\n\nOverride and approve anyway?')) throw v1err;
          result = await api('/v1/loans/' + id + '/approve', {
            method: 'POST',
            body: JSON.stringify({ action: 'approve', force: true })
          });
        } else {
          result = await api('/loans/' + id, {
            method: 'PATCH',
            body: JSON.stringify({ action })
          });
        }
      }
      toast(result.message || 'Loan updated');
      await load();
    } catch (x) {
      alert(x.message);
    }
  };

  window.repay = (id, balance) => {
    const loan = rows.find((x) => x.id === id);
    paymentLoanId.value = id;
    paymentAmount.max = balance;
    paymentAmount.value = balance;
    paymentDescription.textContent =
      (loan ? loan.member_name + ' - ' : '') + 'balance to repay: ' + money(balance);
    paymentModal.classList.add('show');
  };
  closePaymentModal.onclick = cancelPayment.onclick = () => paymentModal.classList.remove('show');
  paymentModal.addEventListener('click', (e) => {
    if (e.target === paymentModal) paymentModal.classList.remove('show');
  });
  paymentForm.onsubmit = async (e) => {
    e.preventDefault();
    try {
      const r = await api('/loans/' + paymentLoanId.value, {
        method: 'PATCH',
        body: JSON.stringify({ action: 'repay', amount: paymentAmount.value })
      });
      paymentModal.classList.remove('show');
      toast(r.status === 'COMPLETED' ? 'Loan fully repaid' : 'Repayment recorded');
      await load();
    } catch (x) {
      alert(x.message);
    }
  };

  // Submit loan request → prefer v1 /api/v1/loans/apply
  loanForm.onsubmit = async (e) => {
    e.preventDefault();
    const payload = {
      member_id: loanMember.value,
      amount: loanAmount.value,
      reason: loanReason.value,
      interest_rate: loanRate.value,
      payback_months: 1,
      required_guarantors: 1
    };
    try {
      try {
        await api('/v1/loans/apply', { method: 'POST', body: JSON.stringify(payload) });
      } catch (v1err) {
        await api('/loans', { method: 'POST', body: JSON.stringify(payload) });
      }
      e.target.reset();
      loanRate.value = 5;
      await load();
      toast('Loan request submitted - pending approval');
    } catch (x) {
      alert(x.message);
    }
  };

  // Optional: guarantor sign-off helper (callable from console or future UI buttons)
  window.guaranteeLoan = async (loanId, decision) => {
    try {
      const result = await api('/v1/loans/' + loanId + '/guarantee', {
        method: 'POST',
        body: JSON.stringify({ decision: decision || 'Accepted' })
      });
      toast(result.message || 'Guarantor decision recorded');
      await load();
      return result;
    } catch (x) {
      alert(x.message);
    }
  };

  statusFilter.onchange = render;
  load().catch((e) => alert(e.message));
})().catch((e) => {
  if (!/session expired/i.test(e.message)) alert(e.message);
});
