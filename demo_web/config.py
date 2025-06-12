import secrets
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class Config:
    #SECRET_KEY = secrets.token_hex(16)
    SECRET_KEY = 'your-fixed-secret-key-here-for-development'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(BASE_DIR, 'site.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False