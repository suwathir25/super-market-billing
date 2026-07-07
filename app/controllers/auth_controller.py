from flask import session
from app.models.user import User

class AuthController:
    @staticmethod
    def login(username, password):
        """
        Handles authentication logic.
        Returns a tuple (success, message_or_user_data).
        """
        if not username or not password:
            return False, "Username and password are required."

        user = User.get_by_username(username.strip())
        if not user:
            return False, "Invalid username or password."

        if user.status != 'active':
            return False, "This account is inactive. Please contact the administrator."

        if not user.verify_password(password):
            return False, "Invalid username or password."

        # Set up session
        session.clear()
        session['user_id'] = user.id
        session['username'] = user.username
        session['role'] = user.role

        return True, {
            'id': user.id,
            'username': user.username,
            'role': user.role
        }

    @staticmethod
    def logout():
        """Clears session variables."""
        session.clear()
        return True

    @staticmethod
    def check_logged_in():
        """Checks if a user is currently logged in via session."""
        if 'user_id' not in session:
            return None
        user = User.get_by_id(session['user_id'])
        if not user or user.status != 'active':
            # Invalidated session
            session.clear()
            return None
        return user

    @staticmethod
    def forgot_password(username, email, phone, new_password):
        """
        Resets password if the user details match (username, email, phone).
        Since this runs locally, matching these three acts as a recovery verification.
        """
        if not username or not email or not phone or not new_password:
            return False, "All fields are required to reset the password."

        user = User.get_by_username(username.strip())
        if not user:
            return False, "User details do not match our records."

        if user.email.lower() != email.strip().lower():
            return False, "User details do not match our records."

        user_phone = user.phone or ""
        if user_phone.strip() != phone.strip():
            return False, "User details do not match our records."

        # Validate password strength
        is_valid, err = User.validate_user_data(user.username, user.email, password=new_password)
        if not is_valid:
            return False, err

        # Reset password
        success, msg = User.reset_password_by_admin(user.id, new_password)
        if success:
            return True, "Password has been reset successfully. You can now login."
        return False, msg
