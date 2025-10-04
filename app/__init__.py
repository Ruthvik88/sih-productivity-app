from flask import Flask
from config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

# Create the Flask application instance
app = Flask(__name__)

# Load the configuration from the Config class
app.config.from_object(Config)

# Initialize the database and migration engine
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Import routes and models at the bottom to avoid circular imports
from app import routes, models