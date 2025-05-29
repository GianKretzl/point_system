from flask import Flask
from routes import bp
from db import db
from models import User, EmployeeSchedule, Justification, TimePunch 
from datetime import time

app = Flask(__name__)
app.config['SECRET_KEY'] = '123456'
app.register_blueprint(bp)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///point_system.db'
db.init_app(app)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # Criação automática do usuário admin
        admin = User.query.filter_by(username='GianKretzl').first()
        if not admin:
            admin = User(
                name='Gian Felipe Kretzl',
                username='GianKretzl',
                password='123456',  # Use hash em produção!
                is_admin=True,
                is_employee=False
            )
            db.session.add(admin)
            db.session.commit()
        # Criação automática do funcionário
        employee = User.query.filter_by(username='JoseSilva').first()
        if not employee:
            employee = User(
                name='Jose Silva',
                username='JoseSilva',
                password='123456',  # Use hash em produção!
                is_admin=False,
                is_employee=True
            )
            db.session.add(employee)
            db.session.commit()

        # Cadastrar horários padrão se não existirem
        from models import EmployeeSchedule

        if not EmployeeSchedule.query.filter_by(user_id=admin.id).first():
            admin_schedule = EmployeeSchedule(
                user_id=admin.id,
                entry_time=time(8, 0),
                lunch_start=time(12, 0),
                lunch_end=time(13, 0),
                exit_time=time(18, 0)
            )
            db.session.add(admin_schedule)
        if not EmployeeSchedule.query.filter_by(user_id=employee.id).first():
            employee_schedule = EmployeeSchedule(
                user_id=employee.id,
                entry_time=time(8, 0),
                lunch_start=time(12, 0),
                lunch_end=time(13, 0),
                exit_time=time(18, 0)
            )
            db.session.add(employee_schedule)
        db.session.commit()
    app.run(debug=True)