#!/usr/bin/env python3
"""
test_smtp.py — Standalone Gmail SMTP diagnostic tool.

Run this script directly from the project root to verify your Gmail
SMTP credentials WITHOUT starting the Flask app:

    python test_smtp.py

It will walk through each step (DNS → connect → STARTTLS → login → NOOP)
and print a clear pass/fail result for each one.

Usage:
  1. Set credentials in a .env file (recommended):
        MAIL_USERNAME=yourshop@gmail.com
        MAIL_PASSWORD=xxxx xxxx xxxx xxxx   # Google App Password

  2. Or set environment variables before running:
        $env:MAIL_USERNAME = "yourshop@gmail.com"
        $env:MAIL_PASSWORD = "xxxx xxxx xxxx xxxx"
        python test_smtp.py

  3. Or edit the OVERRIDE section below (NOT recommended for production).
"""

import os, sys, socket, ssl, smtplib

# ── Minimal .env loader (no pip install needed) ─────────────────────────────
_env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
if os.path.isfile(_env_path):
    with open(_env_path, encoding='utf-8') as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith('#') and '=' in _line:
                _k, _, _v = _line.partition('=')
                _k = _k.strip(); _v = _v.strip().strip('"').strip("'")
                if _k and _k not in os.environ:
                    os.environ[_k] = _v

# ── Configuration (env vars take priority) ───────────────────────────────────
SMTP_SERVER   = os.environ.get('MAIL_SERVER',      'smtp.gmail.com')
SMTP_PORT     = int(os.environ.get('MAIL_PORT',    587))
SMTP_USERNAME = os.environ.get('MAIL_USERNAME',    '')
SMTP_PASSWORD = os.environ.get('MAIL_PASSWORD',    '')

# Optional: who to send a test message to (defaults to sender address)
TEST_RECIPIENT = os.environ.get('TEST_RECIPIENT', SMTP_USERNAME)

# ── OVERRIDES (only for quick testing — delete before committing) ─────────────
# SMTP_USERNAME = "yourshop@gmail.com"
# SMTP_PASSWORD = "xxxx xxxx xxxx xxxx"

# ─────────────────────────────────────────────────────────────────────────────

BOLD   = '\033[1m'
GREEN  = '\033[92m'
RED    = '\033[91m'
YELLOW = '\033[93m'
RESET  = '\033[0m'

def ok(label, detail=''):
    print(f"  {GREEN}✔{RESET} {BOLD}{label}{RESET}" + (f"\n     {detail}" if detail else ''))

def fail(label, detail=''):
    print(f"  {RED}✘{RESET} {BOLD}{label}{RESET}" + (f"\n     {RED}{detail}{RESET}" if detail else ''))
    return False

def warn(msg):
    print(f"  {YELLOW}⚠{RESET}  {msg}")


def run_diagnostic():
    print()
    print(f"{BOLD}{'─'*60}{RESET}")
    print(f"{BOLD} SuperMart — Gmail SMTP Diagnostic{RESET}")
    print(f"{BOLD}{'─'*60}{RESET}")
    print(f"  Server   : {SMTP_SERVER}:{SMTP_PORT}")
    print(f"  Username : {SMTP_USERNAME or '(not set)'}")
    print(f"  Password : {'set (' + str(len(SMTP_PASSWORD)) + ' chars)' if SMTP_PASSWORD else '(not set)'}")
    print(f"{'─'*60}")
    print()

    # ── Step 1: Credentials ──────────────────────────────────────────
    print(f"{BOLD}Step 1: Credentials configured{RESET}")
    if not SMTP_USERNAME or not SMTP_PASSWORD:
        fail('SMTP credentials missing',
             'Set MAIL_USERNAME and MAIL_PASSWORD in a .env file or as environment variables.')
        print()
        print(f"{YELLOW}Create a .env file in the project root:{RESET}")
        print("  MAIL_USERNAME=yourshop@gmail.com")
        print("  MAIL_PASSWORD=xxxx xxxx xxxx xxxx   # Google App Password")
        print()
        sys.exit(1)
    ok('Credentials present',
       f"Username: {SMTP_USERNAME} | Password: {len(SMTP_PASSWORD)} chars")
    print()

    # ── Step 2: DNS resolution ───────────────────────────────────────
    print(f"{BOLD}Step 2: DNS resolution for {SMTP_SERVER}{RESET}")
    try:
        ip = socket.gethostbyname(SMTP_SERVER)
        ok(f"Resolved to {ip}")
    except socket.gaierror as e:
        fail('DNS resolution failed', str(e))
        print()
        warn('Check your internet connection and the SMTP server name.')
        sys.exit(1)
    print()

    # ── Step 3: TCP connect ──────────────────────────────────────────
    use_ssl = (SMTP_PORT == 465)
    mode    = 'SSL' if use_ssl else 'STARTTLS'
    print(f"{BOLD}Step 3: TCP connect to {SMTP_SERVER}:{SMTP_PORT} ({mode}){RESET}")
    ctx = ssl.create_default_context()
    srv = None
    try:
        if use_ssl:
            srv = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, context=ctx, timeout=20)
            ok(f'Connected via SSL')
        else:
            srv = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=20)
            code, banner = srv.ehlo()
            ok(f'TCP connected (EHLO code {code})', banner.decode(errors='replace') if isinstance(banner, bytes) else str(banner))
    except socket.timeout:
        fail('Connection timed out',
             f'Port {SMTP_PORT} may be blocked by your ISP or Windows Firewall.\n'
             '     Try port 465 (SSL) instead of 587 (STARTTLS).')
        sys.exit(1)
    except ConnectionRefusedError:
        fail('Connection refused', f'Nothing listening on {SMTP_SERVER}:{SMTP_PORT}.')
        sys.exit(1)
    except smtplib.SMTPException as e:
        fail('SMTP error during connect', str(e))
        sys.exit(1)
    except OSError as e:
        fail('OS/Network error', str(e))
        sys.exit(1)
    print()

    # ── Step 4: STARTTLS (port 587 only) ────────────────────────────
    if not use_ssl:
        print(f"{BOLD}Step 4: STARTTLS upgrade{RESET}")
        try:
            code, _ = srv.starttls(context=ctx)
            srv.ehlo()
            ok(f'TLS negotiated successfully (code {code})')
        except smtplib.SMTPException as e:
            fail('STARTTLS failed', str(e))
            srv.quit()
            sys.exit(1)
        print()

    # ── Step 5: Authentication ───────────────────────────────────────
    print(f"{BOLD}Step {'5' if not use_ssl else '4'}: Authenticate as {SMTP_USERNAME}{RESET}")
    try:
        srv.login(SMTP_USERNAME, SMTP_PASSWORD)
        ok('Authenticated successfully — Gmail accepted the App Password')
    except smtplib.SMTPAuthenticationError as e:
        fail('Authentication failed (535 5.7.8)',
             'You must use a Google App Password, NOT your regular Gmail password.\n'
             f'     Error: {e}\n'
             '     Fix: https://myaccount.google.com/apppasswords')
        srv.quit()
        sys.exit(1)
    except smtplib.SMTPException as e:
        fail('SMTP authentication error', str(e))
        srv.quit()
        sys.exit(1)
    print()

    # ── Step 6: NOOP ────────────────────────────────────────────────
    print(f"{BOLD}Step {'6' if not use_ssl else '5'}: Connection health check{RESET}")
    try:
        srv.noop()
        ok('Server responded to NOOP — connection is healthy and ready to send')
    except smtplib.SMTPException as e:
        warn(f'NOOP failed: {e}')
    print()

    # ── Optional: send a real test message ──────────────────────────
    if TEST_RECIPIENT:
        print(f"{BOLD}Step {'7' if not use_ssl else '6'}: Send test email to {TEST_RECIPIENT}{RESET}")
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        msg = MIMEMultipart('alternative')
        msg['Subject'] = '✅ SuperMart SMTP Test — All Good!'
        msg['From']    = f'SuperMart <{SMTP_USERNAME}>'
        msg['To']      = TEST_RECIPIENT
        html = f"""<div style="font-family:Arial;max-width:460px;margin:20px auto;
                              padding:24px;background:#f0fdf4;border:2px solid #16a34a;
                              border-radius:12px;">
          <h2 style="color:#16a34a;margin-top:0;">✅ SMTP is working!</h2>
          <p>Sent from: <strong>{SMTP_USERNAME}</strong></p>
          <p>Server: <strong>{SMTP_SERVER}:{SMTP_PORT}</strong></p>
        </div>"""
        msg.attach(MIMEText(html, 'html'))
        try:
            refused = srv.sendmail(SMTP_USERNAME, [TEST_RECIPIENT], msg.as_string())
            if refused:
                fail('Recipient refused', str(refused))
            else:
                ok(f'Test email sent to {TEST_RECIPIENT}',
                   'Check your inbox (and spam/junk folder).')
        except smtplib.SMTPException as e:
            fail('Send failed', str(e))

    srv.quit()

    print()
    print(f"{GREEN}{BOLD}{'─'*60}")
    print(f" ✅  ALL CHECKS PASSED — Gmail SMTP is fully working!")
    print(f"{'─'*60}{RESET}")
    print()
    print("Next step: go to Settings → Email Configuration in the app,")
    print("enter the same credentials there, and click Save Settings.")
    print()


if __name__ == '__main__':
    run_diagnostic()
