from flask import Blueprint, render_template, redirect, url_for, request, flash, session, send_file
from models import EmployeeSchedule, User, Justification, TimePunch
from forms import LoginForm
from datetime import datetime, timedelta
from db import db
import io
import xlwt
from collections import defaultdict

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
    total_records_today = TimePunch.query.filter(TimePunch.date == datetime.today().date()).count()
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
    punches_this_month = TimePunch.query.filter(
        TimePunch.user_id == user.id,
        TimePunch.date >= today.replace(day=1).date(),
        TimePunch.date <= today.date()
    ).count()
    justifications_sent = Justification.query.filter_by(user_id=user.id).count()
    last_punch = TimePunch.query.filter_by(user_id=user.id).order_by(TimePunch.date.desc(), TimePunch.time.desc()).first()
    last_punch_str = last_punch.date.strftime('%d/%m/%Y') if last_punch else '-'
    absences_this_month = get_employee_absences(user.id, today.year, today.month)
    return render_template(
        'employee.html',
        username=user.username,
        records_this_month=punches_this_month,
        absences_this_month=absences_this_month,
        justifications_sent=justifications_sent,
        last_record=last_punch_str
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

        # Agora só exige user_id, entry_time e exit_time
        if not user_id or not entry_time or not exit_time:
            flash('Preencha os campos obrigatórios: Funcionário, Entrada e Saída!', 'danger')
            return render_template('employee_schedule.html', users=users)

        # Conversão para time
        entry_time_obj = datetime.strptime(entry_time, '%H:%M').time()
        exit_time_obj = datetime.strptime(exit_time, '%H:%M').time()
        lunch_start_obj = datetime.strptime(lunch_start, '%H:%M').time() if lunch_start else None
        lunch_end_obj = datetime.strptime(lunch_end, '%H:%M').time() if lunch_end else None

        # Validações de lógica
        if exit_time_obj <= entry_time_obj:
            flash('O horário de saída deve ser maior que o de entrada!', 'danger')
            return render_template('employee_schedule.html', users=users)

        if lunch_start_obj and lunch_start_obj <= entry_time_obj:
            flash('O início do almoço deve ser após o horário de entrada!', 'danger')
            return render_template('employee_schedule.html', users=users)

        if lunch_end_obj and lunch_start_obj and lunch_end_obj <= lunch_start_obj:
            flash('O fim do almoço deve ser após o início do almoço!', 'danger')
            return render_template('employee_schedule.html', users=users)

        if lunch_end_obj and lunch_end_obj <= entry_time_obj:
            flash('O fim do almoço deve ser após o horário de entrada!', 'danger')
            return render_template('employee_schedule.html', users=users)

        schedule = EmployeeSchedule(
            user_id=user_id,
            entry_time=entry_time_obj,
            lunch_start=lunch_start_obj,
            lunch_end=lunch_end_obj,
            exit_time=exit_time_obj
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
    if not session.get('username') or not (session.get('is_employee') or session.get('is_admin')):
        return redirect(url_for('main.login'))
    user = User.query.filter_by(username=session.get('username')).first()
    now = datetime.now()
    punches_today = TimePunch.query.filter_by(user_id=user.id, date=now.date()).order_by(TimePunch.time).all()
    if request.method == 'POST':
        punch_type = request.form.get('punch_type')
        # Busca as últimas batidas do dia
        entry = next((p for p in punches_today if p.punch_type == 'entry'), None)
        lunch_start = next((p for p in punches_today if p.punch_type == 'lunch_start'), None)
        lunch_end = next((p for p in punches_today if p.punch_type == 'lunch_end'), None)
        exit_ = next((p for p in punches_today if p.punch_type == 'exit'), None)

        if punch_type == 'entry':
            pass  # Sempre pode bater entrada
        elif punch_type == 'lunch_start':
            if not entry:
                flash('Registre a entrada antes de iniciar o almoço!', 'danger')
                return render_template('employee_clock.html', username=user.username, is_admin=session.get('is_admin'), punches_today=punches_today)
            if now.time() <= entry.time:
                flash('O início do almoço deve ser após a entrada!', 'danger')
                return render_template('employee_clock.html', username=user.username, is_admin=session.get('is_admin'), punches_today=punches_today)
        elif punch_type == 'lunch_end':
            if not lunch_start:
                flash('Registre o início do almoço antes de finalizar!', 'danger')
                return render_template('employee_clock.html', username=user.username, is_admin=session.get('is_admin'), punches_today=punches_today)
            if now.time() <= lunch_start.time:
                flash('O fim do almoço deve ser após o início do almoço!', 'danger')
                return render_template('employee_clock.html', username=user.username, is_admin=session.get('is_admin'), punches_today=punches_today)
        elif punch_type == 'exit':
            if not entry:
                flash('Registre a entrada antes da saída!', 'danger')
                return render_template('employee_clock.html', username=user.username, is_admin=session.get('is_admin'), punches_today=punches_today)
            if now.time() <= entry.time:
                flash('O horário de saída deve ser após a entrada!', 'danger')
                return render_template('employee_clock.html', username=user.username, is_admin=session.get('is_admin'), punches_today=punches_today)

        if punch_type in ['entry', 'exit', 'lunch_start', 'lunch_end']:
            punch = TimePunch(
                user_id=user.id,
                date=now.date(),
                time=now.time(),
                punch_type=punch_type
            )
            db.session.add(punch)
            db.session.commit()
            flash('Ponto registrado!', 'success')
        else:
            flash('Tipo de batida inválido!', 'danger')
        punches_today = TimePunch.query.filter_by(user_id=user.id, date=now.date()).order_by(TimePunch.time).all()
    return render_template(
        'employee_clock.html',
        username=user.username,
        is_admin=session.get('is_admin'),
        punches_today=punches_today
    )

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

# Justificativas pendentes (admin)
@bp.route('/justifications_admin', methods=['GET', 'POST'])
def justifications_admin():
    """
    Permite ao admin visualizar e abonar (aprovar/rejeitar) justificativas pendentes.
    """
    if not session.get('username') or not session.get('is_admin'):
        return redirect(url_for('main.login'))

    if request.method == 'POST':
        justification_id = request.form.get('justification_id')
        action = request.form.get('action')
        justification = Justification.query.get(justification_id)
        if justification and justification.status == 'pending':
            if action == 'approve':
                justification.status = 'approved'
            elif action == 'reject':
                justification.status = 'rejected'
            justification.reviewed_at = datetime.utcnow()
            db.session.commit()
            flash('Justificativa atualizada!', 'success')
        else:
            flash('Justificativa não encontrada ou já processada.', 'danger')

    justifications = Justification.query.filter_by(status='pending').all()
    return render_template('justifications_admin.html', justifications=justifications)

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
        # Inclui todos que são funcionários OU admin
        users = User.query.filter((User.is_employee == True) | (User.is_admin == True)).all()
        query = TimePunch.query
        if selected_user:
            query = query.filter(TimePunch.user_id == selected_user)
    else:
        user = User.query.filter_by(username=session.get('username')).first()
        query = TimePunch.query.filter(TimePunch.user_id == user.id)

    if start_date:
        query = query.filter(TimePunch.date >= start_date)
    if end_date:
        query = query.filter(TimePunch.date <= end_date)

    query = query.order_by(TimePunch.date.desc(), TimePunch.time.asc())
    punches = query.all()

    # Agrupa por data e usuário, agora com listas de horários
    grouped = defaultdict(lambda: {
        'user': None,
        'date': None,
        'entry_times': [],
        'lunch_start_times': [],
        'lunch_end_times': [],
        'exit_times': []
    })

    for punch in punches:
        key = (punch.user_id, punch.date)
        if grouped[key]['user'] is None:
            grouped[key]['user'] = punch.user
            grouped[key]['date'] = punch.date
        if punch.punch_type == 'entry':
            grouped[key]['entry_times'].append(punch.time.strftime('%H:%M'))
        elif punch.punch_type == 'lunch_start':
            grouped[key]['lunch_start_times'].append(punch.time.strftime('%H:%M'))
        elif punch.punch_type == 'lunch_end':
            grouped[key]['lunch_end_times'].append(punch.time.strftime('%H:%M'))
        elif punch.punch_type == 'exit':
            grouped[key]['exit_times'].append(punch.time.strftime('%H:%M'))

    # Ordena por data decrescente
    records = sorted(grouped.values(), key=lambda x: x['date'], reverse=True)

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

@bp.route('/download_report')
def download_report():
    """
    Gera e baixa o relatório de ponto em formato .xls conforme filtros.
    """
    if not session.get('username'):
        return redirect(url_for('main.login'))

    is_admin = session.get('is_admin')
    user_id = request.args.get('user_id') if is_admin else None
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    if is_admin:
        query = TimePunch.query
        if user_id:
            query = query.filter(TimePunch.user_id == user_id)
    else:
        user = User.query.filter_by(username=session.get('username')).first()
        query = TimePunch.query.filter(TimePunch.user_id == user.id)

    if start_date:
        query = query.filter(TimePunch.date >= start_date)
    if end_date:
        query = query.filter(TimePunch.date <= end_date)

    query = query.order_by(TimePunch.date.desc(), TimePunch.time.desc())
    records = query.all()

    # Cria planilha XLS
    output = io.BytesIO()
    wb = xlwt.Workbook()
    ws = wb.add_sheet('Relatório de Ponto')

    row_num = 0
    columns = []
    if is_admin:
        columns.append('Funcionário')
    columns += ['Data', 'Hora', 'Tipo']

    # Cabeçalho
    for col_num, column_title in enumerate(columns):
        ws.write(row_num, col_num, column_title)

    # Dados
    for record in records:
        row_num += 1
        col = 0
        if is_admin:
            ws.write(row_num, col, record.user.name)
            col += 1
        ws.write(row_num, col, record.date.strftime('%d/%m/%Y'))
        ws.write(row_num, col+1, record.time.strftime('%H:%M:%S'))
        ws.write(row_num, col+2, record.punch_type)

    wb.save(output)
    output.seek(0)

    return send_file(
        output,
        mimetype="application/vnd.ms-excel",
        as_attachment=True,
        download_name="relatorio_ponto.xls"
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
    punches = TimePunch.query.filter(
        TimePunch.user_id == user_id,
        TimePunch.date >= datetime(year, month, 1).date(),
        TimePunch.date <= datetime(year, month, monthrange(year, month)[1]).date()
    ).with_entities(TimePunch.date).distinct().all()
    recorded_days = {p.date for p in punches}
    absences = [d for d in workdays if d not in recorded_days]
    return len(absences)

# Função auxiliar: calcula total de funcionários sem registro de ponto hoje
def get_total_absences_today():
    """Retorna o número de funcionários que não bateram ponto hoje (admin dashboard)."""
    today = datetime.today().date()
    employees = User.query.filter_by(is_employee=True).all()
    total = 0
    for emp in employees:
        has_punch = TimePunch.query.filter_by(user_id=emp.id, date=today).first()
        if not has_punch:
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


