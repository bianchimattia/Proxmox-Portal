# blueprints/user.py
from flask_login import LoginManager, login_required, current_user
from flask import Blueprint, render_template, redirect, url_for, request, flash
from model.model import User, VmRequest, VmCredentials
from model.connection import db
from blueprints.auth import user_has_role

app = Blueprint('user', __name__)

# route per visualizzare il form di richiesta creazione VM
@app.route('/creazione_vm')
@login_required
@user_has_role("user")
def get_creazione_form():
    return render_template('user/creazione.html')

# route per visualizzare la lista delle VM dell'utente, fornisce tutte le credenziali d'accesso salvate in DB
@app.route('/lista')
@login_required
@user_has_role("user")
def get_lista_vm():
    credenziali = (VmCredentials.query.join(VmRequest, VmCredentials.vm_request_id == VmRequest.id).filter(VmRequest.user_id == current_user.id).
                   order_by(VmCredentials.add_ts.desc()).all())
    
    return render_template('user/lista_vm.html', credentials=credenziali)

# route per gestire la richiesta di creazione VM
# controlla il tipo della VM e salva nel DB la richiesta con stato PENDING
@app.route('/creazione_vm', methods=['POST'])
@login_required
@user_has_role("user")
def crea_vm():

    vm_type_id = int(request.form.get('vm_type_id'))
    if vm_type_id is None:
        return redirect(url_for('user.get_creazione_form'))

    new_request = VmRequest(vm_type_id=vm_type_id, user_id=current_user.id, status='PENDING')
    db.session.add(new_request)
    db.session.commit()
    flash("Richiesta di creazione VM inviata")
    return redirect(url_for('user.get_creazione_form'))