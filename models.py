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
    

    