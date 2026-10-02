# Changelog

## 2026-10-01 - Bug-fix and completion release

### Blocking bugs fixed
- **New cycles could never be created from the website.** The "New cycle" form had a required *Target Pool* field that nothing filled in, so the browser refused to submit. The field is now a read-only value calculated from the members' expected amounts (the server uses the same rule). Because every other feature depends on an open cycle, this also unblocked payments, loans and reliability.
- **Members showed an expected contribution of 0 FCFA whenever no cycle was open**, and *editing* a member in that state silently set their expected contribution to 0. The server now always returns the member's real expected amount.
- **Registration errors were unreadable.** One generic message was shown for every problem. The server now says exactly what is wrong (name, e-mail, password), and the page catches the classic typo `name@gmailcom` (a missing dot, which browsers accept as valid) and common misspellings such as `gmial.com` before sending.
- **"Member added. Login password: undefined".** The server never returned a password. The message now explains how the member gets access (temporary password set by the admin, or *Forgot password?*).
- **Password-reset e-mails failed silently.** The site always says "PIN sent" (to avoid revealing which e-mails exist), so a wrong SMTP setup looked like a working page. Now: Google App Passwords are accepted with their spaces; `/api/health` and the Settings page show whether e-mail is configured; `Backend/test_email.py` tests the connection and prints the exact reason for a failure.

### Dead or fake features completed
- **Settings** (every "Settings" link went nowhere): new page for administrators (name, phone, group name, default contribution, frequency) and for members (change password). Changing a password signs out the other devices.
- **History**: member and date filters and the Reset button did nothing; the "Clear Records" button was not connected to anything and would have destroyed reliability data - removed.
- **Loans**: repayment used a browser `prompt()` (blocked on many phones); it now uses the repayment form that was already in the page. The top search box works.
- **Cycles page**: the progress bar, pool, start/end dates, "members paid" and recipient were never filled in. They are now. The top search works.
- **Alerts bell**: shows the number of pending loan requests and opens the Loans page.
- **Sidebar**: shows the real group name and current cycle instead of "Njangi Group".
- **Members**: the *Reliability* column was a made-up number; it now shows the real score (or a dash before the first closed cycle). Administrators can set a temporary password when adding or editing a member, so access does not depend on e-mail.
- **Cycles**: the next recipient and the end date (from the group frequency) are suggested automatically.
- **Registration** now asks for the group name, contribution amount and frequency (it silently used 25 000 FCFA before).
- Dashboard "Search members" box works; empty tables show a message.

### Security and data integrity
- Removed `GET /api/members/public`, which listed the name, e-mail and phone of **every member of every group** to anyone, without logging in.
- Throttle on sign-in (10 failures per 15 minutes per address and e-mail).
- Expired or revoked sessions send the user back to the login page instead of showing error pop-ups.
- Deleting a payment recalculates the member's remaining payments (no stale *Paid*) and is refused for closed cycles (it would rewrite reliability history).
- Payments are refused for members who are not enrolled; numeric fields give readable messages instead of Python errors.

### Tooling
- `Tests/ui.js`: 51 browser checks. `Backend/test_email.py`: SMTP diagnosis.
