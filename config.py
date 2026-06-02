import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-2024')

    # Для локальной разработки и Render
    database_url = os.environ.get('DATABASE_URL', 'postgresql://postgres:ya123@localhost:5432/atelierpro')

    # Render использует postgres://, а SQLAlchemy требует postgresql://
    if database_url and database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)

    SQLALCHEMY_DATABASE_URI = database_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False