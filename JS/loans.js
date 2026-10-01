(async()=>{
  await requireRole('admin');
  logoutButton.onclick=logout;
  let rows=[], members=[];

  async function load(){
    rows=(await api('/loans')).loans;
    members=(await api('/members')).members;
    loanMember.innerHTML=members.filter(m=>m.enrolled).map(m=>`<option value="${m.id}">${esc(m.name)}</option>`).join('');
    render();
  }

  function render(){
    const filter=statusFilter.value;
    const visible=rows.filter(x=>filter==='all'||x.status.toLowerCase()===filter);
    loanTableBody.innerHTML=visible.map(x=>{
      const r=x.reliability||{score:0,completed_cycles:0,on_time:0,late:0,missed:0};
      const balance=Number(x.balance ?? Math.max(Number(x.total_due||x.amount)-Number(x.amount_repaid||0),0));
      const action=x.status==='PENDING'
        ? `<button onclick="loanAction(${x.id},'approve')">Approve</button> <button onclick="loanAction(${x.id},'reject')">Reject</button>`
        : (['APPROVED','ACTIVE'].includes(x.status)?`<button onclick="repay(${x.id},${balance})">Repay</button>`:'');
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
    }).join('');
    emptyState.style.display=visible.length?'none':'block';
    pendingCount.textContent=rows.filter(x=>x.status==='PENDING').length;
    borrowerCount.textContent=rows.filter(x=>['APPROVED','ACTIVE'].includes(x.status)).length;
    activeBalance.textContent=money(rows.filter(x=>['APPROVED','ACTIVE'].includes(x.status)).reduce((sum,x)=>sum+Number(x.balance||0),0));

    const scored=members.map(m=>m.reliability).filter(r=>r&&r.completed_cycles>0);
    const avg=scored.length?Math.round(scored.reduce((sum,r)=>sum+Number(r.score),0)/scored.length):0;
    averageReliability.textContent=avg+'%';
    reliabilityGrid.innerHTML=members.map(m=>{
      const r=m.reliability||{score:0,completed_cycles:0,on_time:0,late:0,missed:0};
      return `<div class="reliability-card">
        <strong>${esc(m.name)}</strong>
        <span>${r.score}%</span>
        <small>${r.completed_cycles} cycle(s): ${r.on_time} on-time, ${r.late} late, ${r.missed} missed</small>
      </div>`;
    }).join('');
  }

  window.loanAction=async(id,action)=>{
    try{
      const result=await api('/loans/'+id,{method:'PATCH',body:JSON.stringify({action})});
      alert(result.message||'Loan updated');
      await load();
    }catch(x){alert(x.message)}
  };

  window.repay=async(id,balance)=>{
    const amount=prompt(`Enter repayment amount (maximum ${balance} FCFA)`);
    if(!amount)return;
    try{
      await api('/loans/'+id,{method:'PATCH',body:JSON.stringify({action:'repay',amount})});
      await load();
    }catch(x){alert(x.message)}
  };

  loanForm.onsubmit=async e=>{
    e.preventDefault();
    try{
      await api('/loans',{method:'POST',body:JSON.stringify({member_id:loanMember.value,amount:loanAmount.value,reason:loanReason.value})});
      e.target.reset();
      await load();
      alert('Loan request submitted. It is now pending approval.');
    }catch(x){alert(x.message)}
  };

  statusFilter.onchange=render;
  load().catch(e=>alert(e.message));
})().catch(e=>alert(e.message));
