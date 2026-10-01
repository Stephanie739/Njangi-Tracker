# Njangi Tracker deployment notes

## Before deployment

1. Create a Gmail account dedicated to Njangi Tracker, or use an account you control.
2. Turn on Google 2-Step Verification.
3. Create a Google App Password. Use the App Password as `NJANGI_SMTP_PASSWORD`, not the normal Gmail password.
4. Set these environment variables on the host:
   - `NJANGI_SMTP_HOST=smtp.gmail.com`
   - `NJANGI_SMTP_PORT=587`
   - `NJANGI_SMTP_USERNAME=your-gmail@gmail.com`
   - `NJANGI_SMTP_PASSWORD=your-app-password`
   - `NJANGI_SMTP_FROM=your-gmail@gmail.com`
   - `NJANGI_DEV_SHOW_PIN=0`
   - `NJANGI_DB_PATH=/var/data/njangi_app.db` when using the Render persistent disk in `render.yaml`.

## Password reset flow

Forgot password -> enter account email -> server generates a random 6-digit PIN -> Gmail sends it -> PIN expires after 10 minutes -> maximum 5 wrong attempts -> verified PIN permits one password change -> all existing sessions for that account are revoked.

The API returns a generic response when an email is not registered so the endpoint does not disclose whether an account exists.

## Loans

1. Member submits a request.
2. Request is saved as `PENDING`.
3. Admin loan page loads the pending request from the server.
4. Admin approves or rejects it.
5. Approval checks the member's reliability and minimum completed cycles on the server.
6. Approval also checks the available pool against existing outstanding loan balances.
7. Approved loans receive the configured interest rate and total due.
8. Admin records repayments. The server prevents overpayment and marks a fully repaid loan `COMPLETED`.

## Reliability

For every closed cycle:
- Fully paid by the cycle deadline = 100 points.
- Fully paid after the deadline = 50 points.
- Not fully paid when the cycle is closed = 0 points.

The score is the average of those cycle points. The API also returns the counts for on-time, late, and missed cycles.

A loan approval currently requires at least 1 closed cycle and a reliability score of at least 70%.

## Database persistence

SQLite is suitable for a small deployment if the host provides persistent storage. The supplied Render configuration uses a persistent disk mounted at `/var/data`.

For larger traffic or multiple application instances, migrate the database to PostgreSQL or another managed relational database before scaling horizontally.

## Security checklist

- Use HTTPS on the public domain.
- Keep `.env` out of Git.
- Keep `NJANGI_DEV_SHOW_PIN=0` in production.
- Use a dedicated Gmail account/App Password.
- Back up the SQLite database regularly if SQLite is used.
- Review the Privacy Policy and Terms with a qualified local professional before launch.
- Configure a custom domain and verify DNS/HTTPS before public launch.
