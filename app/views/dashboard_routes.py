from flask import Blueprint, render_template, session, redirect, url_for
from app.views import login_required, role_required
from app.models.database import query_db

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
@dashboard_bp.route('/dashboard')
@login_required
def index():
    # 1. Fetch dashboard metrics
    sales_data = query_db("SELECT SUM(total_amount) as total FROM bills WHERE status = 'completed'", one=True)
    total_sales = sales_data['total'] if sales_data and sales_data['total'] else 0.0

    products_data = query_db("SELECT COUNT(*) as count FROM products WHERE status = 'active'", one=True)
    total_products = products_data['count'] if products_data else 0

    low_stock_data = query_db("SELECT COUNT(*) as count FROM products WHERE stock_quantity <= min_stock AND status = 'active'", one=True)
    low_stock_count = low_stock_data['count'] if low_stock_data else 0

    bills_data = query_db("SELECT COUNT(*) as count FROM bills", one=True)
    total_bills = bills_data['count'] if bills_data else 0

    customers_data = query_db("SELECT COUNT(*) as count FROM customers", one=True)
    total_customers = customers_data['count'] if customers_data else 0

    # Calculate profit (Total Sales - Total Purchase Cost for completed bills)
    profit_data = query_db("""
        SELECT SUM((bi.selling_price - bi.purchase_price) * bi.quantity - bi.discount_amount) as total_profit
        FROM bill_items bi
        JOIN bills b ON bi.bill_id = b.id
        WHERE b.status = 'completed'
    """, one=True)
    total_profit = profit_data['total_profit'] if profit_data and profit_data['total_profit'] else 0.0

    # 2. Fetch Recent Bills
    recent_bills = query_db("""
        SELECT b.bill_number, COALESCE(c.name, 'Walk-in Customer') as customer_name, b.total_amount, b.created_at, b.status
        FROM bills b
        LEFT JOIN customers c ON b.customer_id = c.id
        ORDER BY b.created_at DESC
        LIMIT 5
    """)

    # 3. Fetch Recent Customers
    recent_customers = query_db("""
        SELECT name, phone, loyalty_points, created_at
        FROM customers
        ORDER BY created_at DESC
        LIMIT 5
    """)

    # 4. Fetch Low Stock Alert Items
    low_stock_items = query_db("""
        SELECT name, stock_quantity, min_stock
        FROM products
        WHERE stock_quantity <= min_stock AND status = 'active'
        ORDER BY stock_quantity ASC
        LIMIT 5
    """)

    # 5. Fetch Top Selling Products
    top_products = query_db("""
        SELECT p.name, SUM(bi.quantity) as total_sold, p.stock_quantity
        FROM bill_items bi
        JOIN products p ON bi.product_id = p.id
        GROUP BY p.id
        ORDER BY total_sold DESC
        LIMIT 5
    """)

    # 6. Fetch settings info
    store_name_data = query_db("SELECT value FROM settings WHERE key = 'store_name'", one=True)
    store_name = store_name_data['value'] if store_name_data else 'SuperMart'

    currency_data = query_db("SELECT value FROM settings WHERE key = 'currency'", one=True)
    currency = currency_data['value'] if currency_data else '₹'

    # 7. Fetch dynamic sales & profit trends
    import datetime
    
    # Weekly raw trends (last 7 days)
    weekly_raw = query_db("""
        SELECT date(b.created_at) as sale_date,
               SUM(b.total_amount) as total_sales,
               COALESCE(SUM((bi.selling_price - bi.purchase_price) * bi.quantity - bi.discount_amount), 0) as total_profit
        FROM bills b
        LEFT JOIN bill_items bi ON b.id = bi.bill_id
        WHERE b.status = 'completed' AND b.created_at >= date('now', '-6 days')
        GROUP BY date(b.created_at)
    """)
    
    # Monthly raw trends (last 6 months)
    monthly_raw = query_db("""
        SELECT strftime('%Y-%m', b.created_at) as month_val,
               SUM(b.total_amount) as total_sales,
               COALESCE(SUM((bi.selling_price - bi.purchase_price) * bi.quantity - bi.discount_amount), 0) as total_profit
        FROM bills b
        LEFT JOIN bill_items bi ON b.id = bi.bill_id
        WHERE b.status = 'completed' AND b.created_at >= date('now', '-180 days')
        GROUP BY strftime('%Y-%m', b.created_at)
    """)

    # Fill weekly datasets (fallback to 0)
    weekly_labels = []
    weekly_sales = []
    weekly_profit = []
    weekly_map = {row['sale_date']: row for row in weekly_raw} if weekly_raw else {}
    for i in range(6, -1, -1):
        day = (datetime.date.today() - datetime.timedelta(days=i)).strftime('%Y-%m-%d')
        display_day = (datetime.date.today() - datetime.timedelta(days=i)).strftime('%a')
        weekly_labels.append(display_day)
        if day in weekly_map:
            weekly_sales.append(float(weekly_map[day]['total_sales'] or 0))
            weekly_profit.append(float(weekly_map[day]['total_profit'] or 0))
        else:
            weekly_sales.append(0.0)
            weekly_profit.append(0.0)

    # Fill monthly datasets (fallback to 0)
    monthly_labels = []
    monthly_sales = []
    monthly_profit = []
    monthly_map = {row['month_val']: row for row in monthly_raw} if monthly_raw else {}
    for i in range(5, -1, -1):
        target_date = datetime.date.today() - datetime.timedelta(days=i*30)
        month_key = target_date.strftime('%Y-%m')
        display_month = target_date.strftime('%b')
        monthly_labels.append(display_month)
        if month_key in monthly_map:
            monthly_sales.append(float(monthly_map[month_key]['total_sales'] or 0))
            monthly_profit.append(float(monthly_map[month_key]['total_profit'] or 0))
        else:
            monthly_sales.append(0.0)
            monthly_profit.append(0.0)

    # Package dashboard view data
    data = {
        "sales": f"{currency}{total_sales:,.2f}",
        "profit": f"{currency}{total_profit:,.2f}",
        "products": total_products,
        "low_stock": low_stock_count,
        "bills": total_bills,
        "customers": total_customers,
        "recent_bills": recent_bills,
        "recent_customers": recent_customers,
        "low_stock_items": low_stock_items,
        "top_products": top_products,
        "store_name": store_name,
        "currency": currency,
        "weekly_labels": weekly_labels,
        "weekly_sales": weekly_sales,
        "weekly_profit": weekly_profit,
        "monthly_labels": monthly_labels,
        "monthly_sales": monthly_sales,
        "monthly_profit": monthly_profit
    }

    return render_template('dashboard.html', data=data)
