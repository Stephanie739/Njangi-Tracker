// =====================================================
// CONTRIBUTIONS PAGE
// A contribution is saved separately and also updates the
// member's paid amount. This keeps both pages connected.
// =====================================================
const MEMBER_KEY="njangiMembers",CONTRIB_KEY="njangiContributions";
const getMembers=()=>JSON.parse(localStorage.getItem(MEMBER_KEY))||[];
const getContribs=()=>JSON.parse(localStorage.getItem(CONTRIB_KEY))||[];
const saveContribs=x=>localStorage.setItem(CONTRIB_KEY,JSON.stringify(x));
const $=id=>document.getElementById(id);
function money(n){return new Intl.NumberFormat("en-US").format(n)+" FCFA";}
function safe(t){const d=document.createElement("div");d.textContent=t;return d.innerHTML;}
function loadMembers(){const s=$("memberSelect");s.innerHTML="";const ms=getMembers();if(!ms.length){s.innerHTML='<option value="">No members available</option>';return;}ms.forEach(m=>{const o=document.createElement("option");o.value=m.id;o.textContent=m.name;s.appendChild(o);});}
function render(){const data=getContribs();$("contributionTable").innerHTML="";const total=data.reduce((a,x)=>a+Number(x.amount),0);$("totalCollected").textContent=money(total);$("paymentCount").textContent=data.length;$("contributors").textContent=new Set(data.map(x=>x.memberId)).size;$("emptyState").style.display=data.length?"none":"block";data.forEach(x=>{const tr=document.createElement("tr");tr.innerHTML=`<td><strong>${safe(x.memberName)}</strong></td><td class="amount">${money(x.amount)}</td><td>${safe(x.date)}</td><td><button class="delete-action" onclick="deleteContribution('${x.id}')">Delete</button></td>`;$("contributionTable").appendChild(tr);});}
$("dateInput").value=new Date().toISOString().split("T")[0];
$("contributionForm").onsubmit=e=>{e.preventDefault();const id=$("memberSelect").value,amount=Number($("amountInput").value),date=$("dateInput").value,ms=getMembers(),m=ms.find(x=>x.id===id);if(!m||amount<=0||!date)return alert("Please complete all fields.");const data=getContribs();data.unshift({id:Date.now().toString(),memberId:id,memberName:m.name,amount,date});saveContribs(data);localStorage.setItem(MEMBER_KEY,JSON.stringify(ms.map(x=>x.id===id?{...x,paid:Number(x.paid||0)+amount}:x)));$("amountInput").value="";render();alert("Contribution recorded successfully!");};
window.deleteContribution=id=>{const data=getContribs(),x=data.find(c=>c.id===id);if(!x||!confirm("Delete this contribution?"))return;saveContribs(data.filter(c=>c.id!==id));const ms=getMembers();localStorage.setItem(MEMBER_KEY,JSON.stringify(ms.map(m=>m.id===x.memberId?{...m,paid:Math.max(Number(m.paid||0)-Number(x.amount),0)}:m)));render();};
$("clearHistory").onclick=()=>{if(!getContribs().length)return;if(!confirm("Clear all contribution history?"))return;localStorage.removeItem(CONTRIB_KEY);localStorage.setItem(MEMBER_KEY,JSON.stringify(getMembers().map(m=>({...m,paid:0}))));render();};
$("mobileMenu").onclick=()=>{$("sidebar").classList.toggle("open");$("sidebarOverlay").classList.toggle("show");};$("sidebarOverlay").onclick=()=>{$("sidebar").classList.remove("open");$("sidebarOverlay").classList.remove("show");};$("logoutButton").onclick=()=>location.href="login.html";loadMembers();render();