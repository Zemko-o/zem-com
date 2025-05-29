from flask import Flask, request, jsonify, render_template
import csv
import os
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def is_overlapping(new_start, new_end, existing_start, existing_end):
    return new_start < existing_end and new_end > existing_start

app = Flask(__name__)
CSV_FILE = 'bookings.csv'

# Ensure CSV file has headers if it doesn't exist
if not os.path.exists(CSV_FILE):
    with open(CSV_FILE, mode='w', newline='') as file:
        writer = csv.writer(file, quoting=csv.QUOTE_ALL)
        writer.writerow(['Name', 'Email', 'Phone', 'Date', 'Timeslot', 'Package', 'Notes'])


@app.route('/booked-timeslots')
def booked_timeslots():
    date = request.args.get('date')
    if not date:
        return jsonify([])

    try:
        # Previesť ISO dátum (YYYY-MM-DD) na d/m/Y
        parsed_date = datetime.strptime(date, "%Y-%m-%d").strftime("%d/%m/%Y")
    except ValueError:
        return jsonify([])

    booked_slots = set()
    try:
        with open(CSV_FILE, mode='r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                if row.get('Name', '').lower() == 'name':
                    continue
                if row.get('Date') == parsed_date:
                    booked_slots.add(row.get('Timeslot', ''))
    except Exception as e:
        print(f"Chyba pri čítaní CSV: {e}")
        return jsonify([])

    return jsonify(list(booked_slots))



@app.route('/booked-dates')
def booked_dates():
    fully_booked = {}
    with open(CSV_FILE, mode='r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            # Skip header rows
            if row.get('Name', '').lower() == 'name':
                continue
            if 'Date' in row:
                date = row['Date']
                btn = row.get('Timeslot', '') or row.get('Time', '')
                if date not in fully_booked:
                    fully_booked[date] = []
                if btn:
                    fully_booked[date].append(btn)
            elif 'Check-in' in row and 'Check-out' in row:
                start = datetime.strptime(row['Check-in'], "%Y-%m-%d")
                end = datetime.strptime(row['Check-out'], "%Y-%m-%d")
                current = start
                while current < end:
                    if current.strftime("%Y-%m-%d") not in fully_booked:
                        fully_booked[current.strftime("%Y-%m-%d")] = []
                    current += timedelta(days=1)
    # A date is fully disabled if all 3 buttons are booked (regardless of package)
    disabled_dates = [d for d, btns in fully_booked.items() if len(set(btns)) >= 3]
    return jsonify({
        'disabledDates': sorted(disabled_dates),
        'fullyBooked': fully_booked
    })

# 👇 This serves your HTML file at the root URL
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


# 👇 This handles form submission and writes to CSV
@app.route('/book', methods=['POST'])
def book():
    data = request.get_json()
    name = data.get('name')
    email = data.get('email')
    phone = data.get('phone')
    date_str = data.get('date')
    package = data.get('package', '')
    timeslot = data.get('timeslot', '')
    notes = data.get('notes', '')

    # Validate
    if not name or not email or not date_str or not package or not timeslot:
        return "All fields are required", 400
    try:
        booking_date = datetime.strptime(date_str, "%d/%m/%Y")
    except Exception:
        return "Invalid date format", 400

    # Check for collision (aj timeslot!)
    with open(CSV_FILE, mode='r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            if row.get('Name', '').lower() == 'name':
                continue
            if ('Date' in row and 'Timeslot' in row and
                row['Date'] == date_str and row['Timeslot'] == timeslot):
                return f"Rezervácia koliduje s už zarezervovaným termínom {date_str} a časom {timeslot}.", 409

    # Write booking
    file_exists = os.path.exists(CSV_FILE)
    with open(CSV_FILE, mode='a', newline='') as file:
        writer = csv.writer(file, quoting=csv.QUOTE_ALL)
        # Write header if needed
        if os.stat(CSV_FILE).st_size == 0 or (file_exists and len(open(CSV_FILE).readline().split(',')) < 7):
            file.seek(0)
            writer.writerow(['Name', 'Email', 'Phone', 'Date', 'Timeslot', 'Package', 'Notes'])
        writer.writerow([name, email, phone, date_str, timeslot, package, notes])

    # Send email notification (fill in your details below)
    email_error = None
    
    try:
        smtp_server = 'smtp.gmail.com'
        smtp_port = 587
        smtp_user = 'filipzemencik@gmail.com'  # <-- your email
        smtp_password = 'jvuk amlc dcrk uzrz'  # <-- your app password or real password
        to_email = 'zemencikova.gabriela@gmail.com'  # <-- your email (admin)
        user_email = email  # the user's email from the booking form

        subject_admin = 'New Booking Received'
        body_admin = f"""
        New booking received:\n\n
        Name: {name}
        Email: {email}
        Date: {date_str}
        Package: {package}
        Timeslot: {timeslot}
        Notes: {notes if notes else '---'}
        """
        msg_admin = MIMEMultipart()
        msg_admin['From'] = smtp_user
        msg_admin['To'] = to_email
        msg_admin['Subject'] = subject_admin
        msg_admin.attach(MIMEText(body_admin, 'plain'))

        subject_user = 'Potvrdenie vašej rezervácie / Booking Confirmation'
        body_user = f"""
        Ďakujeme za vašu rezerváciu pán/i {name}!\n\n
        Budeme vás čakať v {date_str} o {timeslot}
        Váš balíček je: {package} 
        \n\nTešíme sa na vás! Zem-Zen\n"""
        msg_user = MIMEMultipart()
        msg_user['From'] = smtp_user
        msg_user['To'] = user_email
        msg_user['Subject'] = subject_user
        msg_user.attach(MIMEText(body_user, 'plain'))

        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.sendmail(smtp_user, to_email, msg_admin.as_string())
        server.sendmail(smtp_user, user_email, msg_user.as_string())
        server.quit()
    except Exception as e:
        print('Failed to send email:', e)
        email_error = str(e)

    if email_error:
        return f"Booking saved, but email failed to send: {email_error}", 200
    return "Booking saved successfully!"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
