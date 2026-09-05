// 

// MEMBER LOGIN
// Demo: members from localStorage (njangiMembers) or seed data.
// Password for all demo members: member123

// 

const MEMBER_KEY = "njangiMembers";
const MEMBER_SESSION_KEY = "njangiMemberSession";
const DEMO_PASSWORD = "member123";

const DEMO_MEMBERS = [
    { id: "m1", name: "John Mbida", email: "john@example.com", paid: 20000, expected: 20000, status: "Paid" },
    { id: "m2", name: "Mary Asong", email: "mary@example.com", paid: 20000, expected: 20000, status: "Paid" },
    { id: "m3", name: "Peter Fom", email: "peter@example.com", paid: 10000, expected: 20000, status: "Partial" },
    { id: "m4", name: "Paul Nji", email: "paul@example.com", paid: 0, expected: 20000, status: "Pending" },
    { id: "m5", name: "Sarah Etta", email: "sarah@example.com", paid: 20000, expected: 20000, status: "Paid" }
];

function getMembers() {
    const stored = JSON.parse(localStorage.getItem(MEMBER_KEY) || "null");
    if (stored && stored.length) return stored;
    localStorage.setItem(MEMBER_KEY, JSON.stringify(DEMO_MEMBERS));
    return DEMO_MEMBERS;
}

function getInitials(name) {
    if (!name) return "M";
    return name.trim().split(/\s+/).slice(0, 2).map((w) => w[0].toUpperCase()).join("");
}

// Password toggle
document.querySelectorAll(".password-toggle").forEach((button) => {
    button.addEventListener("click", () => {
        const input = document.getElementById(button.dataset.target);
        if (!input) return;
        const show = input.type === "password";
        input.type = show ? "text" : "password";
        button.textContent = show ? "Hide" : "Show";
    });
});

// Populate member select
const memberSelect = document.getElementById("memberSelect");
const members = getMembers();
members.forEach((m) => {
    const opt = document.createElement("option");
    opt.value = m.id;
    opt.textContent = m.name;
    memberSelect.appendChild(opt);
});

const form = document.getElementById("memberLoginForm");
form.addEventListener("submit", (event) => {
    event.preventDefault();

    const selectError = document.getElementById("memberSelectError");
    const passwordError = document.getElementById("memberPasswordError");
    const message = document.getElementById("memberLoginMessage");
    const password = document.getElementById("memberPassword");

    selectError.textContent = "";
    passwordError.textContent = "";
    message.textContent = "";
    message.className = "form-message";

    let valid = true;
    if (!memberSelect.value) {
        selectError.textContent = "Please select your name.";
        valid = false;
    }
    if (!password.value) {
        passwordError.textContent = "Please enter your password.";
        valid = false;
    } else if (password.value !== DEMO_PASSWORD) {
        passwordError.textContent = "Incorrect password. Use member123 for the demo.";
        valid = false;
    }
    if (!valid) return;

    const member = members.find((m) => m.id === memberSelect.value);
    if (!member) {
        message.textContent = "Member not found.";
        message.classList.add("error");
        return;
    }

    const session = {
        role: "member",
        id: member.id,
        name: member.name,
        initials: getInitials(member.name),
        paid: member.paid ?? 0,
        expected: member.expected ?? 20000,
        status: member.status || (member.paid >= member.expected ? "Paid" : member.paid > 0 ? "Partial" : "Pending")
    };

    localStorage.setItem(MEMBER_SESSION_KEY, JSON.stringify(session));
    localStorage.setItem("njangiLoggedIn", "member");

    message.textContent = "Login successful! Opening your dashboard…";
    message.classList.add("success");

    setTimeout(() => {
        window.location.href = "member-dashboard.html";
    }, 500);
});
