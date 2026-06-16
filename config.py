import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'atelierpro-secret-key-2024')

    # Берём адрес базы из переменной окружения (Render) или из .env (локально)
    database_url = os.environ.get('DATABASE_URL')

    # Если переменной нет — используем SQLite для локальной разработки
    if not database_url:
        database_url = 'sqlite:///atelierpro.db'
        print("⚠️ ВНИМАНИЕ: Переменная DATABASE_URL не найдена. Используется SQLite.")
    else:
        # Render иногда передаёт postgres://, а SQLAlchemy требует postgresql://
        if database_url.startswith('postgres://'):
            database_url = database_url.replace('postgres://', 'postgresql://', 1)

    SQLALCHEMY_DATABASE_URI = database_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False