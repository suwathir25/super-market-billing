import os
import sqlite3
from app import create_app
from app.models.database import init_db, query_db, execute_db
from werkzeug.security import generate_password_hash

app = create_app()

def seed_database():
    """Pre-populates sample data if database tables are empty."""
    with app.app_context():
        # Check if users table is empty
        users_count = query_db("SELECT COUNT(*) as count FROM users", one=True)
        if users_count and users_count['count'] == 0:
            print("Seeding database with default accounts and sample transactions...")
            
            # 1. Seed Users (passwords hashed using werkzeug)
            admin_pwd = generate_password_hash("Admin@123")
            manager_pwd = generate_password_hash("Manager@123")
            cashier_pwd = generate_password_hash("Cashier@123")
            
            execute_db("INSERT INTO users (username, password_hash, email, phone, role, status) VALUES (?, ?, ?, ?, ?, ?)",
                       ('admin', admin_pwd, 'admin@supermart.com', '9876543210', 'admin', 'active'))
            execute_db("INSERT INTO users (username, password_hash, email, phone, role, status) VALUES (?, ?, ?, ?, ?, ?)",
                       ('manager', manager_pwd, 'manager@supermart.com', '9876543211', 'manager', 'active'))
            execute_db("INSERT INTO users (username, password_hash, email, phone, role, status) VALUES (?, ?, ?, ?, ?, ?)",
                       ('cashier', cashier_pwd, 'cashier@supermart.com', '9876543212', 'cashier', 'active'))

            # 2. Seed Categories
            execute_db("INSERT INTO categories (name, status) VALUES (?, ?)", ('Groceries', 'active'))
            execute_db("INSERT INTO categories (name, status) VALUES (?, ?)", ('Dairy', 'active'))
            execute_db("INSERT INTO categories (name, status) VALUES (?, ?)", ('Beverages', 'active'))

            # 3. Seed Suppliers
            execute_db("INSERT INTO suppliers (name, email, phone, address, gst_number) VALUES (?, ?, ?, ?, ?)",
                       ('Global Distributors', 'sales@globaldist.com', '9999988888', '45 Distribution Way, Indiaport', '22AAAAA0000A1Z5'))
            execute_db("INSERT INTO suppliers (name, email, phone, address, gst_number) VALUES (?, ?, ?, ?, ?)",
                       ('Metro Dairy Supplies', 'orders@metrodairy.com', '9999911111', '12 Farmhouse Lane, Grasslands', '22BBBBB1111B2Z6'))

            # 4. Seed Products (including some in low stock alert levels)
            # Milk (Dairy)
            execute_db("""INSERT INTO products (name, sku, barcode, category_id, supplier_id, brand, purchase_price, selling_price, gst_rate, stock_quantity, min_stock, status) 
                          VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                       ('Fresh Milk 1L', 'PROD001', '8901234567890', 2, 2, 'Metro Dairy', 40.0, 48.0, 5.0, 50, 15, 'active'))
            
            # Bread (Groceries) - Low stock alert!
            execute_db("""INSERT INTO products (name, sku, barcode, category_id, supplier_id, brand, purchase_price, selling_price, gst_rate, stock_quantity, min_stock, status) 
                          VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                       ('Whole Wheat Bread', 'PROD002', '8901234567891', 1, 1, 'FreshBake', 22.0, 30.0, 0.0, 8, 10, 'active'))
            
            # Sugar (Groceries) - Low stock alert!
            execute_db("""INSERT INTO products (name, sku, barcode, category_id, supplier_id, brand, purchase_price, selling_price, gst_rate, stock_quantity, min_stock, status) 
                          VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                       ('Refined Sugar 1kg', 'PROD003', '8901234567892', 1, 1, 'SweetLife', 36.0, 44.0, 5.0, 4, 10, 'active'))
            
            # Soda Can (Beverages)
            execute_db("""INSERT INTO products (name, sku, barcode, category_id, supplier_id, brand, purchase_price, selling_price, gst_rate, stock_quantity, min_stock, status) 
                          VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                       ('Sparkling Soda 330ml', 'PROD004', '8901234567893', 3, 1, 'ColaCorp', 12.0, 20.0, 18.0, 120, 20, 'active'))

            # 5. Seed Customers
            execute_db("INSERT INTO customers (name, phone, loyalty_points) VALUES (?, ?, ?)", ('Ravi', '9876543210', 120))
            execute_db("INSERT INTO customers (name, phone, loyalty_points) VALUES (?, ?, ?)", ('Kumar', '9876543211', 80))
            execute_db("INSERT INTO customers (name, phone, loyalty_points) VALUES (?, ?, ?)", ('Priya', '9876543212', 250))

            # 6. Seed Bills
            # Bill 1 - Ravi (₹450)
            b1_id, _ = execute_db("""INSERT INTO bills (bill_number, customer_id, user_id, subtotal, discount_amount, tax_amount, total_amount, payment_method) 
                                     VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                                  ('B001', 1, 3, 410.0, 10.0, 50.0, 450.0, 'Cash'))
            # Milk (5 units: 5 * 48 = 240) + Soda (10 units: 10 * 20 = 200) -> 440 gross
            execute_db("INSERT INTO bill_items (bill_id, product_id, quantity, purchase_price, selling_price, discount_amount, tax_amount, total_amount) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                       (b1_id, 1, 5, 40.0, 48.0, 5.0, 10.0, 245.0))
            execute_db("INSERT INTO bill_items (bill_id, product_id, quantity, purchase_price, selling_price, discount_amount, tax_amount, total_amount) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                       (b1_id, 4, 10, 12.0, 20.0, 5.0, 40.0, 205.0))

            # Bill 2 - Kumar (₹780)
            b2_id, _ = execute_db("""INSERT INTO bills (bill_number, customer_id, user_id, subtotal, discount_amount, tax_amount, total_amount, payment_method) 
                                     VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                                  ('B002', 2, 3, 730.0, 20.0, 70.0, 780.0, 'Card'))
            # Milk (15 units: 15 * 48 = 720) + Bread (2 units: 2 * 30 = 60) -> 780 gross
            execute_db("INSERT INTO bill_items (bill_id, product_id, quantity, purchase_price, selling_price, discount_amount, tax_amount, total_amount) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                       (b2_id, 1, 15, 40.0, 48.0, 15.0, 30.0, 735.0))
            execute_db("INSERT INTO bill_items (bill_id, product_id, quantity, purchase_price, selling_price, discount_amount, tax_amount, total_amount) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                       (b2_id, 2, 2, 22.0, 30.0, 5.0, 40.0, 45.0))

            # Bill 3 - Priya (₹620)
            b3_id, _ = execute_db("""INSERT INTO bills (bill_number, customer_id, user_id, subtotal, discount_amount, tax_amount, total_amount, payment_method) 
                                     VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                                  ('B003', 3, 3, 580.0, 15.0, 55.0, 620.0, 'UPI'))
            # Soda (31 units: 31 * 20 = 620)
            execute_db("INSERT INTO bill_items (bill_id, product_id, quantity, purchase_price, selling_price, discount_amount, tax_amount, total_amount) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                       (b3_id, 4, 31, 12.0, 20.0, 15.0, 55.0, 620.0))

            print("Database successfully seeded with clean sample records.")

if __name__ == '__main__':
    # Initialize the tables from database.sql
    init_db(app)
    # Seed the DB tables if empty
    seed_database()
    # Start local development server
    print("Starting Supermarket Billing Software web server...")
    app.run(debug=True, port=5000)
