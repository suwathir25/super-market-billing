from app.models.user import User

class UserController:
    @staticmethod
    def get_all_users():
        """Lists all users (Admin/Manager restricted)."""
        return User.list_all()

    @staticmethod
    def create_user(username, password, email, phone, role):
        """Creates a new user (Admin restricted)."""
        # Admin validation is handled at view/route level
        user_id, err = User.create(username, password, email, phone, role, status='active')
        if err:
            return False, err
        return True, f"User {username} created successfully with role {role}."

    @staticmethod
    def update_user_status(user_id, status):
        """Toggles user status (Admin restricted)."""
        success, err = User.update_status(user_id, status)
        if not success:
            return False, err
        return True, f"User status updated to {status}."

    @staticmethod
    def change_password(user_id, old_password, new_password):
        """Changes user's own password."""
        success, err = User.update_password(user_id, old_password, new_password)
        if not success:
            return False, err
        return True, "Password updated successfully."

    @staticmethod
    def update_profile(user_id, email, phone):
        """Updates user's own profile info."""
        success, err = User.update_profile(user_id, email, phone)
        if not success:
            return False, err
        return True, "Profile details updated successfully."

    @staticmethod
    def admin_reset_password(user_id, new_password):
        """Allows admin to force reset password of a user."""
        success, err = User.reset_password_by_admin(user_id, new_password)
        if not success:
            return False, err
        return True, "User password reset successfully."
