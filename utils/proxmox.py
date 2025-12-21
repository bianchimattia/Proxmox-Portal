# utils/proxmox.py

from proxmoxer import ProxmoxAPI
from flask import current_app

def proxmox_client():
    return ProxmoxAPI(
        current_app.config["PROXMOX_HOST"],
        user=current_app.config["PROXMOX_USER"],
        token_name=current_app.config["PROXMOX_TOKEN_NAME"],
        token_value=current_app.config["PROXMOX_TOKEN_VALUE"],
        verify_ssl=current_app.config.get("PROXMOX_VERIFY_SSL", False),
    )
