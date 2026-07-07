from app.models.database import query_db, execute_db

class Category:
    def __init__(self, id, name, image_path, status, created_at):
        self.id = id
        self.name = name
        self.image_path = image_path
        self.status = status
        self.created_at = created_at

    @classmethod
    def from_row(cls, row):
        if not row:
            return None
        return cls(
            id=row['id'],
            name=row['name'],
            image_path=row['image_path'],
            status=row['status'],
            created_at=row['created_at']
        )

    @classmethod
    def get_by_id(cls, category_id):
        row = query_db("SELECT * FROM categories WHERE id = ?", (category_id,), one=True)
        return cls.from_row(row)

    @classmethod
    def get_by_name(cls, name):
        row = query_db("SELECT * FROM categories WHERE LOWER(name) = LOWER(?)", (name.strip(),), one=True)
        return cls.from_row(row)

    @classmethod
    def create(cls, name, image_path=None, status='active'):
        """Creates a category with name validation."""
        name = name.strip()
        if not name:
            return None, "Category name is required."
        
        # Check uniqueness
        if cls.get_by_name(name):
            return None, f"Category '{name}' already exists."

        if status not in ['active', 'inactive']:
            status = 'active'

        try:
            cat_id, _ = execute_db(
                "INSERT INTO categories (name, image_path, status) VALUES (?, ?, ?)",
                (name, image_path, status)
            )
            return cat_id, ""
        except Exception as e:
            return None, f"Database error: {str(e)}"

    @classmethod
    def update(cls, category_id, name, image_path=None, status='active'):
        """Updates category name, image path, status."""
        name = name.strip()
        if not name:
            return False, "Category name is required."

        category = cls.get_by_id(category_id)
        if not category:
            return False, "Category not found."

        # Unique name constraint
        existing = cls.get_by_name(name)
        if existing and existing.id != category_id:
            return False, f"Category '{name}' already exists."

        if status not in ['active', 'inactive']:
            status = 'active'

        try:
            if image_path:
                execute_db(
                    "UPDATE categories SET name = ?, image_path = ?, status = ? WHERE id = ?",
                    (name, image_path, status, category_id)
                )
            else:
                execute_db(
                    "UPDATE categories SET name = ?, status = ? WHERE id = ?",
                    (name, status, category_id)
                )
            return True, ""
        except Exception as e:
            return False, f"Database error: {str(e)}"

    @classmethod
    def delete(cls, category_id):
        """Deletes category if no products belong to it, or sets category_id to NULL in products."""
        # SQLite handles setting referencing product category_id to NULL if ON DELETE SET NULL is enabled.
        # But we can check if it exists first
        category = cls.get_by_id(category_id)
        if not category:
            return False, "Category not found."
        
        try:
            execute_db("DELETE FROM categories WHERE id = ?", (category_id,))
            return True, ""
        except Exception as e:
            return False, f"Database error: {str(e)}"

    @classmethod
    def list_all(cls, search_query=None, status_filter=None):
        """Lists categories with search filters."""
        sql = "SELECT * FROM categories WHERE 1=1"
        params = []

        if search_query:
            sql += " AND name LIKE ?"
            params.append(f"%{search_query.strip()}%")

        if status_filter in ['active', 'inactive']:
            sql += " AND status = ?"
            params.append(status_filter)

        sql += " ORDER BY name ASC"
        rows = query_db(sql, tuple(params))
        return [cls.from_row(row) for row in rows]
