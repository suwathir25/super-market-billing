from flask import Blueprint, render_template, request
from app.views import login_required, role_required
from app.models.database import query_db

reports_bp = Blueprint('reports', __name__, url_prefix='/reports')


@reports_bp.route('/')
@login_required
@role_required('admin', 'manager')
def index():
    # Overall sales summary
    summary = query_db("""
        SELECT
            COUNT(*) as total_bills,
            COALESCE(SUM(total_amount), 0) as total_revenue,
            COALESCE(SUM(discount_amount), 0) as total_discounts,
            COALESCE(SUM(tax_amount), 0) as total_tax
        FROM bills WHERE status = 'completed'
    """, one=True)

    # Profit calculation
    profit_row = query_db("""
        SELECT COALESCE(SUM((bi.selling_price - bi.purchase_price) * bi.quantity - bi.discount_amount), 0) as gross_profit
        FROM bill_items bi
        JOIN bills b ON bi.bill_id = b.id
        WHERE b.status = 'completed'
    """, one=True)
    gross_profit = profit_row['gross_profit'] if profit_row else 0.0

    # Payment method breakdown
    payment_breakdown = query_db("""
        SELECT payment_method, COUNT(*) as count, COALESCE(SUM(total_amount), 0) as total
        FROM bills WHERE status = 'completed'
        GROUP BY payment_method ORDER BY total DESC
    """)

    # Top 10 products by revenue
    top_products = query_db("""
        SELECT p.name, SUM(bi.quantity) as units_sold,
               SUM(bi.total_amount) as revenue,
               SUM((bi.selling_price - bi.purchase_price) * bi.quantity) as profit
        FROM bill_items bi
        JOIN products p ON bi.product_id = p.id
        JOIN bills b ON bi.bill_id = b.id
        WHERE b.status = 'completed'
        GROUP BY p.id ORDER BY revenue DESC LIMIT 10
    """)

    # Category revenue
    category_revenue = query_db("""
        SELECT c.name as category, COALESCE(SUM(bi.total_amount), 0) as revenue
        FROM bill_items bi
        JOIN products p ON bi.product_id = p.id
        JOIN categories c ON p.category_id = c.id
        JOIN bills b ON bi.bill_id = b.id
        WHERE b.status = 'completed'
        GROUP BY c.id ORDER BY revenue DESC
    """)

    # Monthly trend (last 6 months)
    monthly_trend = query_db("""
        SELECT strftime('%Y-%m', created_at) as month,
               COUNT(*) as bill_count,
               COALESCE(SUM(total_amount), 0) as revenue
        FROM bills WHERE status = 'completed'
        GROUP BY month ORDER BY month DESC LIMIT 6
    """)

    # Low stock report
    low_stock = query_db("""
        SELECT p.name, p.sku, p.stock_quantity, p.min_stock,
               c.name as category
        FROM products p
        LEFT JOIN categories c ON p.category_id = c.id
        WHERE p.stock_quantity <= p.min_stock AND p.status = 'active'
        ORDER BY p.stock_quantity ASC
    """)

    # Top customers
    top_customers = query_db("""
        SELECT c.name, c.phone, c.membership_type, c.total_orders,
               c.total_spent, c.loyalty_points
        FROM customers c
        ORDER BY c.total_spent DESC LIMIT 10
    """)

    currency_row = query_db("SELECT value FROM settings WHERE key='currency'", one=True)
    currency = currency_row['value'] if currency_row else '₹'

    return render_template('reports.html',
                           summary=summary, gross_profit=gross_profit,
                           payment_breakdown=payment_breakdown,
                           top_products=top_products,
                           category_revenue=category_revenue,
                           monthly_trend=monthly_trend,
                           low_stock=low_stock,
                           top_customers=top_customers,
                           currency=currency)
