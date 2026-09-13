// =========================================
// MEMBER DASHBOARD
// =========================================


// LOGOUT

const logout = document.getElementById("memberLogout");

logout.addEventListener("click", () => {

    localStorage.removeItem("memberLoggedIn");

    window.location.href = "member-login.html";

});


// LOAN MODAL

const loanModal = document.getElementById("loanModal");

const requestLoan =
    document.getElementById("requestLoan");

const requestLoanTwo =
    document.getElementById("requestLoanTwo");

const closeLoan =
    document.getElementById("closeLoan");


// Open modal

function openLoanModal() {
    loanModal.classList.add("show");
}

requestLoan.addEventListener(
    "click",
    openLoanModal
);

requestLoanTwo.addEventListener(
    "click",
    openLoanModal
);


// Close modal

closeLoan.addEventListener("click", () => {

    loanModal.classList.remove("show");

});


// SUBMIT LOAN

const loanForm =
    document.getElementById("loanForm");

loanForm.addEventListener("submit", (event) => {

    event.preventDefault();


    const amount =
        document.getElementById("loanAmount").value;

    const reason =
        document.getElementById("loanReason").value;


    if (!amount || !reason) {
        return;
    }


    alert(
        "Loan request submitted successfully. " +
        "The administrator must approve it."
    );


    loanForm.reset();

    loanModal.classList.remove("show");

});


// MAKE PAYMENT

const makePayment =
    document.getElementById("makePayment");

makePayment.addEventListener("click", () => {

    alert(
        "Payment page will be connected to the payment system later."
    );

});