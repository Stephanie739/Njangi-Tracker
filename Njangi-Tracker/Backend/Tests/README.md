# Browser tests

`ui.js` drives the real pages in Chromium against a running backend and frontend (51 checks: registration,
settings, members, cycles, payments, history filters, loans, alerts, password reset, security, ...).

```bash
# 1. a throw-away database, with the reset PIN shown on the page (test mode only!)
cd Backend  && NJANGI_DB_PATH=/tmp/njangi_test.db NJANGI_DEV_SHOW_PIN=1 python3 server.py &
cd ../Frontend && python3 serve.py &

# 2. run the tests (from Backend/Tests)
cd ../Backend/Tests && npm i playwright && npx playwright install chromium && node ui.js
```
Never run it against your production database or with `NJANGI_DEV_SHOW_PIN=1` in production.
