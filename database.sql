-- Database Schema for Supermarket Billing Software

PRAGMA foreign_keys = ON;

-- 1. Users Table
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    phone TEXT,
    role TEXT CHECK(role IN ('admin', 'manager', 'cashier')) NOT NULL,
    status TEXT CHECK(status IN ('active', 'inactive')) DEFAULT 'active',
    full_name TEXT,
    joining_date DATE,
    profile_photo TEXT,
    language TEXT DEFAULT 'en',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Categories Table
CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    image_path TEXT,
    status TEXT CHECK(status IN ('active', 'inactive')) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Suppliers Table
CREATE TABLE IF NOT EXISTS suppliers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT,
    phone TEXT NOT NULL,
    address TEXT,
    gst_number TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. Products Table
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    sku TEXT UNIQUE NOT NULL,
    barcode TEXT UNIQUE,
    category_id INTEGER,
    supplier_id INTEGER,
    brand TEXT,
    purchase_price REAL NOT NULL,
    selling_price REAL NOT NULL,
    discount REAL DEFAULT 0.0,
    gst_rate REAL DEFAULT 0.0,
    hsn_code TEXT,
    expiry_date DATE,
    stock_quantity INTEGER DEFAULT 0,
    min_stock INTEGER DEFAULT 5,
    image_path TEXT,
    status TEXT CHECK(status IN ('active', 'inactive')) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL,
    FOREIGN KEY (supplier_id) REFERENCES suppliers(id) ON DELETE SET NULL
);

-- 5. Customers Table
CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    phone TEXT UNIQUE NOT NULL,
    loyalty_points INTEGER DEFAULT 0,
    email TEXT,
    address TEXT,
    birthday DATE,
    membership_type TEXT CHECK(membership_type IN ('Normal', 'Silver', 'Gold', 'Premium')) DEFAULT 'Normal',
    total_orders INTEGER DEFAULT 0,
    total_spent REAL DEFAULT 0.0,
    last_purchase TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 6. Bills Table
CREATE TABLE IF NOT EXISTS bills (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bill_number TEXT UNIQUE NOT NULL,
    customer_id INTEGER,
    user_id INTEGER,
    subtotal REAL NOT NULL,
    discount_amount REAL DEFAULT 0.0,
    tax_amount REAL DEFAULT 0.0,
    total_amount REAL NOT NULL,
    payment_method TEXT CHECK(payment_method IN ('Cash', 'Card', 'NetBanking', 'Split')) NOT NULL,
    cash_amount REAL DEFAULT 0.0,
    card_amount REAL DEFAULT 0.0,
    net_banking_amount REAL DEFAULT 0.0,
    status TEXT CHECK(status IN ('completed', 'returned', 'cancelled')) DEFAULT 'completed',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE SET NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);

-- 7. Bill Items Table
CREATE TABLE IF NOT EXISTS bill_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bill_id INTEGER NOT NULL,
    product_id INTEGER,
    quantity INTEGER NOT NULL CHECK(quantity > 0),
    purchase_price REAL NOT NULL,
    selling_price REAL NOT NULL,
    discount_amount REAL DEFAULT 0.0,
    tax_amount REAL DEFAULT 0.0,
    total_amount REAL NOT NULL,
    FOREIGN KEY (bill_id) REFERENCES bills(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE SET NULL
);

-- 8. Stock Adjustments Table
CREATE TABLE IF NOT EXISTS stock_adjustments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    reason TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 9. Expenses Table
CREATE TABLE IF NOT EXISTS expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    amount REAL NOT NULL CHECK(amount >= 0),
    category TEXT NOT NULL,
    description TEXT,
    user_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 10. Settings Table
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- 11. Audit Logs Table
CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    action TEXT NOT NULL,
    details TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);

-- Insert Default Settings
INSERT OR IGNORE INTO settings (key, value) VALUES ('store_name', 'SuperMart');
INSERT OR IGNORE INTO settings (key, value) VALUES ('store_logo', '');
INSERT OR IGNORE INTO settings (key, value) VALUES ('gst_number', '22AAAAA0000A1Z5');
INSERT OR IGNORE INTO settings (key, value) VALUES ('address', '123 SuperMart St, Cityville');
INSERT OR IGNORE INTO settings (key, value) VALUES ('currency', '₹');
INSERT OR IGNORE INTO settings (key, value) VALUES ('tax_rate', '18');
INSERT OR IGNORE INTO settings (key, value) VALUES ('printer_type', 'thermal');
INSERT OR IGNORE INTO settings (key, value) VALUES ('upi_id', 'shop@okaxis');
INSERT OR IGNORE INTO settings (key, value) VALUES ('merchant_name', 'SuperMart Merchant');
INSERT OR IGNORE INTO settings (key, value) VALUES ('merchant_number', '1234567890');
INSERT OR IGNORE INTO settings (key, value) VALUES ('discount_normal', '0');
INSERT OR IGNORE INTO settings (key, value) VALUES ('discount_silver', '5');
INSERT OR IGNORE INTO settings (key, value) VALUES ('discount_gold', '10');
INSERT OR IGNORE INTO settings (key, value) VALUES ('discount_premium', '15');

-- 12. Held Bills Table
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

-- 13. Held Bill Items Table
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
