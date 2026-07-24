import re
from werkzeug.security import generate_password_hash, check_password_hash
from app.models.database import query_db, execute_db

class User:
    def __init__(self, id, username, password_hash, email, phone, role, status, created_at, language='en'):
        self.id = id
        self.username = username
        self.password_hash = password_hash
        self.email = email
        self.phone = phone
        self.role = role
        self.status = status
        self.created_at = created_at
        self.language = language

    @staticmethod
    def validate_user_data(username, email, password=None, role=None, phone=None):
        """
        Validates username, email, password, and role.
        Returns a tuple (is_valid, error_message).
        """
        # Validate username
        if not username or not isinstance(username, str):
            return False, "Username is required."
        username = username.strip()
        if not re.match(r"^[a-zA-Z0-9_-]{3,20}$", username):
            return False, "Username must be 3-20 characters long and contain only alphanumeric characters, underscores, or hyphens."

        # Validate email
        if not email or not isinstance(email, str):
            return False, "Email is required."
        email = email.strip()
        if not re.match(r"^[^@]+@[^@]+\.[^@]+$", email):
            return False, "Invalid email address format."

        # Validate password if provided
        if password is not None:
            if not isinstance(password, str) or len(password) < 6:
                return False, "Password must be at least 6 characters long."
            if not any(c.isalpha() for c in password) or not any(c.isdigit() for c in password):
                return False, "Password must contain both letters and numbers."

        # Validate role if provided
        if role is not None:
            if role not in ['admin', 'manager', 'cashier']:
                return False, "Role must be one of: admin, manager, cashier."

        # Validate phone if provided
        if phone:
            phone = phone.strip()
            if not re.match(r"^\+?[0-9]{10,15}$", phone):
                return False, "Phone number must be between 10 and 15 digits."

        return True, ""

    @classmethod
    def from_row(cls, row):
        if not row:
            return None
        return cls(
            id=row['id'],
            username=row['username'],
            password_hash=row['password_hash'],
            email=row['email'],
            phone=row['phone'],
            role=row['role'],
            status=row['status'],
            created_at=row['created_at'],
            language=row.get('language', 'en') or 'en'
        )

    @classmethod
    def get_by_id(cls, user_id):
        row = query_db("SELECT * FROM users WHERE id = ?", (user_id,), one=True)
        return cls.from_row(row)

    @classmethod
    def get_by_username(cls, username):
        row = query_db("SELECT * FROM users WHERE username = ?", (username,), one=True)
        return cls.from_row(row)

    @classmethod
    def get_by_email(cls, email):
        row = query_db("SELECT * FROM users WHERE email = ?", (email,), one=True)
        return cls.from_row(row)

    @classmethod
    def create(cls, username, password, email, phone, role, status='active'):
        """
        Validates, hashes password, and creates a user in the database.
        Returns (user_id, error_message).
        """
        is_valid, err = cls.validate_user_data(username, email, password, role, phone)
        if not is_valid:
            return None, err

        # Check uniqueness
        if cls.get_by_username(username):
            return None, "Username already exists."
        if cls.get_by_email(email):
            return None, "Email address already registered."

        hashed_password = generate_password_hash(password)
        try:
            user_id, _ = execute_db(
                "INSERT INTO users (username, password_hash, email, phone, role, status) VALUES (?, ?, ?, ?, ?, ?)",
                (username.strip(), hashed_password, email.strip(), phone.strip() if phone else None, role, status)
            )
            return user_id, ""
        except Exception as e:
            return None, f"Database error occurred: {str(e)}"

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    @classmethod
    def update_profile(cls, user_id, email, phone):
        """Updates contact info for a user."""
        user = cls.get_by_id(user_id)
        if not user:
            return False, "User not found."

        # Validate username is kept, just validate email and phone
        is_valid, err = cls.validate_user_data(user.username, email, phone=phone)
        if not is_valid:
            return False, err

        # Check unique email (if changed)
        if email.strip() != user.email:
            existing = cls.get_by_email(email)
            if existing and existing.id != user_id:
                return False, "Email address is already in use by another user."

        try:
            execute_db(
                "UPDATE users SET email = ?, phone = ? WHERE id = ?",
                (email.strip(), phone.strip() if phone else None, user_id)
            )
            return True, ""
        except Exception as e:
            return False, f"Database error: {str(e)}"

    @classmethod
    def update_password(cls, user_id, old_password, new_password):
        """Allows a user to change their password securely."""
        user = cls.get_by_id(user_id)
        if not user:
            return False, "User not found."

        if not user.verify_password(old_password):
            return False, "Incorrect current password."

        # Validate new password
        is_valid, err = cls.validate_user_data(user.username, user.email, password=new_password)
        if not is_valid:
            return False, err

        hashed_password = generate_password_hash(new_password)
        try:
            execute_db("UPDATE users SET password_hash = ? WHERE id = ?", (hashed_password, user_id))
            return True, ""
        except Exception as e:
            return False, f"Database error: {str(e)}"

    @classmethod
    def reset_password_by_admin(cls, user_id, new_password):
        """Allows admin to reset a user's password."""
        user = cls.get_by_id(user_id)
        if not user:
            return False, "User not found."

        is_valid, err = cls.validate_user_data(user.username, user.email, password=new_password)
        if not is_valid:
            return False, err

        hashed_password = generate_password_hash(new_password)
        try:
            execute_db("UPDATE users SET password_hash = ? WHERE id = ?", (hashed_password, user_id))
            return True, ""
        except Exception as e:
            return False, f"Database error: {str(e)}"

    @classmethod
    def update_status(cls, user_id, status):
        """Sets user status to active or inactive."""
        if status not in ['active', 'inactive']:
            return False, "Invalid status values."
        try:
            _, count = execute_db("UPDATE users SET status = ? WHERE id = ?", (status, user_id))
            if count == 0:
                return False, "User not found."
            return True, ""
        except Exception as e:
            return False, f"Database error: {str(e)}"

    @classmethod
    def list_all(cls):
        rows = query_db("SELECT * FROM users ORDER BY username ASC")
        return [cls.from_row(row) for row in rows]
