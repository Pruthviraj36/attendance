from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_mail import Mail
from flask_migrate import Migrate
from celery import Celery

db = SQLAlchemy()
login_manager = LoginManager()
mail = Mail()
migrate = Migrate()

def make_celery(app_name=__name__):
    return Celery(app_name, backend='redis://localhost:6379/0', broker='redis://localhost:6379/0')

celery = make_celery()
