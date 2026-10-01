# Njangi Tracker

Njangi Tracker is a group savings application for managing members, contributions, cycles, payment history, emergency loan requests, loan approval, repayments, and payment reliability.

The backend is **Python + SQLite** and the frontend is **HTML + CSS + JavaScript**. No external Python package is required by the backend.

## Run locally

1. Open a terminal in this project folder.
2. Copy `.env.example` to `.env` if you want to test password-reset email settings.
3. Run `python server.py` or use `start.bat` on Windows / `start.sh` on Linux.
4. Open `http://127.0.0.1:8000`.

Register the first administrator on the Register page. The admin can then create members. Each member must have an email address so password recovery can work.

## Password reset

Both admins and members use the same Forgot Password flow:

`Forgot password -> email -> 6-digit PIN -> verify PIN -> new password`

The PIN expires after 10 minutes, is single-use, and allows at most 5 incorrect attempts. A password reset also revokes existing login sessions for that account.

For Gmail, use a Google App Password rather than your normal Gmail password. Keep `NJANGI_DEV_SHOW_PIN=0` in production.

## Loans

A member submits a loan request from the member dashboard. The request is stored as `PENDING` and appears on the admin Emergency Loans page. The admin can approve or reject it.

Before approval, the Python backend checks:
- at least 1 closed cycle;
- reliability score of at least 70%;
- sufficient available loan pool after existing approved/active loan balances.

Approved loans use the configured interest rate (5% by default), and repayments are recorded by the admin until the loan becomes `COMPLETED`.

## Reliability score

Reliability is calculated from closed cycles:
- 100 points: fully paid on or before the cycle deadline;
- 50 points: fully paid after the deadline;
- 0 points: not fully paid when the cycle is closed.

The backend returns the score plus the number of on-time, late, and missed cycles. This calculation is used by both the admin and member dashboards.

Each cycle snapshots the expected contribution for every enrolled member when the cycle is created, so later changes to a member's expected amount do not rewrite historical reliability. An incomplete cycle can be closed after its deadline so missed payments can be recorded. A fully paid cycle can be closed before its deadline.

## Deployment

See `DEPLOYMENT.md` and `render.yaml` for a deployment configuration. The supplied Render configuration uses a persistent disk for SQLite. For larger deployments or multiple server instances, move the database to PostgreSQL or another managed relational database.

Before public launch, finish and review the Privacy Policy, Terms & Conditions, favicon, custom domain, HTTPS, backups, and environment variables.


## Clean starting database

The distributed `njangi_app.db` is intentionally empty. No administrator, member, contribution, cycle, loan, reset PIN, or login session is pre-created. Register the first administrator through `register.html`.

## Member sign-in

Members sign in with the email address stored on their member account and their password. The public member list is no longer required for authentication.

## Loan repayment audit

Every repayment is recorded in the `loan_payments` table with the amount, date, group, loan, and administrator who recorded it. The aggregate loan balance is also updated so the dashboard stays fast.
