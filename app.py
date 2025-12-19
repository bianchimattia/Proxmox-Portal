from flask import Flask
from flask_migrate import Migrate
from model.connection import db
from model.model import init_db

app = Flask(__name__)


app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///proxmox-portal.db'
app.config['SECRET_KEY'] = '12345'

from blueprints.auth import login_manager, app as auth_blueprint
app.register_blueprint(auth_blueprint, url_prefix='/auth')

db.init_app(app)
login_manager.init_app(app)


migrate = Migrate(app, db)
#with app.app_context():
    #init_db()

    
if __name__ == '__main__':
    app.run(debug=True)
