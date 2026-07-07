import os
from werkzeug.utils import secure_filename
from flask import current_app
from app.models.category import Category

class CategoryController:
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

    @staticmethod
    def allowed_file(filename):
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in CategoryController.ALLOWED_EXTENSIONS

    @staticmethod
    def save_image(file):
        """Saves category image and returns the web reference path."""
        if not file or file.filename == '':
            return None
            
        if not CategoryController.allowed_file(file.filename):
            raise ValueError("Invalid image file format. Allowed: png, jpg, jpeg, gif, webp")

        filename = secure_filename(file.filename)
        # Unique naming to avoid collisions
        import time
        filename = f"cat_{int(time.time())}_{filename}"
        
        upload_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'categories')
        os.makedirs(upload_dir, exist_ok=True)
        
        file.save(os.path.join(upload_dir, filename))
        return f"uploads/categories/{filename}"

    @staticmethod
    def list_categories(search=None, status=None):
        return Category.list_all(search, status)

    @staticmethod
    def create_category(name, file=None, status='active'):
        image_path = None
        if file:
            try:
                image_path = CategoryController.save_image(file)
            except ValueError as e:
                return False, str(e)
        
        cat_id, err = Category.create(name, image_path, status)
        if err:
            # Delete uploaded file if DB insertion failed
            if image_path:
                try:
                    os.remove(os.path.join(current_app.root_path, 'static', image_path))
                except OSError:
                    pass
            return False, err
        return True, "Category created successfully."

    @staticmethod
    def update_category(category_id, name, file=None, status='active'):
        image_path = None
        if file and file.filename != '':
            try:
                image_path = CategoryController.save_image(file)
            except ValueError as e:
                return False, str(e)

        success, err = Category.update(category_id, name, image_path, status)
        if not success:
            if image_path:
                try:
                    os.remove(os.path.join(current_app.root_path, 'static', image_path))
                except OSError:
                    pass
            return False, err
        return True, "Category updated successfully."

    @staticmethod
    def delete_category(category_id):
        # We can also clean up the category image file if deleted
        cat = Category.get_by_id(category_id)
        if cat and cat.image_path:
            try:
                os.remove(os.path.join(current_app.root_path, 'static', cat.image_path))
            except OSError:
                pass
        return Category.delete(category_id)
