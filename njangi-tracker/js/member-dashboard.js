// =====================================================
// MEMBER DASHBOARD
// Shows only: active cycle, payment status, recent contributions,
// and loan request form. Loan requests share LOAN_KEY with admin loans page.
// =====================================================

const MEMBER_KEY = "njangiMembers";
const LOAN_KEY = "njangiLoans";
const MEMBER_SESSION_KEY = "njangiMemberSession";

function getSession() {
    try {
        return JSON.parse(localStorage.getItem(MEMBER_SESSION_KEY) || "null");
    } catch {
        return null;
    }
}

function getMembers() {
    return JSON.parse(localStorage.getItem(MEMBER_KEY) || "[]");
}

function getLoans() {
    return JSON.parse(localStorage.getItem(LOAN_KEY) || "[]");
}

function saveLoans(loans) {
    localStorage.setItem(LOAN_KEY, JSON.stringify(loans));
}

function money(value) {
    return new Intl.NumberFormat("en-US").format(Number(value) || 0) + " FCFA";
}

function safe(text) {
    const div = document.createElement("div");
    div.textContent = text == null ? "" : String(text);
    return div.innerHTML;
}

function cap(value) {
    if (!value) return "";
    return value.charAt(0).toUpperCase() + value.slice(1);
}

// Guard: must be logged in as member
const session = getSession();
if (!session || session.role !== "member") {
    window.location.href = "member-login.html";
}

// Header / welcome
document.getElementById("userName").textContent = session.name;
document.getElementById("welcomeName").textContent = session.name.split(" ")[0];
document.getElementById("userAvatar").textContent = session.initials || "M";
document.getElementById("statusAvatar").textContent = session.initials || "M";
document.getElementById("statusName").textContent = session.name;

const paid = Number(session.paid) || 0;
const expected = Number(session.expected) || 20000;
const statusLabel = session.status || (paid >= expected ? "Paid" : paid > 0 ? "Partial" : "Pending");

document.getElementById("paidAmount").textContent = money(paid);
document.getElementById("expectedAmount").textContent = money(expected);
document.getElementById("statusDetail").textContent =
    paid >= expected ? "You are up to date for this cycle." :
    paid > 0 ? "Partial payment recorded." : "Contribution still pending.";

const badge = document.getElementById("statusBadge");
badge.textContent = statusLabel;
badge.className = "payment-status " + statusLabel.toLowerCase();

// Demo cycle numbers (same as admin dashboard demo)
const cycle = { target: 500000, collected: 350000 };
const progress = Math.round((cycle.collected / cycle.target) * 100);
document.getElementById("collectedAmount").textContent = money(cycle.collected);
document.getElementById("remainingAmount").textContent = money(cycle.target - cycle.collected) + " remaining";
document.getElementById("progressText").textContent = progress + "%";
document.getElementById("progressFill").style.width = progress + "%";

// Recent contributions — demo list filtered to show group activity (member view)
const demoContributions = [
    { name: "John Mbida", amount: 20000, date: "30 Aug 2026", status: "Paid" },
    { name: "Mary Asong", amount: 20000, date: "29 Aug 2026", status: "Paid" },
    { name: "Peter Fom", amount: 10000, date: "29 Aug 2026", status: "Partial" },
    { name: "Sarah Etta", amount: 20000, date: "28 Aug 2026", status: "Paid" },
    { name: session.name, amount: paid, date: "This cycle", status: statusLabel }
];

const tableBody = document.getElementById("contributionTable");
const unique = [];
const seen = new Set();
demoContributions.forEach((row) => {
    const key = row.name + row.date;
    if (seen.has(key)) return;
    seen.add(key);
    unique.push(row);
});

tableBody.innerHTML = unique
    .slice(0, 6)
    .map(
        (row) => `
    <tr>
      <td><strong>${safe(row.name)}</strong></td>
      <td class="amount">${money(row.amount)}</td>
      <td>${safe(row.date)}</td>
      <td><span class="payment-status ${String(row.status).toLowerCase()}">${safe(row.status)}</span></td>
    </tr>`
    )
    .join("");

// My loans (only this member's requests — same store as admin Emergency Loans)
function renderMyLoans() {
    const loans = getLoans().filter((l) => l.memberId === session.id || l.memberName === session.name);
    const tbody = document.getElementById("myLoansTable");
    const empty = document.getElementById("loansEmpty");

    tbody.innerHTML = "";
    if (!loans.length) {
        empty.style.display = "block";
        return;
    }
    empty.style.display = "none";

    loans.forEach((loan) => {
        const balance = Math.max(Number(loan.requestedAmount) - Number(loan.paidAmount || 0), 0);
        const tr = document.createElement("tr");
        tr.innerHTML = `
      <td class="amount">${money(loan.requestedAmount)}</td>
      <td>${safe(loan.reason)}</td>
      <td>${safe(loan.requestedAt || "-")}</td>
      <td>${money(balance)}</td>
      <td><span class="status ${loan.status}">${cap(loan.status)}</span></td>`;
        tbody.appendChild(tr);
    });
}

// Submit loan → same shape as admin loans page expects
document.getElementById("memberLoanForm").addEventListener("submit", (event) => {
    event.preventDefault();
    const amountInput = document.getElementById("loanAmount");
    const reasonInput = document.getElementById("loanReason");
    const message = document.getElementById("loanMessage");

    const amount = Number(amountInput.value);
    const reason = reasonInput.value.trim();

    message.textContent = "";
    message.className = "form-message";

    if (!amount || amount < 1 || !reason) {
        message.textContent = "Enter a valid amount and reason.";
        message.classList.add("error");
        return;
    }

    const loans = getLoans();
    loans.unshift({
        id: Date.now().toString(),
        memberId: session.id,
        memberName: session.name,
        requestedAmount: amount,
        paidAmount: 0,
        reason,
        status: "pending",
        requestedAt: new Date().toISOString().split("T")[0],
        approvedAt: null
    });
    saveLoans(loans);

    amountInput.value = "";
    reasonInput.value = "";
    message.textContent = "Request submitted. An admin will review it on the Emergency Loans page.";
    message.classList.add("success");
    renderMyLoans();
});

renderMyLoans();

// Mobile menu
const menuBtn = document.getElementById("menuBtn");
const sidebar = document.getElementById("sidebar");
const overlay = document.getElementById("overlay");
menuBtn.addEventListener("click", () => {
    sidebar.classList.toggle("open");
    overlay.classList.toggle("show");
});
overlay.addEventListener("click", () => {
    sidebar.classList.remove("open");
    overlay.classList.remove("show");
});

// Logout
document.getElementById("logoutBtn").addEventListener("click", () => {
    localStorage.removeItem(MEMBER_SESSION_KEY);
    localStorage.removeItem("njangiLoggedIn");
    window.location.href = "member-login.html";
});
