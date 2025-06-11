from flask import Flask, jsonify, render_template, request, redirect, url_for, flash
from datetime import datetime
import webbrowser
from threading import Timer
import os
from flask_sqlalchemy import SQLAlchemy
import sys

app = Flask(__name__)
# Il est crucial de définir une clé secrète pour utiliser les messages flash.
# Remplacez ceci par une chaîne de caractères aléatoire et sécurisée dans une vraie application.
app.secret_key = 'votre_cle_secrete_super_securisee_ici_a_changer'

# Déterminer le chemin de base pour les fichiers de données (comme planning.db)
if getattr(sys, 'frozen', False):
    # Si l'application est exécutée comme un bundle/exécutable gelé (par PyInstaller)
    base_path = os.path.dirname(sys.executable)
else:
    # Si l'application est exécutée comme un script Python normal
    base_path = os.path.dirname(os.path.abspath(__file__))

# Configuration de la base de données SQLite
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(base_path, "planning.db")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False # Optionnel: supprime un avertissement
db = SQLAlchemy(app)

# Modèle de données pour les rendez-vous
class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True) # Clé primaire auto-incrémentée
    customer_name = db.Column(db.String(100), nullable=False)
    vehicle_plate = db.Column(db.String(20), nullable=False)
    service_description = db.Column(db.Text, nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(50), nullable=False, default='Planifié')
    technician = db.Column(db.String(100), nullable=False)

    def __repr__(self):
        return f'<Appointment {self.id} - {self.customer_name}>'

# La liste en mémoire appointments_db et next_id ne sont plus nécessaires.

def open_browser():
    """Ouvre le navigateur par défaut sur l'URL de l'application."""
    webbrowser.open_new_tab("http://127.0.0.1:5000/")

@app.route('/')
def index():
    # Récupérer tous les rendez-vous de la base de données, triés par date
    appointments = Appointment.query.order_by(Appointment.start_time).all()
    return render_template('planning.html', appointments=appointments)

@app.route('/appointments/new', methods=['GET', 'POST'])
def new_appointment():
    if request.method == 'POST':
        customer_name = request.form.get('customer_name')
        vehicle_plate = request.form.get('vehicle_plate')
        service_description = request.form.get('service_description')
        start_time_str = request.form.get('start_time')
        technician = request.form.get('technician')

        if not all([customer_name, vehicle_plate, service_description, start_time_str, technician]):
            flash('Tous les champs sont obligatoires.', 'error')
            return render_template('new_appointment_form.html',
                                   customer_name=customer_name,
                                   vehicle_plate=vehicle_plate,
                                   service_description=service_description,
                                   start_time_str=start_time_str,
                                   technician=technician), 400
        try:
            start_time = datetime.strptime(start_time_str, '%Y-%m-%dT%H:%M')
            
            new_appt_obj = Appointment(
                customer_name=customer_name,
                vehicle_plate=vehicle_plate,
                service_description=service_description,
                start_time=start_time,
                # status="Planifié", # Le statut par défaut est déjà "Planifié" dans le modèle
                technician=technician
            )
            db.session.add(new_appt_obj)
            db.session.commit()
            flash('Rendez-vous ajouté avec succès!', 'success')
            return redirect(url_for('index'))
        except ValueError:
            flash('Format de date invalide. Utilisez YYYY-MM-DDTHH:MM.', 'error')
            return render_template('new_appointment_form.html',
                                   customer_name=customer_name,
                                   vehicle_plate=vehicle_plate,
                                   service_description=service_description,
                                   start_time_str=start_time_str,
                                   technician=technician), 400
    return render_template('new_appointment_form.html')

@app.route('/appointments/edit/<int:appointment_id>', methods=['GET', 'POST'])
def edit_appointment(appointment_id):
    # Récupérer le rendez-vous par ID ou renvoyer une erreur 404 s'il n'existe pas
    appointment_to_edit = Appointment.query.get_or_404(appointment_id)

    if request.method == 'POST':
        # Les données du formulaire sont récupérées
        customer_name = request.form.get('customer_name')
        vehicle_plate = request.form.get('vehicle_plate')
        service_description = request.form.get('service_description')
        start_time_str = request.form.get('start_time')
        technician = request.form.get('technician')
        # Optionnel: si vous voulez aussi pouvoir modifier le statut
        # status = request.form.get('status', appointment_to_edit.status)

        if not all([customer_name, vehicle_plate, service_description, start_time_str, technician]):
            flash('Tous les champs sont obligatoires pour la modification.', 'error')
            # Renvoyer l'objet original et la chaîne de date pour pré-remplissage
            # Le template utilisera appointment_to_edit pour les autres champs (anciennes valeurs)
            return render_template('edit_appointment_form.html',
                                   appointment=appointment_to_edit, 
                                   start_time_str=start_time_str), 400
        try:
            start_time = datetime.strptime(start_time_str, '%Y-%m-%dT%H:%M')
            
            appointment_to_edit.customer_name = customer_name
            appointment_to_edit.vehicle_plate = vehicle_plate
            appointment_to_edit.service_description = service_description
            appointment_to_edit.start_time = start_time
            appointment_to_edit.technician = technician
            # if status: # Si vous permettez la modification du statut
            #    appointment_to_edit.status = status
            
            db.session.commit()
            flash('Rendez-vous modifié avec succès!', 'success')
            return redirect(url_for('index'))
        except ValueError:
            flash('Format de date invalide pour la modification. Utilisez YYYY-MM-DDTHH:MM.', 'error')
            return render_template('edit_appointment_form.html',
                                   appointment=appointment_to_edit,
                                   start_time_str=start_time_str), 400
    else: # GET request
        # Pour pré-remplir le champ datetime-local, il faut formater la date correctement
        start_time_str_for_form = appointment_to_edit.start_time.strftime('%Y-%m-%dT%H:%M')
        return render_template('edit_appointment_form.html',
                               appointment=appointment_to_edit,
                               start_time_str=start_time_str_for_form)

@app.route('/api/appointments')
def api_appointments():
    all_appointments = Appointment.query.all()
    events = []
    for appt in all_appointments:
        events.append({
            'title': f"{appt.customer_name} ({appt.technician or 'N/A'}) - {appt.service_description}",
            'start': appt.start_time.isoformat(),
            'id': appt.id
        })
    return jsonify(events)

if __name__ == '__main__':
    # Crée la base de données et les tables si elles n'existent pas
    # Doit être dans le contexte de l'application pour accéder à `app` et `db`
    with app.app_context():
        db.create_all()

    if os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        Timer(1, open_browser).start()

    app.run(debug=True, host='0.0.0.0', port=5000)
