from flask_login import LoginManager, login_required, login_user, logout_user, current_user
from flask import Blueprint, render_template, redirect, url_for, request, flash, abort
from model.model import User
from model.connection import db
from functools import wraps

login_manager = LoginManager()
login_manager.login_view = 'auth.login'

app = Blueprint('auth', __name__)

# def user_has_role(*role_names):
#     def decorator(f):
#         @wraps(f)
#         def decorated_function(*args, **kwargs):
#             if not current_user.is_authenticated:
#                 flash("Devi essere autenticato per accedere a questa pagina.")
#                 return redirect(url_for('login'))
#             if not any(current_user.has_role(role) for role in role_names):
#                 flash("Non hai il permesso per accedere a questa pagina.")
#                 return abort(403)
#             return f(*args, **kwargs)
#         return decorated_function
#     return decorator

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

    # check if the user actually exists
    # take the user-supplied password, hash it, and compare it to the hashed password in the database
    if not user or not user.check_password(password):
        flash('Please check your login details and try again.')
        return redirect(url_for('auth.login')) # if the user doesn't exist or password is wrong, reload the page

    # if the above check passes, then we know the user has the right credentials
    login_user(user, remember=remember)
    return redirect(url_for('auth.profile'))  

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))

@app.route('/profile')
@login_required
def profile():
     return render_template('auth/profile.html', name=current_user.username)

@app.route('/signup')
def signup():
    return render_template('auth/signup.html')

@app.route('/signup', methods=['POST'])
def signup_post():
    # signup input validation and logic
    #TODO verify password strenght
    username = request.form["username"] #as an alternative use request.form.get("username")
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
    
    user = User.query.filter_by(email=email).first() # if this returns a user, then the email already exists in database
    if user: 
        # if a user is found, we want to redirect back to signup page so user can try again
        # display some kind of error
        flash('User with this email address already exists')
        return redirect(url_for('auth.signup'))

    user = User(username=username, email=email)
    user.set_password(password)  # Imposta la password criptata
    db.session.add(user)  # equivalente a INSERT
    db.session.commit()


    login_user(user)
    return redirect(url_for('auth.login'))


# @app.route('/dashboard')
# @user_has_role('admin')
# def admin_dashboard():
    return render_template('auth/dashboard.html')

@login_manager.user_loader
def load_user(user_id):
    # since the user_id is just the primary key of our user table, use it in the query for the user
    stmt = db.select(User).filter_by(id=user_id)
    user = db.session.execute(stmt).scalar_one_or_none()
    
    # return User.query.get(int(user_id))   # legacy
    
    return user

