import re
from app.models.database import query_db, execute_db

class Product:
    def __init__(self, id, name, sku, barcode, category_id, supplier_id, brand, purchase_price,
                 selling_price, discount, gst_rate, hsn_code, expiry_date, stock_quantity, min_stock,
                 image_path, status, created_at, category_name=None, supplier_name=None):
        self.id = id
        self.name = name
        self.sku = sku
        self.barcode = barcode
        self.category_id = category_id
        self.supplier_id = supplier_id
        self.brand = brand
        self.purchase_price = purchase_price
        self.selling_price = selling_price
        self.discount = discount
        self.gst_rate = gst_rate
        self.hsn_code = hsn_code
        self.expiry_date = expiry_date
        self.stock_quantity = stock_quantity
        self.min_stock = min_stock
        self.image_path = image_path
        self.status = status
        self.created_at = created_at
        
        # Joined attributes
        self.category_name = category_name
        self.supplier_name = supplier_name

    @classmethod
    def from_row(cls, row):
        if not row:
            return None
        return cls(
            id=row['id'],
            name=row['name'],
            sku=row['sku'],
            barcode=row['barcode'],
            category_id=row['category_id'],
            supplier_id=row['supplier_id'],
            brand=row['brand'],
            purchase_price=row['purchase_price'],
            selling_price=row['selling_price'],
            discount=row['discount'],
            gst_rate=row['gst_rate'],
            hsn_code=row['hsn_code'],
            expiry_date=row['expiry_date'],
            stock_quantity=row['stock_quantity'],
            min_stock=row['min_stock'],
            image_path=row['image_path'],
            status=row['status'],
            created_at=row['created_at'],
            category_name=row.get('category_name'),
            supplier_name=row.get('supplier_name')
        )

    @classmethod
    def get_by_id(cls, product_id):
        row = query_db("""
            SELECT p.*, c.name as category_name, s.name as supplier_name 
            FROM products p 
            LEFT JOIN categories c ON p.category_id = c.id
            LEFT JOIN suppliers s ON p.supplier_id = s.id
            WHERE p.id = ?
        """, (product_id,), one=True)
        return cls.from_row(row)

    @classmethod
    def get_by_sku(cls, sku):
        if not sku:
            return None
        row = query_db("SELECT * FROM products WHERE LOWER(sku) = LOWER(?)", (sku.strip(),), one=True)
        return cls.from_row(row)

    @classmethod
    def get_by_barcode(cls, barcode):
        if not barcode:
            return None
        row = query_db("SELECT * FROM products WHERE barcode = ?", (barcode.strip(),), one=True)
        return cls.from_row(row)

    @staticmethod
    def validate_product_data(name, sku, purchase_price, selling_price, barcode=None, discount=0.0, gst_rate=0.0, stock_quantity=0, min_stock=5):
        """
        Validates product parameters.
        Returns (is_valid, error_message).
        """
        if not name or not isinstance(name, str) or len(name.strip()) < 2:
            return False, "Product name must be at least 2 characters long."
        
        if not sku or not isinstance(sku, str) or len(sku.strip()) < 3:
            return False, "SKU must be at least 3 characters long."

        try:
            p_price = float(purchase_price)
            s_price = float(selling_price)
            disc = float(discount)
            gst = float(gst_rate)
            stock = int(stock_quantity)
            min_st = int(min_stock)
        except (ValueError, TypeError):
            return False, "Prices, discount, and tax must be numbers. Stock must be integers."

        if p_price < 0 or s_price < 0:
            return False, "Prices must be positive numbers."

        if s_price < p_price:
            return False, "Selling price cannot be less than purchase price."

        if disc < 0 or disc > s_price:
            return False, "Discount cannot be negative or exceed selling price."

        if gst < 0 or gst > 100:
            return False, "GST rate must be between 0% and 100%."

        if stock < 0 or min_st < 0:
            return False, "Stock quantity and minimum stock thresholds cannot be negative."

        return True, ""

    @classmethod
    def create(cls, name, sku, purchase_price, selling_price, category_id=None, supplier_id=None,
               brand=None, barcode=None, discount=0.0, gst_rate=0.0, hsn_code=None, expiry_date=None,
               stock_quantity=0, min_stock=5, image_path=None, status='active'):
        """Creates a product in DB with complete validation checks."""
        # Clean inputs
        name = name.strip()
        sku = sku.strip()
        barcode = barcode.strip() if barcode else None
        brand = brand.strip() if brand else None
        hsn_code = hsn_code.strip() if hsn_code else None
        expiry_date = expiry_date.strip() if expiry_date else None

        is_valid, err = cls.validate_product_data(
            name, sku, purchase_price, selling_price, barcode, discount, gst_rate, stock_quantity, min_stock
        )
        if not is_valid:
            return None, err

        # Check unique constraints
        if cls.get_by_sku(sku):
            return None, f"Product SKU '{sku}' already exists."

        if barcode and cls.get_by_barcode(barcode):
            return None, f"Product Barcode '{barcode}' already exists."

        try:
            prod_id, _ = execute_db("""
                INSERT INTO products (
                    name, sku, barcode, category_id, supplier_id, brand, purchase_price, selling_price,
                    discount, gst_rate, hsn_code, expiry_date, stock_quantity, min_stock, image_path, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                name, sku, barcode, category_id if category_id else None, supplier_id if supplier_id else None,
                brand, float(purchase_price), float(selling_price), float(discount), float(gst_rate),
                hsn_code, expiry_date, int(stock_quantity), int(min_stock), image_path, status
            ))
            return prod_id, ""
        except Exception as e:
            return None, f"Database error: {str(e)}"

    @classmethod
    def update(cls, product_id, name, sku, purchase_price, selling_price, category_id=None, supplier_id=None,
               brand=None, barcode=None, discount=0.0, gst_rate=0.0, hsn_code=None, expiry_date=None,
               stock_quantity=0, min_stock=5, image_path=None, status='active'):
        """Updates product parameters."""
        name = name.strip()
        sku = sku.strip()
        barcode = barcode.strip() if barcode else None
        brand = brand.strip() if brand else None
        hsn_code = hsn_code.strip() if hsn_code else None
        expiry_date = expiry_date.strip() if expiry_date else None

        product = cls.get_by_id(product_id)
        if not product:
            return False, "Product not found."

        is_valid, err = cls.validate_product_data(
            name, sku, purchase_price, selling_price, barcode, discount, gst_rate, stock_quantity, min_stock
        )
        if not is_valid:
            return False, err

        # Unique checks
        existing_sku = cls.get_by_sku(sku)
        if existing_sku and existing_sku.id != product_id:
            return False, f"Product SKU '{sku}' already exists."

        if barcode:
            existing_barcode = cls.get_by_barcode(barcode)
            if existing_barcode and existing_barcode.id != product_id:
                return False, f"Product Barcode '{barcode}' already exists."

        try:
            if image_path:
                execute_db("""
                    UPDATE products SET 
                        name=?, sku=?, barcode=?, category_id=?, supplier_id=?, brand=?, purchase_price=?, 
                        selling_price=?, discount=?, gst_rate=?, hsn_code=?, expiry_date=?, stock_quantity=?, 
                        min_stock=?, image_path=?, status=? 
                    WHERE id=?
                """, (
                    name, sku, barcode, category_id if category_id else None, supplier_id if supplier_id else None,
                    brand, float(purchase_price), float(selling_price), float(discount), float(gst_rate),
                    hsn_code, expiry_date, int(stock_quantity), int(min_stock), image_path, status, product_id
                ))
            else:
                execute_db("""
                    UPDATE products SET 
                        name=?, sku=?, barcode=?, category_id=?, supplier_id=?, brand=?, purchase_price=?, 
                        selling_price=?, discount=?, gst_rate=?, hsn_code=?, expiry_date=?, stock_quantity=?, 
                        min_stock=?, status=? 
                    WHERE id=?
                """, (
                    name, sku, barcode, category_id if category_id else None, supplier_id if supplier_id else None,
                    brand, float(purchase_price), float(selling_price), float(discount), float(gst_rate),
                    hsn_code, expiry_date, int(stock_quantity), int(min_stock), status, product_id
                ))
            return True, ""
        except Exception as e:
            return False, f"Database error: {str(e)}"

    @classmethod
    def delete(cls, product_id):
        product = cls.get_by_id(product_id)
        if not product:
            return False, "Product not found."
        try:
            execute_db("DELETE FROM products WHERE id = ?", (product_id,))
            return True, ""
        except Exception as e:
            return False, f"Database error: {str(e)}"

    @classmethod
    def list_all(cls, search_query=None, category_id=None, stock_status=None, limit=None, offset=None):
        """Lists products with custom pagination and filters."""
        sql = """
            SELECT p.*, c.name as category_name, s.name as supplier_name 
            FROM products p 
            LEFT JOIN categories c ON p.category_id = c.id
            LEFT JOIN suppliers s ON p.supplier_id = s.id
            WHERE 1=1
        """
        params = []

        if search_query:
            sql += " AND (p.name LIKE ? OR p.sku LIKE ? OR p.barcode LIKE ?)"
            q = f"%{search_query.strip()}%"
            params.extend([q, q, q])

        if category_id:
            sql += " AND p.category_id = ?"
            params.append(category_id)

        if stock_status == 'low_stock':
            sql += " AND p.stock_quantity <= p.min_stock AND p.status = 'active'"
        elif stock_status == 'out_of_stock':
            sql += " AND p.stock_quantity = 0"
        elif stock_status == 'in_stock':
            sql += " AND p.stock_quantity > p.min_stock"

        sql += " ORDER BY p.name ASC"

        if limit is not None:
            sql += " LIMIT ?"
            params.append(limit)
            if offset is not None:
                sql += " OFFSET ?"
                params.append(offset)

        rows = query_db(sql, tuple(params))
        return [cls.from_row(row) for row in rows]

    @classmethod
    def get_count(cls, search_query=None, category_id=None, stock_status=None):
        """Calculates total matching products (pagination helper)."""
        sql = "SELECT COUNT(*) as count FROM products p WHERE 1=1"
        params = []

        if search_query:
            sql += " AND (p.name LIKE ? OR p.sku LIKE ? OR p.barcode LIKE ?)"
            q = f"%{search_query.strip()}%"
            params.extend([q, q, q])

        if category_id:
            sql += " AND p.category_id = ?"
            params.append(category_id)

        if stock_status == 'low_stock':
            sql += " AND p.stock_quantity <= p.min_stock AND p.status = 'active'"
        elif stock_status == 'out_of_stock':
            sql += " AND p.stock_quantity = 0"
        elif stock_status == 'in_stock':
            sql += " AND p.stock_quantity > p.min_stock"

        row = query_db(sql, tuple(params), one=True)
        return row['count'] if row else 0
