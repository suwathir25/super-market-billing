from flask import Blueprint, render_template, request, redirect, url_for, flash, session, g, jsonify, make_response
from app.views import login_required
from app.models.database import query_db, execute_db

pos_bp = Blueprint('pos', __name__, url_prefix='/pos')


def _next_bill_number():
    """Generate the next sequential invoice number like INV-2026-000001."""
    from datetime import datetime
    year = datetime.utcnow().year
    row = query_db("SELECT bill_number FROM bills ORDER BY id DESC LIMIT 1", one=True)
    if row:
        try:
            # Expected format: INV-YYYY-XXXXXX
            parts = row['bill_number'].split('-')
            last_seq = int(parts[-1])
            return f"INV-{year}-{last_seq + 1:06d}"
        except (ValueError, IndexError, AttributeError):
            pass
    return f"INV-{year}-000001"


@pos_bp.route('/')
@login_required
def index():
    products = query_db(
        "SELECT p.*, c.name as category_name FROM products p "
        "LEFT JOIN categories c ON p.category_id = c.id "
        "WHERE p.status = 'active' AND p.stock_quantity > 0 ORDER BY p.name"
    )
    customers = query_db("SELECT id, name, phone, loyalty_points, membership_type FROM customers ORDER BY name")
    categories = query_db("SELECT id, name FROM categories WHERE status='active' ORDER BY name")
    currency_row = query_db("SELECT value FROM settings WHERE key='currency'", one=True)
    currency = currency_row['value'] if currency_row else '₹'
    next_bill = _next_bill_number()
    return render_template('pos.html', products=products, customers=customers,
                           categories=categories, currency=currency, next_bill=next_bill)


@pos_bp.route('/checkout', methods=['POST'])
@login_required
def checkout():
    """Process a sale and save the bill with support for cash, card, net banking, or split payments.
    Expected form fields:
    - customer_id (optional)
    - payment_method (Cash, Card, NetBanking, Split)
    - discount_amount
    - items (JSON list)
    For Split, additional fields:
    - split_cash_amount, split_card_amount, split_upi_amount (optional, sum must equal total)
    """,
      
    import json

    customer_id = request.form.get('customer_id') or None
    payment_method = request.form.get('payment_method', 'Cash')
    discount_amount = float(request.form.get('discount_amount', 0) or 0)
    items_json = request.form.get('items', '[]')

    try:
        items = json.loads(items_json)
    except (ValueError, TypeError):
        flash('Invalid cart data.', 'danger')
        return redirect(url_for('pos.index'))

    if not items:
        flash('Cart is empty. Add products before checkout.', 'warning')
        return redirect(url_for('pos.index'))

    subtotal = sum(float(i['selling_price']) * int(i['quantity']) for i in items)
    tax_amount = sum(float(i.get('tax_amount', 0)) for i in items)
    total_amount = subtotal + tax_amount - discount_amount
    bill_number = _next_bill_number()

    # Parse split payments if method is Split
    split_cash = float(request.form.get('split_cash_amount', 0) or 0)
    split_card = float(request.form.get('split_card_amount', 0) or 0)
    split_net = float(request.form.get('split_net_amount', 0) or 0)
    
    # Determine final payment amounts
    if payment_method == 'Split':
        total_split = split_cash + split_card + split_net
        if abs(total_split - total_amount) > 0.01:
            flash('Split payment amounts do not total the grand total.', 'danger')
            return redirect(url_for('pos.index'))
        cash_amount = split_cash
        card_amount = split_card
        net_banking_amount = split_net
    else:
        cash_amount = total_amount if payment_method == 'Cash' else 0
        card_amount = total_amount if payment_method == 'Card' else 0
        net_banking_amount = total_amount if payment_method == 'NetBanking' else 0
    
    db_payment_method = 'UPI' if payment_method == 'NetBanking' else payment_method

    # Insert bill with detailed amounts
    bill_id, _ = execute_db(
        """INSERT INTO bills (bill_number, customer_id, user_id, subtotal, discount_amount, tax_amount, total_amount, payment_method, cash_amount, card_amount, net_banking_amount, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (bill_number, customer_id, g.user.id, subtotal, discount_amount, tax_amount, total_amount, db_payment_method, cash_amount, card_amount, net_banking_amount, 'completed')
    )
    
    # Insert bill items and deduct stock (same as before)
    for item in items:
        qty = int(item['quantity'])
        sp = float(item['selling_price'])
        pp = float(item.get('purchase_price', 0))
        item_tax = float(item.get('tax_amount', 0))
        item_disc = float(item.get('discount_amount', 0))
        item_total = sp * qty + item_tax - item_disc
        
        execute_db(
            """INSERT INTO bill_items (bill_id, product_id, quantity, purchase_price, selling_price, discount_amount, tax_amount, total_amount)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (bill_id, item['product_id'], qty, pp, sp, item_disc, item_tax, item_total)
        )
        # Deduct stock
        execute_db(
            "UPDATE products SET stock_quantity = stock_quantity - ? WHERE id = ?",
            (qty, item['product_id'])
        )
    
    # Update customer stats if linked
    if customer_id:
        execute_db(
            "UPDATE customers SET total_orders = total_orders + 1, total_spent = total_spent + ?, last_purchase = CURRENT_TIMESTAMP WHERE id = ?",
            (total_amount, customer_id)
        )
    currency_row = query_db("SELECT value FROM settings WHERE key='currency'", one=True)
    currency = currency_row['value'] if currency_row else '₹'
    flash(f'Bill {bill_number} created successfully! Total: {currency}{total_amount:.2f}', 'success')
    return redirect(url_for('pos.receipt', bill_id=bill_id))


@pos_bp.route('/receipt/<int:bill_id>')
@login_required
def receipt(bill_id):
    """Render a beautiful, printable HTML receipt for the given bill."""
    bill = query_db("SELECT * FROM bills WHERE id = ?", (bill_id,), one=True)
    items = query_db("SELECT bi.*, p.name as product_name, p.image_path as product_image_path FROM bill_items bi JOIN products p ON bi.product_id = p.id WHERE bill_id = ?", (bill_id,))
    if not bill:
        flash('Bill not found.', 'danger')
        return redirect(url_for('pos.index'))

    # Generate UPI QR code if the payment method is NetBanking
    qr_data_uri = None
    if bill['payment_method'] in ('NetBanking', 'UPI'):
        import io
        import base64
        import qrcode
        upi_url = f"upi://pay?pa=suwathi387@oksbi&pn=Suwathi&aid=uGICAgODAgKqmFg&am={bill['total_amount']:.2f}&cu=INR"
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=4,
        )
        qr.add_data(upi_url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        qr_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
        qr_data_uri = f"data:image/png;base64,{qr_base64}"

    currency_row = query_db("SELECT value FROM settings WHERE key='currency'", one=True)
    currency = currency_row['value'] if currency_row else '₹'

    return render_template('receipt.html', bill=bill, items=items, qr_data_uri=qr_data_uri, currency=currency)
