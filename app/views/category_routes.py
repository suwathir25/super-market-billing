from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from app.views import login_required, role_required
from app.controllers.category_controller import CategoryController
from app.models.category import Category

category_bp = Blueprint('category', __name__)

@category_bp.route('/categories', methods=['GET'])
@login_required
@role_required('admin', 'manager')
def index():
    search = request.args.get('search')
    status = request.args.get('status')
    categories = CategoryController.list_categories(search, status)
    return render_template('categories.html', categories=categories, search=search, status=status)

@category_bp.route('/categories/add', methods=['POST'])
@login_required
@role_required('admin', 'manager')
def add():
    name = request.form.get('name')
    status = request.form.get('status', 'active')
    file = request.files.get('image')
    
    success, msg = CategoryController.create_category(name, file, status)
    if success:
        flash(msg, "success")
    else:
        flash(msg, "danger")
    return redirect(url_for('category.index'))

@category_bp.route('/categories/edit/<int:category_id>', methods=['POST'])
@login_required
@role_required('admin', 'manager')
def edit(category_id):
    name = request.form.get('name')
    status = request.form.get('status', 'active')
    file = request.files.get('image')
    
    success, msg = CategoryController.update_category(category_id, name, file, status)
    if success:
        flash(msg, "success")
    else:
        flash(msg, "danger")
    return redirect(url_for('category.index'))

@category_bp.route('/categories/toggle/<int:category_id>', methods=['POST'])
@login_required
@role_required('admin', 'manager')
def toggle(category_id):
    cat = Category.get_by_id(category_id)
    if not cat:
        return jsonify({'success': False, 'message': "Category not found."})
        
    new_status = 'inactive' if cat.status == 'active' else 'active'
    success, msg = CategoryController.update_category(category_id, cat.name, file=None, status=new_status)
    if success:
        return jsonify({'success': True, 'message': f"Category status changed to {new_status}.", 'new_status': new_status})
    return jsonify({'success': False, 'message': msg})

@category_bp.route('/categories/delete/<int:category_id>', methods=['POST'])
@login_required
@role_required('admin')
def delete(category_id):
    success, msg = CategoryController.delete_category(category_id)
    if success:
        flash("Category deleted successfully.", "success")
    else:
        flash(msg, "danger")
    return redirect(url_for('category.index'))
