(async()=>{
  const me=await requireRole('member');
  if(!me)return;
  userName.textContent=me.name;
  userAvatar.textContent=me.name.slice(0,2).toUpperCase();
  logoutBtn.onclick=logout;
  menuBtn.onclick=()=>{sidebar.classList.toggle('open');overlay.classList.toggle('show')};

  function renderLoans(loans){
    myLoansTable.innerHTML=loans.map(x=>`<tr>
      <td>${money(x.amount)}</td>
      <td>${esc(x.reason)}</td>
      <td>${fmtDate(x.date_requested)}</td>
      <td>${money(x.balance ?? Math.max(Number(x.total_due||x.amount)-Number(x.amount_repaid||0),0))}</td>
      <td>${x.status}</td>
    </tr>`).join('');
    loansEmpty.style.display=loans.length?'none':'block';
  }

  async function loadDashboard(){
    const d=await api('/member/dashboard');
    statusName.textContent=d.member.name;
    statusAvatar.textContent=d.member.name.slice(0,2).toUpperCase();
    statusBadge.textContent=d.member.status;
    paidAmount.textContent=money(d.member.paid);
    expectedAmount.textContent=money(d.member.expected);
    collectedAmount.textContent=money(d.cycle_collected);
    cycleTargetAmount.textContent=money(d.active_cycle?.target||0);
    progressFill.style.width=d.progress+'%';
    progressText.textContent=d.progress+'%';
    remainingAmount.textContent=money(Math.max(d.cycle_expected-d.cycle_collected,0))+' remaining';
    membersPaid.textContent=`${d.members_paid} / group`;

    const r=d.member.reliability||{score:0,completed_cycles:0,on_time:0,late:0,missed:0};
    const reliabilityScore=document.getElementById('memberReliabilityScore');
    const reliabilityDetails=document.getElementById('memberReliabilityDetails');
    if(reliabilityScore)reliabilityScore.textContent=r.score+'%';
    if(reliabilityDetails)reliabilityDetails.textContent=r.completed_cycles
      ? `${r.completed_cycles} closed cycle(s): ${r.on_time} on-time, ${r.late} late, ${r.missed} missed.`
      : 'No closed cycles yet. Your reliability score will appear after a cycle is closed.';

    contributionTable.innerHTML=d.contributions.map(x=>`<tr><td>${esc(x.member_name)}</td><td>${money(x.amount)}</td><td>${fmtDate(x.date)}</td><td>${esc(x.status)}</td></tr>`).join('');
    contribEmpty.style.display=d.contributions.length?'none':'block';
    renderLoans(d.loans);
  }

  await loadDashboard();

  memberLoanForm.onsubmit=async e=>{
    e.preventDefault();
    loanMessage.textContent='Submitting...';
    try{
      await api('/loans',{method:'POST',body:JSON.stringify({amount:loanAmount.value,reason:loanReason.value})});
      e.target.reset();
      loanMessage.textContent='Loan request submitted. The group admin can now review it.';
      await loadDashboard();
    }catch(x){loanMessage.textContent=x.message}
  };
})().catch(e=>alert(e.message));