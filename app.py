from  flask import Flask, render_template, request, redirect, url_for, flash
from flask_migrate import Migrate
from config import Config
from models import db, User, Kartinas, AdGroups, AdSyncLog, KartinasISTiesibas, sis, Tiesibas
from datetime import datetime
from ad_sync import sync_ad_users_and_groups
from flask_login import LoginManager, login_user, logout_user, current_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)
migrate = Migrate(app, db)

# Flask-Login
login_manager = LoginManager()
login_manager = LoginManager(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Sākumlapa
@app.route('/')
#@login_required
def index():
    results = Kartinas.query.all()
    return render_template('index.html', results=results)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            login_user(user)
            flash('Pieslēgšanās veiksmīga!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Nepareizs lietotājvārds vai parole.', 'danger')

    return render_template('login.html')
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Jūs esat veiksmīgi izlogojies!', 'success')
    return redirect(url_for('login'))



# AD sinhronizācija
@app.route('/ad_sync', methods=['GET', 'POST'])
#@login_required
def ad_sync():
    if request.method == 'POST':
        sync_ad_users_and_groups()  # Izsauc AD sinhronizācijas funkciju
        flash("AD sinhronizācija veiksmīgi pabeigta!", "success")
        return redirect(url_for('ad_sync'))
    users = Kartinas.query.filter_by(statuss=1).all()
    return render_template('ad_sync.html', users=users)

@app.route('/lietotaja_kartina/<int:id>', methods=['GET', 'POST'])
#@login_required
def lietotaja_kartina(id):
    # Meklēt lietotāju pēc ID
    lietotajs = Kartinas.query.filter_by(id=id).first()

    # Fetch existing permissions for this user
    existing_permissions_raw = (
    db.session.query(sis.is_name, Tiesibas.t_name, KartinasISTiesibas)
    .join(sis, KartinasISTiesibas.is_id == sis.id)
    .join(Tiesibas, KartinasISTiesibas.tiesibas_id == Tiesibas.id)
    .filter(KartinasISTiesibas.user_id == id)
    .all()
)

    # Fetch available IS and tiesibas for dropdowns
    available_is = sis.query.all()
    available_tiesibas = Tiesibas.query.all()
    
    # Formatē atļaujas grupētas pēc sistēmas nosaukuma
    existing_permissions = {}
    for is_name, t_name, kartinas_tiesibas in existing_permissions_raw:
        if is_name not in existing_permissions:
            existing_permissions[is_name] = []
        existing_permissions[is_name].append({
        't_name': t_name,
        'tiesibas_id': kartinas_tiesibas.tiesibas_id,
        'is_id': kartinas_tiesibas.is_id
    })
    if request.method == 'POST':
        delete_is_id = request.form.get('delete_is_id')
        delete_tiesibas_id = request.form.get('delete_tiesibas_id')

        # Dzēš konkrētu tiesību sistēmai
        if delete_is_id and delete_tiesibas_id:
            KartinasISTiesibas.query.filter_by(
                user_id=id,
                is_id=delete_is_id,
                tiesibas_id=delete_tiesibas_id
            ).delete()
            db.session.commit()
            flash('Tiesības veiksmīgi dzēstas!', 'success')
            return redirect(url_for('lietotaja_kartina', id=id))

        # Handle form submission for adding/updating permissions
        is_id = request.form.get('is_id')
        tiesibas_ids = request.form.getlist('tiesibas_ids')

        for tiesibas_id in tiesibas_ids:
            # Avoid duplicates
            if not db.session.query(KartinasISTiesibas).filter_by(
                user_id=id, is_id=is_id, tiesibas_id=tiesibas_id
            ).first():
                new_permission = KartinasISTiesibas(
                    user_id=id, is_id=is_id, tiesibas_id=tiesibas_id
                )
                db.session.add(new_permission)

        db.session.commit()
        flash("Tiesības veiksmīgi saglabātas!", "success")
        return redirect(url_for('lietotaja_kartina', id=id))

    return render_template(
        'lietotaja_kartina.html',
        lietotajs=lietotajs,
        existing_permissions=existing_permissions,
        available_is=available_is,
        available_tiesibas=available_tiesibas
    )

@app.route('/add_is', methods=['GET', 'POST'])
#@login_required
def add_is():
    if request.method == 'POST':
        is_name = request.form.get('isName', '').strip()  # Sistēmas nosaukums

        # Pievienot sistēmu, ja ievadīts sistēmas nosaukums
        if is_name:
            existing_is = sis.query.filter_by(is_name=is_name).first()
            if existing_is:
                flash(f"Sistēma '{is_name}' jau eksistē!", "warning")
            else:
                new_is = sis(is_name=is_name)
                db.session.add(new_is)
                db.session.commit()
                flash(f"Sistēma '{is_name}' veiksmīgi pievienota!", "success")
        else:
            flash("Lūdzu ievadiet sistēmas nosaukumu!", "danger")

        return redirect(url_for('add_is'))

    return render_template('add_is.html')

@app.route('/add_tiesibas', methods=['GET', 'POST'])
#@login_required
def add_tiesibas():
    if request.method == 'POST':
        tiesibas_text = request.form.get('tiesibas', '').strip()  # Tiesību teksts

        # Pievienot tiesības, ja ievadītas
        if tiesibas_text:
            tiesibas_names = [t.strip() for t in tiesibas_text.split('\n') if t.strip()]
            for t_name in tiesibas_names:
                existing_tiesibas = Tiesibas.query.filter_by(t_name=t_name).first()
                if existing_tiesibas:
                    flash(f"Tiesības '{t_name}' jau eksistē!", "warning")
                else:
                    new_tiesibas = Tiesibas(t_name=t_name)
                    db.session.add(new_tiesibas)
                    db.session.commit()
                    flash(f"Tiesības '{t_name}' veiksmīgi pievienotas!", "success")
        else:
            flash("Lūdzu ievadiet vismaz vienu tiesību!", "danger")

        return redirect(url_for('add_tiesibas'))

    return render_template('add_tiesibas.html')
# Flask lietotnes palaišana
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
