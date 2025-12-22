# utils/ssh.py
import time,socket,secrets,string,shlex,paramiko

# metodi generai in parte da ChatGPT per risolvere vari problemi come la mancata connessione SSH e mancata creazione dell'utente
# genera una password casuale 
def gen_password(n: int = 16) -> str:

    """
    Funzione per generare una password da fornire all'utente
    Genera una stringa casuale di lunghezza n composta da lettere maiuscole, minuscole, numeri e simboli
    Ritorna la password generata come stringa

    """
    caratteri = string.ascii_letters + string.digits + "!@#$%_-+"
    car_random = []
    for _ in range(n):
        # scelta casuale di un carattere della stringa caratteri
        car_random.append(secrets.choice(caratteri))

    password = "".join(car_random)
    return password

# funzione simile a wait_task
def wait_port(host: str, port: int = 22, timeout_s: int = 180) -> None:
    """Aspetta che la porta TCP sia raggiungibile (es: 22 per SSH)."""
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=3):
                return
        except OSError:
            time.sleep(2)
    raise RuntimeError(f"Porta {port} non disponibile su {host} entro {timeout_s}s")


def ssh_exec(host: str, user: str, password: str, cmd: str, timeout: int = 30) -> str:
    """Esegue un comando via SSH (non interattivo) e ritorna stdout. Alza eccezione se rc != 0."""
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        client.connect(hostname=host,username=user,password=password,timeout=timeout,banner_timeout=timeout,
            auth_timeout=timeout,allow_agent=False,look_for_keys=False,)

        stdin, stdout, stderr = client.exec_command(cmd)
        out = stdout.read().decode("utf-8", "ignore")
        err = stderr.read().decode("utf-8", "ignore")
        rc = stdout.channel.recv_exit_status()

        if rc != 0:
            raise RuntimeError(f"SSH cmd non riuscito")
        return out.strip()

    finally:
        try:
            client.close()
        except Exception:
            pass


def wait_ssh_up(host: str, user: str, password: str, timeout_s: int = 180) -> None:
    """
    Aspetta che:
    - la porta 22 sia aperta
    - il banner SSH risponda correttamente (paramiko)
    """
    wait_port(host, 22, timeout_s=timeout_s)

    deadline = time.time() + timeout_s
    last = None
    while time.time() < deadline:
        try:
            ssh_exec(host, user, password, "true", timeout=30)
            return
        except Exception as e:
            last = e
            time.sleep(2)

    raise RuntimeError(f"SSH non disponibile su {host} entro {timeout_s}s. Ultimo errore: {last}")


def sudo_cmd(cmd: str) -> str:
    """
    Usa sudo NOPASSWD:
    -n = non chiedere password (se non è NOPASSWD fallisce subito)
    bash -lc = supporta pipe, redirect, ecc.
    """
    return f"sudo -n bash -lc {cmd!r}"


def create_user_over_ssh(
        
    host_ip: str,bootstrap_user: str,bootstrap_pass: str,new_user: str,new_pass: str,make_sudo: bool = True,
        lock_bootstrap: bool = False,timeout_s: int = 180,) -> None:

    """
    Crea un utente dentro al CT via SSH usando un utente bootstrap che ha sudo NOPASSWD.
    """
    # sanity: evita caratteri strani nell'username (useradd è schizzinoso)
    if not new_user.isalnum():
        raise ValueError("new_user deve essere alfanumerico (solo lettere/numeri).")

    # aspetta che SSH sia su
    wait_ssh_up(host_ip, bootstrap_user, bootstrap_pass, timeout_s=timeout_s)

    # Check: sudo NOPASSWD deve funzionare
    ssh_exec(host_ip, bootstrap_user, bootstrap_pass, "sudo -n true")

    u = shlex.quote(new_user)

    # crea utente se non esiste
    ssh_exec(
        host_ip, bootstrap_user, bootstrap_pass,
        sudo_cmd(f"id -u {u} >/dev/null 2>&1 || useradd -m -s /bin/bash {u}")
    )

    # imposta password nuovo utente
    # (quoting robusto: chpasswd legge "user:pass")
    line = f"{new_user}:{new_pass}"
    ssh_exec(
        host_ip, bootstrap_user, bootstrap_pass,
        sudo_cmd(f"echo {shlex.quote(line)} | chpasswd")
    )

    # aggiunta utente a sudo
    if make_sudo:
        ssh_exec(
            host_ip, bootstrap_user, bootstrap_pass,
            sudo_cmd(f"getent group sudo >/dev/null 2>&1 || exit 0; usermod -aG sudo {u}")
        )

    # verifica della creazione utente
    ssh_exec(
        host_ip, bootstrap_user, bootstrap_pass,
        sudo_cmd(f"getent passwd {u}")
    )
