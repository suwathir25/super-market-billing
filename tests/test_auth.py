import unittest
import os
import sqlite3
from flask import session, g
from config import Config
from app import create_app
from app.models.database import init_db, query_db, execute_db
from app.models.user import User
from app.controllers.auth_controller import AuthController

class TestConfig(Config):
    TESTING = True
    # Dedicated isolated test database
    DATABASE = 'test_supermarket.db'

class AuthTestCase(unittest.TestCase):
    def setUp(self):
        # Setup application with testing configs
        self.app = create_app(TestConfig)
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
        
        # Initialize isolated database schema
        init_db(self.app)
        
        # Insert test users
        User.create('admin', 'Admin@123', 'admin@test.com', '9876543210', 'admin')
        User.create('cashier', 'Cashier@123', 'cashier@test.com', '9876543211', 'cashier')

    def tearDown(self):
        # Clean up context and delete test database file
        self.app_context.pop()
        if os.path.exists('test_supermarket.db'):
            try:
                os.remove('test_supermarket.db')
            except OSError:
                pass

    def test_password_hashing(self):
        user = User.get_by_username('admin')
        self.assertIsNotNone(user)
        self.assertNotEqual(user.password_hash, 'Admin@123')
        self.assertTrue(user.verify_password('Admin@123'))
        self.assertFalse(user.verify_password('wrongpassword'))

    def test_user_validation(self):
        # Invalid email format
        is_valid, msg = User.validate_user_data('newuser', 'invalidemail', 'Password@123', 'cashier')
        self.assertFalse(is_valid)
        self.assertIn("email", msg.lower())

        # Password length too short
        is_valid, msg = User.validate_user_data('newuser', 'new@test.com', '123', 'cashier')
        self.assertFalse(is_valid)
        self.assertIn("password", msg.lower())

        # Invalid username character
        is_valid, msg = User.validate_user_data('new user', 'new@test.com', 'Password@123', 'cashier')
        self.assertFalse(is_valid)
        self.assertIn("username", msg.lower())

        # Valid input parameters
        is_valid, msg = User.validate_user_data('valid_user', 'new@test.com', 'Password123', 'cashier')
        self.assertTrue(is_valid)

    def test_login_controller(self):
        # Successful login
        with self.app.test_request_context():
            success, res = AuthController.login('admin', 'Admin@123')
            self.assertTrue(success)
            self.assertEqual(res['role'], 'admin')
            self.assertEqual(session['user_id'], res['id'])
            
            # Verify session check works
            current_user = AuthController.check_logged_in()
            self.assertIsNotNone(current_user)
            self.assertEqual(current_user.username, 'admin')

        # Incorrect password login
        with self.app.test_request_context():
            success, res = AuthController.login('admin', 'wrong_pass')
            self.assertFalse(success)
            self.assertIn("invalid", res.lower())

    def test_inactive_user_login(self):
        # Deactivate user
        User.update_status(2, 'inactive')
        with self.app.test_request_context():
            success, res = AuthController.login('cashier', 'Cashier@123')
            self.assertFalse(success)
            self.assertIn("inactive", res.lower())

    def test_forgot_password_recovery(self):
        # Correct verification details
        success, msg = AuthController.forgot_password('admin', 'admin@test.com', '9876543210', 'NewAdmin@123')
        self.assertTrue(success)
        
        # Verify login works with new password
        with self.app.test_request_context():
            success, res = AuthController.login('admin', 'NewAdmin@123')
            self.assertTrue(success)

        # Incorrect phone number match details
        success, msg = AuthController.forgot_password('admin', 'admin@test.com', '0000000000', 'NewAdmin@123')
        self.assertFalse(success)

    def test_unauthorized_dashboard_redirect(self):
        # Accessing dashboard without session should redirect to login
        response = self.client.get('/dashboard')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login', response.headers['Location'])

    def test_role_restricted_users_list(self):
        # Log in as cashier
        with self.client as c:
            with c.session_transaction() as sess:
                sess['user_id'] = 2
                sess['username'] = 'cashier'
                sess['role'] = 'cashier'
            
            # Access user list (restricted to admin/manager)
            response = c.get('/users')
            self.assertEqual(response.status_code, 403)

        # Log in as admin
        with self.client as c:
            with c.session_transaction() as sess:
                sess['user_id'] = 1
                sess['username'] = 'admin'
                sess['role'] = 'admin'
            
            # Access user list (allowed)
            response = c.get('/users')
            self.assertEqual(response.status_code, 200)

if __name__ == '__main__':
    unittest.main()
