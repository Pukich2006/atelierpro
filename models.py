from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20))
    role = db.Column(db.String(20), default='client')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def get_id(self):
        return str(self.id)


class Order(db.Model):
    __tablename__ = 'orders'

    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    service = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    measurements = db.Column(db.Text)
    deadline = db.Column(db.String(50), nullable=False)
    total_price = db.Column(db.Float, default=0)
    status = db.Column(db.String(50), default='new')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    client = db.relationship('User', backref='orders', foreign_keys=[client_id])


class Message(db.Model):
    __tablename__ = 'messages'

    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    sender = db.relationship('User', foreign_keys=[sender_id], backref='sent_messages')
    receiver = db.relationship('User', foreign_keys=[receiver_id], backref='received_messages')


class WorkingHours(db.Model):
    __tablename__ = 'working_hours'

    id = db.Column(db.Integer, primary_key=True)
    day_of_week = db.Column(db.Integer, nullable=False)
    is_working = db.Column(db.Boolean, default=True)
    start_time = db.Column(db.String(5), default='10:00')
    end_time = db.Column(db.String(5), default='18:00')
    slot_duration = db.Column(db.Integer, default=30)


class Appointment(db.Model):
    __tablename__ = 'appointments'

    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    appointment_date = db.Column(db.Date, nullable=False)
    appointment_time = db.Column(db.String(5), nullable=False)
    purpose = db.Column(db.String(200), nullable=False)
    status = db.Column(db.String(50), default='pending')
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    client = db.relationship('User', backref='appointments', foreign_keys=[client_id])