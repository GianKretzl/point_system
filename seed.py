from app import app
from db import db
from models import User

@app.cli.command("seed")
def seed():
    """Popula o banco com dados iniciais."""
    with app.app_context():
        if not User.query.filter_by(username='GianKretzl').first():
            user = User(
                name='Gian Felipe Kretzl',
                username='GianKretzl',
                password='123456',  # Use hash em produção!
                is_admin=True,
                is_employee=False
            )
            db.session.add(user)
            db.session.commit()
            print("Usuário admin criado.")
        else:
            print("Usuário admin já existe.")