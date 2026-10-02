# Njangi Tracker

Njangi Tracker is a group savings application for managing members, contributions, cycles, payment history, emergency loan requests, loan approval, repayments, and payment reliability.

This folder is the **backend**: a Python + SQLite JSON API (routes under `/api`). It serves no HTML. The website is the separate **Frontend** folder/repository; it calls this API over HTTP (CORS enabled). No external Python package is required.

## Run locally

1. Open a terminal in this `Backend` folder.
2. Copy `.env.example` to `.env` and fill in the SMTP settings (needed for password-reset emails).
3. Run `python server.py` or use `start.bat` on Windows / `start.sh` on Linux.
4. Check `http://127.0.0.1:8000/api/health`, then start the frontend (`python serve.py` in the Frontend folder) and open `http://127.0.0.1:5500`.

`NJANGI_CORS_ORIGINS` (in `.env`) lists the website origins allowed to call the API. `*` is fine locally; use your real frontend URL in production.

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


## Database

`njangi_app.db` is the SQLite database. It currently contains the test accounts/data created during development. To start from a clean database, delete `njangi_app.db` and restart the server: the schema is recreated automatically, then register the first administrator through `register.html`.

## Member sign-in

Members sign in with the email address stored on their member account and their password. The public member list is no longer required for authentication.

## Loan repayment audit

Every repayment is recorded in the `loan_payments` table with the amount, date, group, loan, and administrator who recorded it. The aggregate loan balance is also updated so the dashboard stays fast.


## Updating a running server

```bash
PORT=2030 ./update.sh      # backs up the DB, git pull, compile check, restart (pm2 / systemd / background), health check
```
`PORT` is only used by the final health check (use the port your backend listens on). `update.sh` refuses to run if tracked files have local changes, and stops *before* restarting if the new code does not compile.

## Troubleshooting

| Problem | What to do |
|---|---|
| Password-reset e-mail never arrives | Run `python3 test_email.py you@example.com` in this folder. It prints the exact reason (placeholder password, wrong App Password, blocked port...). `GET /api/health` and the Settings page also show `email_configured`. |
| "valid email ... required" when creating an account | The e-mail is missing its dot (`name@gmailcom`). The form points this out. |
| A member cannot sign in | The member has no password yet: **Forgot password?** on the member login page, or set a temporary password in Members > Edit. |
| Cannot create a cycle | Add at least one enrolled member with an expected contribution first. |

See `CHANGELOG.md` for everything fixed in the latest release, `Tests/` for the browser tests, and `PROJECT-OVERVIEW.md` for the project description (problem, features, methodology, team).
