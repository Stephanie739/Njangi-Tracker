
(async()=>{

  // Make sure only an admin can access this page
  await requireRole('admin');

  // Set the logout button to call the logout function
  logoutButton.onclick=logout;

  // Store loans and members
  let rows=[], members=[];


  // Load loans and members from the server
  async function load(){

    // Get all loans
    rows=(await api('/loans')).loans;

    // Get all members
    members=(await api('/members')).members;

    // Add enrolled members to the loan member dropdown
    loanMember.innerHTML=members
      .filter(m=>m.enrolled)
      .map(m=>`<option value="${m.id}">${esc(m.name)}</option>`)
      .join('');

    // Display the loans
    render();
  }


  // Display loans and update the page statistics
  function render(){

    // Get the selected loan status filter
    const filter=statusFilter.value;

    // Show all loans or only loans matching the filter
    const visible=rows.filter(
      x=>filter==='all'||x.status.toLowerCase()===filter
    );


    // Create a table row for each visible loan
    loanTableBody.innerHTML=visible.map(x=>{

      // Get the member's reliability information
      const r=x.reliability||{
        score:0,
        completed_cycles:0,
        on_time:0,
        late:0,
        missed:0
      };

      // Calculate the remaining loan balance
      const balance=Number(
        x.balance ??
        Math.max(
          Number(x.total_due||x.amount)-Number(x.amount_repaid||0),
          0
        )
      );


      // Decide which buttons should be displayed
      const action=x.status==='PENDING'
        ? `<button onclick="loanAction(${x.id},'approve')">Approve</button>
           <button onclick="loanAction(${x.id},'reject')">Reject</button>`
        : (
          ['APPROVED','ACTIVE'].includes(x.status)
          ? `<button onclick="repay(${x.id},${balance})">Repay</button>`
          : ''
        );


      // Create the HTML row for the loan
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


    // Hide the empty message when loans exist
    emptyState.style.display=visible.length?'none':'block';


    // Count pending loans
    pendingCount.textContent=
      rows.filter(x=>x.status==='PENDING').length;


    // Count approved or active loans
    borrowerCount.textContent=
      rows.filter(x=>['APPROVED','ACTIVE'].includes(x.status)).length;


    // Calculate the total balance of active loans
    activeBalance.textContent=money(
      rows
        .filter(x=>['APPROVED','ACTIVE'].includes(x.status))
        .reduce((sum,x)=>sum+Number(x.balance||0),0)
    );


    // Get members who have completed at least one cycle
    const scored=members
      .map(m=>m.reliability)
      .filter(r=>r&&r.completed_cycles>0);


    // Calculate the average reliability score
    const avg=scored.length
      ? Math.round(
          scored.reduce((sum,r)=>sum+Number(r.score),0)/scored.length
        )
      : 0;

    averageReliability.textContent=avg+'%';


    // Display reliability information for each member
    reliabilityGrid.innerHTML=members.map(m=>{

      // Get reliability data or use default values
      const r=m.reliability||{
        score:0,
        completed_cycles:0,
        on_time:0,
        late:0,
        missed:0
      };


      // Create a reliability card
      return `<div class="reliability-card">
        <strong>${esc(m.name)}</strong>
        <span>${r.score}%</span>
        <small>
          ${r.completed_cycles} cycle(s):
          ${r.on_time} on-time,
          ${r.late} late,
          ${r.missed} missed
        </small>
      </div>`;

    }).join('');
  }


  // Approve or reject a loan
  window.loanAction=async(id,action)=>{

    try{

      // Send the selected action to the server
      const result=await api('/loans/'+id,{
        method:'PATCH',
        body:JSON.stringify({action})
      });

      // Show the server message
      alert(result.message||'Loan updated');

      // Reload the loan list
      await load();

    }catch(x){

      // Show an error if the request fails
      alert(x.message);
    }
  };


  // Record a loan repayment
  window.repay=async(id,balance)=>{

    // Ask the admin how much the member wants to repay
    const amount=prompt(
      `Enter repayment amount (maximum ${balance} FCFA)`
    );

    // Stop if no amount was entered
    if(!amount)return;


    try{

      // Send the repayment amount to the server
      await api('/loans/'+id,{
        method:'PATCH',
        body:JSON.stringify({
          action:'repay',
          amount
        })
      });

      // Reload the loan information
      await load();

    }catch(x){

      // Show an error if the repayment fails
      alert(x.message);
    }
  };


  // Handle the loan request form
  loanForm.onsubmit=async e=>{

    // Stop the browser from refreshing the page
    e.preventDefault();

    try{

      // Send the new loan request to the server
      await api('/loans',{
        method:'POST',
        body:JSON.stringify({
          member_id:loanMember.value,
          amount:loanAmount.value,
          reason:loanReason.value
        })
      });

      // Clear the form
      e.target.reset();

      // Reload the loan list
      await load();

      // Tell the admin that the request was submitted
      alert('Loan request submitted. It is now pending approval.');

    }catch(x){

      // Show an error if the request fails
      alert(x.message);
    }
  };


  // Reload the loans whenever the status filter changes
  statusFilter.onchange=render;


  // Load the page data when the script starts
  // Show an error if loading fails
  load().catch(e=>alert(e.message));


})().catch(e=>alert(e.message));

