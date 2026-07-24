from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session, g
from app.views import login_required
from app.models.database import execute_db
from app.controllers.auth_controller import AuthController

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if AuthController.check_logged_in():
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        if request.is_json:
            data     = request.get_json()
            username = data.get('username')
            password = data.get('password')
            is_ajax  = True
        else:
            username = request.form.get('username')
            password = request.form.get('password')
            is_ajax  = False

        success, res = AuthController.login(username, password)
        if success:
            if is_ajax:
                return jsonify({'success': True, 'redirect': url_for('dashboard.index')})
            flash("Welcome back, " + res['username'] + "!", "success")
            return redirect(url_for('dashboard.index'))
        else:
            if is_ajax:
                return jsonify({'success': False, 'message': res})
            flash(res, "danger")

    return render_template('login.html')


@auth_bp.route('/logout')
def logout():
    AuthController.logout()
    flash("You have been logged out.", "info")
    return redirect(url_for('auth.login'))


# ------------------------------------------------------------------ #
#  Forgot Password — Step 1: User enters registered email            #
# ------------------------------------------------------------------ #
@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if AuthController.check_logged_in():
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)

        if request.is_json:
            data     = request.get_json()
            email    = data.get('email', '').strip()
            is_ajax  = True
        else:
            email   = request.form.get('email', '').strip()
            is_ajax = False

        success, msg = AuthController.request_password_reset(email, client_ip=client_ip)

        if is_ajax:
            return jsonify({'success': success, 'message': msg})

        flash(msg, "success" if success else "danger")
        if success:
            return redirect(url_for('auth.forgot_password'))

    return render_template('forgot_password.html')


# ------------------------------------------------------------------ #
#  Reset Password — Step 2: User sets new password via token link    #
# ------------------------------------------------------------------ #
@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if AuthController.check_logged_in():
        return redirect(url_for('dashboard.index'))

    # Validate token on GET — show clear error before rendering the form
    user, token_err = AuthController.verify_reset_token(token)
    if not user:
        flash(token_err, "danger")
        return redirect(url_for('auth.forgot_password'))

    if request.method == 'POST':
        client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)

        if request.is_json:
            data             = request.get_json()
            new_password     = data.get('new_password', '')
            confirm_password = data.get('confirm_password', '')
            is_ajax          = True
        else:
            new_password     = request.form.get('new_password', '')
            confirm_password = request.form.get('confirm_password', '')
            is_ajax          = False

        success, msg = AuthController.reset_password_with_token(
            token, new_password, confirm_password, client_ip=client_ip
        )

        if is_ajax:
            resp = {'success': success, 'message': msg}
            if success:
                resp['redirect'] = url_for('auth.login')
            return jsonify(resp)

        if success:
            flash(msg, "success")
            return redirect(url_for('auth.login'))
        else:
            flash(msg, "danger")

    return render_template('reset_password.html', token=token, username=user.username)


@auth_bp.route('/update_language', methods=['POST'])
@login_required
def update_language():
    data = request.get_json() or {}
    lang = data.get('language')
    if lang in ['en', 'ta', 'hi', 'te']:
        execute_db("UPDATE users SET language = ? WHERE id = ?", (lang, g.user.id))
        session['language'] = lang
        return jsonify({'success': True})
    return jsonify({'success': False, 'message': 'Invalid language'}), 400
