from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.views import login_required, role_required
from app.models.database import query_db, execute_db

customer_bp = Blueprint('customer', __name__, url_prefix='/customers')


@customer_bp.route('/')
@login_required
@role_required('admin', 'manager')
def index():
    search = request.args.get('search', '').strip()
    if search:
        customers = query_db(
            "SELECT * FROM customers WHERE name LIKE ? OR phone LIKE ? ORDER BY created_at DESC",
            (f'%{search}%', f'%{search}%')
        )
    else:
        customers = query_db("SELECT * FROM customers ORDER BY created_at DESC")
    return render_template('customers.html', customers=customers, search=search)


@customer_bp.route('/add', methods=['POST'])
@login_required
@role_required('admin', 'manager')
def add():
    name = request.form.get('name', '').strip()
    phone = request.form.get('phone', '').strip()
    email = request.form.get('email', '').strip()
    address = request.form.get('address', '').strip()
    membership_type = request.form.get('membership_type', 'Normal')

    if not name or not phone:
        flash('Name and phone are required.', 'danger')
        return redirect(url_for('customer.index'))

    existing = query_db("SELECT id FROM customers WHERE phone = ?", (phone,), one=True)
    if existing:
        flash('A customer with this phone number already exists.', 'warning')
        return redirect(url_for('customer.index'))

    execute_db(
        "INSERT INTO customers (name, phone, email, address, membership_type) VALUES (?, ?, ?, ?, ?)",
        (name, phone, email or None, address or None, membership_type)
    )
    flash(f'Customer "{name}" added successfully.', 'success')
    return redirect(url_for('customer.index'))


@customer_bp.route('/edit/<int:customer_id>', methods=['POST'])
@login_required
@role_required('admin', 'manager')
def edit(customer_id):
    name = request.form.get('name', '').strip()
    phone = request.form.get('phone', '').strip()
    email = request.form.get('email', '').strip()
    address = request.form.get('address', '').strip()
    membership_type = request.form.get('membership_type', 'Normal')

    if not name or not phone:
        flash('Name and phone are required.', 'danger')
        return redirect(url_for('customer.index'))

    execute_db(
        "UPDATE customers SET name=?, phone=?, email=?, address=?, membership_type=? WHERE id=?",
        (name, phone, email or None, address or None, membership_type, customer_id)
    )
    flash(f'Customer updated successfully.', 'success')
    return redirect(url_for('customer.index'))


@customer_bp.route('/delete/<int:customer_id>', methods=['POST'])
@login_required
@role_required('admin', 'manager')
def delete(customer_id):
    customer = query_db("SELECT name FROM customers WHERE id = ?", (customer_id,), one=True)
    if not customer:
        flash('Customer not found.', 'danger')
        return redirect(url_for('customer.index'))
    execute_db("DELETE FROM customers WHERE id = ?", (customer_id,))
    flash(f'Customer "{customer["name"]}" deleted.', 'success')
    return redirect(url_for('customer.index'))
