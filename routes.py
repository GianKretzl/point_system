from flask import Blueprint, render_template, redirect, url_for, request, flash, session
from models import EmployeeSchedule, User, TimeRecord, Justification
from forms import LoginForm
from datetime import datetime, timedelta
from db import db

bp = Blueprint('main', __name__)

# Rota inicial: redireciona para login
@bp.route('/')
def home():
    return redirect(url_for('main.login'))

# Rota de login
@bp.route('/login', methods=['GET', 'POST'])
def login():
    """
    Login de usuário. Salva informações na sessão.
    Redireciona para painel admin ou funcionário conforme perfil.
    """
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.password == form.password.data:  # Em produção, use hash!
            session['username'] = user.username
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

# Painel do administrador
@bp.route('/admin')
def admin():
    """
    Painel do admin: mostra dashboard com totais de funcionários, registros, justificativas e faltas do dia.
    """
    if not session.get('username') or not session.get('is_admin'):
        return redirect(url_for('main.login'))
    total_employees = User.query.filter_by(is_employee=True).count()
    total_records_today = TimeRecord.query.filter(TimeRecord.date == datetime.today().date()).count()
    total_justifications_pending = Justification.query.filter_by(status='pendente').count() if hasattr(Justification, 'status') else 0
    total_absences_today = get_total_absences_today()
    return render_template(
        'admin.html',
        username=session.get('username'),
        total_employees=total_employees,
        total_records_today=total_records_today,
        total_justifications_pending=total_justifications_pending,
        total_absences_today=total_absences_today
    )

# Painel do funcionário
@bp.route('/employee')
def employee():
    """
    Painel do funcionário: mostra dashboard com registros do mês, faltas, justificativas e último registro.
    """
    if not session.get('username') or not session.get('is_employee'):
        return redirect(url_for('main.login'))
    user = User.query.filter_by(username=session.get('username')).first()
    today = datetime.today()
    records_this_month = TimeRecord.query.filter(
        TimeRecord.user_id == user.id,
        TimeRecord.date >= today.replace(day=1).date(),
        TimeRecord.date <= today.date()
    ).count()
    absences_this_month = get_employee_absences(user.id, today.year, today.month)
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

# Cadastro de funcionários (admin)
@bp.route('/register_employees', methods=['GET', 'POST'])
def register_employees():
    """
    Permite ao admin cadastrar novos funcionários.
    """
    if not session.get('username') or not session.get('is_admin'):
        return redirect(url_for('main.login'))
    if request.method == 'POST':
        name = request.form.get('name')
        username = request.form.get('username')
        password = request.form.get('password')
        is_admin = True if request.form.get('is_admin') == '1' else False

        if User.query.filter_by(username=username).first():
            flash('Usuário já existe!', 'danger')
            return render_template('register_employees.html')

        user = User(
            name=name,
            username=username,
            password=password,  # Em produção, use hash!
            is_admin=is_admin,
            is_employee=True
        )
        db.session.add(user)
        db.session.commit()
        flash('Funcionário cadastrado com sucesso!', 'success')
        return redirect(url_for('main.register_employees'))
    return render_template('register_employees.html')

# Cadastro de horários padrão dos funcionários (admin)
@bp.route('/employee_schedule', methods=['GET', 'POST'])
def employee_schedule():
    """
    Permite ao admin cadastrar o horário padrão de cada funcionário.
    """
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

# Logout (encerra sessão)
@bp.route('/logout', methods=['POST'])
def logout():
    """
    Encerra a sessão do usuário.
    """
    session.clear()
    return redirect(url_for('main.login'))

# Registro de ponto (funcionário/admin)
@bp.route('/clock', methods=['GET', 'POST'])
def clock():
    """
    Permite ao funcionário/admin registrar batidas de ponto (entrada, almoço, saída).
    """
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
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_template('employee_clock_partial.html', username=user.username, is_admin=session.get('is_admin'))
    return render_template('employee_clock.html', username=user.username, is_admin=session.get('is_admin'))

# Justificativa de ausência/atraso (funcionário/admin)
@bp.route('/justification', methods=['GET', 'POST'])
def justification():
    """
    Permite ao funcionário enviar justificativas de ausência/atraso.
    """
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
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_template('employee_justification_partial.html', username=user.username, is_admin=session.get('is_admin'))
    return render_template('employee_justification.html', username=user.username, is_admin=session.get('is_admin'))

# Relatórios (admin vê todos, funcionário vê só os próprios)
@bp.route('/reports', methods=['GET', 'POST'])
def reports():
    """
    Relatórios de ponto: admin pode filtrar por funcionário e datas, funcionário vê só seus registros.
    """
    if not session.get('username'):
        return redirect(url_for('main.login'))

    is_admin = session.get('is_admin')
    users = []
    records = []

    selected_user = request.form.get('user_id') if is_admin else None
    start_date = request.form.get('start_date')
    end_date = request.form.get('end_date')

    if is_admin:
        users = User.query.filter_by(is_employee=True).all()
        query = TimeRecord.query
        if selected_user:
            query = query.filter(TimeRecord.user_id == selected_user)
    else:
        user = User.query.filter_by(username=session.get('username')).first()
        query = TimeRecord.query.filter(TimeRecord.user_id == user.id)

    if start_date:
        query = query.filter(TimeRecord.date >= start_date)
    if end_date:
        query = query.filter(TimeRecord.date <= end_date)

    query = query.order_by(TimeRecord.date.desc())
    records = query.all()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_template(
            'reports_partial.html',
            is_admin=is_admin,
            users=users,
            records=records,
            selected_user=selected_user,
            start_date=start_date,
            end_date=end_date
        )
    return render_template(
        'reports.html',
        is_admin=is_admin,
        users=users,
        records=records,
        selected_user=selected_user,
        start_date=start_date,
        end_date=end_date
    )
# Função auxiliar: retorna lista de dias úteis do mês
def get_workdays_in_month(year, month):
    """Retorna uma lista de datas dos dias úteis do mês."""
    from calendar import monthrange
    num_days = monthrange(year, month)[1]
    return [
        datetime(year, month, day).date()
        for day in range(1, num_days + 1)
        if datetime(year, month, day).weekday() < 5  # 0=segunda, 4=sexta
    ]

# Função auxiliar: calcula faltas do funcionário no mês
def get_employee_absences(user_id, year, month):
    """Retorna o número de faltas do funcionário no mês."""
    from calendar import monthrange
    workdays = get_workdays_in_month(year, month)
    records = TimeRecord.query.filter(
        TimeRecord.user_id == user_id,
        TimeRecord.date >= datetime(year, month, 1).date(),
        TimeRecord.date <= datetime(year, month, monthrange(year, month)[1]).date()
    ).with_entities(TimeRecord.date).all()
    recorded_days = {r.date for r in records}
    absences = [d for d in workdays if d not in recorded_days]
    return len(absences)

# Função auxiliar: calcula total de funcionários sem registro de ponto hoje
def get_total_absences_today():
    """Retorna o número de funcionários que não bateram ponto hoje (admin dashboard)."""
    today = datetime.today().date()
    employees = User.query.filter_by(is_employee=True).all()
    total = 0
    for emp in employees:
        has_record = TimeRecord.query.filter_by(user_id=emp.id, date=today).first()
        if not has_record:
            total += 1
    return total

@bp.route('/account', methods=['GET', 'POST'])
def account():
    """
    Permite ao usuário editar suas informações (nome, senha).
    """
    if not session.get('username'):
        return redirect(url_for('main.login'))
    user = User.query.filter_by(username=session.get('username')).first()
    if request.method == 'POST':
        name = request.form.get('name')
        password = request.form.get('password')
        if name:
            user.name = name
        if password:
            user.password = password  # Em produção, use hash!
        db.session.commit()
        flash('Dados atualizados com sucesso!', 'success')
        return redirect(url_for('main.account'))
    return render_template('account.html', user=user)


