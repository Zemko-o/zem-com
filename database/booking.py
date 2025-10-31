from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# -------- DATABASE MODELS --------
# WELLNESS
class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    date = db.Column(db.String(10), nullable=False)  # Format: "dd/mm/yyyy"
    timeslot = db.Column(db.String(20), nullable=False)
    package = db.Column(db.String(50), nullable=False)
    notes = db.Column(db.Text, nullable=True)
# STAY
class StayBooking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    start_date = db.Column(db.String(10), nullable=False)  # Format: "dd/mm/yyyy"
    end_date = db.Column(db.String(10), nullable=False)    # Format: "dd/mm/yyyy"
    notes = db.Column(db.Text, nullable=True)