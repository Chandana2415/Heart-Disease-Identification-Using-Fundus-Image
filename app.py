from flask import Flask, render_template
from config import Config
from models import db
from flask_login import LoginManager
import os

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Initialize extensions
    db.init_app(app)
    login_manager = LoginManager(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'info'
    
    # Create upload directories
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'users'), exist_ok=True)
    os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'admin'), exist_ok=True)
    
    # User loader
    from models import User
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    # Register blueprints
    from routes.auth import auth_bp
    from routes.main import main_bp
    from routes.user import user_bp
    from routes.admin import admin_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    
    # Create tables and admin user
    with app.app_context():
        db.create_all()
        create_admin_user(app)
    
    return app

def create_admin_user(app):
    from models import User, db
    from config import Config
    
    admin_email = app.config.get('ADMIN_EMAIL', 'admin@cardioscan.com')
    admin_password = app.config.get('ADMIN_PASSWORD', 'admin123')
    
    admin_user = User.query.filter_by(email=admin_email).first()
    if not admin_user:
        admin_user = User(
            email=admin_email,
            first_name='Admin',
            last_name='User',
            is_admin=True,
            is_active=True
        )
        admin_user.set_password(admin_password)
        db.session.add(admin_user)
        db.session.commit()
        print(f"Admin user created: {admin_email}")

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0')