from flask import Blueprint, render_template, redirect, url_for, request, flash, session
from models import EmployeeSchedule, User
from forms import LoginForm
from werkzeug.security import generate_password_hash
from datetime import datetime

bp = Blueprint('main', __name__)

@bp.route('/')
def home():
    return redirect(url_for('main.login'))

@bp.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.password == form.password.data:  # Em produção, use hash!
            session['username'] = user.username  # Salva o usuário na sessão
            session['is_admin'] = user.is_admin
            session['is_employee'] = user.is_employee
            if user.is_admin:
                return redirect(url_for('main.admin'))
            elif user.is_employee:
                return redirect(url_for('main.employee'))
            else:
                flash('Usuário sem permissão.', 'danger')
        else:
            flash('Usuário ou senha inválidos.', 'danger')
    return render_template('login.html', form=form)

@bp.route('/admin')
def admin():
    if not session.get('username') or not session.get('is_admin'):
        return redirect(url_for('main.login'))
    return render_template('admin.html', username=session.get('username'))

@bp.route('/employee')
def employee():
    if not session.get('username') or not session.get('is_employee'):
        return redirect(url_for('main.login'))
    return render_template('employee.html', username=session.get('username'))

@bp.route('/register_employees', methods=['GET', 'POST'])
def register_employees():
    if not session.get('username') or not session.get('is_admin'):
        return redirect(url_for('main.login'))
    if request.method == 'POST':
        name = request.form.get('name')
        username = request.form.get('username')
        password = request.form.get('password')
        is_admin = True if request.form.get('is_admin') == '1' else False

        # Verifica se usuário já existe
        if User.query.filter_by(username=username).first():
            flash('Usuário já existe!', 'danger')
            return render_template('register_employees.html')

        user = User(
            name=name,
            username=username,
            password=password,  
            is_admin=is_admin,
            is_employee=True
        )
        from db import db
        db.session.add(user)
        db.session.commit()
        flash('Funcionário cadastrado com sucesso!', 'success')
        return redirect(url_for('main.register_employees'))
    return render_template('register_employees.html')

@bp.route('/employee_schedule', methods=['GET', 'POST'])
def employee_schedule():
    if not session.get('username') or not session.get('is_admin'):
        return redirect(url_for('main.login'))
    users = User.query.all()
    if request.method == 'POST':
        user_id = request.form.get('user_id')
        date = request.form.get('date')
        entry_time = request.form.get('entry_time')
        exit_time = request.form.get('exit_time')

        if not user_id or not date or not entry_time or not exit_time:
            flash('Preencha todos os campos!', 'danger')
            return render_template('employee_schedule.html', users=users)

        schedule = EmployeeSchedule(
            user_id=user_id,
            date=datetime.strptime(date, '%Y-%m-%d').date(),
            entry_time=datetime.strptime(entry_time, '%H:%M').time(),
            exit_time=datetime.strptime(exit_time, '%H:%M').time()
        )
        from db import db
        db.session.add(schedule)
        db.session.commit()
        flash('Horário cadastrado com sucesso!', 'success')
        return redirect(url_for('main.employee_schedule'))
    return render_template('employee_schedule.html', users=users)

@bp.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return redirect(url_for('main.login'))