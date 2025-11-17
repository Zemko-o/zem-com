from database import booking as booking_db
from app import app

# Testovacie údaje pre wellness rezervácie
wellness_test_data = [
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
        "date": "20/11/2025",
        "timeslot": "17:00-19:00",
        "package": "Exkluzív",
        "notes": "Bez špeciálnych požiadaviek."
    },
    {
        "name": "Nikolette",
        "email": "nikolette@example.com",
        "phone": "456123789",
        "date": "18/11/2025",
        "timeslot": "14:30-16:30",
        "package": "Romantika",
        "notes": "Pripravte šampanské."
    }
]

# Testovacie údaje pre pobyty (stay bookings)
stay_test_data = [
    {
        "name": "Peter",
        "email": "peter@example.com",
        "phone": "123123123",
        "start_date": "05/11/2025",
        "end_date": "10/11/2025",
        "notes": "Chceme izbu s výhľadom na hory."
    },
    {
        "name": "Anna",
        "email": "anna@example.com",
        "phone": "321321321",
        "start_date": "12/11/2025",
        "end_date": "15/11/2025",
        "notes": "Prosím o detskú postieľku."
    }
]

# Pridanie údajov do databázy
with app.app_context():
    # NOTE: With Supabase you must create the tables in your Supabase project
    # beforehand (bookings, stay_bookings). This script will insert test rows.

    # Pridanie wellness rezervácií
    for data in wellness_test_data:
        booking_payload = {
            "name": data["name"],
            "email": data["email"],
            "phone": data["phone"],
            "date": data["date"],
            "timeslot": data["timeslot"],
            "package": data["package"],
            "notes": data["notes"],
        }
        booking_db.create_booking(booking_payload)

    # Pridanie pobytov (stay bookings)
    for data in stay_test_data:
        stay_payload = {
            "name": data["name"],
            "email": data["email"],
            "phone": data["phone"],
            "start_date": data["start_date"],
            "end_date": data["end_date"],
            "notes": data["notes"],
        }
        booking_db.create_stay(stay_payload)

    print("✅ Testovacie údaje pre wellness a pobyty boli úspešne pridané do Supabase!")

# Overenie pridaných údajov
with app.app_context():
    print("\nWellness rezervácie:")
    bookings = booking_db.get_all_bookings()
    for booking in bookings:
        print(f"{booking.get('name')} - {booking.get('date')} - {booking.get('timeslot')}")

    print("\nPobyty (Stay bookings):")
    stays = booking_db.get_all_stays()
    for stay in stays:
        print(f"{stay.get('name')} - {stay.get('start_date')} to {stay.get('end_date')}")