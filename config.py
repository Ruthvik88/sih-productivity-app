import os

# Get the absolute path of the directory the script is in
basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    # A secret key is needed for security, e.g., for session cookies
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'

    # Database configuration
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'app.db')
    
    # Disable a feature of Flask-SQLAlchemy that we don't need
    SQLALCHEMY_TRACK_MODIFICATIONS = False