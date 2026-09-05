// =====================================================
// MEMBERS PAGE
// Uses localStorage as our simple browser database.
// =====================================================
const KEY="njangiMembers";
const getMembers=()=>JSON.parse(localStorage.getItem(KEY))||[];
const saveMembers=data=>localStorage.setItem(KEY,JSON.stringify(data));
const $=id=>document.getElementById(id);

function money(n){return new Intl.NumberFormat("en-US").format(n)+" FCFA";}
function safe(text){const d=document.createElement("div");d.textContent=text;return d.innerHTML;}
function initials(name){return name.split(" ").map(x=>x[0]).slice(0,2).join("").toUpperCase();}

function render(){
 const all=getMembers(), q=$("memberSearch").value.toLowerCase().trim();
 const list=all.filter(m=>m.name.toLowerCase().includes(q)||m.phone.toLowerCase().includes(q));
 let paid=0,pending=0,expected=0;
 all.forEach(m=>{expected+=Number(m.expected||0);if(Number(m.paid||0)>=Number(m.expected||0)&&Number(m.expected||0)>0)paid++;else pending++;});
 $("totalMembers").textContent=all.length;$("paidMembers").textContent=paid;$("pendingMembers").textContent=pending;$("expectedTotal").textContent=money(expected);$("memberCountLabel").textContent=all.length+" Members";
 $("memberTable").innerHTML="";$("emptyState").style.display=list.length?"none":"block";
 list.forEach(m=>{const p=Number(m.paid||0),b=Math.max(Number(m.expected||0)-p,0);let status="Pending",cls="pending";if(p>=Number(m.expected)&&Number(m.expected)>0){status="Paid";cls="paid"}else if(p>0){status="Partial";cls="partial"}
 const tr=document.createElement("tr");tr.innerHTML=`<td><div class="member-main"><span class="mini-avatar">${initials(safe(m.name))}</span><strong>${safe(m.name)}</strong></div></td><td>${safe(m.phone)}</td><td>${money(Number(m.expected))}</td><td class="amount">${money(p)}</td><td class="balance">${money(b)}</td><td><span class="payment-status ${cls}">${status}</span></td><td><div class="member-actions"><button class="small-action edit-action" onclick="editMember('${m.id}')">Edit</button><button class="small-action delete-action" onclick="deleteMember('${m.id}')">Delete</button></div></td>`;$("memberTable").appendChild(tr);});
}
function openForm(){$("modalTitle").textContent="Add Member";$("memberForm").reset();$("memberId").value="";$("memberModal").classList.add("show");}
function closeForm(){$("memberModal").classList.remove("show");}
$("openAddMember").onclick=openForm;$("closeModal").onclick=closeForm;$("cancelModal").onclick=closeForm;$("memberModal").onclick=e=>{if(e.target.id==="memberModal")closeForm();};
$("memberForm").onsubmit=e=>{e.preventDefault();let data=getMembers(),id=$("memberId").value,name=$("memberName").value.trim(),phone=$("memberPhone").value.trim(),expected=Number($("expectedAmount").value);if(!name||!phone||expected<0)return alert("Please complete the form correctly.");if(id)data=data.map(m=>m.id===id?{...m,name,phone,expected}:m);else data.push({id:Date.now().toString(),name,phone,expected,paid:0});saveMembers(data);closeForm();render();};
window.editMember=id=>{const m=getMembers().find(x=>x.id===id);if(!m)return;$("modalTitle").textContent="Edit Member";$("memberId").value=m.id;$("memberName").value=m.name;$("memberPhone").value=m.phone;$("expectedAmount").value=m.expected;$("memberModal").classList.add("show");};
window.deleteMember=id=>{const data=getMembers(),m=data.find(x=>x.id===id);if(m&&confirm("Delete "+m.name+"?")){saveMembers(data.filter(x=>x.id!==id));render();}};
$("memberSearch").oninput=render;
$("mobileMenu").onclick=()=>{$("sidebar").classList.toggle("open");$("sidebarOverlay").classList.toggle("show");};$("sidebarOverlay").onclick=()=>{$("sidebar").classList.remove("open");$("sidebarOverlay").classList.remove("show");};$("logoutButton").onclick=()=>location.href="login.html";
render();