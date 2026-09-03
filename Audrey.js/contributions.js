// =====================================================
// CONTRIBUTIONS PAGE
// =====================================================
const contributionTable=document.getElementById("contributionTable");
const contributionModal=document.getElementById("contributionModal");
const form=document.getElementById("contributionForm");
const memberSelect=document.getElementById("memberSelect");
const amountInput=document.getElementById("amountInput");
const dateInput=document.getElementById("dateInput");
const searchContribution=document.getElementById("searchContribution");
const cycleFilter=document.getElementById("cycleFilter");

dateInput.value=new Date().toISOString().split("T")[0];

function loadMemberOptions(){
  memberSelect.innerHTML="";
  getMembers().filter(m=>m.enrolled).sort((a,b)=>a.name.localeCompare(b.name)).forEach(m=>{const o=document.createElement("option");o.value=m.id;o.textContent=`${m.name} — Position #${m.rotationPosition}`;memberSelect.appendChild(o);});
  if(!memberSelect.options.length)memberSelect.innerHTML='<option value="">No enrolled members</option>';
}

function renderContributions(){
  const active=getActiveCycle();
  const cycleId=cycleFilter.value==="all"?null:active?.id;
  const search=searchContribution.value.toLowerCase().trim();
  let payments=getContributions().filter(p=>(!cycleId||p.cycleId===cycleId)&&p.memberName.toLowerCase().includes(search));
  contributionTable.innerHTML="";
  payments.forEach(p=>{const cycle=getCycles().find(c=>c.id===p.cycleId);const row=document.createElement("tr");row.innerHTML=`<td><strong>${escapeHTML(p.memberName)}</strong></td><td class="amount-positive">+${formatMoney(p.amount)}</td><td>${formatDate(p.date)}</td><td>Cycle #${cycle?.number||"-"}</td><td><span class="status paid">Recorded</span></td><td><button class="action-delete" onclick="deleteContribution('${p.id}')">Delete</button></td>`;contributionTable.appendChild(row);});

  const activeTotal=active?getCycleCollected(active.id):0;
  const members=getMembers();
  document.getElementById("totalCollected").textContent=formatMoney(activeTotal);
  document.getElementById("paymentCount").textContent=getContributions().length;
  document.getElementById("outstandingCount").textContent=members.filter(m=>Number(m.paid||0)<Number(m.expected||0)).length;
  const progress=active?Math.min(100,Math.round(activeTotal/Math.max(active.target,1)*100)):0;
  document.getElementById("cycleProgress").textContent=progress+"%";
  document.getElementById("cycleTargetText").textContent=`Target: ${formatMoney(active?.target||0)}`;
  document.getElementById("sideCycle").textContent=active?`Cycle #${active.number}`:"No active cycle";
}

form.addEventListener("submit",e=>{
  e.preventDefault();
  const memberId=memberSelect.value,amount=Number(amountInput.value),date=dateInput.value,cycle=getActiveCycle(),member=getMembers().find(m=>m.id===memberId);
  if(!member||!cycle||amount<=0||!date){alert("You need an active cycle and valid payment details.");return;}
  saveContributions([{id:Date.now().toString(),memberId,memberName:member.name,amount,date,cycleId:cycle.id},...getContributions()]);
  saveMembers(getMembers().map(m=>m.id===memberId?{...m,paid:Number(m.paid||0)+amount}:m));
  closeModal();amountInput.value="";renderContributions();alert("Payment recorded successfully.");
});

window.deleteContribution=id=>{const payment=getContributions().find(p=>p.id===id);if(!payment)return;if(!confirm(`Delete ${payment.memberName}'s payment?`))return;saveContributions(getContributions().filter(p=>p.id!==id));saveMembers(getMembers().map(m=>m.id===payment.memberId?{...m,paid:Math.max(Number(m.paid||0)-Number(payment.amount),0)}:m));renderContributions();};

function openModal(){loadMemberOptions();contributionModal.classList.add("show");contributionModal.setAttribute("aria-hidden","false");}
function closeModal(){contributionModal.classList.remove("show");contributionModal.setAttribute("aria-hidden","true");form.reset();dateInput.value=new Date().toISOString().split("T")[0];}
document.getElementById("openContribution").addEventListener("click",openModal);document.getElementById("closeContribution").addEventListener("click",closeModal);document.getElementById("cancelContribution").addEventListener("click",closeModal);contributionModal.addEventListener("click",e=>{if(e.target===contributionModal)closeModal();});
searchContribution.addEventListener("input",renderContributions);cycleFilter.addEventListener("change",renderContributions);

document.getElementById("logoutButton").addEventListener("click",()=>{localStorage.removeItem(DB_KEYS.loggedIn);location.href="login.html";});
const mobileMenu=document.getElementById("mobileMenu"),sidebar=document.getElementById("sidebar"),overlay=document.getElementById("sidebarOverlay");mobileMenu.addEventListener("click",()=>{sidebar.classList.toggle("open");overlay.classList.toggle("show")});overlay.addEventListener("click",()=>{sidebar.classList.remove("open");overlay.classList.remove("show")});
const savedUser=JSON.parse(localStorage.getItem("njangiDemoUser")||"null");if(savedUser){document.getElementById("userName").textContent=savedUser.name||"Njangi Admin";document.getElementById("userAvatar").textContent=getInitials(savedUser.name);}
loadMemberOptions();renderContributions();
