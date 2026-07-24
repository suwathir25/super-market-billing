import sqlite3
import os
from flask import current_app, g

def get_db():
    """
    Opens a thread-safe connection to the SQLite database.
    Configures Row factory to return dictionaries.
    """
    if 'db' not in g:
        db_path = current_app.config['DATABASE']
        g.db = sqlite3.connect(db_path, check_same_thread=False)
        g.db.row_factory = sqlite3.Row
        # Enable foreign key support
        g.db.execute("PRAGMA foreign_keys = ON;")
    return g.db

def close_db(e=None):
    """Closes the database connection at the end of request context."""
    db = g.pop('db', None)
    if db is not None:
        db.close()

def query_db(query, args=(), one=False):
    """
    Executes a query and returns results.
    Returns list of dicts or a single dict if one=True.
    """
    db = get_db()
    cur = db.execute(query, args)
    rv = cur.fetchall()
    cur.close()
    if rv:
        return (dict(rv[0]) if one else [dict(r) for r in rv])
    return (None if one else [])

def execute_db(query, args=(), commit=True):
    """
    Executes an INSERT, UPDATE, or DELETE statement.
    Optionally commits the transaction and returns lastrowid and rowcount.
    """
    db = get_db()
    cur = db.execute(query, args)
    lastrowid = cur.lastrowid
    rowcount = cur.rowcount
    cur.close()
    if commit:
        db.commit()
    return lastrowid, rowcount

def run_migrations(conn):
    """Safely adds missing columns and tables to ensure backwards compatibility."""
    cursor = conn.cursor()
    
    # Check customers table columns
    cursor.execute("PRAGMA table_info(customers)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'email' not in columns:
        conn.execute("ALTER TABLE customers ADD COLUMN email TEXT;")
    if 'address' not in columns:
        conn.execute("ALTER TABLE customers ADD COLUMN address TEXT;")
    if 'birthday' not in columns:
        conn.execute("ALTER TABLE customers ADD COLUMN birthday DATE;")
    if 'membership_type' not in columns:
        conn.execute("ALTER TABLE customers ADD COLUMN membership_type TEXT CHECK(membership_type IN ('Normal', 'Silver', 'Gold', 'Premium')) DEFAULT 'Normal';")
    if 'total_orders' not in columns:
        conn.execute("ALTER TABLE customers ADD COLUMN total_orders INTEGER DEFAULT 0;")
    if 'total_spent' not in columns:
        conn.execute("ALTER TABLE customers ADD COLUMN total_spent REAL DEFAULT 0.0;")
    if 'last_purchase' not in columns:
        conn.execute("ALTER TABLE customers ADD COLUMN last_purchase TIMESTAMP;")
        
    # Check users table columns (for Employee Dashboard support)
    cursor.execute("PRAGMA table_info(users)")
    user_columns = [col[1] for col in cursor.fetchall()]
    if 'full_name' not in user_columns:
        conn.execute("ALTER TABLE users ADD COLUMN full_name TEXT;")
    if 'joining_date' not in user_columns:
        conn.execute("ALTER TABLE users ADD COLUMN joining_date DATE;")
    if 'profile_photo' not in user_columns:
        conn.execute("ALTER TABLE users ADD COLUMN profile_photo TEXT;")
    if 'language' not in user_columns:
        conn.execute("ALTER TABLE users ADD COLUMN language TEXT DEFAULT 'en';")
        
    # Check bills table columns (for payment method split support)
    cursor.execute("PRAGMA table_info(bills)")
    bills_columns = [col[1] for col in cursor.fetchall()]
    if 'cash_amount' not in bills_columns:
        conn.execute("ALTER TABLE bills ADD COLUMN cash_amount REAL DEFAULT 0.0;")
    if 'card_amount' not in bills_columns:
        conn.execute("ALTER TABLE bills ADD COLUMN card_amount REAL DEFAULT 0.0;")
    if 'net_banking_amount' not in bills_columns:
        conn.execute("ALTER TABLE bills ADD COLUMN net_banking_amount REAL DEFAULT 0.0;")
        
    # Create held_bills tables
    conn.execute("""
    CREATE TABLE IF NOT EXISTS held_bills (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        hold_number TEXT UNIQUE NOT NULL,
        customer_id INTEGER,
        subtotal REAL NOT NULL,
        discount_amount REAL DEFAULT 0.0,
        tax_amount REAL DEFAULT 0.0,
        total_amount REAL NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE SET NULL
    );
    """)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS held_bill_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        held_bill_id INTEGER NOT NULL,
        product_id INTEGER,
        quantity INTEGER NOT NULL,
        selling_price REAL NOT NULL,
        discount_amount REAL DEFAULT 0.0,
        tax_amount REAL DEFAULT 0.0,
        total_amount REAL NOT NULL,
        FOREIGN KEY (held_bill_id) REFERENCES held_bills(id) ON DELETE CASCADE,
        FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE SET NULL
    );
    """)
    
    # Seeding payment and discount configs if not existing
    conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('upi_id', 'shop@okaxis');")
    conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('merchant_name', 'SuperMart Merchant');")
    conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('merchant_number', '1234567890');")
    conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('discount_normal', '0');")
    conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('discount_silver', '5');")
    conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('discount_gold', '10');")
    conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('discount_premium', '15');")

    # Password reset tokens table
    conn.execute("""
    CREATE TABLE IF NOT EXISTS password_reset_tokens (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        token TEXT NOT NULL UNIQUE,
        expires_at TIMESTAMP NOT NULL,
        used INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    """)
    conn.commit()

def init_db(app):
    """Initializes the database schema using database.sql and runs migrations."""
    db_path = app.config['DATABASE']
    schema_path = os.path.join(app.config['BASE_DIR'], 'database.sql')
    
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        with open(schema_path, 'r', encoding='utf-8') as f:
            schema_sql = f.read()
        conn.executescript(schema_sql)
        conn.commit()
        # Run migrations dynamically to support new columns/tables on existing DBs
        run_migrations(conn)
    except Exception as e:
        print(f"Error initializing database: {e}")
        raise e
    finally:
        conn.close()

def init_app(app):
    """Registers db teardown with Flask application."""
    app.teardown_appcontext(close_db)
