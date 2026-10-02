# Njangi Tracker test report (2026-10-01)

Tested against a fresh SQLite database, with the real pages running in Chromium (Playwright) against the live API.

**51 / 51 browser checks passed** (`Tests/ui.js` (in this folder), run repeatedly): registration (including the e-mail typo hint),
settings and password change, adding/editing members, cycle creation with automatic recipient and dates,
payments (partial payments, deletion recalculation, closed-cycle protection), history filters, cycle panel,
loans (request, approval, repayment through the modal, search), alerts, member sign-in and password change,
expired-session redirect, sign-in throttle, removal of the public member list, and the password-reset flow.

**Mobile (390 px):** no horizontal overflow on any admin page; the side menu opens and closes; no JavaScript errors.

**Not testable here:** real Gmail delivery (needs the account's App Password). Run `python3 test_email.py you@example.com`
on the server to verify it.
