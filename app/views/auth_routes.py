from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from app.controllers.auth_controller import AuthController

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    # If already logged in, redirect to dashboard
    if AuthController.check_logged_in():
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        # Accept JSON (AJAX) or Form data
        if request.is_json:
            data = request.get_json()
            username = data.get('username')
            password = data.get('password')
            is_ajax = True
        else:
            username = request.form.get('username')
            password = request.form.get('password')
            is_ajax = False

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

@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if AuthController.check_logged_in():
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        if request.is_json:
            data = request.get_json()
            username = data.get('username')
            email = data.get('email')
            phone = data.get('phone')
            new_password = data.get('new_password')
            is_ajax = True
        else:
            username = request.form.get('username')
            email = request.form.get('email')
            phone = request.form.get('phone')
            new_password = request.form.get('new_password')
            is_ajax = False

        success, msg = AuthController.forgot_password(username, email, phone, new_password)
        if success:
            if is_ajax:
                return jsonify({'success': True, 'message': msg, 'redirect': url_for('auth.login')})
            flash(msg, "success")
            return redirect(url_for('auth.login'))
        else:
            if is_ajax:
                return jsonify({'success': False, 'message': msg})
            flash(msg, "danger")

    return render_template('forgot_password.html')
