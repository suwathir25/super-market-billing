import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'super-secret-key-12345-change-in-production')
    # Default SQLite database path
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DATABASE = os.path.join(BASE_DIR, 'supermarket.db')
    DEBUG = True
