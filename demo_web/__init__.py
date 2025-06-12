from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager


app = Flask(__name__)
app.config.from_object('demo_web.config.Config')

db = SQLAlchemy(app)

from demo_web.models import db, User 

login_manager = LoginManager()
login_manager.init_app(app)   

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
from . import models, routes

with app.app_context():
    db.create_all()