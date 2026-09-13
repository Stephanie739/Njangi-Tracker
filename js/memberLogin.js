// =========================================
// NJANGI TRACKER - MEMBER LOGIN
// =========================================


// SHOW / HIDE PASSWORD

const passwordButton =
    document.querySelector(".password-toggle");

passwordButton.addEventListener("click", () => {

    const password =
        document.getElementById("memberPassword");

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
    document.getElementById("memberLoginForm");


loginForm.addEventListener("submit", (event) => {

    event.preventDefault();


    const email =
        document.getElementById("memberEmail");

    const password =
        document.getElementById("memberPassword");

    const emailError =
        document.getElementById("memberEmailError");

    const passwordError =
        document.getElementById("memberPasswordError");

    const message =
        document.getElementById("memberLoginMessage");


    // Clear old errors

    emailError.textContent = "";
    passwordError.textContent = "";

    email.classList.remove("input-error");
    password.classList.remove("input-error");

    message.textContent = "";

    let valid = true;


    // Check email

    if (!email.value.trim()) {

        emailError.textContent =
            "Please enter your email address.";

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
        "Login successful! Opening your dashboard...";

    message.classList.add("success");


    localStorage.setItem(
        "memberLoggedIn",
        "true"
    );


    // Go to member dashboard

    setTimeout(() => {

        window.location.href =
            "member-dashboard.html";

    }, 700);

});


// FORGOT PASSWORD

const forgotPassword =
    document.getElementById("memberForgotPassword");


forgotPassword.addEventListener("click", (event) => {

    event.preventDefault();

    alert(
        "Password recovery will be added later."
    );

});

