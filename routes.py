from flask import Blueprint, render_template, redirect, url_for, request, flash, session
from models import EmployeeSchedule, User, TimeRecord, Justification
from forms import LoginForm
from werkzeug.security import generate_password_hash
from datetime import datetime
from db import db
from sqlalchemy import and_

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
    total_employees = User.query.filter_by(is_employee=True).count()
    total_records_today = TimeRecord.query.filter(TimeRecord.date == datetime.today().date()).count()
    total_justifications_pending = Justification.query.filter_by(status='pendente').count()
    total_absences_today = ... # sua lógica de faltas
    return render_template(
        'admin.html',
        username=session.get('username'),
        total_employees=total_employees,
        total_records_today=total_records_today,
        total_justifications_pending=total_justifications_pending,
        total_absences_today=total_absences_today
    )

@bp.route('/employee')
def employee():
    if not session.get('username') or not session.get('is_employee'):
        return redirect(url_for('main.login'))
    user = User.query.filter_by(username=session.get('username')).first()
    records_this_month = TimeRecord.query.filter(
        TimeRecord.user_id == user.id,
        TimeRecord.date >= datetime.today().replace(day=1)
    ).count()
    absences_this_month = ... # sua lógica de faltas
    justifications_sent = Justification.query.filter_by(user_id=user.id).count()
    last_record = TimeRecord.query.filter_by(user_id=user.id).order_by(TimeRecord.date.desc()).first()
    last_record_str = last_record.date.strftime('%d/%m/%Y') if last_record else '-'
    return render_template(
        'employee.html',
        username=user.username,
        records_this_month=records_this_month,
        absences_this_month=absences_this_month,
        justifications_sent=justifications_sent,
        last_record=last_record_str
    )

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
        entry_time = request.form.get('entry_time')
        lunch_start = request.form.get('lunch_start')
        lunch_end = request.form.get('lunch_end')
        exit_time = request.form.get('exit_time')

        if not user_id or not entry_time or not lunch_start or not lunch_end or not exit_time:
            flash('Preencha todos os campos!', 'danger')
            return render_template('employee_schedule.html', users=users)

        schedule = EmployeeSchedule(
            user_id=user_id,
            entry_time=datetime.strptime(entry_time, '%H:%M').time(),
            lunch_start=datetime.strptime(lunch_start, '%H:%M').time(),
            lunch_end=datetime.strptime(lunch_end, '%H:%M').time(),
            exit_time=datetime.strptime(exit_time, '%H:%M').time()
        )
        db.session.add(schedule)
        db.session.commit()
        flash('Horário cadastrado com sucesso!', 'success')
        return redirect(url_for('main.employee_schedule'))
    return render_template('employee_schedule.html', users=users)

@bp.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return redirect(url_for('main.login'))

@bp.route('/clock', methods=['GET', 'POST'])
def clock():
    if not session.get('username') or not (session.get('is_employee') or session.get('is_admin')):
        return redirect(url_for('main.login'))
    user = User.query.filter_by(username=session.get('username')).first()
    if request.method == 'POST':
        punch_type = request.form.get('punch_type')
        now = datetime.now()
        record = TimeRecord.query.filter_by(user_id=user.id, date=now.date()).first()
        if not record:
            record = TimeRecord(user_id=user.id, date=now.date())
            db.session.add(record)
        if punch_type == 'entry':
            record.entry_time = now.time()
        elif punch_type == 'lunch_start':
            record.lunch_start = now.time()
        elif punch_type == 'lunch_end':
            record.lunch_end = now.time()
        elif punch_type == 'exit':
            record.exit_time = now.time()
        db.session.commit()
        flash('Ponto registrado!', 'success')
    return render_template('employee_clock.html', username=user.username, is_admin=session.get('is_admin'))

@bp.route('/justification', methods=['GET', 'POST'])
def justification():
    if not session.get('username') or not (session.get('is_employee') or session.get('is_admin')):
        return redirect(url_for('main.login'))
    user = User.query.filter_by(username=session.get('username')).first()
    if request.method == 'POST':
        date = request.form.get('date')
        reason = request.form.get('reason')
        if not date or not reason:
            flash('Preencha todos os campos!', 'danger')
        else:
            justification = Justification(
                user_id=user.id,
                date=datetime.strptime(date, '%Y-%m-%d').date(),
                reason=reason
            )
            db.session.add(justification)
            db.session.commit()
            flash('Justificativa enviada para análise!', 'success')
    return render_template('employee_justification.html', username=user.username, is_admin=session.get('is_admin'))

@bp.route('/reports', methods=['GET', 'POST'])
def reports():
    if not session.get('username'):
        return redirect(url_for('main.login'))

    is_admin = session.get('is_admin')
    filters = {}
    users = []
    records = []

    # Filtros do formulário
    selected_user = request.form.get('user_id') if is_admin else None
    start_date = request.form.get('start_date')
    end_date = request.form.get('end_date')

    # Admin pode ver todos, funcionário só vê o próprio
    if is_admin:
        users = User.query.filter_by(is_employee=True).all()
        query = TimeRecord.query
        if selected_user:
            query = query.filter(TimeRecord.user_id == selected_user)
    else:
        user = User.query.filter_by(username=session.get('username')).first()
        query = TimeRecord.query.filter(TimeRecord.user_id == user.id)

    # Filtro por datas
    if start_date:
        query = query.filter(TimeRecord.date >= start_date)
    if end_date:
        query = query.filter(TimeRecord.date <= end_date)

    # Ordenação
    query = query.order_by(TimeRecord.date.desc())
    records = query.all()

    return render_template(
        'reports.html',
        is_admin=is_admin,
        users=users,
        records=records,
        selected_user=selected_user,
        start_date=start_date,
        end_date=end_date
    )
