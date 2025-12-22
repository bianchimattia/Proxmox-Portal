# utils/proxmox.py
import os,time
from proxmoxer import ProxmoxAPI
from flask import current_app

# funzione che estrae dal .env le variabili per connettersi a Proxmox
def proxmox_client():
    return ProxmoxAPI(
        os.getenv("PROXMOX_HOST", "192.168.56.15"),
        user=os.getenv("PROXMOX_USER" , "root@pam"),
        token_name=os.getenv("PROXMOX_TOKEN_NAME"),
        token_value=os.getenv("PROXMOX_TOKEN_VALUE"),
        verify_ssl=False,
    )


# fonte chatgpt, causa: creazione fallita perchè provavo ad avviarla mentre il clone era ancora in corso
def wait_task(proxmox, node: str, upid: str, timeout_s: int = 600):
    
    """
    Funzione che attende il completamento di una task Proxmox.
    Verifica continuamente lo stato della task fino a quando non viene completata o scade il timeout.

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
