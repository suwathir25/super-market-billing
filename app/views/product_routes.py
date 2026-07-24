from flask import Blueprint, render_template, request, redirect, url_for, flash, Response, jsonify
from app.views import login_required, role_required
from app.controllers.product_controller import ProductController
from app.models.product import Product
from app.models.category import Category
from app.models.database import query_db

product_bp = Blueprint('product', __name__)

@product_bp.route('/products', methods=['GET'])
@login_required
def index():
    search = request.args.get('search', '')
    category_id = request.args.get('category_id')
    stock_status = request.args.get('stock_status', 'all')
    
    # Pagination
    try:
        page = int(request.args.get('page', 1))
    except ValueError:
        page = 1
    limit = 10
    offset = (page - 1) * limit

    # Convert category_id to integer if exists
    cat_id_int = int(category_id) if category_id else None

    products = ProductController.list_products(search, cat_id_int, stock_status, limit, offset)
    total_products = ProductController.get_products_count(search, cat_id_int, stock_status)
    
    # Calculate pages count
    import math
    total_pages = math.ceil(total_products / limit)
    total_pages = max(1, total_pages)

    # Fetch lookup parameters for category filter dropdown
    categories = query_db("SELECT id, name FROM categories WHERE status = 'active'")

    return render_template(
        'products.html',
        products=products,
        categories=categories,
        search=search,
        selected_category=category_id,
        stock_status=stock_status,
        page=page,
        total_pages=total_pages,
        total_products=total_products
    )

@product_bp.route('/products/add', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'manager')
def add():
    if request.method == 'POST':
        file = request.files.get('image')
        success, msg = ProductController.create_product(request.form, file)
        if success:
            flash(msg, "success")
            return redirect(url_for('product.index'))
        flash(msg, "danger")

    categories = query_db("SELECT id, name FROM categories WHERE status = 'active'")
    suppliers = query_db("SELECT id, name FROM suppliers")
    return render_template('product_form.html', product=None, categories=categories, suppliers=suppliers)

@product_bp.route('/products/edit/<int:product_id>', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'manager')
def edit(product_id):
    product = Product.get_by_id(product_id)
    if not product:
        flash("Product not found.", "danger")
        return redirect(url_for('product.index'))

    if request.method == 'POST':
        file = request.files.get('image')
        success, msg = ProductController.update_product(product_id, request.form, file)
        if success:
            flash(msg, "success")
            return redirect(url_for('product.index'))
        flash(msg, "danger")

    categories = query_db("SELECT id, name FROM categories WHERE status = 'active'")
    suppliers = query_db("SELECT id, name FROM suppliers")
    return render_template('product_form.html', product=product, categories=categories, suppliers=suppliers)

@product_bp.route('/products/delete/<int:product_id>', methods=['POST'])
@login_required
@role_required('admin')
def delete(product_id):
    success, msg = ProductController.delete_product(product_id)
    if success:
        flash("Product deleted successfully.", "success")
    else:
        flash(msg, "danger")
    return redirect(url_for('product.index'))

@product_bp.route('/products/export', methods=['GET'])
@login_required
def export_csv():
    csv_data = ProductController.export_to_csv()
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=products_export.csv"}
    )

@product_bp.route('/products/import', methods=['POST'])
@login_required
@role_required('admin', 'manager')
def import_csv():
    file = request.files.get('csv_file')
    if not file:
        flash("Please upload a valid CSV file.", "danger")
        return redirect(url_for('product.index'))

    success_count, errors = ProductController.import_from_csv(file)
    if success_count > 0:
        flash(f"Successfully imported {success_count} products.", "success")
    
    if errors:
        for err in errors[:5]:  # Display first 5 errors to avoid flooding
            flash(err, "warning")
        if len(errors) > 5:
            flash(f"...and {len(errors) - 5} more errors during CSV import.", "warning")

    return redirect(url_for('product.index'))

# JSON API for POS scanning and autocomplete search
@product_bp.route('/api/products/search', methods=['GET'])
@login_required
def api_search():
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify([])

    # Matches exact barcode first, then partial matching by name or SKU
    sql = """
        SELECT id, name, sku, barcode, purchase_price, selling_price, discount, gst_rate, stock_quantity, image_path 
        FROM products 
        WHERE status = 'active' AND (barcode = ? OR name LIKE ? OR sku LIKE ?)
        LIMIT 10
    """
    rows = query_db(sql, (query, f"%{query}%", f"%{query}%"))
    results = []
    for r in rows:
        results.append({
            'id': r['id'],
            'name': r['name'],
            'sku': r['sku'],
            'barcode': r['barcode'] or '',
            'purchase_price': r['purchase_price'],
            'selling_price': r['selling_price'],
            'discount': r['discount'],
            'gst_rate': r['gst_rate'],
            'stock_quantity': r['stock_quantity'],
            'image_path': r['image_path'] or ''
        })
    return jsonify(results)

@product_bp.route('/products/details/<int:product_id>', methods=['GET'])
@login_required
def details(product_id):
    product = Product.get_by_id(product_id)
    if not product:
        flash("Product not found.", "danger")
        return redirect(url_for('product.index'))
    return render_template('product_details.html', product=product)
