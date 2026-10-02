#!/usr/bin/env python3
"""Check the e-mail (SMTP) settings of Njangi Tracker and show the exact reason if sending fails.

Run it on the machine that runs the backend (it reads the same .env file):

    python3 test_email.py                      # only tests the connection and login
    python3 test_email.py someone@example.com  # also sends a test e-mail to that address

The password is never printed.
"""
import os
import smtplib
import ssl
import sys
from email.message import EmailMessage
from pathlib import Path

HERE = Path(__file__).resolve().parent
env_file = HERE / ".env"
if env_file.exists():
    for raw in env_file.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
else:
    print(f"!! No .env file found in {HERE}")

host = os.getenv("NJANGI_SMTP_HOST", "smtp.gmail.com").strip()
port = int(os.getenv("NJANGI_SMTP_PORT", "587"))
username = os.getenv("NJANGI_SMTP_USERNAME", "").strip()
password = os.getenv("NJANGI_SMTP_PASSWORD", "").replace(" ", "").strip()
sender = os.getenv("NJANGI_SMTP_FROM", username).strip()
timeout = int(os.getenv("NJANGI_SMTP_TIMEOUT", "20"))

print(f"Server   : {host}:{port}")
print(f"Username : {username or '(empty)'}")
print(f"From     : {sender or '(empty)'}")
print(f"Password : {len(password)} characters" + ("  <- PLACEHOLDER, replace it" if "your-" in password else ""))
if "your-" in username or "your-" in password or not username or not password:
    print("\nXX The e-mail settings in .env are still empty or placeholders.")
    print("   Fill NJANGI_SMTP_USERNAME, NJANGI_SMTP_PASSWORD (a Google App Password) and NJANGI_SMTP_FROM,")
    print("   then restart the backend (pm2 restart njangi-backend --update-env).")
    sys.exit(1)
if host.endswith("gmail.com") and len(password) != 16:
    print("!! A Google App Password has exactly 16 characters. Yours has", len(password), "- check that it was copied completely.")

try:
    if port == 465:
        smtp = smtplib.SMTP_SSL(host, port, timeout=timeout)
    else:
        smtp = smtplib.SMTP(host, port, timeout=timeout)
        smtp.ehlo()
        smtp.starttls(context=ssl.create_default_context())
        smtp.ehlo()
    print("OK connection to the mail server")
    smtp.login(username, password)
    print("OK login accepted")
    if len(sys.argv) > 1:
        message = EmailMessage()
        message["Subject"] = "Njangi Tracker - test e-mail"
        message["From"] = sender
        message["To"] = sys.argv[1]
        message.set_content("This is a test e-mail from Njangi Tracker. E-mail sending works.")
        smtp.send_message(message)
        print(f"OK test e-mail sent to {sys.argv[1]} (check the inbox and the spam folder)")
    smtp.quit()
    print("\nAll good: password-reset PINs can be delivered.")
except smtplib.SMTPAuthenticationError as exc:
    print("\nXX Gmail refused the login:", exc)
    print("   - Use a Google App Password (Google account > Security > 2-Step Verification > App passwords),")
    print("     not your normal password. 2-Step Verification must be ON.")
    print("   - If the password is new, copy it again without spaces; if it is old, create a new one.")
    print("   - Check your Gmail inbox for a 'Critical security alert' and approve the sign-in from the server.")
    sys.exit(2)
except (OSError, smtplib.SMTPException) as exc:
    print("\nXX Could not reach/use the mail server:", type(exc).__name__, exc)
    print("   - Is outbound port", port, "open on this server?  Test: timeout 5 bash -c '</dev/tcp/%s/%d' && echo open" % (host, port))
    sys.exit(3)
