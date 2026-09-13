// =========================================
// NJANGI TRACKER - ADMIN LOGIN
// =========================================


// SHOW / HIDE PASSWORD

const passwordButton =
    document.querySelector(".password-toggle");


passwordButton.addEventListener("click", () => {

    const password =
        document.getElementById("adminPassword");


    if (password.type === "password") {

        password.type = "text";

        passwordButton.textContent = "Hide";

    } else {

        password.type = "password";

        passwordButton.textContent = "Show";

    }

});


// LOGIN FORM

const loginForm =
    document.getElementById("adminLoginForm");


loginForm.addEventListener("submit", (event) => {

    event.preventDefault();


    const email =
        document.getElementById("adminEmail");

    const password =
        document.getElementById("adminPassword");


    const emailError =
        document.getElementById("adminEmailError");

    const passwordError =
        document.getElementById("adminPasswordError");


    const message =
        document.getElementById("adminLoginMessage");


    // Clear errors

    emailError.textContent = "";
    passwordError.textContent = "";

    email.classList.remove("input-error");
    password.classList.remove("input-error");

    message.textContent = "";

    let valid = true;


    // Check email

    if (!email.value.trim()) {

        emailError.textContent =
            "Please enter your admin email.";

        email.classList.add("input-error");

        valid = false;

    } else if (
        !email.value.includes("@")
    ) {

        emailError.textContent =
            "Please enter a valid email address.";

        email.classList.add("input-error");

        valid = false;

    }


    // Check password

    if (!password.value) {

        passwordError.textContent =
            "Please enter your password.";

        password.classList.add("input-error");

        valid = false;

    }


    // Stop if invalid

    if (!valid) {
        return;
    }


    // Demo login

    message.textContent =
        "Admin login successful! Opening dashboard...";

    message.classList.add("success");


    localStorage.setItem(
        "adminLoggedIn",
        "true"
    );


    // Go to admin dashboard

    setTimeout(() => {

        window.location.href =
            "admin-dashboard.html";

    }, 700);

});


// FORGOT PASSWORD

const forgotPassword =
    document.getElementById("adminForgotPassword");


forgotPassword.addEventListener("click", (event) => {

    event.preventDefault();

    alert(
        "Admin password recovery will be added later."
    );

});

