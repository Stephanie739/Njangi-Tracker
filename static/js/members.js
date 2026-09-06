// =====================================================
// MEMBERS PAGE - Integrated with Flask API
// =====================================================

const memberTable = document.getElementById("memberTable");
const memberModal = document.getElementById("memberModal");
const memberForm = document.getElementById("memberForm");
const searchMember = document.getElementById("searchMember");
const searchMemberTop = document.getElementById("memberSearchTop");
const statusFilter = document.getElementById("statusFilter");
const enrollmentFilter = document.getElementById("enrollmentFilter");

let currentMembers = [];
let activeGroupName = "Njangi Group";

function escapeHTML(str) {
  if (!str) return "";
  return String(str).replace(/[&<>'"]/g, tag => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;'
  }[tag] || tag));
}

function getInitials(name) {
  if (!name) return "??";
  return name.split(" ").map(n => n[0]).join("").toUpperCase().slice(0, 2);
}

function formatMoney(amount) {
  return Number(amount || 0).toLocaleString() + " FCFA";
}

function paymentStatus(member) {
  const expected = Number(member.expected || 0);
  const paid = Number(member.paid || 0);
  if (expected > 0 && paid >= expected) return ["Paid", "paid"];
  if (paid > 0) return ["Partial", "partial"];
  return ["Pending", "pending"];
}

// Fetch members from the Flask backend
async function fetchMembers() {
  try {
    const res = await fetch(`/api/members?group=${encodeURIComponent(activeGroupName)}`);
    if (!res.ok) throw new Error("Could not retrieve members");
    currentMembers = await res.json();
    renderMembers();
  } catch (err) {
    console.error("Fetch error:", err);
  }
}

function renderMembers() {
  const members = [...currentMembers].sort((a, b) => Number(a.rotationPosition) - Number(b.rotationPosition));
  const text = searchMember.value.toLowerCase().trim();
  const status = statusFilter.value;
  const enrollment = enrollmentFilter.value;

  const filtered = members.filter(member => {
    const [label] = paymentStatus(member);
    const matchesText = member.name.toLowerCase().includes(text) || (member.phone && member.phone.toLowerCase().includes(text));
    const matchesStatus = status === "all" || label.toLowerCase() === status;
    const matchesEnrollment = enrollment === "all" || (enrollment === "enrolled" ? member.enrolled : !member.enrolled);
    return matchesText && matchesStatus && matchesEnrollment;
  });

  memberTable.innerHTML = "";
  filtered.forEach(member => {
    const [label, className] = paymentStatus(member);
    const paid = Number(member.paid || 0);
    const balance = Math.max(Number(member.expected || 0) - paid, 0);

    const row = document.createElement("tr");
    row.innerHTML = `
      <td><span class="position-number">#${Number(member.rotationPosition) || "-"}</span></td>
      <td>
        <div class="member-cell">
          <span class="member-mini-avatar">${getInitials(member.name)}</span>
          <div>
            <strong>${escapeHTML(member.name)}</strong>
            <small>${member.enrolled ? "Enrolled" : "Not enrolled"}</small>
          </div>
        </div>
      </td>
      <td>${escapeHTML(member.phone)}</td>
      <td>${formatMoney(member.expected)}</td>
      <td>${formatMoney(paid)}</td>
      <td>${formatMoney(balance)}</td>
      <td><span class="status ${className}">${label}</span></td>
      <td><span class="reliability good">100%</span></td>
      <td>
        <div class="row-actions">
          <button class="table-action edit" onclick="editMember('${member.id}')">Edit</button>
        </div>
      </td>`;
    memberTable.appendChild(row);
  });

  updateSummary(members);
}

function updateSummary(members) {
  const fullyPaid = members.filter(m => paymentStatus(m)[0] === "Paid").length;
  const outstanding = members.filter(m => paymentStatus(m)[0] !== "Paid").length;
  const expected = members.reduce((sum, m) => sum + Number(m.expected || 0), 0);
  const enrolled = members.filter(m => m.enrolled).length;

  document.getElementById("totalMembers").textContent = members.length;
  document.getElementById("fullyPaid").textContent = fullyPaid;
  document.getElementById("outstandingCount").textContent = outstanding;
  document.getElementById("totalExpected").textContent = formatMoney(expected);
  document.getElementById("enrollmentSummary").textContent = `${enrolled} enrolled`;
}

function openMemberModal(member = null) {
  document.getElementById("modalTitle").textContent = member ? "Edit Member" : "Add Member";
  document.getElementById("memberId").value = member?.id || "";
  document.getElementById("memberName").value = member?.name || "";
  document.getElementById("memberPhone").value = member?.phone || "";
  document.getElementById("memberExpected").value = member?.expected ?? "10000";
  document.getElementById("memberPosition").value = member?.rotationPosition ?? (currentMembers.length + 1);
  document.getElementById("memberEnrolled").checked = member?.enrolled ?? true;

  memberModal.classList.add("show");
  memberModal.setAttribute("aria-hidden", "false");
}

function closeMemberModal() {
  memberModal.classList.remove("show");
  memberModal.setAttribute("aria-hidden", "true");
  memberForm.reset();
}

document.getElementById("openMemberModal").addEventListener("click", () => openMemberModal());
document.getElementById("closeMemberModal").addEventListener("click", closeMemberModal);
document.getElementById("cancelMember").addEventListener("click", closeMemberModal);
memberModal.addEventListener("click", e => { if (e.target === memberModal) closeMemberModal(); });

// POST to Flask Add Member route
memberForm.addEventListener("submit", async e => {
  e.preventDefault();

  const payload = {
    group: activeGroupName,
    name: document.getElementById("memberName").value.trim(),
    phone: document.getElementById("memberPhone").value.trim()
  };

  if (!payload.name || !payload.phone) {
    alert("Please enter a valid name and phone number.");
    return;
  }

  try {
    const res = await fetch("/api/members", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    if (!res.ok) {
      const err = await res.json();
      alert(err.error || "Failed to add member.");
      return;
    }

    closeMemberModal();
    await fetchMembers();
  } catch (err) {
    console.error("Submission failed:", err);
    alert("Error communicating with server.");
  }
});

function connectSearch(input) {
  input.addEventListener("input", () => {
    searchMember.value = input.value;
    searchMemberTop.value = input.value;
    renderMembers();
  });
}
connectSearch(searchMember);
connectSearch(searchMemberTop);

statusFilter.addEventListener("change", renderMembers);
enrollmentFilter.addEventListener("change", renderMembers);

// Mobile Sidebar
const mobileMenu = document.getElementById("mobileMenu");
const sidebar = document.getElementById("sidebar");
const overlay = document.getElementById("sidebarOverlay");
if (mobileMenu && sidebar && overlay) {
  mobileMenu.addEventListener("click", () => {
    sidebar.classList.toggle("open");
    overlay.classList.toggle("show");
  });
  overlay.addEventListener("click", () => {
    sidebar.classList.remove("open");
    overlay.classList.remove("show");
  });
}

// Initial load
fetchMembers();