"""
email_helper.py — SMTP email utility for SuperMart password reset.

Credential priority (highest → lowest):
  1. DB settings table  (admin enters via Settings → Email Configuration)
  2. Environment variables / .env file loaded at startup
  3. Flask app.config defaults (smtp.gmail.com:587, empty user/pass)

Gmail quick-start:
  1. Enable 2-Step Verification on your Google account.
  2. Go to https://myaccount.google.com/apppasswords
  3. Create an App Password for "Mail".
  4. Paste the 16-character code into the App Password field in Settings.
"""

import smtplib
import ssl
import logging
import socket
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import current_app
from app.models.database import query_db

log = logging.getLogger('supermart.security')

# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _get_mail_config() -> dict:
    """
    Merges DB settings (highest priority) with Flask config / env vars.
    Returns a plain dict — never raises.
    """
    try:
        rows = query_db(
            "SELECT key, value FROM settings WHERE key IN "
            "('mail_server','mail_port','mail_username','mail_password',"
            " 'mail_sender_name','reset_token_expiry_minutes')"
        )
        db = {r['key']: (r['value'] or '').strip() for r in rows} if rows else {}
    except Exception:
        db = {}

    cfg = current_app.config

    server      = db.get('mail_server')   or cfg.get('MAIL_SERVER',      'smtp.gmail.com')
    port_raw    = db.get('mail_port')     or str(cfg.get('MAIL_PORT',    587))
    username    = db.get('mail_username') or cfg.get('MAIL_USERNAME',    '')
    password    = db.get('mail_password') or cfg.get('MAIL_PASSWORD',    '')
    sender_name = db.get('mail_sender_name') or cfg.get('MAIL_SENDER_NAME', 'SuperMart')

    try:
        port = int(port_raw)
    except (TypeError, ValueError):
        port = 587

    # Decide TLS mode from port
    use_ssl     = (port == 465)
    use_starttls = not use_ssl   # 587 and 25 both use STARTTLS

    return {
        'server':       server.strip(),
        'port':         port,
        'use_ssl':      use_ssl,
        'use_starttls': use_starttls,
        'username':     username.strip(),
        'password':     password.strip(),
        'sender_name':  sender_name.strip(),
    }


def _build_smtp_connection(mail: dict):
    """
    Opens and authenticates an SMTP connection.
    Returns (server_obj, None) on success or (None, error_string) on failure.
    """
    ctx = ssl.create_default_context()

    try:
        if mail['use_ssl']:
            # Port 465 — direct SSL
            log.info("[SMTP] Connecting via SSL to %s:%d", mail['server'], mail['port'])
            srv = smtplib.SMTP_SSL(mail['server'], mail['port'], context=ctx, timeout=20)
        else:
            # Port 587 — STARTTLS
            log.info("[SMTP] Connecting via STARTTLS to %s:%d", mail['server'], mail['port'])
            srv = smtplib.SMTP(mail['server'], mail['port'], timeout=20)
            srv.ehlo()
            srv.starttls(context=ctx)
            srv.ehlo()

    except socket.timeout:
        return None, (
            f"Connection timed out reaching {mail['server']}:{mail['port']}. "
            "Check that port 587 is not blocked by your firewall or ISP."
        )
    except socket.gaierror:
        return None, (
            f"Cannot resolve hostname '{mail['server']}'. "
            "Verify the SMTP server name (should be smtp.gmail.com for Gmail)."
        )
    except ConnectionRefusedError:
        return None, (
            f"Connection refused to {mail['server']}:{mail['port']}. "
            "Try port 587 (STARTTLS) or 465 (SSL)."
        )
    except smtplib.SMTPConnectError as e:
        return None, f"SMTP connect error: {e}"
    except smtplib.SMTPException as e:
        return None, f"SMTP error during handshake: {e}"
    except OSError as e:
        return None, f"Network error: {e}"

    # Authenticate
    try:
        log.info("[SMTP] Authenticating as %s", mail['username'])
        srv.login(mail['username'], mail['password'])
        log.info("[SMTP] Authenticated OK")
        return srv, None

    except smtplib.SMTPAuthenticationError:
        srv.quit()
        return None, (
            "Gmail authentication failed (535 5.7.8). "
            "Causes: \n"
            "  • You used your normal Gmail password instead of an App Password.\n"
            "  • 2-Step Verification is NOT enabled on your Google account.\n"
            "  • The App Password was typed/pasted incorrectly.\n\n"
            "Fix: Go to https://myaccount.google.com/apppasswords → "
            "create an App Password for 'Mail' → paste the 16-char code here."
        )
    except smtplib.SMTPException as e:
        srv.quit()
        return None, f"Authentication error: {e}"


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def send_reset_email(
    to_email: str,
    reset_url: str,
    username: str = "",
    expiry_minutes: int = 15,
) -> tuple:
    """
    Sends a professional password-reset email.
    Returns (success: bool, message: str).
    """
    mail = _get_mail_config()

    # ── Guard: credentials must be set ───────────────────────────────
    if not mail['username'] or not mail['password']:
        msg = (
            "Email is not configured — no SMTP credentials found. "
            "Go to Settings → Email Configuration, enter your Gmail address "
            "and App Password, then Save."
        )
        log.error("[SMTP] send_reset_email aborted: %s", msg)
        return False, msg

    display_name = username or to_email
    sender_name  = mail['sender_name']

    # ── Build message ─────────────────────────────────────────────────
    html_body = _render_reset_html(display_name, sender_name, reset_url, expiry_minutes)
    text_body = (
        f"Hi {display_name},\n\n"
        f"Reset your {sender_name} password using the link below "
        f"(expires in {expiry_minutes} minutes):\n\n"
        f"{reset_url}\n\n"
        "If you did not request this, ignore this email.\n\n"
        f"— {sender_name} Security"
    )

    msg = MIMEMultipart('alternative')
    msg['Subject']    = f"Reset your {sender_name} password — expires in {expiry_minutes} min"
    msg['From']       = f"{sender_name} <{mail['username']}>"
    msg['To']         = to_email
    msg['X-Priority'] = '1'
    msg.attach(MIMEText(text_body, 'plain', 'utf-8'))
    msg.attach(MIMEText(html_body, 'html',  'utf-8'))

    # ── Connect + send ────────────────────────────────────────────────
    srv, conn_err = _build_smtp_connection(mail)
    if not srv:
        log.error("[SMTP] Connection/auth failed for reset email to %s: %s", to_email, conn_err)
        return False, conn_err

    try:
        refused = srv.sendmail(mail['username'], [to_email], msg.as_string())
        srv.quit()
        if refused:
            log.warning("[SMTP] Recipients refused: %s", refused)
            return False, f"Recipient address '{to_email}' was refused by Gmail."
        log.info("[SMTP] Reset email delivered to %s", to_email)
        return True, "Reset email sent successfully."

    except smtplib.SMTPRecipientsRefused:
        return False, f"Recipient '{to_email}' was refused."
    except smtplib.SMTPException as e:
        log.error("[SMTP] Send error: %s", e)
        return False, f"SMTP error while sending: {e}"
    except Exception as e:
        log.error("[SMTP] Unexpected send error: %s", e)
        return False, f"Unexpected error: {e}"


def send_test_email(to_email: str) -> tuple:
    """
    Sends a simple test email to `to_email`.
    Returns (success: bool, message: str).
    """
    mail = _get_mail_config()

    if not mail['username'] or not mail['password']:
        return False, (
            "No SMTP credentials configured. "
            "Enter your Gmail address and App Password in Settings → Email Configuration."
        )

    html_body = f"""
    <div style="font-family:Arial,sans-serif;max-width:500px;margin:30px auto;
                background:#f0fdf4;border:2px solid #16a34a;border-radius:12px;padding:32px;">
      <h2 style="color:#16a34a;margin-top:0;">✅ Test Email Successful!</h2>
      <p style="color:#374151;">SMTP is working correctly for <strong>{mail['sender_name']}</strong>.</p>
      <p style="color:#6b7280;font-size:13px;">
        Sender: <strong>{mail['username']}</strong><br>
        Server: <strong>{mail['server']}:{mail['port']}</strong>
      </p>
    </div>"""

    msg = MIMEMultipart('alternative')
    msg['Subject'] = f"✅ {mail['sender_name']} — SMTP Test OK"
    msg['From']    = f"{mail['sender_name']} <{mail['username']}>"
    msg['To']      = to_email
    msg.attach(MIMEText(html_body, 'html', 'utf-8'))

    srv, conn_err = _build_smtp_connection(mail)
    if not srv:
        return False, conn_err

    try:
        srv.sendmail(mail['username'], [to_email], msg.as_string())
        srv.quit()
        return True, f"✅ Test email sent to {to_email} — check your inbox (and spam folder)!"
    except smtplib.SMTPException as e:
        return False, f"Send error: {e}"
    except Exception as e:
        return False, f"Unexpected error: {e}"


def diagnose_smtp() -> dict:
    """
    Runs a step-by-step SMTP diagnostic and returns a structured report.
    Does NOT send any email. Used by the Settings → Diagnose button.

    Returns:
    {
        'config': { server, port, username, password_set },
        'steps': [
            { 'name': str, 'ok': bool, 'detail': str },
            ...
        ],
        'overall': bool
    }
    """
    mail  = _get_mail_config()
    steps = []

    # ── Step 1: Credentials present ──────────────────────────────────
    creds_ok = bool(mail['username'] and mail['password'])
    steps.append({
        'name':   'Credentials configured',
        'ok':     creds_ok,
        'detail': (
            f"Username: {mail['username'] or '(empty)'} | "
            f"Password: {'set (' + str(len(mail['password'])) + ' chars)' if mail['password'] else '(empty)'}"
        )
    })
    if not creds_ok:
        steps.append({
            'name':   'SMTP connection',
            'ok':     False,
            'detail': 'Skipped — credentials must be set first.'
        })
        steps.append({
            'name':   'Authentication',
            'ok':     False,
            'detail': 'Skipped.'
        })
        return _diag_report(mail, steps, False)

    # ── Step 2: DNS / TCP connect ────────────────────────────────────
    ctx = ssl.create_default_context()
    srv = None
    try:
        if mail['use_ssl']:
            srv = smtplib.SMTP_SSL(mail['server'], mail['port'], context=ctx, timeout=20)
            steps.append({
                'name':   f"Connect to {mail['server']}:{mail['port']} (SSL)",
                'ok':     True,
                'detail': 'TCP + SSL handshake succeeded.'
            })
        else:
            srv = smtplib.SMTP(mail['server'], mail['port'], timeout=20)
            banner = srv.ehlo()
            steps.append({
                'name':   f"Connect to {mail['server']}:{mail['port']}",
                'ok':     True,
                'detail': f"EHLO response code: {banner[0]}"
            })
            # ── Step 3: STARTTLS ─────────────────────────────────────
            tls_resp = srv.starttls(context=ctx)
            srv.ehlo()
            steps.append({
                'name':   'STARTTLS upgrade',
                'ok':     True,
                'detail': f"TLS negotiated. Response: {tls_resp[0]}"
            })

    except socket.timeout:
        steps.append({
            'name':   f"Connect to {mail['server']}:{mail['port']}",
            'ok':     False,
            'detail': (
                "Timed out. Port 587 may be blocked by your ISP or firewall. "
                "Try port 465 (SSL) instead."
            )
        })
        return _diag_report(mail, steps, False)
    except socket.gaierror:
        steps.append({
            'name':   f"Connect to {mail['server']}:{mail['port']}",
            'ok':     False,
            'detail': (
                f"DNS lookup failed for '{mail['server']}'. "
                "Check internet connectivity and SMTP server name."
            )
        })
        return _diag_report(mail, steps, False)
    except smtplib.SMTPException as e:
        steps.append({
            'name':   f"Connect to {mail['server']}:{mail['port']}",
            'ok':     False,
            'detail': str(e)
        })
        return _diag_report(mail, steps, False)
    except OSError as e:
        steps.append({
            'name':   f"Connect to {mail['server']}:{mail['port']}",
            'ok':     False,
            'detail': str(e)
        })
        return _diag_report(mail, steps, False)

    # ── Step 4: Login ────────────────────────────────────────────────
    try:
        srv.login(mail['username'], mail['password'])
        steps.append({
            'name':   f"Authenticate as {mail['username']}",
            'ok':     True,
            'detail': 'Login accepted by Gmail.'
        })
    except smtplib.SMTPAuthenticationError as e:
        steps.append({
            'name':   f"Authenticate as {mail['username']}",
            'ok':     False,
            'detail': (
                f"Gmail rejected the credentials (code {e.smtp_code}). "
                "You must use a Google App Password, not your regular Gmail password. "
                "Get one at: myaccount.google.com/apppasswords"
            )
        })
        try:
            srv.quit()
        except Exception:
            pass
        return _diag_report(mail, steps, False)
    except smtplib.SMTPException as e:
        steps.append({
            'name':   'Authenticate',
            'ok':     False,
            'detail': str(e)
        })
        try:
            srv.quit()
        except Exception:
            pass
        return _diag_report(mail, steps, False)

    # ── Step 5: NOOP / keepalive (verify connection alive) ──────────
    try:
        srv.noop()
        steps.append({
            'name':   'Connection health check (NOOP)',
            'ok':     True,
            'detail': 'Server responded to NOOP — ready to send emails.'
        })
    except smtplib.SMTPException as e:
        steps.append({'name': 'NOOP', 'ok': False, 'detail': str(e)})
    finally:
        try:
            srv.quit()
        except Exception:
            pass

    return _diag_report(mail, steps, True)


def _diag_report(mail: dict, steps: list, overall: bool) -> dict:
    return {
        'config': {
            'server':       mail['server'],
            'port':         mail['port'],
            'mode':         'SSL (port 465)' if mail['use_ssl'] else 'STARTTLS (port 587)',
            'username':     mail['username'] or '(not set)',
            'password_set': bool(mail['password']),
            'password_len': len(mail['password']) if mail['password'] else 0,
        },
        'steps':   steps,
        'overall': overall,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Email HTML template
# ─────────────────────────────────────────────────────────────────────────────

def _render_reset_html(display_name: str, sender_name: str, reset_url: str, expiry_minutes: int) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Reset Your Password</title>
</head>
<body style="margin:0;padding:0;background:#f0f4f8;font-family:'Segoe UI',Arial,sans-serif;">
<table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0"
       style="background:#f0f4f8;">
  <tr><td style="padding:40px 20px;">

    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0"
           style="max-width:560px;margin:0 auto;background:#fff;border-radius:20px;
                  overflow:hidden;box-shadow:0 8px 40px rgba(30,58,138,.12);">

      <!-- Header -->
      <tr>
        <td style="background:linear-gradient(135deg,#1e3a8a,#2563eb 60%,#3b82f6);
                   padding:40px 40px 32px;text-align:center;">
          <div style="font-size:48px;line-height:1;margin-bottom:14px;">🔐</div>
          <h1 style="color:#fff;margin:0 0 8px;font-size:26px;font-weight:700;">Password Reset Request</h1>
          <p style="color:#bfdbfe;margin:0;font-size:14px;">{sender_name} — Account Security</p>
        </td>
      </tr>

      <!-- Body -->
      <tr>
        <td style="padding:40px 40px 32px;">

          <p style="color:#1e293b;font-size:16px;line-height:1.6;margin:0 0 20px;">
            Hi <strong style="color:#1e3a8a;">{display_name}</strong>,
          </p>
          <p style="color:#475569;font-size:15px;line-height:1.7;margin:0 0 28px;">
            We received a request to reset the password for your <strong>{sender_name}</strong>
            account. Click the button below to set a new password.
          </p>

          <!-- CTA -->
          <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
            <tr>
              <td style="text-align:center;padding:0 0 32px;">
                <a href="{reset_url}"
                   style="display:inline-block;background:linear-gradient(135deg,#2563eb,#1d4ed8);
                          color:#fff;text-decoration:none;padding:16px 44px;border-radius:12px;
                          font-size:16px;font-weight:700;letter-spacing:.3px;
                          box-shadow:0 6px 20px rgba(37,99,235,.4);">
                  Reset My Password &rarr;
                </a>
              </td>
            </tr>
          </table>

          <!-- Expiry -->
          <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
            <tr>
              <td style="background:#fef3c7;border-left:4px solid #f59e0b;
                         border-radius:8px;padding:14px 18px;">
                <p style="margin:0;color:#92400e;font-size:13px;line-height:1.5;">
                  &#9201; <strong>This link expires in {expiry_minutes} minutes.</strong>
                  If expired, go back to the login page and request a new one.
                </p>
              </td>
            </tr>
          </table>

          <!-- Backup link -->
          <p style="color:#64748b;font-size:13px;margin:24px 0 8px;">
            If the button does not work, copy this link into your browser:
          </p>
          <div style="background:#f1f5f9;border:1px solid #e2e8f0;border-radius:8px;
                      padding:12px 16px;word-break:break-all;">
            <a href="{reset_url}" style="color:#2563eb;font-size:12px;text-decoration:none;">{reset_url}</a>
          </div>

          <!-- Security notice -->
          <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0"
                 style="margin-top:28px;">
            <tr>
              <td style="background:#fef2f2;border-left:4px solid #ef4444;
                         border-radius:8px;padding:14px 18px;">
                <p style="margin:0;color:#991b1b;font-size:13px;line-height:1.5;">
                  &#128274; <strong>Didn't request this?</strong>
                  Ignore this email — your account is secure and no changes have been made.
                </p>
              </td>
            </tr>
          </table>

        </td>
      </tr>

      <!-- Footer -->
      <tr>
        <td style="background:#f8fafc;border-top:1px solid #e2e8f0;
                   padding:24px 40px;text-align:center;">
          <p style="color:#94a3b8;font-size:12px;margin:0 0 4px;">
            &copy; {sender_name} &bull; Automated security email — do not reply.
          </p>
        </td>
      </tr>

    </table>
  </td></tr>
</table>
</body>
</html>"""
