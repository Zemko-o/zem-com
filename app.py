from flask import Flask, request, jsonify, render_template
import csv
import os
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from google.oauth2 import service_account
from googleapiclient.discovery import build

app = Flask(__name__)
CSV_FILE = 'bookings.csv'

# Inicializácia CSV
if not os.path.exists(CSV_FILE):
    with open(CSV_FILE, mode='w', newline='') as file:
        writer = csv.writer(file, quoting=csv.QUOTE_ALL)
        writer.writerow(['Name', 'Email', 'Phone', 'Date', 'Timeslot', 'Package', 'Notes'])

# -------- ROUTES --------

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/galeria')
def galeria():
    return render_template('galeria.html')

@app.route('/pobyt')
def pobyt():
    return render_template('pobyt.html')

@app.route('/kontakt')
def kontakt():
    return render_template('kontakt.html')

@app.route('/wellness')
def wellness():
    return render_template('wellness.html')

@app.route('/booked-timeslots')
def booked_timeslots():
    date = request.args.get('date')
    if not date:
        return jsonify([])

    try:
        parsed_date = datetime.strptime(date, "%Y-%m-%d").strftime("%d/%m/%Y")
    except ValueError:
        return jsonify([])

    booked_slots = set()
    with open(CSV_FILE, mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        reader.fieldnames = [f.strip('"') for f in reader.fieldnames]
        for row in reader:
            if row.get('Date') == parsed_date:
                booked_slots.add(row.get('Timeslot', ''))

    return jsonify(list(booked_slots))

@app.route('/booked-dates')
def booked_dates():
    fully_booked = {}
    with open(CSV_FILE, mode='r') as file:
        reader = csv.DictReader(file)
        reader.fieldnames = [f.strip('"') for f in reader.fieldnames]
        for row in reader:
            date = row.get('Date')
            timeslot = row.get('Timeslot', '')
            if date:
                fully_booked.setdefault(date, []).append(timeslot)
    disabled_dates = [d for d, slots in fully_booked.items() if len(set(slots)) >= 3]
    return jsonify({
        'disabledDates': sorted(disabled_dates),
        'fullyBooked': fully_booked
    })

@app.route('/book', methods=['POST'])
def book():
    data = request.get_json()
    name = data.get('name')
    email = data.get('email')
    phone = data.get('phone')
    date_str = data.get('date')
    package = data.get('package')
    timeslot = data.get('timeslot')
    notes = data.get('notes', '')

    if not name or not email or not date_str or not package or not timeslot:
        return "Všetky polia sú povinné", 400

    try:
        booking_date = datetime.strptime(date_str, "%d/%m/%Y")
    except Exception:
        return "Neplatný formát dátumu", 400

    # Overenie konfliktu
    with open(CSV_FILE, mode='r') as file:
        reader = csv.DictReader(file)
        reader.fieldnames = [f.strip('"') for f in reader.fieldnames]
        for row in reader:
            if row['Date'] == date_str and row['Timeslot'] == timeslot:
                return f"Čas {timeslot} je už zarezervovaný pre {date_str}.", 409

    # Zapísať do CSV
    with open(CSV_FILE, mode='a', newline='') as file:
        writer = csv.writer(file, quoting=csv.QUOTE_ALL)
        writer.writerow([name, email, phone, date_str, timeslot, package, notes])

    # Poslať email
    send_email(name, email, date_str, timeslot, package, notes)

    # Pridať do kalendára
    add_to_google_calendar(name, email, date_str, timeslot, package, notes)

    return "Rezervácia bola úspešne uložená!"

# -------- EMAIL --------

def send_email(name, email, date_str, timeslot, package, notes):
    try:
        smtp_server = 'smtp.gmail.com'
        smtp_port = 587
        smtp_user = 'filipzemencik@gmail.com'
        smtp_password = 'jvuk amlc dcrk uzrz'  # alebo tvoje heslo do Gmail app

        to_admin = 'zemencikova.gabriela@gmail.com'
        subject_admin = 'Nová rezervácia'
        body_admin = f"""Nová rezervácia:\n\nMeno: {name}\nEmail: {email}\nDátum: {date_str}\nČas: {timeslot}\nBalíček: {package}\nPoznámky: {notes or '---'}"""

        subject_user = 'Potvrdenie rezervácie'
        body_user = f"""Ďakujeme za vašu rezerváciu {name}!\n\nTešíme sa na vás {date_str} o {timeslot}.\nBalíček: {package}\n\nTím Zem-Zen"""

        msg_admin = MIMEMultipart()
        msg_admin['From'] = smtp_user
        msg_admin['To'] = to_admin
        msg_admin['Subject'] = subject_admin
        msg_admin.attach(MIMEText(body_admin, 'plain'))

        msg_user = MIMEMultipart()
        msg_user['From'] = smtp_user
        msg_user['To'] = email
        msg_user['Subject'] = subject_user
        msg_user.attach(MIMEText(body_user, 'plain'))

        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.sendmail(smtp_user, to_admin, msg_admin.as_string())
        server.sendmail(smtp_user, email, msg_user.as_string())
        server.quit()

    except Exception as e:
        print(f"❌ Chyba pri odosielaní emailu: {e}")

# -------- KALENDÁR --------

def add_to_google_calendar(name, email, date_str, timeslot, package, notes):
    try:
        SERVICE_ACCOUNT_FILE = 'service_account.json'
        SCOPES = ['https://www.googleapis.com/auth/calendar']
        CALENDAR_ID = 'zemencikova.gabriela@gmail.com'

        credentials = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        service = build('calendar', 'v3', credentials=credentials)

        start_time = timeslot.split('-')[0].strip()  # vezme len "19:30"
        start_dt = datetime.strptime(f"{date_str} {start_time}", "%d/%m/%Y %H:%M")

        end_dt = start_dt + timedelta(hours=2)

        event = {
            'summary': f'Rezervácia - {name} ({package})',
            'description': f'Meno: {name}\nEmail: {email}\nBalíček: {package}\nPoznámky: {notes or "Žiadne"}',
            'start': {'dateTime': start_dt.isoformat(), 'timeZone': 'Europe/Bratislava'},
            'end': {'dateTime': end_dt.isoformat(), 'timeZone': 'Europe/Bratislava'}
        }

        created_event = service.events().insert(calendarId=CALENDAR_ID, body=event).execute()
        print(f"✅ Google kalendár: {created_event.get('htmlLink')}")
    except Exception as e:
        print(f"❌ Chyba pri vkladaní do kalendára: {e}")

# -------- SPUSTENIE --------

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
