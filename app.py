from flask import Flask
from routes import bp
from db import db
from models import User

app = Flask(__name__)
app.register_blueprint(bp)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///example.db'
db.init_app(app)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  
    app.run(debug=True)