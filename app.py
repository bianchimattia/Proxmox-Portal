# app.py
from flask import Flask, redirect, url_for
from flask_migrate import Migrate
from model.connection import db
from model.model import init_db
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)


app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///proxmox-portal.db'
app.config['SECRET_KEY'] = '12345'
app.config.from_object('config')

from blueprints.auth import login_manager, app as auth_blueprint
from blueprints.admin import app as admin_blueprint
from blueprints.user import app as user_blueprint

app.register_blueprint(auth_blueprint, url_prefix='/auth')
app.register_blueprint(admin_blueprint, url_prefix='/admin')
app.register_blueprint(user_blueprint, url_prefix='/user')

db.init_app(app)
login_manager.init_app(app)


migrate = Migrate(app, db)
with app.app_context():
    init_db()

@app.route("/")
def home():
    return redirect(url_for('auth.login'))


    
if __name__ == '__main__':
    app.run(debug=True)
