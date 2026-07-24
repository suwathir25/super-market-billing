import os
import logging

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'super-secret-key-12345-change-in-production')
    # Default SQLite database path
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DATABASE = os.path.join(BASE_DIR, 'supermarket.db')
    DEBUG = True
    # File upload settings
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max upload size
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'app', 'static', 'uploads')

    # --- Email / SMTP settings (for password reset) ---
    # NEVER hardcode credentials here. Use environment variables:
    #   $env:MAIL_USERNAME="yourshop@gmail.com"
    #   $env:MAIL_PASSWORD="xxxx xxxx xxxx xxxx"   # Gmail App Password
    MAIL_SERVER      = os.environ.get('MAIL_SERVER',   'smtp.gmail.com')
    MAIL_PORT        = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS     = True
    MAIL_USERNAME    = os.environ.get('MAIL_USERNAME', '')  # Set via env var
    MAIL_PASSWORD    = os.environ.get('MAIL_PASSWORD', '')  # Set via env var or Settings page
    MAIL_SENDER_NAME = os.environ.get('MAIL_SENDER_NAME', 'SuperMart')

    # Reset token validity (15 minutes — per security requirement)
    RESET_TOKEN_EXPIRY_MINUTES = int(os.environ.get('RESET_TOKEN_EXPIRY_MINUTES', 15))

    # --- Security audit logging ---
    @staticmethod
    def configure_security_logging():
        """Sets up a dedicated security audit log file."""
        log_dir = os.path.join(Config.BASE_DIR, 'logs')
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, 'security.log')

        logger = logging.getLogger('supermart.security')
        logger.setLevel(logging.INFO)

        if not logger.handlers:
            fh = logging.FileHandler(log_path, encoding='utf-8')
            fh.setLevel(logging.INFO)
            fmt = logging.Formatter(
                '%(asctime)s UTC | %(levelname)s | %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            fh.setFormatter(fmt)
            logger.addHandler(fh)
            # Also echo to console during development
            ch = logging.StreamHandler()
            ch.setLevel(logging.WARNING)
            ch.setFormatter(fmt)
            logger.addHandler(ch)
