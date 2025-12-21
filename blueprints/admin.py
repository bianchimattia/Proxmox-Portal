# blueprints/admin.py
import time, ipaddress
from flask_login import login_required
from flask import Blueprint, render_template, redirect, url_for, flash

from model.connection import db
from blueprints.auth import user_has_role
from utils.proxmox import proxmox_client

from model.model import VmRequest, VmType, User, VmCredentials
from flask import current_app

app = Blueprint('admin', __name__)

# fonte chatgpt, causa: creazione fallita perchè provavo ad avviarla mentre il clone era ancora in corso
def wait_task(proxmox, node: str, upid: str, timeout_s: int = 600):
    """
    Polling di un task Proxmox (UPID) fino a fine.
    - timeout_s: quanto aspettare massimo
    """
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        st = proxmox.nodes(node).tasks(upid).status.get()
        if st.get("status") == "stopped":
            exitstatus = st.get("exitstatus")
            if exitstatus == "OK":
                return
            raise RuntimeError(f"Task Proxmox fallito: {exitstatus}")
        time.sleep(1)
    raise RuntimeError("Timeout: task Proxmox non terminato in tempo")

def _normalize_ip(ip: str) -> str:
    return ip.split("/", 1)[0].strip()

def _is_valid_ipv4(ip: str) -> bool:
    try:
        ip = _normalize_ip(ip)
        obj = ipaddress.ip_address(ip)
        return (
            obj.version == 4
            and not obj.is_loopback
            and not obj.is_link_local
        )
    except Exception:
        return False


def wait_lxc_ipv4_from_interfaces(proxmox, node: str, vmid: int, timeout_s: int = 180) -> str:
    deadline = time.time() + timeout_s

    while time.time() < deadline:
        ifaces = proxmox.nodes(node).lxc(vmid).interfaces.get()

        # Debug utile: se vuoi capire cosa arriva davvero
        # print("IFACES:", ifaces)

        if isinstance(ifaces, list):
            eth0_first = sorted(ifaces, key=lambda x: 0 if x.get("name") == "eth0" else 1)

            for nic in eth0_first:
                inet = nic.get("inet")

                # Caso A: stringa "x.x.x.x/24"
                if isinstance(inet, str) and _is_valid_ipv4(inet):
                    return _normalize_ip(inet)

                # Caso B: lista di stringhe
                if isinstance(inet, list):
                    for item in inet:
                        if isinstance(item, str) and _is_valid_ipv4(item):
                            return _normalize_ip(item)

        time.sleep(1)

    raise RuntimeError(f"Timeout: IP DHCP non trovato per CT {vmid} entro {timeout_s}s")



@app.route('/richieste')
@login_required
@user_has_role("admin")
def get_richieste():
    richieste = VmRequest.query.order_by(VmRequest.request_ts.desc()).all()
    return render_template('admin/richieste.html', requests=richieste)

@app.route('/utenti')
@login_required
@user_has_role("admin")
def get_utenti():
    utenti = User.query.order_by(User.username.desc()).all()
    return render_template('admin/utenti.html', users=utenti)

@app.route("/richieste/<int:req_id>/rifiuta", methods=["POST"])
@login_required
@user_has_role("admin")
def rifiuta(req_id: int):
    req = VmRequest.query.get_or_404(req_id)

    if req.status != "PENDING":
        flash(f"Non puoi rifiutare: stato attuale {req.status}", "warning")
        return redirect(url_for("admin.get_richieste"))

    req.status = "REJECTED"
    db.session.commit()

    flash("Richiesta rifiutata", "info")
    return redirect(url_for("admin.get_richieste"))


@app.route("/richieste/<int:req_id>/accetta", methods=["POST"])
@login_required
@user_has_role("admin")
def accetta(req_id: int):
    req = VmRequest.query.get(req_id)
    user = User.query.get(req.user_id)

    if req.status != "PENDING":
        flash(f"Non puoi accettare: stato attuale {req.status}", "warning")
        return redirect(url_for("admin.get_richieste"))

    vm_type = VmType.query.get(req.vm_type_id)
    if not vm_type:
        flash("Tipo VM non trovato", "danger")
        return redirect(url_for("admin.get_richieste"))

    try:
        proxmox = proxmox_client()
        node = current_app.config["PROXMOX_DEFAULT_NODE"]

        template_vmid = int(vm_type.template_vmid)
        new_vmid = int(proxmox.cluster.nextid.get())
        hostname = f"vm-{user.username}-{new_vmid}"

        # clone template
        upid_clone = proxmox.nodes(node).lxc(template_vmid).clone.post(
            newid=new_vmid,
            hostname=hostname,
            full=1,
        )
        wait_task(proxmox, node, upid_clone, timeout_s=900)

        # ram,cpu,hostname
        proxmox.nodes(node).lxc(new_vmid).config.put(
            cores=int(vm_type.cores),
            memory=int(vm_type.ram),
            hostname=hostname,
        )

        # avvio vm
        upid_start = proxmox.nodes(node).lxc(new_vmid).status.start.post()
        wait_task(proxmox, node, upid_start, timeout_s=300)

        # ✅ leggi IP (DHCP) dal container running
        ipv4 = wait_lxc_ipv4_from_interfaces(proxmox, node, new_vmid, timeout_s=120)

        req.status = "READY"
        db.session.commit()

        # ✅ salva credenziali / dati accesso (adatta i campi al tuo model)
        creds = VmCredentials.query.filter_by(vm_request_id=req.id).first()
        if not creds:
            creds = VmCredentials(vm_request_id=req.id)

        # NON fare creds.vm_request_id = new_vmid
        creds.ip_address = ipv4
        creds.username = current_app.config["VM_DEFAULT_USERNAME"]
        creds.password = current_app.config["VM_DEFAULT_PASSWORD"]
        creds.hostname = hostname

        db.session.add(creds)
        db.session.commit()


        flash(f"VM creata e avviata (CT {new_vmid}) - IP: {ipv4}", "success")

    except Exception as e:
        req.status = "FAILED"
        db.session.commit()
        print("ERRORE PROVISIONING:", repr(e))
        flash(f"Errore creazione VM: {e}", "danger")

    return redirect(url_for("admin.get_richieste"))
