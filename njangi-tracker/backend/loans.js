// loans.js
// Functions for loan requests and loan decisions.
// The detailed business rules can be added here later.

function getLoans(db) {
    return db.loans;
}

function addLoan(db, loan) {
    db.loans.push(loan);
}

function findLoan(db, id) {
    return db.loans.find(loan => loan.id === id);
}

function approveLoan(db, id) {
    const loan = findLoan(db, id);

    if (!loan) {
        return null;
    }

    loan.status = "approved";
    return loan;
}

function rejectLoan(db, id) {
    const loan = findLoan(db, id);

    if (!loan) {
        return null;
    }

    loan.status = "rejected";
    return loan;
}

module.exports = {
    getLoans,
    addLoan,
    findLoan,
    approveLoan,
    rejectLoan
};
