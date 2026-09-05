// =====================================================
// HISTORY PAGE
// This page reads contribution data already saved by contributions.js.
// =====================================================
const MEMBER_KEY = "njangiMembers";
const CONTRIBUTION_KEY = "njangiContributions";
const CYCLE_KEY = "njangiCycles";

function getMembers() { return JSON.parse(localStorage.getItem(MEMBER_KEY)) || []; }
function getContributions() { return JSON.parse(localStorage.getItem(CONTRIBUTION_KEY)) || []; }
function getCycles() { return JSON.parse(localStorage.getItem(CYCLE_KEY)) || []; }
function money(n) { return new Intl.NumberFormat("en-US").format(Number(n) || 0) + " FCFA"; }
function dateText(d) { return d ? new Date(d + "T00:00:00").toLocaleDateString("en-GB") : "—"; }
function safe(text) { const div = document.createElement("div"); div.textContent = text; return div.innerHTML; }

const search = document.getElementById("historySearch");
const memberFilter = document.getElementById("memberFilter");
const dateFilter = document.getElementById("dateFilter");
const body = document.getElementById("historyBody");
const empty = document.getElementById("emptyHistory");

// Fill the member filter with names from the Members page.
function loadMembers() {
  memberFilter.innerHTML = '<option value="">All members</option>';
  getMembers().forEach(member => {
    const option = document.createElement("option");
    option.value = member.id;
    option.textContent = member.name;
    memberFilter.appendChild(option);
  });
}

// Show the contribution history using the selected filters.
function renderHistory() {
  const contributions = getContributions();
  const searchText = search.value.toLowerCase().trim();
  const selectedMember = memberFilter.value;
  const selectedDate = dateFilter.value;

  const filtered = contributions.filter(item => {
    const matchesSearch = item.memberName.toLowerCase().includes(searchText);
    const matchesMember = !selectedMember || item.memberId === selectedMember;
    const matchesDate = !selectedDate || item.date === selectedDate;
    return matchesSearch && matchesMember && matchesDate;
  });

  body.innerHTML = "";
  empty.style.display = filtered.length ? "none" : "flex";

  filtered.forEach(item => {
    const row = document.createElement("tr");
    row.innerHTML = `<td><strong>${safe(item.memberName)}</strong></td><td class="amount">${money(item.amount)}</td><td>${dateText(item.date)}</td><td>Current Cycle</td><td><span class="type-badge">Contribution</span></td>`;
    body.appendChild(row);
  });

  // Update summary using all records, not only the filtered records.
  const total = contributions.reduce((sum, item) => sum + Number(item.amount || 0), 0);
  const uniqueMembers = new Set(contributions.map(item => item.memberId));
  document.getElementById("historyTotal").textContent = money(total);
  document.getElementById("historyCount").textContent = contributions.length;
  document.getElementById("historyMembers").textContent = uniqueMembers.size;
  document.getElementById("historyCycles").textContent = getCycles().length;
}

search.addEventListener("input", renderHistory);
memberFilter.addEventListener("change", renderHistory);
dateFilter.addEventListener("change", renderHistory);

document.getElementById("resetFilter").onclick = () => {
  search.value = "";
  memberFilter.value = "";
  dateFilter.value = "";
  renderHistory();
};

// Clear all contribution records and reset members' paid totals.
document.getElementById("clearHistory").onclick = () => {
  if (!getContributions().length) return;
  if (!confirm("Clear all contribution history?")) return;
  localStorage.removeItem(CONTRIBUTION_KEY);
  const resetMembers = getMembers().map(member => ({...member, paid: 0}));
  localStorage.setItem(MEMBER_KEY, JSON.stringify(resetMembers));
  renderHistory();
};

// Mobile sidebar.
const sidebar = document.getElementById("sidebar");
const overlay = document.getElementById("sidebarOverlay");
document.getElementById("mobileMenu").onclick = () => { sidebar.classList.toggle("open"); overlay.classList.toggle("show"); };
overlay.onclick = () => { sidebar.classList.remove("open"); overlay.classList.remove("show"); };
document.getElementById("logoutButton").onclick = () => window.location.href = "login.html";

loadMembers();
renderHistory();
