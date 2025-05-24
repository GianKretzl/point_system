from flask import Blueprint, render_template, redirect, url_for, request, flash, session
from models import User
from forms import LoginForm

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
    if request.method == 'POST':
        # Lógica para cadastrar funcionário
        pass
    return render_template('register_employees.html')

@bp.route('/employee_schedule', methods=['GET', 'POST'])
def employee_schedule():
    # Lógica para cadastrar horário
    return render_template('employee_schedule.html')

@bp.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return redirect(url_for('main.login'))