# config.py
import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'pureflow-secret-key'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///pureflow.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS') is not None
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    WTF_CSRF_ENABLED = True
    WTF_CSRF_CHECK_DEFAULT = True  # We'll handle CSRF checking manually for API routes