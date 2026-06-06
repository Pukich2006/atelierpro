from flask import Blueprint, render_template, request, redirect, url_for, flash, Response
from flask_login import login_required, current_user
from models import db, Order, User, Message, WorkingHours, Appointment
from datetime import datetime, date, timedelta
import csv
from io import StringIO

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    return render_template('index.html')


# ==================== ПАНЕЛЬ МАСТЕРА ====================

@main_bp.route('/dashboard/master')
@login_required
def dashboard_master():
    if current_user.role != 'master':
        return redirect(url_for('main.dashboard_client'))

    total_orders = Order.query.count()
    new_orders = Order.query.filter_by(status='new').count()
    work_orders = Order.query.filter_by(status='work').count()
    ready_orders = Order.query.filter_by(status='ready').count()
    total_clients = User.query.filter_by(role='client').count()
    orders = Order.query.order_by(Order.created_at.desc()).all()

    unread_count = Message.query.filter_by(receiver_id=current_user.id, is_read=False).count()
    pending_appointments = Appointment.query.filter_by(status='pending').count()

    return render_template('dashboard_master.html',
                           user=current_user,
                           total_orders=total_orders,
                           new_orders=new_orders,
                           work_orders=work_orders,
                           ready_orders=ready_orders,
                           total_clients=total_clients,
                           orders=orders,
                           unread_count=unread_count,
                           pending_count=pending_appointments)


@main_bp.route('/order/status/<int:order_id>', methods=['POST'])
@login_required
def change_order_status(order_id):
    if current_user.role != 'master':
        flash('Доступ запрещён', 'danger')
        return redirect(url_for('main.dashboard_client'))

    order = Order.query.get_or_404(order_id)
    new_status = request.form.get('status')

    if new_status in ['new', 'work', 'fitting', 'ready', 'completed', 'cancelled']:
        order.status = new_status
        db.session.commit()
        flash(f'Статус заказа #{order.id} изменён на "{new_status}"', 'success')

    return redirect(url_for('main.dashboard_master'))


# ==================== ПАНЕЛЬ КЛИЕНТА ====================

@main_bp.route('/dashboard/client')
@login_required
def dashboard_client():
    if current_user.role != 'client':
        return redirect(url_for('main.dashboard_master'))

    orders = Order.query.filter_by(client_id=current_user.id).order_by(Order.created_at.desc()).all()
    unread_count = Message.query.filter_by(receiver_id=current_user.id, is_read=False).count()

    return render_template('dashboard_client.html',
                           user=current_user,
                           orders=orders,
                           unread_count=unread_count)


@main_bp.route('/order/create', methods=['GET', 'POST'])
@login_required
def create_order():
    if current_user.role != 'client':
        flash('Только клиенты могут создавать заказы', 'danger')
        return redirect(url_for('main.dashboard_master'))

    if request.method == 'POST':
        service = request.form.get('service')
        description = request.form.get('description')
        measurements = request.form.get('measurements')
        deadline = request.form.get('deadline')
        total_price = request.form.get('total_price', 0)

        if not service or not description or not deadline:
            flash('Заполните все обязательные поля', 'danger')
            return redirect(url_for('main.create_order'))

        order = Order(
            client_id=current_user.id,
            service=service,
            description=description,
            measurements=measurements,
            deadline=deadline,
            total_price=float(total_price) if total_price else 0,
            status='new'
        )

        db.session.add(order)
        db.session.commit()

        flash(f'Заказ #{order.id} успешно создан! Мастер скоро свяжется с вами.', 'success')
        return redirect(url_for('main.dashboard_client'))

    return render_template('create_order.html')


# ==================== ЧАТ ====================

@main_bp.route('/chat')
@login_required
def chat():
    if current_user.role == 'master':
        clients = User.query.filter_by(role='client').all()

        for client in clients:
            last_msg = Message.query.filter(
                ((Message.sender_id == current_user.id) & (Message.receiver_id == client.id)) |
                ((Message.sender_id == client.id) & (Message.receiver_id == current_user.id))
            ).order_by(Message.created_at.desc()).first()
            client.last_message = last_msg.message if last_msg else ''
            client.last_message_time = last_msg.created_at if last_msg else None

        clients.sort(key=lambda x: x.last_message_time or datetime.min, reverse=True)
        return render_template('chat_master.html', clients=clients, current_user=current_user)
    else:
        master = User.query.filter_by(role='master').first()
        if not master:
            flash('Мастер пока не зарегистрирован', 'danger')
            return redirect(url_for('main.dashboard_client'))

        messages = Message.query.filter(
            ((Message.sender_id == current_user.id) & (Message.receiver_id == master.id)) |
            ((Message.sender_id == master.id) & (Message.receiver_id == current_user.id))
        ).order_by(Message.created_at.asc()).all()

        for msg in messages:
            if msg.receiver_id == current_user.id and not msg.is_read:
                msg.is_read = True
        db.session.commit()

        return render_template('chat_client.html', messages=messages, master=master)


@main_bp.route('/chat/send/<int:receiver_id>', methods=['POST'])
@login_required
def send_message(receiver_id):
    message_text = request.form.get('message')

    if not message_text or not message_text.strip():
        flash('Сообщение не может быть пустым', 'danger')
        return redirect(request.referrer or url_for('main.chat'))

    message = Message(
        sender_id=current_user.id,
        receiver_id=receiver_id,
        message=message_text.strip(),
        is_read=False
    )

    db.session.add(message)
    db.session.commit()

    flash('Сообщение отправлено!', 'success')

    if current_user.role == 'master':
        return redirect(url_for('main.chat_with_client', client_id=receiver_id))
    else:
        return redirect(url_for('main.chat'))


@main_bp.route('/chat/client/<int:client_id>')
@login_required
def chat_with_client(client_id):
    if current_user.role != 'master':
        return redirect(url_for('main.chat'))

    client = User.query.get_or_404(client_id)

    messages = Message.query.filter(
        ((Message.sender_id == current_user.id) & (Message.receiver_id == client.id)) |
        ((Message.sender_id == client.id) & (Message.receiver_id == current_user.id))
    ).order_by(Message.created_at.asc()).all()

    for msg in messages:
        if msg.sender_id == client.id and not msg.is_read:
            msg.is_read = True
    db.session.commit()

    return render_template('chat_master_detail.html', client=client, messages=messages)


# ==================== КАЛЕНДАРЬ И ЗАПИСЬ ====================

@main_bp.route('/settings/working-hours', methods=['GET', 'POST'])
@login_required
def working_hours():
    if current_user.role != 'master':
        flash('Доступ запрещён', 'danger')
        return redirect(url_for('main.dashboard_client'))

    days = {
        0: 'Понедельник',
        1: 'Вторник',
        2: 'Среда',
        3: 'Четверг',
        4: 'Пятница',
        5: 'Суббота',
        6: 'Воскресенье'
    }

    if request.method == 'POST':
        for day in range(7):
            is_working = request.form.get(f'is_working_{day}') == 'on'
            start_time = request.form.get(f'start_time_{day}', '10:00')
            end_time = request.form.get(f'end_time_{day}', '18:00')

            hours = WorkingHours.query.filter_by(day_of_week=day).first()
            if hours:
                hours.is_working = is_working
                hours.start_time = start_time
                hours.end_time = end_time
            else:
                hours = WorkingHours(
                    day_of_week=day,
                    is_working=is_working,
                    start_time=start_time,
                    end_time=end_time,
                    slot_duration=30
                )
                db.session.add(hours)

        db.session.commit()
        flash('Рабочие часы сохранены!', 'success')
        return redirect(url_for('main.working_hours'))

    settings = {}
    for day in range(7):
        hours = WorkingHours.query.filter_by(day_of_week=day).first()
        if hours:
            settings[day] = hours
        else:
            default = WorkingHours(
                day_of_week=day,
                is_working=(day < 5),
                start_time='10:00',
                end_time='18:00',
                slot_duration=30
            )
            settings[day] = default

    return render_template('working_hours.html', days=days, settings=settings)


@main_bp.route('/appointment/book', methods=['GET', 'POST'])
@login_required
def book_appointment():
    if current_user.role != 'client':
        flash('Только клиенты могут записываться', 'danger')
        return redirect(url_for('main.dashboard_master'))

    if request.method == 'POST':
        appointment_date = request.form.get('appointment_date')
        appointment_time = request.form.get('appointment_time')
        purpose = request.form.get('purpose')

        if not appointment_date or not appointment_time or not purpose:
            flash('Заполните все поля', 'danger')
            return redirect(url_for('main.book_appointment'))

        existing = Appointment.query.filter_by(
            appointment_date=datetime.strptime(appointment_date, '%Y-%m-%d').date(),
            appointment_time=appointment_time,
            status='confirmed'
        ).first()

        if existing:
            flash('Это время уже занято! Выберите другое', 'danger')
            return redirect(url_for('main.book_appointment'))

        appointment = Appointment(
            client_id=current_user.id,
            appointment_date=datetime.strptime(appointment_date, '%Y-%m-%d').date(),
            appointment_time=appointment_time,
            purpose=purpose,
            status='pending'
        )

        db.session.add(appointment)
        db.session.commit()

        flash(f'Заявка на {appointment_date} в {appointment_time} отправлена! Мастер подтвердит запись.', 'success')
        return redirect(url_for('main.my_appointments'))

    available_dates = []
    today = date.today()

    for i in range(30):
        current_date = today + timedelta(days=i)
        day_of_week = current_date.weekday()

        hours = WorkingHours.query.filter_by(day_of_week=day_of_week).first()
        if hours and hours.is_working:
            available_dates.append({
                'date': current_date,
                'start_time': hours.start_time,
                'end_time': hours.end_time
            })

    return render_template('book_appointment.html', available_dates=available_dates)


@main_bp.route('/my-appointments')
@login_required
def my_appointments():
    if current_user.role != 'client':
        return redirect(url_for('main.dashboard_master'))

    appointments = Appointment.query.filter_by(client_id=current_user.id).order_by(Appointment.appointment_date).all()
    return render_template('my_appointments.html', appointments=appointments)


@main_bp.route('/all-appointments')
@login_required
def all_appointments():
    if current_user.role != 'master':
        return redirect(url_for('main.dashboard_client'))

    appointments = Appointment.query.order_by(Appointment.appointment_date).all()
    pending_count = Appointment.query.filter_by(status='pending').count()

    return render_template('all_appointments.html', appointments=appointments, pending_count=pending_count)


@main_bp.route('/appointment/status/<int:appointment_id>', methods=['POST'])
@login_required
def change_appointment_status(appointment_id):
    if current_user.role != 'master':
        flash('Доступ запрещён', 'danger')
        return redirect(url_for('main.dashboard_client'))

    appointment = Appointment.query.get_or_404(appointment_id)
    new_status = request.form.get('status')

    if new_status in ['pending', 'confirmed', 'cancelled', 'completed']:
        appointment.status = new_status
        db.session.commit()
        flash(f'Запись #{appointment.id} изменена на "{new_status}"', 'success')

    return redirect(url_for('main.all_appointments'))


@main_bp.route('/appointment/cancel/<int:appointment_id>')
@login_required
def cancel_appointment(appointment_id):
    appointment = Appointment.query.get_or_404(appointment_id)

    if appointment.client_id != current_user.id and current_user.role != 'master':
        flash('Доступ запрещён', 'danger')
        return redirect(url_for('main.dashboard_client'))

    appointment.status = 'cancelled'
    db.session.commit()

    flash('Запись отменена', 'info')

    if current_user.role == 'master':
        return redirect(url_for('main.all_appointments'))
    else:
        return redirect(url_for('main.my_appointments'))


# ==================== СТРАНИЦА РАСЦЕНОК ====================

@main_bp.route('/prices')
def prices():
    return render_template('prices.html')


# ==================== ФИНАНСОВЫЙ МОДУЛЬ (без БД) ====================

@main_bp.route('/finance')
@login_required
def finance():
    if current_user.role != 'master':
        flash('Доступ запрещён', 'danger')
        return redirect(url_for('main.dashboard_client'))

    # Статические данные для демонстрации
    total_income = 125000
    total_expense = 45000
    profit = total_income - total_expense

    income_by_category = [
        {'category': 'Пошив одежды', 'total': 80000},
        {'category': 'Ремонт одежды', 'total': 30000},
        {'category': 'Подгонка по фигуре', 'total': 15000},
    ]

    expense_by_category = [
        {'category': 'Материалы (ткань, нитки)', 'total': 20000},
        {'category': 'Фурнитура', 'total': 5000},
        {'category': 'Аренда', 'total': 15000},
        {'category': 'Прочие расходы', 'total': 5000},
    ]

    return render_template('finance.html',
                           user=current_user,
                           total_income=total_income,
                           total_expense=total_expense,
                           profit=profit,
                           income_by_category=income_by_category,
                           expense_by_category=expense_by_category,
                           date_from=None,
                           date_to=None)


@main_bp.route('/finance/export')
@login_required
def export_finance():
    if current_user.role != 'master':
        flash('Доступ запрещён', 'danger')
        return redirect(url_for('main.dashboard_client'))

    transactions = [
        {'id': 1, 'type': 'Доход', 'category': 'Пошив одежды', 'amount': 50000, 'description': 'Пошив платья',
         'date': '2026-06-01', 'order_id': 1},
        {'id': 2, 'type': 'Доход', 'category': 'Пошив одежды', 'amount': 30000, 'description': 'Пошив костюма',
         'date': '2026-06-02', 'order_id': 2},
        {'id': 3, 'type': 'Доход', 'category': 'Ремонт одежды', 'amount': 15000, 'description': 'Ремонт брюк',
         'date': '2026-06-03', 'order_id': 3},
        {'id': 4, 'type': 'Расход', 'category': 'Материалы', 'amount': 10000, 'description': 'Ткань',
         'date': '2026-06-01', 'order_id': None},
        {'id': 5, 'type': 'Расход', 'category': 'Фурнитура', 'amount': 5000, 'description': 'Молнии, пуговицы',
         'date': '2026-06-02', 'order_id': None},
    ]

    si = StringIO()
    cw = csv.writer(si)
    cw.writerow(['ID', 'Тип', 'Категория', 'Сумма', 'Описание', 'Дата', 'ID заказа'])

    for t in transactions:
        cw.writerow([t['id'], t['type'], t['category'], t['amount'], t['description'], t['date'], t['order_id'] or '-'])

    output = si.getvalue().encode('utf-8-sig')

    return Response(output,
                    mimetype='text/csv',
                    headers={'Content-Disposition': 'attachment; filename=finance_report.csv'})