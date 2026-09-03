// =====================================================
// MEMBERS PAGE
// =====================================================

const memberTable = document.getElementById("memberTable");
const memberModal = document.getElementById("memberModal");
const memberForm = document.getElementById("memberForm");
const searchMember = document.getElementById("searchMember");
const searchMemberTop = document.getElementById("memberSearchTop");
const statusFilter = document.getElementById("statusFilter");
const enrollmentFilter = document.getElementById("enrollmentFilter");

function paymentStatus(member) {
  const expected = Number(member.expected || 0);
  const paid = Number(member.paid || 0);
  if (expected > 0 && paid >= expected) return ["Paid", "paid"];
  if (paid > 0) return ["Partial", "partial"];
  return ["Pending", "pending"];
}

// A simple reliability score: paid on time records / total records.
function reliabilityScore(member) {
  const payments = getContributions().filter(p => p.memberId === member.id);
  if (!payments.length) return 0;
  const paid = payments.filter(p => Number(p.amount) >= Number(member.expected || 0)).length;
  return Math.round((paid / payments.length) * 100);
}

function renderMembers() {
  const members = getMembers().sort((a,b) => Number(a.rotationPosition)-Number(b.rotationPosition));
  const text = searchMember.value.toLowerCase().trim();
  const status = statusFilter.value;
  const enrollment = enrollmentFilter.value;

  const filtered = members.filter(member => {
    const [label] = paymentStatus(member);
    const matchesText = member.name.toLowerCase().includes(text) || member.phone.toLowerCase().includes(text);
    const matchesStatus = status === "all" || label.toLowerCase() === status;
    const matchesEnrollment = enrollment === "all" || (enrollment === "enrolled" ? member.enrolled : !member.enrolled);
    return matchesText && matchesStatus && matchesEnrollment;
  });

  memberTable.innerHTML = "";
  filtered.forEach(member => {
    const [label, className] = paymentStatus(member);
    const paid = Number(member.paid || 0);
    const balance = Math.max(Number(member.expected || 0) - paid, 0);
    const score = reliabilityScore(member);
    const scoreClass = score >= 75 ? "good" : score >= 40 ? "medium" : "low";

    const row = document.createElement("tr");
    row.innerHTML = `
      <td><span class="position-number">#${Number(member.rotationPosition) || "-"}</span></td>
      <td><div class="member-cell"><span class="member-mini-avatar">${getInitials(member.name)}</span><div><strong>${escapeHTML(member.name)}</strong><small>${member.enrolled ? "Enrolled" : "Not enrolled"}</small></div></div></td>
      <td>${escapeHTML(member.phone)}</td><td>${formatMoney(member.expected)}</td><td>${formatMoney(paid)}</td><td>${formatMoney(balance)}</td>
      <td><span class="status ${className}">${label}</span></td>
      <td><span class="reliability ${scoreClass}">${score}%</span></td>
      <td><div class="row-actions"><button class="table-action edit" onclick="editMember('${member.id}')">Edit</button><button class="table-action delete" onclick="deleteMember('${member.id}')">Delete</button></div></td>`;
    memberTable.appendChild(row);
  });

  updateSummary(members);
}

function updateSummary(members) {
  const fullyPaid = members.filter(m => paymentStatus(m)[0] === "Paid").length;
  const outstanding = members.filter(m => paymentStatus(m)[0] !== "Paid").length;
  const expected = members.reduce((sum,m) => sum + Number(m.expected || 0),0);
  const enrolled = members.filter(m => m.enrolled).length;
  document.getElementById("totalMembers").textContent = members.length;
  document.getElementById("fullyPaid").textContent = fullyPaid;
  document.getElementById("outstandingCount").textContent = outstanding;
  document.getElementById("totalExpected").textContent = formatMoney(expected);
  document.getElementById("enrollmentSummary").textContent = `${enrolled} enrolled`;
  const cycle = getActiveCycle();
  document.getElementById("sideCycle").textContent = cycle ? `Cycle #${cycle.number}` : "No active cycle";
}

function openMemberModal(member = null) {
  document.getElementById("modalTitle").textContent = member ? "Edit Member" : "Add Member";
  document.getElementById("memberId").value = member?.id || "";
  document.getElementById("memberName").value = member?.name || "";
  document.getElementById("memberPhone").value = member?.phone || "";
  document.getElementById("memberExpected").value = member?.expected ?? "";
  document.getElementById("memberPosition").value = member?.rotationPosition ?? (getMembers().length + 1);
  document.getElementById("memberEnrolled").checked = member?.enrolled ?? true;
  memberModal.classList.add("show"); memberModal.setAttribute("aria-hidden","false");
}
function closeMemberModal(){memberModal.classList.remove("show");memberModal.setAttribute("aria-hidden","true");memberForm.reset();}

document.getElementById("openMemberModal").addEventListener("click",()=>openMemberModal());
document.getElementById("closeMemberModal").addEventListener("click",closeMemberModal);
document.getElementById("cancelMember").addEventListener("click",closeMemberModal);
memberModal.addEventListener("click",e=>{if(e.target===memberModal)closeMemberModal();});

memberForm.addEventListener("submit",e=>{
  e.preventDefault();
  const id=document.getElementById("memberId").value;
  const data={
    id:id||Date.now().toString(),
    name:document.getElementById("memberName").value.trim(),
    phone:document.getElementById("memberPhone").value.trim(),
    expected:Number(document.getElementById("memberExpected").value),
    rotationPosition:Number(document.getElementById("memberPosition").value),
    enrolled:document.getElementById("memberEnrolled").checked,
    paid:0
  };
  if(!data.name||!data.phone||data.expected<0||data.rotationPosition<1){alert("Please enter valid member information.");return;}
  const members=getMembers();
  if(id){const old=members.find(m=>m.id===id);data.paid=old?.paid||0;saveMembers(members.map(m=>m.id===id?data:m));}
  else{saveMembers([...members,data]);}
  closeMemberModal();renderMembers();
});

window.editMember=id=>{const member=getMembers().find(m=>m.id===id);if(member)openMemberModal(member);};
window.deleteMember=id=>{
  const member=getMembers().find(m=>m.id===id); if(!member)return;
  if(!confirm(`Delete ${member.name}?`))return;
  saveMembers(getMembers().filter(m=>m.id!==id));
  saveContributions(getContributions().filter(p=>p.memberId!==id));
  renderMembers();
};

function connectSearch(input){input.addEventListener("input",()=>{searchMember.value=input.value;searchMemberTop.value=input.value;renderMembers();});}
connectSearch(searchMember);connectSearch(searchMemberTop);
statusFilter.addEventListener("change",renderMembers);enrollmentFilter.addEventListener("change",renderMembers);

document.getElementById("logoutButton").addEventListener("click",()=>{localStorage.removeItem(DB_KEYS.loggedIn);location.href="login.html";});

// Mobile sidebar
const mobileMenu=document.getElementById("mobileMenu"),sidebar=document.getElementById("sidebar"),overlay=document.getElementById("sidebarOverlay");
mobileMenu.addEventListener("click",()=>{sidebar.classList.toggle("open");overlay.classList.toggle("show");});
overlay.addEventListener("click",()=>{sidebar.classList.remove("open");overlay.classList.remove("show");});

// Display saved user.
const savedUser=JSON.parse(localStorage.getItem("njangiDemoUser")||"null");
if(savedUser){document.getElementById("userName").textContent=savedUser.name||"Njangi Admin";document.getElementById("userAvatar").textContent=getInitials(savedUser.name);}
renderMembers();
