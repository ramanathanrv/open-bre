from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from models import db 


app = Flask(__name__)

# Configure your database URI
app.config['SECRET_KEY'] = 'redyellowparrot26oct'  # 🔑 Required for CSRF
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///mydatabase.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
migrate = Migrate(app, db)  # Initialize Flask-Migrate

# Import routes at the end to avoid circular imports
import routes