from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sqlalchemy.orm import relationship
from flask_login import UserMixin

db = SQLAlchemy()

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)  # Hashed parole
    role = db.Column(db.String(50), nullable=False, default='user')  # Lietotāja loma

# Lietotāju kartiņas tabula
class Kartinas(db.Model):
    __tablename__ = 'kartinas'
    id = db.Column(db.Integer, primary_key=True)
    vards = db.Column(db.String(100), nullable=False)
    uzvards = db.Column(db.String(100), nullable=False)
    epasts = db.Column(db.String(150), unique=True, nullable=False)
    tel_nr = db.Column(db.String(15))
    amats = db.Column(db.String(100))
    acc_date = db.Column(db.DateTime, default=datetime.now)
    disable_date = db.Column(db.DateTime)
    #lietotaja_vards = db.Column(db.String(100))
    samaccountname = db.Column(db.String(100), unique=True)  # Lietotāja vārds no AD
    statuss = db.Column(db.Integer, default=1)
    last_synced = db.Column(db.DateTime, default=datetime.now)
    groups = relationship('AdGroups', secondary='user_groups', back_populates='users')
# AD grupu tabula
class AdGroups(db.Model):
    __tablename__ = 'ad_groups'
    group_id = db.Column(db.Integer, primary_key=True)
    group_name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.String(200), nullable=True)
    users = db.relationship('Kartinas', secondary='user_groups', back_populates='groups')
# Users group tabula
class UserGroups(db.Model):
    __tablename__ = 'user_groups'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('kartinas.id'), nullable=False)
    group_id = db.Column(db.Integer, db.ForeignKey('ad_groups.group_id'), nullable=False)

# AD sinhronizācijas žurnāls
class AdSyncLog(db.Model):
    __tablename__ = 'ad_sync_log'
    sync_id = db.Column(db.Integer, primary_key=True)
    synced_at = db.Column(db.DateTime, default=datetime.now)
    total_users_synced = db.Column(db.Integer)

# Informācijas sistēmu kategorijas
#class IsKategorijas(db.Model):
#    __tablename__ = 'is_kategorijas'
#    kategorija_id = db.Column(db.Integer, primary_key=True)
#    kategorija_nosaukums = db.Column(db.String(100), unique=True, nullable=False)

# Informācijas sistēmu resursi
#class IsResursi(db.Model):
#    __tablename__ = 'is_resursi'
#    resursa_id = db.Column(db.Integer, primary_key=True)
#    kategorija_id = db.Column(db.Integer, db.ForeignKey('is_kategorijas.kategorija_id'))
#    resursa_nosaukums = db.Column(db.String(100), nullable=False)

# Resursu tiesības
#class ResursaTiesibas(db.Model):
#    __tablename__ = 'resursa_tiesibas'
#    tiesibas_id = db.Column(db.Integer, primary_key=True)
#    resursa_id = db.Column(db.Integer, db.ForeignKey('is_resursi.resursa_id'))
#    lietotajs_id = db.Column(db.Integer, db.ForeignKey('kartinas.id'))
#    tiesibu_limenis = db.Column(db.String(50))
#    tiesibu_datums = db.Column(db.DateTime, default=datetime.now)
#    anul_dienas = db.Column(db.DateTime)

class sis(db.Model):
    __tablename__ = 'sis'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    is_name = db.Column(db.String(100), nullable=False)

class Tiesibas(db.Model):
    __tablename__ = 'tiesibas'
    id = db.Column(db.Integer, primary_key=True)
    t_name = db.Column(db.String(100), nullable=False)

class KartinasISTiesibas(db.Model):
    __tablename__ = 'kartinas_is_tiesibas'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('kartinas.id'), nullable=False)
    is_id = db.Column(db.Integer, db.ForeignKey('sis.id'), nullable=False)
    tiesibas_id = db.Column(db.Integer, db.ForeignKey('tiesibas.id'), nullable=False)

    # Attiecības
    user = db.relationship('Kartinas', backref='kartinas_is_tiesibas')
    is_entity = db.relationship('sis', backref='kartinas_is_tiesibas')  # Atjaunināta relācija
    tiesibas = db.relationship('Tiesibas', backref='kartinas_is_tiesibas')
