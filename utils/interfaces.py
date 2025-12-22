# utils/interfaces.py
import time,ipaddress


def _normalize_ip(ip: str) -> str:

    """
    Rimuove la parte di subnet da un IP (es: /24) e spazi bianchi.

    """
    return ip.split("/", 1)[0].strip()

# funzione creata e consigliata da ChatGPT per evitare problemi di IP
def _is_valid_ipv4(ip: str) -> bool:

    """
    Funzione che verifica se l'IP è valido
    Controlla che sia IPV4 e che non sia loopback o link-local
    Ritorna True se l'IP è valido, False altrimenti

    """

    try:
        # taglia la subnet
        ip = _normalize_ip(ip)

        # converte in oggetto IP
        obj = ipaddress.ip_address(ip)

        return (
            obj.version == 4
            and not obj.is_loopback
            and not obj.is_link_local
        )
    except Exception:
        return False

# funzione per estrapolare l'IP in DHCP del container clonato, fonte ChatGPT
def wait_lxc_ipv4_from_interfaces(proxmox, node: str, vmid: int, timeout_s: int = 180) -> str:

    """    
    :param proxmox: parametro contente le connessioni Proxmox
    :param node: parametro contenente il nodo di proxmox
    :param vmid: id del container appena creato
    :param timeout_s: timeout della richiesta. se raggiunto va in timeout

    Funzione che estrae l'IP in DHCP del container clonato
    Ritorna l'IP come stringa

    """

    deadline = time.time() + timeout_s

    while time.time() < deadline:
        # ottiene le interfacce di rete del container
        ifaces = proxmox.nodes(node).lxc(vmid).interfaces.get()

        if isinstance(ifaces, list):
            # mette al primo posto eth0 che dovrebbe contenere l'IP in DHCP
            eth0_first = sorted(ifaces, key=lambda x: 0 if x.get("name") == "eth0" else 1)

            for nic in eth0_first:
                inet = nic.get("inet")

                # stringa "x.x.x.x/24"
                if isinstance(inet, str) and _is_valid_ipv4(inet):
                    return _normalize_ip(inet)

                # lista di stringhe
                if isinstance(inet, list):
                    for item in inet:
                        if isinstance(item, str) and _is_valid_ipv4(item):
                            return _normalize_ip(item)

        time.sleep(1)

    raise RuntimeError(f"IP DHCP non trovato")