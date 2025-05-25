from db import db
from datetime import datetime

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)    
    password = db.Column(db.String(128), nullable=False)    
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    is_employee = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<User {self.username}>'

class EmployeeSchedule(db.Model):
    __tablename__ = 'employee_schedules'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    entry_time = db.Column(db.Time, nullable=False)
    lunch_start = db.Column(db.Time, nullable=False)
    lunch_end = db.Column(db.Time, nullable=False)
    exit_time = db.Column(db.Time, nullable=False)

    user = db.relationship('User', backref='schedule')

    def __repr__(self):
        return f'<EmployeeSchedule {self.user_id}>'

class TimeRecord(db.Model):
    __tablename__ = 'time_records'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    entry_time = db.Column(db.Time)
    lunch_start = db.Column(db.Time)
    lunch_end = db.Column(db.Time)
    exit_time = db.Column(db.Time)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='time_records')

    def __repr__(self):
        return f'<TimeRecord {self.user_id} {self.date}>'

class Justification(db.Model):
    __tablename__ = 'justifications'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    reason = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    reviewed_at = db.Column(db.DateTime)

    user = db.relationship('User', backref='justifications')

    def __repr__(self):
        return f'<Justification {self.user_id} {self.date} {self.status}>'


