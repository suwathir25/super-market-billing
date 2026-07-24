import re
import secrets
import logging
from datetime import datetime, timedelta
from flask import session, current_app
from app.models.user import User
from app.models.database import query_db, execute_db

# Security audit logger — configured in Config.configure_security_logging()
security_logger = logging.getLogger('supermart.security')

# Special-character set for password validation
_SPECIAL_CHARS = re.compile(r'[!@#$%^&*()\-_,.?\":{}|<>\[\]\\\/~`+=;]')


class AuthController:
    @staticmethod
    def login(username, password):
        """Handles authentication. Returns (success, message_or_user_data)."""
        if not username or not password:
            return False, "Username and password are required."

        user = User.get_by_username(username.strip())
        if not user:
            return False, "Invalid username or password."
        if user.status != 'active':
            return False, "This account is inactive. Please contact the administrator."
        if not user.verify_password(password):
            return False, "Invalid username or password."

        session.clear()
        session['user_id']  = user.id
        session['username'] = user.username
        session['role']     = user.role
        session['language'] = user.language

        return True, {
            'id': user.id, 'username': user.username,
            'role': user.role, 'language': user.language
        }

    @staticmethod
    def logout():
        """Clears session variables."""
        session.clear()
        return True

    @staticmethod
    def check_logged_in():
        """Returns the active User object if logged in, else None."""
        if 'user_id' not in session:
            return None
        user = User.get_by_id(session['user_id'])
        if not user or user.status != 'active':
            session.clear()
            return None
        return user

    # ------------------------------------------------------------------ #
    #  Strong password validation (production-grade)                      #
    # ------------------------------------------------------------------ #

    @staticmethod
    def validate_strong_password(password):
        """
        Enforces:
          - >= 8 characters
          - At least one uppercase letter
          - At least one lowercase letter
          - At least one digit
          - At least one special character
        Returns (is_valid: bool, error_message: str).
        """
        if not password or len(password) < 8:
            return False, "Password must be at least 8 characters long."
        if not re.search(r'[A-Z]', password):
            return False, "Password must contain at least one uppercase letter (A-Z)."
        if not re.search(r'[a-z]', password):
            return False, "Password must contain at least one lowercase letter (a-z)."
        if not re.search(r'[0-9]', password):
            return False, "Password must contain at least one number (0-9)."
        if not _SPECIAL_CHARS.search(password):
            return False, "Password must contain at least one special character (!@#$%^&* etc.)."
        return True, ""

    # ------------------------------------------------------------------ #
    #  Step 1 — Request password reset link                              #
    # ------------------------------------------------------------------ #

    @staticmethod
    def request_password_reset(email, client_ip=None):
        """
        Generates a 15-minute reset token, stores it in DB, and emails a link.
        Rate-limited to 1 request per 60 seconds per user.
        Always returns the same generic message to prevent email enumeration.
        Returns (success: bool, message: str).
        """
        from app.utils.email_helper import send_reset_email
        from flask import url_for

        GENERIC_MSG        = "If an account with this email exists, a password reset link has been sent."
        RATE_LIMIT_SECONDS = 60
        EXPIRY_MINUTES     = 15

        if not email or not email.strip():
            return False, "Please enter your registered email address."

        email = email.strip().lower()

        # Basic email format validation
        if not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email):
            return False, "Please enter a valid email address."

        user = User.get_by_email(email)
        if user and user.status == 'active':

            # ── Rate limit: 1 request per 60 seconds ──────────────
            recent = query_db(
                "SELECT created_at FROM password_reset_tokens "
                "WHERE user_id = ? ORDER BY created_at DESC LIMIT 1",
                (user.id,), one=True
            )
            if recent:
                try:
                    last_req = datetime.strptime(recent['created_at'], '%Y-%m-%d %H:%M:%S')
                    elapsed  = (datetime.utcnow() - last_req).total_seconds()
                    if elapsed < RATE_LIMIT_SECONDS:
                        security_logger.warning(
                            "[PasswordReset] Rate-limit hit | user_id=%s email=%s ip=%s wait=%ds",
                            user.id, email, client_ip, int(RATE_LIMIT_SECONDS - elapsed)
                        )
                        return True, GENERIC_MSG
                except (ValueError, TypeError):
                    pass

            # ── Invalidate all previous unused tokens ──────────────
            execute_db(
                "UPDATE password_reset_tokens SET used = 1 WHERE user_id = ? AND used = 0",
                (user.id,)
            )

            # ── Generate cryptographically secure token ─────────────
            token      = secrets.token_urlsafe(64)
            expires_at = datetime.utcnow() + timedelta(minutes=EXPIRY_MINUTES)

            execute_db(
                "INSERT INTO password_reset_tokens (user_id, token, expires_at) VALUES (?, ?, ?)",
                (user.id, token, expires_at.strftime('%Y-%m-%d %H:%M:%S'))
            )

            # ── Security audit log ─────────────────────────────────
            security_logger.info(
                "[PasswordReset] REQUESTED | user_id=%s username=%s email=%s ip=%s expires=%s",
                user.id, user.username, email, client_ip, expires_at.isoformat()
            )

            # ── Build absolute reset URL ───────────────────────────
            reset_url    = url_for('auth.reset_password', token=token, _external=True)
            display_name = getattr(user, 'full_name', None) or user.username

            # ── Send email ─────────────────────────────────────────
            ok, err = send_reset_email(
                to_email=user.email,
                reset_url=reset_url,
                username=display_name,
                expiry_minutes=EXPIRY_MINUTES
            )
            if not ok:
                security_logger.error(
                    "[PasswordReset] Email FAILED | user_id=%s email=%s error=%s",
                    user.id, email, err
                )
                return False, err

        return True, GENERIC_MSG

    # ------------------------------------------------------------------ #
    #  Token verification                                                 #
    # ------------------------------------------------------------------ #

    @staticmethod
    def verify_reset_token(token):
        """
        Validates a reset token.
        Returns (user, None) on success, or (None, error_message) on failure.
        """
        if not token:
            return None, "Invalid or missing reset token."

        row = query_db(
            "SELECT * FROM password_reset_tokens WHERE token = ?",
            (token,), one=True
        )
        if not row:
            return None, "This reset link is invalid or has already been used."
        if row['used']:
            return None, "This reset link has already been used. Please request a new one."

        try:
            expires_at = datetime.strptime(row['expires_at'], '%Y-%m-%d %H:%M:%S')
        except ValueError:
            return None, "This reset link is invalid."

        if datetime.utcnow() > expires_at:
            return None, (
                "This reset link has expired (links are valid for 15 minutes). "
                "Please request a new one."
            )

        user = User.get_by_id(row['user_id'])
        if not user or user.status != 'active':
            return None, "The account associated with this link is no longer active."

        return user, None

    # ------------------------------------------------------------------ #
    #  Step 2 — Set new password via token                               #
    # ------------------------------------------------------------------ #

    @staticmethod
    def reset_password_with_token(token, new_password, confirm_password, client_ip=None):
        """
        Validates token + strong password policy, resets password (bcrypt via werkzeug),
        marks token as one-time-used, and logs the event.
        Returns (success: bool, message: str).
        """
        if not new_password or not confirm_password:
            return False, "Both password fields are required."
        if new_password != confirm_password:
            return False, "Passwords do not match. Please re-enter both passwords."

        # Enforce strong password policy
        is_valid, pw_err = AuthController.validate_strong_password(new_password)
        if not is_valid:
            return False, pw_err

        # Validate token
        user, token_err = AuthController.verify_reset_token(token)
        if not user:
            return False, token_err

        # Hash and persist (werkzeug uses pbkdf2-sha256 / scrypt — bcrypt-compatible strength)
        from werkzeug.security import generate_password_hash
        hashed = generate_password_hash(new_password)
        try:
            execute_db("UPDATE users SET password_hash = ? WHERE id = ?", (hashed, user.id))
        except Exception as exc:
            security_logger.error(
                "[PasswordReset] DB update FAILED | user_id=%s error=%s", user.id, exc
            )
            return False, "A database error occurred. Please try again."

        # Immediately invalidate token (one-time use)
        execute_db("UPDATE password_reset_tokens SET used = 1 WHERE token = ?", (token,))

        security_logger.info(
            "[PasswordReset] SUCCESS | user_id=%s username=%s ip=%s",
            user.id, user.username, client_ip
        )

        return True, "Your password has been reset successfully. Please login with your new password."

    # ------------------------------------------------------------------ #
    #  Legacy direct-reset (backward compatibility)                      #
    # ------------------------------------------------------------------ #

    @staticmethod
    def forgot_password(username, email, phone, new_password):
        """Legacy: resets password by verifying username + email + phone."""
        if not username or not email or not phone or not new_password:
            return False, "All fields are required to reset the password."

        user = User.get_by_username(username.strip())
        if not user:
            return False, "User details do not match our records."
        if user.email.lower() != email.strip().lower():
            return False, "User details do not match our records."
        if (user.phone or "").strip() != phone.strip():
            return False, "User details do not match our records."

        is_valid, err = User.validate_user_data(user.username, user.email, password=new_password)
        if not is_valid:
            return False, err

        success, msg = User.reset_password_by_admin(user.id, new_password)
        return (True, "Password has been reset successfully. You can now login.") if success else (False, msg)
