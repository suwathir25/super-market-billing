import os
import csv
import io
from flask import current_app
from werkzeug.utils import secure_filename
from app.models.product import Product
from app.models.category import Category
from app.models.database import query_db

class ProductController:
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}

    @staticmethod
    def allowed_file(filename):
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in ProductController.ALLOWED_EXTENSIONS

    @staticmethod
    def save_image(file):
        """Saves product image, compresses it, and returns the web reference path."""
        if not file or file.filename == '':
            return None
            
        if not ProductController.allowed_file(file.filename):
            raise ValueError("Invalid image file format. Allowed: png, jpg, jpeg, webp")

        # Check file size (max 5 MB)
        file.seek(0, os.SEEK_END)
        size = file.tell()
        file.seek(0)
        if size > 5 * 1024 * 1024:
            raise ValueError("File size exceeds the maximum limit of 5 MB.")

        filename = secure_filename(file.filename)
        import time
        filename = f"prod_{int(time.time())}_{filename}"
        
        upload_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'products')
        os.makedirs(upload_dir, exist_ok=True)
        
        target_path = os.path.join(upload_dir, filename)

        # Open and compress the image
        from PIL import Image
        img = Image.open(file)
        
        # Max width/height limit
        max_size = (800, 800)
        img.thumbnail(max_size, Image.Resampling.LANCZOS if hasattr(Image, 'Resampling') else Image.ANTIALIAS)
        
        # Determine output format
        img_format = img.format if img.format else 'JPEG'
        if img.mode in ('RGBA', 'LA') and img_format.upper() in ('JPEG', 'JPG'):
            img = img.convert('RGB')
            
        img.save(target_path, format=img_format, quality=75, optimize=True)
        return f"uploads/products/{filename}"

    @staticmethod
    def list_products(search=None, category_id=None, stock_status=None, limit=None, offset=None):
        return Product.list_all(search, category_id, stock_status, limit, offset)

    @staticmethod
    def get_products_count(search=None, category_id=None, stock_status=None):
        return Product.get_count(search, category_id, stock_status)

    @staticmethod
    def create_product(form_data, file=None):
        """Validates and processes product insertions."""
        image_path = None
        if file and file.filename != '':
            try:
                image_path = ProductController.save_image(file)
            except ValueError as e:
                return False, str(e)

        cat_id = form_data.get('category_id')
        sup_id = form_data.get('supplier_id')
        
        prod_id, err = Product.create(
            name=form_data.get('name'),
            sku=form_data.get('sku'),
            purchase_price=form_data.get('purchase_price', 0.0),
            selling_price=form_data.get('selling_price', 0.0),
            category_id=int(cat_id) if cat_id else None,
            supplier_id=int(sup_id) if sup_id else None,
            brand=form_data.get('brand'),
            barcode=form_data.get('barcode'),
            discount=form_data.get('discount', 0.0),
            gst_rate=form_data.get('gst_rate', 0.0),
            hsn_code=form_data.get('hsn_code'),
            expiry_date=form_data.get('expiry_date'),
            stock_quantity=form_data.get('stock_quantity', 0),
            min_stock=form_data.get('min_stock', 5),
            image_path=image_path,
            status=form_data.get('status', 'active')
        )
        
        if err:
            if image_path:
                try:
                    os.remove(os.path.join(current_app.root_path, 'static', image_path))
                except OSError:
                    pass
            return False, err
        return True, "Product created successfully."

    @staticmethod
    def update_product(product_id, form_data, file=None):
        """Validates and processes product updates."""
        # Get existing product to delete old file if replaced/removed
        prod = Product.get_by_id(product_id)
        
        clear_image = form_data.get('delete_image') == '1'
        image_path = None

        if file and file.filename != '':
            try:
                image_path = ProductController.save_image(file)
                # If we successfully saved a new image, we don't clear the image
                clear_image = False
            except ValueError as e:
                return False, str(e)

        cat_id = form_data.get('category_id')
        sup_id = form_data.get('supplier_id')

        success, err = Product.update(
            product_id=product_id,
            name=form_data.get('name'),
            sku=form_data.get('sku'),
            purchase_price=form_data.get('purchase_price', 0.0),
            selling_price=form_data.get('selling_price', 0.0),
            category_id=int(cat_id) if cat_id else None,
            supplier_id=int(sup_id) if sup_id else None,
            brand=form_data.get('brand'),
            barcode=form_data.get('barcode'),
            discount=form_data.get('discount', 0.0),
            gst_rate=form_data.get('gst_rate', 0.0),
            hsn_code=form_data.get('hsn_code'),
            expiry_date=form_data.get('expiry_date'),
            stock_quantity=form_data.get('stock_quantity', 0),
            min_stock=form_data.get('min_stock', 5),
            image_path=image_path,
            status=form_data.get('status', 'active'),
            clear_image=clear_image
        )

        if not success:
            if image_path:
                try:
                    os.remove(os.path.join(current_app.root_path, 'static', image_path))
                except OSError:
                    pass
            return False, err
            
        # Clean up old image if cleared or replaced
        if (clear_image or image_path) and prod and prod.image_path:
            try:
                os.remove(os.path.join(current_app.root_path, 'static', prod.image_path))
            except OSError:
                pass
                
        return True, "Product updated successfully."

    @staticmethod
    def delete_product(product_id):
        prod = Product.get_by_id(product_id)
        if prod and prod.image_path:
            try:
                os.remove(os.path.join(current_app.root_path, 'static', prod.image_path))
            except OSError:
                pass
        return Product.delete(product_id)

    @staticmethod
    def export_to_csv():
        """Generates a CSV string representation of all products."""
        products = Product.list_all()
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Headers
        writer.writerow([
            'Name', 'SKU', 'Barcode', 'Category', 'Supplier', 'Brand',
            'Purchase Price', 'Selling Price', 'Discount', 'GST Rate',
            'HSN Code', 'Expiry Date', 'Stock Quantity', 'Min Stock', 'Status'
        ])
        
        for p in products:
            writer.writerow([
                p.name, p.sku, p.barcode or '', p.category_name or '', p.supplier_name or '', p.brand or '',
                p.purchase_price, p.selling_price, p.discount, p.gst_rate,
                p.hsn_code or '', p.expiry_date or '', p.stock_quantity, p.min_stock, p.status
            ])
            
        return output.getvalue()

    @staticmethod
    def import_from_csv(file):
        """
        Parses an uploaded CSV file, resolving category and supplier names.
        Returns a tuple (success_count, error_messages_list).
        """
        if not file or file.filename == '':
            return 0, ["No file was provided."]

        # Read CSV file contents
        if hasattr(file, 'stream'):
            csv_data = file.stream.read()
        else:
            csv_data = file.read()
            
        stream = io.StringIO(csv_data.decode("utf8"), newline=None)
        reader = csv.DictReader(stream)
        
        success_count = 0
        errors = []
        row_number = 1
        
        # Cache existing categories and suppliers for performance
        categories = {c['name'].lower(): c['id'] for c in query_db("SELECT id, name FROM categories")}
        suppliers = {s['name'].lower(): s['id'] for s in query_db("SELECT id, name FROM suppliers")}

        for row in reader:
            row_number += 1
            name = row.get('Name') or row.get('name')
            sku = row.get('SKU') or row.get('sku')
            barcode = row.get('Barcode') or row.get('barcode')
            category_name = row.get('Category') or row.get('category')
            supplier_name = row.get('Supplier') or row.get('supplier')
            brand = row.get('Brand') or row.get('brand')
            purchase_price = row.get('Purchase Price') or row.get('purchase_price') or 0.0
            selling_price = row.get('Selling Price') or row.get('selling_price') or 0.0
            discount = row.get('Discount') or row.get('discount') or 0.0
            gst_rate = row.get('GST Rate') or row.get('gst_rate') or 0.0
            hsn_code = row.get('HSN Code') or row.get('hsn_code')
            expiry_date = row.get('Expiry Date') or row.get('expiry_date')
            stock_quantity = row.get('Stock Quantity') or row.get('stock_quantity') or 0
            min_stock = row.get('Min Stock') or row.get('min_stock') or 5
            status = row.get('Status') or row.get('status') or 'active'

            if not name or not sku:
                errors.append(f"Row {row_number}: Missing required fields (Name or SKU).")
                continue

            # 1. Resolve Category
            cat_id = None
            if category_name:
                category_name_clean = category_name.strip()
                cat_key = category_name_clean.lower()
                if cat_key in categories:
                    cat_id = categories[cat_key]
                else:
                    # Automatically create missing category
                    created_cat_id, _ = Category.create(category_name_clean)
                    if created_cat_id:
                        categories[cat_key] = created_cat_id
                        cat_id = created_cat_id

            # 2. Resolve Supplier
            sup_id = None
            if supplier_name:
                sup_key = supplier_name.strip().lower()
                if sup_key in suppliers:
                    sup_id = suppliers[sup_key]

            # 3. Create Product
            prod_id, err = Product.create(
                name=name, sku=sku, purchase_price=purchase_price, selling_price=selling_price,
                category_id=cat_id, supplier_id=sup_id, brand=brand, barcode=barcode,
                discount=discount, gst_rate=gst_rate, hsn_code=hsn_code, expiry_date=expiry_date,
                stock_quantity=stock_quantity, min_stock=min_stock, status=status
            )
            
            if err:
                errors.append(f"Row {row_number} (SKU: {sku}): {err}")
            else:
                success_count += 1
                
        return success_count, errors
