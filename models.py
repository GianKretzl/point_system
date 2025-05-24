from db import db
from datetime import datetime
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship

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
    date = db.Column(db.Date, nullable=False)
    entry_time = db.Column(db.Time, nullable=False)
    exit_time = db.Column(db.Time, nullable=False)

    user = db.relationship('User', backref='schedules')

    def __repr__(self):
        return f'<EmployeeSchedule {self.user_id} {self.date}>'


