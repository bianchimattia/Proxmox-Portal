# blueprints/auth.py
from flask_login import LoginManager, login_required, login_user, logout_user, current_user
from flask import Blueprint, render_template, redirect, url_for, request, flash, abort
from model.model import User,Role
from model.connection import db
from functools import wraps

login_manager = LoginManager()
login_manager.login_view = 'auth.login'

app = Blueprint('auth', __name__)

def user_has_role(*role_names):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash("Devi essere autenticato per accedere a questa pagina.")
                return redirect(url_for('login'))
            if not any(current_user.has_role(role) for role in role_names):
                flash("Non hai il permesso per accedere a questa pagina.")
                return abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@app.route('/login')
def login():
    return render_template('auth/login.html')

@app.route('/login', methods=['POST'])
def login_post():
    # manages the login form post request
    email = request.form.get('email')
    password = request.form.get('password')
    remember = True if request.form.get('remember') else False

    user = User.query.filter_by(email=email).first()

    if not user or not user.check_password(password):
        flash('Please check your login details and try again.')
        return redirect(url_for('auth.login'))

    login_user(user, remember=remember)

    if user.has_role("admin"):
        return redirect(url_for('admin.get_richieste'))
    elif user.has_role("user"):
        return redirect(url_for('user.get_lista_vm'))  

@app.route('/logout')
@login_required
@user_has_role("admin", "user")
def logout():
    logout_user()
    return redirect(url_for('auth.login'))

@app.route('/profile')
@login_required
@user_has_role("admin", "user")
def profile():
     return render_template('auth/profile.html', name=current_user.username)

@app.route('/signup')
def signup():
    return render_template('auth/signup.html')

@app.route('/signup', methods=['POST'])
def signup_post():

    username = request.form["username"] 
    email = request.form["email"]    
    password = request.form["password"]

    if not username:
        flash('Invalid username')
        return redirect(url_for('auth.signup'))
    if not email:
        flash('Invalid email')
        return redirect(url_for('auth.signup'))
    if not password:
        flash('Invalid password')
        return redirect(url_for('auth.signup'))                
    
    user = User.query.filter_by(email=email).first() 
    if user: 
        flash('User with this email address already exists')
        return redirect(url_for('auth.signup'))

    user = User(username=username, email=email)
    user.set_password(password)  
    db.session.add(user) 
    db.session.commit()

    # role = Role(id=user.id, name='user')
    # db.session.add(role)
    # db.session.commit()

    login_user(user)
    return redirect(url_for('auth.login'))

@login_manager.user_loader
def load_user(user_id):
    stmt = db.select(User).filter_by(id=user_id)
    user = db.session.execute(stmt).scalar_one_or_none()    
    return user

