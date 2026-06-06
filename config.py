import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = 'atelierpro-secret-key-2024'

    # PostgreSQL (ЗАМЕНИТЕ ваш_пароль на реальный)
    SQLALCHEMY_DATABASE_URI = 'postgresql://postgres:ya123@localhost:5432/atelierpro'

    SQLALCHEMY_TRACK_MODIFICATIONS = False