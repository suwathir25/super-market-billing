import unittest
import os
import io
import json
from flask import g
from config import Config
from app import create_app
from app.models.database import init_db, query_db, execute_db
from app.models.category import Category
from app.models.product import Product
from app.controllers.category_controller import CategoryController
from app.controllers.product_controller import ProductController
from app.models.user import User

class TestConfig(Config):
    TESTING = True
    DATABASE = 'test_inventory.db'

class InventoryTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
        
        # Initialize schema
        init_db(self.app)
        
        # Insert test users
        User.create('admin', 'Admin@123', 'admin@test.com', '9876543210', 'admin')
        # Insert a sample supplier
        execute_db("INSERT INTO suppliers (name, phone) VALUES ('Dairy Corp', '9999988888')")

    def tearDown(self):
        self.app_context.pop()
        if os.path.exists('test_inventory.db'):
            try:
                os.remove('test_inventory.db')
            except OSError:
                pass

    def test_category_crud(self):
        # 1. Create
        cat_id, err = Category.create("Dairy Products")
        self.assertIsNotNone(cat_id)
        self.assertEqual(err, "")

        # 2. Duplicate Check
        dup_id, err = Category.create("Dairy Products")
        self.assertNil = self.assertIsNone(dup_id)
        self.assertIn("already exists", err)

        # 3. Read
        cat = Category.get_by_id(cat_id)
        self.assertIsNotNone(cat)
        self.assertEqual(cat.name, "Dairy Products")

        # 4. List Active
        cats = Category.list_all()
        self.assertEqual(len(cats), 1)

        # 5. Update
        success, err = Category.update(cat_id, "Fresh Dairy", status="inactive")
        self.assertTrue(success)
        cat = Category.get_by_id(cat_id)
        self.assertEqual(cat.name, "Fresh Dairy")
        self.assertEqual(cat.status, "inactive")

        # 6. Delete
        success, err = Category.delete(cat_id)
        self.assertTrue(success)
        self.assertIsNone(Category.get_by_id(cat_id))

    def test_product_validations(self):
        # Category ID setup
        cat_id, _ = Category.create("Beverages")

        # Valid product creation
        prod_id, err = Product.create(
            name="Soda Can 330ml", sku="SODA-CAN-123", purchase_price=10.0, selling_price=15.0,
            category_id=cat_id, supplier_id=1, barcode="1234567890", stock_quantity=10, min_stock=2
        )
        self.assertIsNotNone(prod_id)
        self.assertEqual(err, "")

        # Test duplicate SKU constraint
        dup_id, err = Product.create(
            name="Soda Bottle 1L", sku="SODA-CAN-123", purchase_price=10.0, selling_price=15.0
        )
        self.assertIsNone(dup_id)
        self.assertIn("already exists", err)

        # Selling price less than purchase price
        err_id, err = Product.create(
            name="Soda Can 330ml", sku="SODA-CAN-OTHER", purchase_price=20.0, selling_price=15.0
        )
        self.assertIsNone(err_id)
        self.assertIn("selling price", err.lower())

        # Negative price validation
        err_id, err = Product.create(
            name="Soda Can 330ml", sku="SODA-CAN-OTHER", purchase_price=-5.0, selling_price=15.0
        )
        self.assertIsNone(err_id)
        self.assertIn("positive", err.lower())

    def test_api_autocomplete_search(self):
        cat_id, _ = Category.create("Snacks")
        Product.create(
            name="Potato Chips Salted", sku="CHIPS-SALT", purchase_price=10.0, selling_price=15.0,
            category_id=cat_id, supplier_id=1, barcode="98765432101", stock_quantity=10, min_stock=2
        )

        with self.client as c:
            # Login session simulation
            with c.session_transaction() as sess:
                sess['user_id'] = 1
                sess['username'] = 'admin'
                sess['role'] = 'admin'
                
            # Search by exact barcode
            res = c.get('/api/products/search?q=98765432101')
            self.assertEqual(res.status_code, 200)
            data = json.loads(res.data)
            self.assertEqual(len(data), 1)
            self.assertEqual(data[0]['name'], "Potato Chips Salted")

            # Search by name match
            res = c.get('/api/products/search?q=Chips')
            data = json.loads(res.data)
            self.assertEqual(len(data), 1)

            # Missing search query parameter
            res = c.get('/api/products/search?q=')
            data = json.loads(res.data)
            self.assertEqual(len(data), 0)

    def test_csv_export(self):
        cat_id, _ = Category.create("Snacks")
        Product.create(
            name="Potato Chips Salted", sku="CHIPS-SALT", purchase_price=10.0, selling_price=15.0,
            category_id=cat_id, supplier_id=1, barcode="98765432101", stock_quantity=10, min_stock=2
        )
        
        csv_str = ProductController.export_to_csv()
        self.assertIn("CHIPS-SALT", csv_str)
        self.assertIn("Potato Chips Salted", csv_str)
        self.assertIn("GST Rate", csv_str)

    def test_csv_import(self):
        csv_content = """Name,SKU,Barcode,Category,Supplier,Brand,Purchase Price,Selling Price,Discount,GST Rate,HSN Code,Expiry Date,Stock Quantity,Min Stock,Status
Chocolate Bar,CHOC-BAR-99,7777777777,Sweets,Dairy Corp,SweetCo,15.0,25.0,0.0,5.0,1806,2027-12-31,50,5,active
"""
        csv_file = io.BytesIO(csv_content.encode('utf-8'))
        csv_file.filename = 'products.csv'
        
        # Test controller import
        success, errors = ProductController.import_from_csv(csv_file)
        self.assertEqual(success, 1)
        self.assertEqual(len(errors), 0)

        # Check DB to confirm details
        prod = Product.get_by_sku("CHOC-BAR-99")
        self.assertIsNotNone(prod)
        self.assertEqual(prod.name, "Chocolate Bar")
        self.assertEqual(prod.selling_price, 25.0)
        self.assertEqual(prod.stock_quantity, 50)
        
        # Check that category 'Sweets' was dynamically auto-created
        cat = Category.get_by_name("Sweets")
        self.assertIsNotNone(cat)
        self.assertEqual(prod.category_id, cat.id)

if __name__ == '__main__':
    unittest.main()
