// =========================================
// NJANGI TRACKER - LOGIN & REGISTER
// Frontend prototype only.
// =========================================

// =====================================================
// 1. SHOW / HIDE PASSWORD
// =====================================================
// Finds every button with class .password-toggle and lets
// the user switch the related password input between hidden
// (type="password") and visible (type="text").
const passwordButtons = document.querySelectorAll(".password-toggle");

passwordButtons.forEach((button) => {
    button.addEventListener("click", () => {
        const input = document.getElementById(button.dataset.target);

        if (!input) return;

        const isPassword = input.type === "password";
        input.type = isPassword ? "text" : "password";
        button.textContent = isPassword ? "Hide" : "Show";
        button.setAttribute("aria-label", isPassword ? "Hide password" : "Show password");
    });
});

// =====================================================
// 2. HELPER FUNCTIONS
// =====================================================
// These small functions are reused by both the login and
// registration forms.
function showError(input, errorElement, message) {
    input.classList.add("input-error");
    errorElement.textContent = message;
}

function clearError(input, errorElement) {
    input.classList.remove("input-error");
    errorElement.textContent = "";
}

function isValidEmail(email) {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

// =====================================================
// 3. LOGIN FORM
// =====================================================
// The login form is only a frontend prototype for now.
// Later we will connect it to a real backend/database.
const loginForm = document.getElementById("loginForm");

if (loginForm) {
    loginForm.addEventListener("submit", (event) => {
        event.preventDefault();

        const email = document.getElementById("loginEmail");
        const password = document.getElementById("loginPassword");
        const emailError = document.getElementById("loginEmailError");
        const passwordError = document.getElementById("loginPasswordError");
        const message = document.getElementById("loginMessage");

        clearError(email, emailError);
        clearError(password, passwordError);
        message.textContent = "";
        message.className = "form-message";

        let valid = true;

        if (!email.value.trim()) {
            showError(email, emailError, "Please enter your email address.");
            valid = false;
        } else if (!isValidEmail(email.value.trim())) {
            showError(email, emailError, "Please enter a valid email address.");
            valid = false;
        }

        if (!password.value) {
            showError(password, passwordError, "Please enter your password.");
            valid = false;
        }

        if (!valid) return;

        // This is a frontend demo. A real login will be connected to a backend later.
        message.textContent = "Login successful! Opening your dashboard...";
        message.classList.add("success");

        // Save a simple login flag for this frontend prototype.
        localStorage.setItem("njangiLoggedIn", "true");

        // Move the user to the dashboard after a short delay.
        setTimeout(() => {
            window.location.href = "dashboard.html";
        }, 600);
    });
}

// =====================================================
// 4. FORGOT PASSWORD DEMO
// =====================================================
// This currently displays a message. Real password recovery
// will be added when the backend is built.
const forgotPassword = document.getElementById("forgotPassword");

if (forgotPassword) {
    forgotPassword.addEventListener("click", (event) => {
        event.preventDefault();
        alert("Password recovery will be added when we connect the backend.");
    });
}

// =====================================================
// 5. REGISTER FORM
// =====================================================
// Validates the registration fields and stores basic demo
// information in localStorage for this frontend prototype.
const registerForm = document.getElementById("registerForm");
const registerPassword = document.getElementById("registerPassword");

if (registerForm) {
    registerForm.addEventListener("submit", (event) => {
        event.preventDefault();

        const name = document.getElementById("registerName");
        const email = document.getElementById("registerEmail");
        const password = document.getElementById("registerPassword");
        const confirmPassword = document.getElementById("registerConfirm");
        const terms = document.getElementById("agreeTerms");

        const nameError = document.getElementById("registerNameError");
        const emailError = document.getElementById("registerEmailError");
        const passwordError = document.getElementById("registerPasswordError");
        const confirmError = document.getElementById("registerConfirmError");
        const termsError = document.getElementById("termsError");
        const message = document.getElementById("registerMessage");

        clearError(name, nameError);
        clearError(email, emailError);
        clearError(password, passwordError);
        clearError(confirmPassword, confirmError);
        termsError.textContent = "";
        message.textContent = "";
        message.className = "form-message";

        let valid = true;

        if (name.value.trim().length < 2) {
            showError(name, nameError, "Please enter your full name.");
            valid = false;
        }

        if (!email.value.trim()) {
            showError(email, emailError, "Please enter your email address.");
            valid = false;
        } else if (!isValidEmail(email.value.trim())) {
            showError(email, emailError, "Please enter a valid email address.");
            valid = false;
        }

        if (password.value.length < 6) {
            showError(password, passwordError, "Password must contain at least 6 characters.");
            valid = false;
        }

        if (confirmPassword.value !== password.value) {
            showError(confirmPassword, confirmError, "Passwords do not match.");
            valid = false;
        }

        if (!terms.checked) {
            termsError.textContent = "Please accept the agreement to continue.";
            valid = false;
        }

        if (!valid) return;

        // Save basic demo information in the browser for now.
        // Do NOT use this as real authentication; a backend is needed for security.
        const demoUser = {
            name: name.value.trim(),
            email: email.value.trim(),
            phone: document.getElementById("registerPhone").value.trim()
        };

        localStorage.setItem("njangiDemoUser", JSON.stringify(demoUser));

        message.textContent = "Account created successfully! Redirecting to login...";
        message.classList.add("success");

        // Give the user a moment to read the success message.
        setTimeout(() => {
            window.location.href = "login.html";
        }, 800);
    });
}

// =====================================================
// 6. PASSWORD STRENGTH INDICATOR
// =====================================================
// Gives the user visual feedback while typing a password.
function updatePasswordStrength(password) {
    const bars = document.querySelectorAll("#passwordStrength span");
    const strengthText = document.getElementById("strengthText");

    if (!bars.length || !strengthText) return;

    let score = 0;

    if (password.length >= 6) score++;
    if (password.length >= 10) score++;
    if (/[A-Z]/.test(password) && /[a-z]/.test(password)) score++;
    if (/\d/.test(password) || /[^A-Za-z0-9]/.test(password)) score++;

    bars.forEach((bar, index) => {
        bar.style.background = index < score ? "#176b4d" : "#dce3df";
    });

    if (!password) {
        strengthText.textContent = "Use at least 6 characters.";
    } else if (score <= 1) {
        strengthText.textContent = "Weak password";
    } else if (score <= 2) {
        strengthText.textContent = "Fair password";
    } else if (score === 3) {
        strengthText.textContent = "Good password";
    } else {
        strengthText.textContent = "Strong password";
    }
}

if (registerPassword) {
    registerPassword.addEventListener("input", () => {
        updatePasswordStrength(registerPassword.value);
    });
}
