// =====================================================
// NJANGI TRACKER - DASHBOARD JAVASCRIPT
// =====================================================
// This dashboard currently uses demo data.
// Later, these arrays will be replaced by real database data.

// -----------------------------------------------------
// 1. DEMO DATA
// -----------------------------------------------------
const members = [
    { name: "John Mbida", initials: "JM", amount: 20000, status: "Paid", style: "" },
    { name: "Mary Asong", initials: "MA", amount: 20000, status: "Paid", style: "alt" },
    { name: "Peter Fom", initials: "PF", amount: 10000, status: "Partial", style: "blue" },
    { name: "Paul Nji", initials: "PN", amount: 0, status: "Pending", style: "" },
    { name: "Sarah Etta", initials: "SE", amount: 20000, status: "Paid", style: "alt" }
];

const contributions = [
    { name: "John Mbida", initials: "JM", amount: 20000, date: "30 Aug 2026, 10:30 AM" },
    { name: "Mary Asong", initials: "MA", amount: 20000, date: "29 Aug 2026, 4:15 PM" },
    { name: "Peter Fom", initials: "PF", amount: 10000, date: "29 Aug 2026, 1:20 PM" },
    { name: "Sarah Etta", initials: "SE", amount: 20000, date: "28 Aug 2026, 11:05 AM" }
];

const cycle = {
    target: 500000,
    collected: 350000
};

// -----------------------------------------------------
// 2. HELPER FUNCTIONS
// -----------------------------------------------------
function formatMoney(amount) {
    return new Intl.NumberFormat("en-US").format(amount) + " FCFA";
}

function getSavedUser() {
    const saved = localStorage.getItem("njangiDemoUser");

    if (!saved) return null;

    try {
        return JSON.parse(saved);
    } catch (error) {
        return null;
    }
}

function getInitials(name) {
    if (!name) return "NG";

    return name
        .trim()
        .split(/\s+/)
        .slice(0, 2)
        .map((word) => word[0].toUpperCase())
        .join("");
}

// -----------------------------------------------------
// 3. DISPLAY USER INFORMATION
// -----------------------------------------------------
const user = getSavedUser();
const displayName = user?.name || "Njangi Admin";
const firstName = displayName.split(" ")[0];

const userName = document.getElementById("userName");
const welcomeName = document.getElementById("welcomeName");
const userAvatar = document.getElementById("userAvatar");

userName.textContent = displayName;
welcomeName.textContent = firstName;
userAvatar.textContent = getInitials(displayName);

// -----------------------------------------------------
// 4. CALCULATE CURRENT CYCLE PROGRESS
// -----------------------------------------------------
const progress = Math.round((cycle.collected / cycle.target) * 100);
const remaining = Math.max(cycle.target - cycle.collected, 0);

document.getElementById("totalPool").textContent = formatMoney(cycle.collected);
document.getElementById("progressValue").textContent = progress + "%";
document.getElementById("collectedAmount").textContent = formatMoney(cycle.collected);
document.getElementById("remainingAmount").textContent = formatMoney(remaining) + " remaining";
document.getElementById("progressText").textContent = progress + "%";
document.getElementById("progressFill").style.width = progress + "%";

document.getElementById("totalMembers").textContent = members.length;

// -----------------------------------------------------
// 5. CREATE MEMBER STATUS LIST
// -----------------------------------------------------
const memberList = document.getElementById("memberList");

function renderMembers(list) {
    memberList.innerHTML = "";

    if (list.length === 0) {
        memberList.innerHTML = `<p class="empty-message">No members found.</p>`;
        return;
    }

    list.forEach((member) => {
        const row = document.createElement("div");
        row.className = "member-row";

        const statusClass = member.status.toLowerCase();

        row.innerHTML = `
            <span class="member-avatar ${member.style}">${member.initials}</span>
            <div>
                <strong>${member.name}</strong>
                <small>${formatMoney(member.amount)} contributed</small>
            </div>
            <span class="payment-status ${statusClass}">${member.status}</span>
        `;

        memberList.appendChild(row);
    });
}

renderMembers(members);

// -----------------------------------------------------
// 6. CREATE CONTRIBUTION TABLE
// -----------------------------------------------------
const contributionTable = document.getElementById("contributionTable");

contributions.forEach((payment) => {
    const row = document.createElement("tr");

    row.innerHTML = `
        <td><strong>${payment.name}</strong></td>
        <td class="amount">+${formatMoney(payment.amount)}</td>
        <td>${payment.date}</td>
        <td><span class="payment-status paid">Recorded</span></td>
    `;

    contributionTable.appendChild(row);
});

// -----------------------------------------------------
// 7. SEARCH MEMBERS
// -----------------------------------------------------
// As the user types, only matching members remain visible.
const memberSearch = document.getElementById("memberSearch");

memberSearch.addEventListener("input", () => {
    const searchTerm = memberSearch.value.toLowerCase().trim();

    const filteredMembers = members.filter((member) =>
        member.name.toLowerCase().includes(searchTerm)
    );

    renderMembers(filteredMembers);
});

// -----------------------------------------------------
// 8. MOBILE SIDEBAR
// -----------------------------------------------------
const mobileMenu = document.getElementById("mobileMenu");
const sidebar = document.getElementById("sidebar");
const sidebarOverlay = document.getElementById("sidebarOverlay");

function closeSidebar() {
    sidebar.classList.remove("open");
    sidebarOverlay.classList.remove("show");
}

mobileMenu.addEventListener("click", () => {
    sidebar.classList.toggle("open");
    sidebarOverlay.classList.toggle("show");
});

sidebarOverlay.addEventListener("click", closeSidebar);

// -----------------------------------------------------
// 9. QUICK CONTRIBUTION MODAL
// -----------------------------------------------------
const modal = document.getElementById("contributionModal");
const addContributionButton = document.getElementById("addContributionButton");
const closeModal = document.getElementById("closeModal");
const modalOk = document.getElementById("modalOk");

function openModal() {
    modal.classList.add("show");
    modal.setAttribute("aria-hidden", "false");
}

function hideModal() {
    modal.classList.remove("show");
    modal.setAttribute("aria-hidden", "true");
}

addContributionButton.addEventListener("click", openModal);
closeModal.addEventListener("click", hideModal);
modalOk.addEventListener("click", hideModal);

modal.addEventListener("click", (event) => {
    if (event.target === modal) hideModal();
});

// -----------------------------------------------------
// 10. LOGOUT
// -----------------------------------------------------
// This removes the demo login flag and returns to login.html.
const logoutButton = document.getElementById("logoutButton");

logoutButton.addEventListener("click", () => {
    localStorage.removeItem("njangiLoggedIn");
    window.location.href = "login.html";
});

// -----------------------------------------------------
// 11. PLACEHOLDER LINKS
// -----------------------------------------------------
// These pages do not exist yet. For now, we prevent the link
// from jumping around the page and show a small explanation.
const comingSoonLinks = document.querySelectorAll(".coming-soon");

comingSoonLinks.forEach((item) => {
    item.addEventListener("click", (event) => {
        if (item.tagName === "A" && item.getAttribute("href") === "#") {
            event.preventDefault();
        }

        // Do not show the message for the logout button.
        if (item.id === "logoutButton") return;

        if (item.id === "addContributionButton") return;

        if (item.classList.contains("coming-soon")) {
            event.preventDefault();
            alert("This section will be built next. We are creating Members, Cycles and Contributions step by step.");
        }
    });
});

// -----------------------------------------------------
// 12. SIMPLE LOGIN GUARD
// -----------------------------------------------------
// If the user has not completed the demo login, send them back.
// Comment this block out while testing the dashboard directly.
if (localStorage.getItem("njangiLoggedIn") !== "true") {
    // We allow direct dashboard testing during development.
    // When authentication is fully connected, redirect here:
    // window.location.href = "login.html";
}
