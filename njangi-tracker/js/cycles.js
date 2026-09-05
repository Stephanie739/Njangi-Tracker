// =====================================================
// CYCLES PAGE
// Simple localStorage version for learning.
// =====================================================
const CYCLE_KEY = "njangiCycles";
const MEMBER_KEY = "njangiMembers";
const CONTRIBUTION_KEY = "njangiContributions";

function getCycles() { return JSON.parse(localStorage.getItem(CYCLE_KEY)) || []; }
function saveCycles(cycles) { localStorage.setItem(CYCLE_KEY, JSON.stringify(cycles)); }
function getMembers() { return JSON.parse(localStorage.getItem(MEMBER_KEY)) || []; }
function getContributions() { return JSON.parse(localStorage.getItem(CONTRIBUTION_KEY)) || []; }
function money(n) { return new Intl.NumberFormat("en-US").format(Number(n) || 0) + " FCFA"; }
function dateText(d) { return d ? new Date(d + "T00:00:00").toLocaleDateString("en-GB") : "—"; }

const modal = document.getElementById("cycleModal");
const form = document.getElementById("cycleForm");
const tableBody = document.getElementById("cycleTableBody");
const emptyCycles = document.getElementById("emptyCycles");

// Open/close the create cycle form.
document.getElementById("openCycleModal").onclick = () => {
  form.reset();
  document.getElementById("cycleStart").value = new Date().toISOString().split("T")[0];
  modal.classList.add("show");
};
document.getElementById("closeCycleModal").onclick = () => modal.classList.remove("show");
modal.addEventListener("click", e => { if (e.target === modal) modal.classList.remove("show"); });

// Create a new cycle.
form.addEventListener("submit", e => {
  e.preventDefault();
  const cycles = getCycles();
  const newCycle = {
    id: Date.now().toString(),
    name: document.getElementById("cycleName").value.trim(),
    target: Number(document.getElementById("cycleTarget").value),
    start: document.getElementById("cycleStart").value,
    end: document.getElementById("cycleEnd").value,
    status: "Active"
  };

  if (newCycle.end < newCycle.start) { alert("End date cannot be before the start date."); return; }
  // Only one cycle is active in this simple version.
  const updated = cycles.map(cycle => ({...cycle, status: "Finished"}));
  updated.unshift(newCycle);
  saveCycles(updated);
  modal.classList.remove("show");
  render();
});

function render() {
  let cycles = getCycles();

  // If no cycle exists yet, create the same demo cycle shown on the dashboard.
  if (!cycles.length) {
    cycles = [{id:"demo-05", name:"Cycle #05", target:500000, start:"2026-08-01", end:"2026-08-31", status:"Active"}];
    saveCycles(cycles);
  }

  const active = cycles.find(c => c.status === "Active") || cycles[0];
  const members = getMembers();
  const contributions = getContributions();

  // Contributions are summed from the existing contribution page data.
  const collected = contributions.reduce((sum, item) => sum + Number(item.amount || 0), 0);
  const progress = active.target ? Math.min((collected / active.target) * 100, 100) : 0;
  const remaining = Math.max(active.target - collected, 0);
  const paidIds = new Set(contributions.map(item => item.memberId));

  document.getElementById("activeCycleName").textContent = active.name;
  document.getElementById("activeTarget").textContent = money(active.target);
  document.getElementById("activeStatus").textContent = active.status;
  document.getElementById("cycleCount").textContent = cycles.length;
  document.getElementById("activeTitle").textContent = active.name;
  document.getElementById("collectedAmount").textContent = money(collected);
  document.getElementById("targetAmount").textContent = money(active.target);
  document.getElementById("progressFill").style.width = progress + "%";
  document.getElementById("progressText").textContent = Math.round(progress) + "%";
  document.getElementById("remainingAmount").textContent = money(remaining) + " remaining";
  document.getElementById("startDate").textContent = dateText(active.start);
  document.getElementById("endDate").textContent = dateText(active.end);
  document.getElementById("membersPaid").textContent = paidIds.size + " / " + members.length;
  document.getElementById("cycleState").textContent = active.status;

  tableBody.innerHTML = "";
  emptyCycles.style.display = cycles.length ? "none" : "flex";
  cycles.forEach(cycle => {
    const row = document.createElement("tr");
    row.innerHTML = `<td><strong>${safe(cycle.name)}</strong></td><td>${dateText(cycle.start)}</td><td>${dateText(cycle.end)}</td><td class="amount">${money(cycle.target)}</td><td><span class="payment-status ${cycle.status === "Active" ? "paid" : "pending"}">${cycle.status}</span></td><td><button class="table-action" onclick="finishCycle('${cycle.id}')">${cycle.status === "Active" ? "Finish" : "Done"}</button></td>`;
    tableBody.appendChild(row);
  });
}

// Finish an active cycle.
function finishCycle(id) {
  const cycles = getCycles();
  const cycle = cycles.find(c => c.id === id);
  if (!cycle || cycle.status !== "Active") return;
  if (!confirm(`Finish ${cycle.name}?`)) return;
  saveCycles(cycles.map(c => c.id === id ? {...c, status:"Finished"} : c));
  render();
}

function safe(text) { const div = document.createElement("div"); div.textContent = text; return div.innerHTML; }

// Mobile sidebar.
const sidebar = document.getElementById("sidebar");
const overlay = document.getElementById("sidebarOverlay");
document.getElementById("mobileMenu").onclick = () => { sidebar.classList.toggle("open"); overlay.classList.toggle("show"); };
overlay.onclick = () => { sidebar.classList.remove("open"); overlay.classList.remove("show"); };
document.getElementById("logoutButton").onclick = () => window.location.href = "login.html";

render();
