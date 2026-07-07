import os
from flask import Flask, render_template, session, g
from config import Config
from app.models import database
from app.models.database import query_db

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize Database handlers
    database.init_app(app)

    # Register Blueprints
    from app.views.auth_routes import auth_bp
    from app.views.dashboard_routes import dashboard_bp
    from app.views.user_routes import user_bp
    from app.views.category_routes import category_bp
    from app.views.product_routes import product_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(category_bp)
    app.register_blueprint(product_bp)

    # Inject store settings globally into all templates
    @app.context_processor
    def inject_settings():
        # Avoid running DB queries if not in app/request context or database not initialized yet
        try:
            store_name_row = query_db("SELECT value FROM settings WHERE key = 'store_name'", one=True)
            store_name = store_name_row['value'] if store_name_row else 'SuperMart'
            currency_row = query_db("SELECT value FROM settings WHERE key = 'currency'", one=True)
            currency = currency_row['value'] if currency_row else '₹'
        except Exception:
            store_name = 'SuperMart'
            currency = '₹'
            
        return {
            'store_name': store_name,
            'currency': currency,
            'current_user': g.get('user', None)
        }

    # Setup request-bound user global object
    @app.before_request
    def load_logged_in_user():
        from app.models.user import User
        user_id = session.get('user_id')
        if user_id is None:
            g.user = None
        else:
            g.user = User.get_by_id(user_id)

    # Error handling routes
    @app.errorhandler(403)
    def forbidden_error(error):
        return render_template('errors/403.html'), 403

    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        return render_template('errors/500.html'), 500

    return app
