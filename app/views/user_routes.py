from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from app.views import login_required, role_required
from app.controllers.auth_controller import AuthController
from app.controllers.user_controller import UserController
from app.models.user import User

user_bp = Blueprint('user', __name__)

@user_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    user = AuthController.check_logged_in()
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'update_info':
            email = request.form.get('email')
            phone = request.form.get('phone')
            
            success, msg = UserController.update_profile(user.id, email, phone)
            if success:
                flash(msg, "success")
            else:
                flash(msg, "danger")
                
        elif action == 'change_password':
            old_password = request.form.get('old_password')
            new_password = request.form.get('new_password')
            confirm_password = request.form.get('confirm_password')
            
            if new_password != confirm_password:
                flash("New passwords do not match.", "danger")
            else:
                success, msg = UserController.change_password(user.id, old_password, new_password)
                if success:
                    flash(msg, "success")
                else:
                    flash(msg, "danger")
                    
        return redirect(url_for('user.profile'))

    return render_template('profile.html', user=user)

@user_bp.route('/users', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'manager')
def list_users():
    current_user = AuthController.check_logged_in()
    
    if request.method == 'POST':
        # Creating a user - Admin only!
        if current_user.role != 'admin':
            flash("Access denied: Only administrators can create users.", "danger")
            return redirect(url_for('user.list_users'))
            
        username = request.form.get('username')
        email = request.form.get('email')
        phone = request.form.get('phone')
        password = request.form.get('password')
        role = request.form.get('role')
        
        success, msg = UserController.create_user(username, password, email, phone, role)
        if success:
            flash(msg, "success")
        else:
            flash(msg, "danger")
            
        return redirect(url_for('user.list_users'))

    users = UserController.get_all_users()
    return render_template('users.html', users=users, current_user=current_user)

@user_bp.route('/users/<int:user_id>/toggle', methods=['POST'])
@login_required
@role_required('admin')
def toggle_user(user_id):
    current_user = AuthController.check_logged_in()
    if current_user.id == user_id:
        return jsonify({'success': False, 'message': "You cannot deactivate your own account."})
        
    user = User.get_by_id(user_id)
    if not user:
        return jsonify({'success': False, 'message': "User not found."})
        
    new_status = 'inactive' if user.status == 'active' else 'active'
    success, msg = UserController.update_user_status(user_id, new_status)
    
    if success:
        return jsonify({'success': True, 'message': f"User status updated to {new_status}.", 'new_status': new_status})
    return jsonify({'success': False, 'message': msg})

@user_bp.route('/users/<int:user_id>/reset-password', methods=['POST'])
@login_required
@role_required('admin')
def reset_password(user_id):
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')
    
    if not new_password or new_password != confirm_password:
        flash("Passwords do not match or are empty.", "danger")
        return redirect(url_for('user.list_users'))
        
    success, msg = UserController.admin_reset_password(user_id, new_password)
    if success:
        flash(msg, "success")
    else:
        flash(msg, "danger")
        
    return redirect(url_for('user.list_users'))
