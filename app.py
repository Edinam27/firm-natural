# app.py
from flask import Flask
from extensions import db, login_manager
from config import Config
from flask_wtf.csrf import CSRFProtect

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'pureflow-secret-key'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///pureflow.db'
    
    csrf = CSRFProtect(app)
    
    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'main.login'
    login_manager.login_message_category = 'info'

    # Import models
    from models import User, SubscriptionPlan

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Register blueprints
    from routes import bp
    app.register_blueprint(bp)

    # Create tables within app context
    with app.app_context():
        db.create_all()
        from routes import initialize_subscription_plans
        initialize_subscription_plans()

    return app



app = create_app(Config)

if __name__ == '__main__':
    app.run(debug=True)