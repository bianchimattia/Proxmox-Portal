# blueprints/admin.py
import time, ipaddress, os
from flask_login import login_required
from flask import Blueprint, render_template, redirect, url_for, flash, current_app

from model.connection import db
from model.model import VmRequest, VmType, User, VmCredentials

from blueprints.auth import user_has_role

from utils.proxmox import proxmox_client, wait_task
from utils.ssh import gen_password, create_user_over_ssh
from utils.interfaces import wait_lxc_ipv4_from_interfaces

app = Blueprint('admin', __name__)


@app.route('/richieste')
@login_required
@user_has_role("admin")
def get_richieste():

    """
    Funzione per visualizzare tutte le richieste di VM.
    Fornisce una lista di richieste ordinate per data decrescente prendendole dal DB
    Una volta estrapolate, le passa al template e le visualizza

    """
    richieste = VmRequest.query.order_by(VmRequest.request_ts.desc()).all()
    return render_template('admin/richieste.html', requests=richieste)


@app.route('/utenti')
@login_required
@user_has_role("admin")
def get_utenti():

    """
    Funzione per visualizzare tutti gli utenti presenti nel portale
    Una volta estrapolati, li passa al template e li visualizza

    """

    utenti = User.query.order_by(User.username.desc()).all()
    return render_template('admin/utenti.html', users=utenti)


@app.route("/richieste/<int:req_id>/rifiuta", methods=["POST"])
@login_required
@user_has_role("admin")
def rifiuta(req_id: int):

    """
    Funzione per rifiutare una richiesta di creazione VM
    Esegue un controllo sullo stato e rifiuta la richiesta solo se lo stato è "PENDING"
    Cambia lo stato della richiesta nel DB in "REJECTED" e ritorna alla pagina delle richieste
    All'utente viene ritornato un messaggio per renderlo coscente del rifiuto

    """

    # ottieni l'ID della richiesta dal DB
    req = VmRequest.query.get_or_404(req_id)

    # verifica stato
    if req.status != "PENDING":
        flash(f"Non puoi rifiutare: stato attuale {req.status}", "warning")
        return redirect(url_for("admin.get_richieste"))

    # aggiorno dello stato
    req.status = "REJECTED"
    db.session.commit()

    flash("Richiesta rifiutata", "info")
    return redirect(url_for("admin.get_richieste"))


@app.route("/richieste/<int:req_id>/accetta", methods=["POST"])
@login_required
@user_has_role("admin")
def accetta(req_id: int):

    """
    Provisiona ed esegue un full clone partendo dal template presente nel nodo Proxmox
    Ridimensiona il disco e configura CPU e RAM in base al tipo di VM richiesto
    Una volta completato il clone, avvia la VM e ne legge l'IP assegnato via DHCP
    Crea un nuovo utente all'interno della VM tramite SSH con le credenziali generate
    Salva le credenziali di accesso alla VM nel DB

    """

    req = VmRequest.query.get(req_id)
    user = User.query.get(req.user_id)
    template_disk_gb = 8

    if req.status != "PENDING":
        flash(f"Non puoi accettare: stato attuale {req.status}", "warning")
        return redirect(url_for("admin.get_richieste"))

    vm_type = VmType.query.get(req.vm_type_id)
    if not vm_type:
        flash("Tipo VM non trovato", "danger")
        return redirect(url_for("admin.get_richieste"))

    try:
        # ottiene dati di accesso per API Proxmox
        proxmox = proxmox_client()
        node = os.getenv("PROXMOX_DEFAULT_NODE", "px1")

        # prepara parametri del clone
        template_vmid = int(vm_type.template_vmid)
        new_vmid = int(proxmox.cluster.nextid.get())
        hostname = f"vm-{user.username}-{new_vmid}"
        dimensione_disk = int(vm_type.disk)

        # clone template
        upid_clone = proxmox.nodes(node).lxc(template_vmid).clone.post(
            newid=new_vmid,
            hostname=hostname,
            full=1,
        )

        wait_task(proxmox, node, upid_clone, timeout_s=900)

        # ridimensiona il disco in base al tipo di VM scelto
        ridimensionamento_disco = dimensione_disk - template_disk_gb
        if ridimensionamento_disco > 0:

            upid_resize = proxmox.nodes(node).lxc(new_vmid).resize.put(
                disk="rootfs",
                size=f"+{ridimensionamento_disco}G",
            )
            
            wait_task(proxmox, node, upid_resize, timeout_s=300)

        # ram,cpu,hostname
        proxmox.nodes(node).lxc(new_vmid).config.put(
            cores=int(vm_type.cores),
            memory=int(vm_type.ram),
            hostname=hostname,
        )

        # avvio vm
        upid_start = proxmox.nodes(node).lxc(new_vmid).status.start.post()
        wait_task(proxmox, node, upid_start, timeout_s=300)

        # imposta username e password per la VM
        vm_username = user.username
        vm_password = gen_password(12)

        # ottiene l'ip della VM
        ipv4 = wait_lxc_ipv4_from_interfaces(proxmox, node, new_vmid, timeout_s=120)

        # crea l'utente all'interno della VM tramite SSH
        create_user_over_ssh(host_ip=ipv4,bootstrap_user="default_user",bootstrap_pass="Admin123",
            new_user=vm_username,new_pass=vm_password,make_sudo=True,lock_bootstrap=False,timeout_s=240)
        

        # aggiorna stato 
        req.status = "READY"
        db.session.commit()

        # salva le credenziali di accesso da fornire all'utente
        creds = VmCredentials.query.filter_by(vm_request_id=req.id).first()
        if not creds:
            creds = VmCredentials(vm_request_id=req.id)

        creds.ip_address = ipv4
        creds.username = vm_username
        creds.password = vm_password
        creds.hostname = hostname

        db.session.add(creds)
        db.session.commit()

    except Exception as e:
        req.status = "FAILED"
        db.session.commit()

    return redirect(url_for("admin.get_richieste"))
