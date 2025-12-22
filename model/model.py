import os
from model.connection import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash


user_roles = db.Table('user_roles',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('role_id', db.Integer, db.ForeignKey('role.id'))
)

class Role(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=False)

    def __repr__(self):
        return f'<Role {self.name}>'

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))

    # Relazione many-to-many tra User e Role
    roles = db.relationship('Role', secondary=user_roles, backref=db.backref('users', lazy='dynamic'))

    add_ts = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp())

    def set_password(self, password):
        """Imposta la password criptata."""
        self.password_hash = generate_password_hash(password)

    def has_role(self, role_name):
        return any(role.name == role_name for role in self.roles)

    def check_password(self, password):
        """Verifica se la password è corretta."""
        return check_password_hash(self.password_hash, password)
    
    def __str__(self):
        user = f'User(id={self.id}, username={self.username}, email={self.email}, added={self.add_ts})'
        return user
    
    def __repr__(self):
        return f'<User = {self.to_dict}>'
    
    def to_dict(self):
        
        alt = {}
        alt['id'] = self.id
        alt['username'] = self.username
        alt['email'] = self.email
        alt['added'] = self.add_ts.isoformat()
        
        return alt

class VmType(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    
    name = db.Column(db.String(50), unique=True, nullable=False)
    cores = db.Column(db.Integer, nullable=False)
    ram = db.Column(db.Integer, nullable=False)  # in MB
    disk = db.Column(db.Integer, nullable=False)  # in GB
    template_vmid = db.Column(db.Integer, nullable=False)  # ID del template VM in Proxmox

    
    def __repr__(self):
        return f'<VmType {self.name} cores={self.cores} ram={self.ram} disk={self.disk}>'

class VmRequest(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    vm_type_id = db.Column(db.Integer, db.ForeignKey('vm_type.id'), nullable=False)
    status = db.Column(db.String(50), nullable=False, default='PENDING')
    request_ts = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp())

    user = db.relationship('User', backref=db.backref('vm_requests', lazy='dynamic'))
    vm_type = db.relationship('VmType', backref=db.backref('vm_requests', lazy='dynamic'))

    def __repr__(self):
        return f'<VmRequest id={self.id} user_id={self.user_id} vm_type_id={self.vm_type_id} status={self.status}>'

class VmCredentials(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    vm_request_id = db.Column(db.Integer, db.ForeignKey('vm_request.id'), nullable=False)
    hostname = db.Column(db.String(100), nullable=False)
    ip_address = db.Column(db.String(45), nullable=False)
    username = db.Column(db.String(50), nullable=False)
    password = db.Column(db.String(128), nullable=False) 
    add_ts = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp())

    vm_request = db.relationship('VmRequest', backref=db.backref('credentials', uselist=False))

    def __repr__(self):
        return f'<VmCredentials id={self.id} vm_request_id={self.vm_request_id} ip_address={self.ip_address}>'

def init_db():  

    # Verifica se i ruoli esistono già
    if not db.session.execute(db.select(Role).filter_by(name='admin')).scalars().first():
        admin_role = Role(name='admin')
        db.session.add(admin_role)
        db.session.commit()

    if not db.session.execute(db.select(Role).filter_by(name='user')).scalars().first():
        user_role = Role(name='user')
        db.session.add(user_role)
        db.session.commit()

    # Verifica se l'utente admin esiste già
    if not db.session.execute(db.select(User).filter_by(username='admin')).scalars().first():
        admin_user = User(username=os.getenv("PORTAL_ADMIN_USERNAME"), email="admin@example.com")
        admin_user.set_password(os.getenv("PORTAL_ADMIN_PASSWORD", "Admin$00"))

        # Aggiunge il ruolo 'admin' all'utente
        admin_role = db.session.execute(db.select(Role).filter_by(name='admin')).scalars().first()
        admin_user.roles.append(admin_role)

        db.session.add(admin_user)
        db.session.commit()


    # Aggiungi tipi di VM di esempio se non esistono
    if not db.session.execute(db.select(VmType)).scalars().first():
        bronze = VmType(name='bronze', cores=1, ram=512, disk=10, template_vmid=int(os.getenv("PROXMOX_TEMPLATE_ID", "1102")))
        silver = VmType(name='silver', cores=2, ram=1024, disk=15, template_vmid=int(os.getenv("PROXMOX_TEMPLATE_ID", "1102")))
        gold = VmType(name='gold', cores=4, ram=2048, disk=20, template_vmid=int(os.getenv("PROXMOX_TEMPLATE_ID", "1102")))

        db.session.add_all([bronze, silver, gold])
        db.session.commit()