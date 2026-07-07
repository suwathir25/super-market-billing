from functools import wraps
from flask import session, redirect, url_for, flash, request, abort
from app.controllers.auth_controller import AuthController

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = AuthController.check_logged_in()
        if not user:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = AuthController.check_logged_in()
            if not user:
                return redirect(url_for('auth.login'))
            if user.role not in roles:
                flash("Access denied: You do not have permissions for this page.", "danger")
                return abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator
