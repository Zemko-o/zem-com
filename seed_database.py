from database.booking import db, Booking
from app import app

# Testovacie údaje
test_data = [
    {
        "name": "Janko",
        "email": "janko@example.com",
        "phone": "123456789",
        "date": "01/11/2025",
        "timeslot": "14:30-16:30",
        "package": "Klasik",
        "notes": "Prosím o romantickú výzdobu."
    },
    {
        "name": "Marika",
        "email": "marika@example.com",
        "phone": "987654321",
        "date": "01/11/2025",
        "timeslot": "17:00-19:00",
        "package": "Exkluzív",
        "notes": "Bez špeciálnych požiadaviek."
    },
    {
        "name": "Nikolette",
        "email": "nikolette@example.com",
        "phone": "456123789",
        "date": "02/11/2025",
        "timeslot": "14:30-16:30",
        "package": "Romantika",
        "notes": "Pripravte šampanské."
    }
]

# Pridanie údajov do databázy
with app.app_context():
    db.create_all()  # Vytvorí tabuľky, ak ešte neexistujú
    for data in test_data:
        booking = Booking(
            name=data["name"],
            email=data["email"],
            phone=data["phone"],
            date=data["date"],
            timeslot=data["timeslot"],
            package=data["package"],
            notes=data["notes"]
        )
        db.session.add(booking)
    db.session.commit()
    print("✅ Testovacie údaje boli úspešne pridané do databázy!")

# Overenie pridaných údajov
with app.app_context():
    bookings = Booking.query.all()
    for booking in bookings:
        print(f"{booking.name} - {booking.date} - {booking.timeslot}")