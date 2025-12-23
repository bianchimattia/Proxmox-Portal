# Proxmox Portal - Mattia Bianchi

Portale web per la creazione di macchine virtuali. Il sistema si integra con l'hypervisor Proxmox creato in classe e permette la creazione
di nuove macchine virtuali destinate agli utenti. Le macchine saranno dei container LXC clonate da un template presente in Proxmox.

## Caratteristiche Principali

- **Autenticazione e Autorizzazione**: Sistema di login sicuro con gestione dei ruoli (User, Admin)
- **Gestione VM**: Clonazione di un template per la creazione di nuovi container con accesso tramite SSH con credenziali fornite
- **Sistema di Richieste**: Approvazione/rifiuto delle richieste di creazione VM
- **Gestione Utenti**: Gli admin possono visualizzare gli utenti e le richieste delle creazioni
- **Database SQLite**: Mantenimento dei dati degli utenti e delle credenziali d'accesso con Database SQLite
- **Connessioni SSH**: Integrazione con Proxmox tramite SSH
- **Interfaccia Web**: Template HTML responsivi con CSS personalizzato

## Struttura del Progetto

```
Proxmox-Portal/
├── app.py                 # Applicazione principale Flask
├── requirements.txt       # Dipendenze del progetto
├── config.py             # Configurazioni generali
├── README.md             # Questo file
│
├── blueprints/          # Moduli blueprint per le rotte
│   ├── auth.py          # Autenticazione e login
│   ├── admin.py         # Pagine amministratore
│   └── user.py          # Pagine utente
│
├── model/               # Modelli e connessioni database
│   ├── connection.py    # Inizializzazione SQLAlchemy
│   └── model.py         # Modelli User, Role, VM, Request
│
├── templates/           # Template HTML Jinja2
│   ├── base.html
│   ├── header_base.html
│   ├── auth/            # Template di autenticazione
│   ├── admin/           # Template amministrator
│   └── user/            # Template utente
│
├── static/              # File statici (CSS, JS)
│   └── css/
│       ├── header.css
│       ├── login.css
│       └── table.css
│
├── utils/               # Funzioni utilitarie
│   ├── interfaces.py    # Interfacce custom
│   ├── proxmox.py      # Integrazione Proxmox
│   └── ssh.py          # Connessioni SSH
│
├── migrations/          # Migrazioni database Alembic
│   ├── alembic.ini
│   ├── env.py
│   └── versions/        # File di migrazione
│
└── instance/            # File istanza (database, config locale)
```

## Prerequisiti

- **Python 3.8+**
- **pip** (gestore pacchetti Python)
- **Accesso al nodo di Proxmox** (per le funzionalità di integrazione)
- **Connessione SSH** verso il server Proxmox

## Implementazione da clone GitHub

- **Clonare il repository nella cartella che si vuole**
- **Creare il file .env nella root del progetto prendendo spunta da .env.example**
   - **PROXMOX_TOKEN_VALUE e PROXMOX_TOKEN_NAME sono presenti sotto al Datacenter in Proxmox**
- **Creare ambiene virtuale dalla root del progetto e installazione delle dipendenze**
```bash
1. python -m venv venv
2. ./.venv/bin/pip install --upgrade pip (linux) - pip install --upgrade pip (windows)
3. ./.venv/bin/pip install -r requirements.txt (linux) - pip install -r requirements.txt (windows)
```
- **Avviare il server**
```bash
python app.py
```

## Raggiungimento del Portale da Proxmox

### 1. Avvio del cluster Proxmox e dei nodi 

```bash
1. Avvio tramite VirtualBox dei nodi e tramite browser raggiungerli con il loro IP
2. Accesso con utente root
3. Avvio dei nodi
```

### 2. Accesso al portale tramite IP

```bash
1. Avviare il container "portal-hosting" presente sotto al px1
2. Verificare l'IP di rete della scheda di rete eth1
3. Tramite browser, raggiungere l'IP della macchina
```

## Accesso all'Applicazione

1. Naviga su **http://[ip del portal-hosting]**
2. Verrai reindirizzato automaticamente alla pagina di login
3. Accedi con le credenziali:
   - **Email**: admin@samtrevano.com (account admin default)
   - **Password**: Password&1 (uguale per l'utente di default mattia.bianchi@samtrevano.ch)

### Ruoli disponibili:

- **Admin**: Accesso completo, approvazione richieste, gestione utenti
- **User**: Creazione richieste, visualizzazione VM personali

## Funzionalità Principali

### Per gli Utenti
- **Creazione Richiesta VM**: Form per richiedere una nuova macchina virtuale
- **Dashboard**: Visualizzazione delle credenziali delle VM se accettate

### Per gli Amministratori
- **Gestione Richieste**: Approvazione/rifiuto delle richieste di VM
- **Gestione Utenti**: Lista degli utenti


## Integrazioni

### Proxmox
L'applicazione si integra con Proxmox tramite:
- **API REST** tramite `proxmoxer`
- **SSH** per operazioni avanzate tramite `paramiko`

Vedi `utils/proxmox.py` e `utils/ssh.py` per i dettagli

## Stack Tecnologico

| Componente | Versione | Descrizione |
|-----------|----------|------------|
| Flask | 3.1.2 | Framework web |
| SQLAlchemy | 2.0.45 | ORM database |
| Flask-Login | 0.6.3 | Gestione sessioni |
| Flask-Migrate | 4.1.0 | Migrazioni database |
| Proxmoxer | 2.2.0 | API Proxmox client |
| Paramiko | 4.0.0 | SSH client |
| Bcrypt | 5.0.0 | Hashing password |
| Requests | 2.32.5 | HTTP client |

## Troubleshooting

### Errore di connessione a Proxmox
Verifica le credenziali nel file `.env` e che il server Proxmox sia raggiungibile.


### Errore Bad Gateway Nginx alla creazione della macchina
Basta un reload della pagina, la macchina sarà stata creata e le credenziali fornite

---

**Ultima modifica**: 23 Dicembre 2025  
**Versione**: 1.0.0
**Autore**: Mattia Bianchi I4AA
