from flask import Flask
from flask_login import LoginManager
from config import Config
from models import db, User, WorkingHours
from auth import auth_bp
from routes import main_bp
import os

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


app.register_blueprint(auth_bp)
app.register_blueprint(main_bp)

with app.app_context():
    db.create_all()

    # Создаём мастера, если его нет
    if not User.query.filter_by(role='master').first():
        from werkzeug.security import generate_password_hash

        master = User(
            email='master@atelier.ru',
            password_hash=generate_password_hash('admin123'),
            name='Ирина Пименова',
            phone='+7-999-123-45-67',
            role='master'
        )
        db.session.add(master)
        db.session.commit()
        print('Создан мастер: master@atelier.ru / admin123')

    # Создаём рабочие часы по умолчанию, если их нет
    if WorkingHours.query.count() == 0:
        days = [
            (0, True, '10:00', '18:00'),
            (1, True, '10:00', '18:00'),
            (2, True, '10:00', '18:00'),
            (3, True, '10:00', '18:00'),
            (4, True, '10:00', '18:00'),
            (5, False, '10:00', '14:00'),
            (6, False, '10:00', '14:00'),
        ]
        for day, is_working, start, end in days:
            hours = WorkingHours(
                day_of_week=day,
                is_working=is_working,
                start_time=start,
                end_time=end,
                slot_duration=30
            )
            db.session.add(hours)
        db.session.commit()
        print('Созданы рабочие часы по умолчанию')

    print('База данных готова к работе!')

if __name__ == '__main__':
    app.run(debug=True)