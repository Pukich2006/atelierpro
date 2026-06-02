from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            flash(f'Добро пожаловать, {user.name}!', 'success')

            if user.role == 'master':
                return redirect(url_for('main.dashboard_master'))
            else:
                return redirect(url_for('main.dashboard_client'))
        else:
            flash('Неверный email или пароль', 'danger')

    return render_template('login.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        name = request.form.get('name')
        phone = request.form.get('phone')

        if User.query.filter_by(email=email).first():
            flash('Пользователь с таким email уже существует', 'danger')
            return redirect(url_for('auth.register'))

        hashed_password = generate_password_hash(password)

        user = User(
            email=email,
            password_hash=hashed_password,
            name=name,
            phone=phone,
            role='client'
        )

        db.session.add(user)
        db.session.commit()

        flash('Регистрация успешна! Теперь войдите в систему', 'success')
        return redirect(url_for('auth.login'))

    return render_template('register.html')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('main.index'))