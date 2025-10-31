from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
#import csv
import os
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from google.oauth2 import service_account
from googleapiclient.discovery import build

# load environment variables
from dotenv import load_dotenv
load_dotenv()

from database.booking import db, Booking

app = Flask(__name__)

# Configure the database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///bookings.db'  # Use SQLite database
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize the database
db.init_app(app)

# CSV_FILE = 'bookings.csv'

# # Inicializácia CSV
# if not os.path.exists(CSV_FILE):
#     with open(CSV_FILE, mode='w', newline='') as file:
#         writer = csv.writer(file, quoting=csv.QUOTE_ALL)
#         writer.writerow(['Name', 'Email', 'Phone', 'Date', 'Timeslot', 'Package', 'Notes'])

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
        # Parse the date from the request
        parsed_date = datetime.strptime(date, "%Y-%m-%d").strftime("%d/%m/%Y")
    except ValueError:
        return jsonify([])

    # Query the database for booked timeslots on the given date
    booked_slots = Booking.query.filter_by(date=parsed_date).all()
    timeslots = [booking.timeslot for booking in booked_slots]

    return jsonify(timeslots)


@app.route('/booked-dates')
def booked_dates():
    # Query all bookings from the database
    bookings = Booking.query.all()
    fully_booked = {}

    # Group bookings by date and count timeslots
    for booking in bookings:
        fully_booked.setdefault(booking.date, []).append(booking.timeslot)

    # Identify dates where all timeslots are booked (3 timeslots per day)
    disabled_dates = [date for date, slots in fully_booked.items() if len(set(slots)) >= 3]

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

    # Validate required fields
    if not name or not email or not date_str or not package or not timeslot:
        return "Všetky polia sú povinné", 400

    try:
        # Validate date format
        booking_date = datetime.strptime(date_str, "%d/%m/%Y")
    except ValueError:
        return "Neplatný formát dátumu", 400

    # Check for conflicts in the database
    existing_booking = Booking.query.filter_by(date=date_str, timeslot=timeslot).first()
    if existing_booking:
        return f"Čas {timeslot} je už zarezervovaný pre {date_str}.", 409

    # Save the booking to the database
    new_booking = Booking(
        name=name,
        email=email,
        phone=phone,
        date=date_str,
        timeslot=timeslot,
        package=package,
        notes=notes
    )
    db.session.add(new_booking)
    db.session.commit()

    # Send email confirmation
    send_email(name, email, date_str, timeslot, package, notes)

    # Add to Google Calendar
    add_to_google_calendar(name, email, date_str, timeslot, package, notes)

    return "Rezervácia bola úspešne uložená!"

# -------- EMAIL WELLNESS --------

def send_email(name, email, date_str, timeslot, package, notes):
    try:
        smtp_server = 'mail.webhouse.sk'
        smtp_port = 587
        smtp_user = 'zem-zen@gacel.sk'
        smtp_password = os.getenv('zemzen_heslo')

        to_admin = 'zemencikova.gabriela@gmail.com'
        subject_admin = 'Nová rezervácia'
        body_admin = f"""Nová rezervácia:\n\nMeno: {name}\nEmail: {email}\nDátum: {date_str}\nČas: {timeslot}\nBalíček: {package}\nPoznámky: {notes or '---'}"""

        subject_user = 'Potvrdenie rezervácie wellness zážitku'
        body_user = f"""\
Milý/á {name},

ďakujeme, že ste si rezervovali wellness zážitok v našom centre – tešíme sa na Vás {date_str} o {timeslot}.  
Vybraný balíček: **{package}**

Prosíme, dostavte sa aspoň 10 minút pred začiatkom, aby ste si pobyt mohli naplno vychutnať. **Zrušenie rezervácie je možné najneskôr 24 hodín pred termínom.**  
V prípade neskoršieho zrušenia alebo nedostavenia sa môže byť účtovaný storno poplatok.

Ak máte akékoľvek otázky alebo špeciálne požiadavky, neváhajte nás kontaktovať.

Prajeme Vám krásny deň!

S pozdravom,  
Tím Zem-Zen
"""

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

def send_stay_email(name, email, phone, start_date, end_date, notes):
    try:
        smtp_server = 'smtp.gmail.com'
        smtp_port = 587
        smtp_user = 'filipzemencik@gmail.com'
        smtp_password = os.getenv('filip_gmail_heslo')

        to_admin = 'zemencikova.gabriela@gmail.com'
        subject_admin = 'Nová rezervácia pobytu'
        body_admin = f"""Nová rezervácia pobytu:\n\nMeno: {name}\nEmail: {email}\nTelefón: {phone}\nOd: {start_date}\nDo: {end_date}\nPoznámky: {notes or '---'}"""

        subject_user = 'Potvrdenie rezervácie pobytu'
        body_user = f"""\
Milý/á {name},

ďakujeme, že ste si vybrali pobyt u nás – Vaša rezervácia od {start_date} do {end_date} bola úspešne potvrdená. Tešíme na Vašu návštevu!

Dôležité informácie k Vášmu pobytu:

- Príchod (check-in) je možný od 16:00, odchod (check-out) prosíme najneskôr do 11:00.
- V interiéri chatky platí prísny zákaz fajčenia – fajčiť je možné iba vonku na terase.
- Ubytovanie nie je vhodné pre domáce zvieratá.
- Počas letných mesiacov je po dohode k dispozícii súkromný bazén, ktorý sa nachádza pri chatke.
- Využiť môžete bezplatné WiFi pripojenie a parkovanie priamo pri chatke.
- Raňajky neposkytujeme.

**Zrušenie rezervácie je možné najneskôr 24 hodín pred rezervovaným dátumom..**  
V prípade neskoršieho zrušenia alebo nedostavenia sa môže byť účtovaný storno poplatok.

Ak máte akékoľvek otázky alebo špeciálne požiadavky, sme Vám radi k dispozícii – stačí nám napísať alebo zavolať.

Prajeme krásny deň a tešíme sa na Vás!

S pozdravom,
Tím Zem-Com
"""

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
        print(f"❌ Chyba pri odosielaní emailu (pobyt): {e}")

# -------- KALENDÁR --------

def add_to_google_calendar(name, email, date_str, timeslot, package, notes):
    try:
        if os.path.exists("service_account.json"):
            SERVICE_ACCOUNT_FILE = "service_account.json"
        else:
            SERVICE_ACCOUNT_FILE = "/etc/secrets/service_account.json"
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

# -------- KALENDÁR PRE POBYT --------

def add_stay_to_google_calendar(name, email, phone, start_date, end_date, notes):
    try:
        SERVICE_ACCOUNT_FILE = 'service_account.json'
        SCOPES = ['https://www.googleapis.com/auth/calendar']
        CALENDAR_ID = 'zemencikova.gabriela@gmail.com'

        credentials = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        service = build('calendar', 'v3', credentials=credentials)

        start_dt = datetime.strptime(start_date, "%d/%m/%Y")
        end_dt = datetime.strptime(end_date, "%d/%m/%Y")

        event = {
            'summary': f'Rezervácia pobytu - {name}',
            'description': f'Meno: {name}\nEmail: {email}\nTelefón: {phone}\nPoznámky: {notes or "Žiadne"}',
            'start': {'date': start_dt.strftime("%Y-%m-%d")},
            'end': {'date': end_dt.strftime("%Y-%m-%d")},
        }

        created_event = service.events().insert(calendarId=CALENDAR_ID, body=event).execute()
        print(f"✅ Google kalendár (pobyt): {created_event.get('htmlLink')}")
    except Exception as e:
        print(f"❌ Chyba pri vkladaní pobytu do kalendára: {e}")

# -------- ACCOMMODATION --------

@app.route('/booked-stay-dates')
def booked_stay_dates():
    booked = set()
    try:
        with open('stay_bookings.csv', mode='r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                start = datetime.strptime(row['Start Date'], "%d/%m/%Y")
                end = datetime.strptime(row['End Date'], "%d/%m/%Y")
                d = start
                while d < end:  # checkout day is free
                    booked.add(d.strftime("%d/%m/%Y"))
                    d += timedelta(days=1)
    except Exception as e:
        print("Chyba pri čítaní stay_bookings.csv:", e)
    return jsonify({"booked": sorted(booked)})

@app.route('/book-stay', methods=['POST'])
def book_stay():
    data = request.get_json()
    name = data.get('name')
    email = data.get('email')
    phone = data.get('phone')
    start_date = data.get('start')
    end_date = data.get('end')
    notes = data.get('notes', '')

    print("Received data:", data)

    if not name or not email or not phone or not start_date or not end_date:
        return "Všetky polia sú povinné", 400

    try:
        start_dt = datetime.strptime(start_date, "%d/%m/%Y")
        end_dt = datetime.strptime(end_date, "%d/%m/%Y")
        if (end_dt - start_dt).days < 3:
            return "Pobyt musí mať minimálne 3 noci", 400
    except Exception:
        return "Neplatný formát dátumu", 400

    # --- kontrola kolízie s existujúcimi rezerváciami ---
    booked = set()
    try:
        with open('stay_bookings.csv', mode='r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                existing_start = datetime.strptime(row['Start Date'], "%d/%m/%Y")
                existing_end = datetime.strptime(row['End Date'], "%d/%m/%Y")
                d = existing_start
                while d < existing_end:  # posledný deň je voľný
                    booked.add(d.strftime("%d/%m/%Y"))
                    d += timedelta(days=1)
    except FileNotFoundError:
        # Ak súbor ešte neexistuje, to je OK
        pass
    except Exception as e:
        print("Chyba pri kontrole kolízie:", e)

    # Skontroluj, či niektorý z požadovaných dní už nie je obsadený
    d = start_dt
    while d < end_dt:
        if d.strftime("%d/%m/%Y") in booked:
            return "Zvolený termín sa prekrýva s inou rezerváciou.", 400
        d += timedelta(days=1)

    # --- uloženie do CSV ---
    with open('stay_bookings.csv', mode='a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file, quoting=csv.QUOTE_ALL)
        if file.tell() == 0:
            writer.writerow(['Name', 'Email', 'Phone', 'Start Date', 'End Date', 'Notes'])
        writer.writerow([name, email, phone, start_date, end_date, notes])

    # Po úspešnom zápise pošli email
    send_stay_email(name, email, phone, start_date, end_date, notes)

    # Pridaj do Google kalendára
    add_stay_to_google_calendar(name, email, phone, start_date, end_date, notes)

    return jsonify({"message": "Rezervácia bola úspešne uložená!"})


# -------- SPUSTENIE --------

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
