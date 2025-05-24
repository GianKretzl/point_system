from flask import Blueprint, render_template, redirect, url_for

bp = Blueprint('main', __name__)

@bp.route('/')
def home():
    return redirect(url_for('main.login'))

@bp.route('/login')
def login():
    return render_template('login.html')

@bp.route('/admin')
def admin():
    return render_template('admin.html')

@bp.route('/employee')
def employee():
    return render_template('employee.html')