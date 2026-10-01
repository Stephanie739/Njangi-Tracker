# Njangi Tracker functional test report

Tested locally against a temporary SQLite database using the Python backend.

## Passed

- Admin registration and login
- Member creation with generated temporary password
- Member login by email and password
- Cycle creation and duplicate cycle-number protection
- Contribution recording
- Closing a fully paid cycle
- Reliability calculation from a closed cycle
- Member loan request
- Admin retrieval of the pending request
- Server-side reliability check before loan approval
- Server-side available-pool check before loan approval
- Loan approval and 5% interest calculation
- Partial loan repayment
- Final repayment and automatic `COMPLETED` status
- Repayment audit record in `loan_payments`
- Admin password reset with a 6-digit PIN
- Member password reset with a 6-digit PIN
- PIN expiry/attempt-limit logic
- Password reset revokes existing sessions
- Old password rejected after reset
- New password accepted after reset
- Sensitive files such as `.env`, `.db`, and Python source are not served publicly
- All frontend HTML pages and JavaScript files pass basic syntax/static checks

## Email limitation

The password-reset SMTP flow was tested with a local fake SMTP sender so the application logic and generated email were verified. A real Gmail delivery cannot be verified without the Gmail account/App Password supplied by the deployer.

Before deployment, configure:

- `NJANGI_SMTP_HOST=smtp.gmail.com`
- `NJANGI_SMTP_PORT=587`
- `NJANGI_SMTP_USERNAME=<Gmail address>`
- `NJANGI_SMTP_PASSWORD=<Google App Password>`
- `NJANGI_SMTP_FROM=<Gmail address>`
- `NJANGI_DEV_SHOW_PIN=0`

## Database

The distributed `njangi_app.db` contains zero admins, members, groups, cycles, contributions, loans, sessions, reset tokens, and repayment records. No demo account is included.
