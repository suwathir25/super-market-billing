from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, g
from app.views import login_required, role_required
from app.models.database import query_db, execute_db

settings_bp = Blueprint('settings', __name__, url_prefix='/settings')

SETTINGS_KEYS = [
    'store_name', 'gst_number', 'address', 'currency', 'tax_rate',
    'printer_type', 'upi_id', 'merchant_name', 'merchant_number',
    'discount_normal', 'discount_silver', 'discount_gold', 'discount_premium',
    # Email / SMTP settings (for password reset)
    'mail_server', 'mail_port', 'mail_username', 'mail_sender_name',
    'reset_token_expiry_minutes'
]
# mail_password saved separately — only written when non-empty
MAIL_PASSWORD_KEY = 'mail_password'


@settings_bp.route('/', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def index():
    if request.method == 'POST':
        for key in SETTINGS_KEYS:
            value = request.form.get(key, '').strip()
            existing = query_db("SELECT key FROM settings WHERE key = ?", (key,), one=True)
            if existing:
                execute_db("UPDATE settings SET value = ? WHERE key = ?", (value, key))
            else:
                execute_db("INSERT INTO settings (key, value) VALUES (?, ?)", (key, value))

        # Only update mail_password when admin explicitly types a new one
        new_pw = request.form.get(MAIL_PASSWORD_KEY, '').strip()
        if new_pw:
            existing_pw = query_db(
                "SELECT key FROM settings WHERE key = ?", (MAIL_PASSWORD_KEY,), one=True
            )
            if existing_pw:
                execute_db(
                    "UPDATE settings SET value = ? WHERE key = ?",
                    (new_pw, MAIL_PASSWORD_KEY)
                )
            else:
                execute_db(
                    "INSERT INTO settings (key, value) VALUES (?, ?)",
                    (MAIL_PASSWORD_KEY, new_pw)
                )

        flash('Settings saved successfully.', 'success')
        return redirect(url_for('settings.index'))

    settings_rows = query_db("SELECT key, value FROM settings")
    settings = {row['key']: row['value'] for row in settings_rows} if settings_rows else {}
    return render_template('settings.html', settings=settings)


# ─────────────────────────────────────────────────────────────────────────────
#  SMTP diagnostic — tests each step of the Gmail connection chain
# ─────────────────────────────────────────────────────────────────────────────
@settings_bp.route('/smtp-diagnose', methods=['POST'])
@login_required
@role_required('admin')
def smtp_diagnose():
    """
    Runs a non-destructive step-by-step SMTP diagnostic (no email sent).
    Returns JSON: { config, steps: [{name, ok, detail}], overall }
    """
    from app.utils.email_helper import diagnose_smtp
    result = diagnose_smtp()
    return jsonify(result)


# ─────────────────────────────────────────────────────────────────────────────
#  Send a test email to a specified address
# ─────────────────────────────────────────────────────────────────────────────
@settings_bp.route('/test-email', methods=['POST'])
@login_required
@role_required('admin')
def test_email():
    """
    Sends a real test email.
    Body: { "to": "someone@gmail.com" }  (optional — defaults to admin's own email)
    """
    from app.utils.email_helper import send_test_email

    data     = request.get_json(silent=True) or {}
    to_email = (data.get('to') or '').strip()

    # Fall back to the admin's own account email
    if not to_email:
        to_email = (g.user.email or '').strip() if g.user else ''

    if not to_email:
        return jsonify({
            'success': False,
            'message': (
                'No recipient email. Either pass {"to":"email@example.com"} in the request '
                'or set an email address on your admin profile.'
            )
        })

    ok, msg = send_test_email(to_email)
    return jsonify({'success': ok, 'message': msg})
