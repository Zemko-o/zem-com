"""
Supabase-backed database helpers for bookings.

This module replaces the previous SQLAlchemy models with a small set of
functions used by the Flask app. It expects two Supabase tables to exist:

- bookings
  - id (uuid or int)
  - name (text)
  - email (text)
  - phone (text)
  - date (text)  # dd/mm/YYYY
  - timeslot (text)
  - package (text)
  - notes (text)

- stay_bookings
  - id
  - name
  - email
  - phone
  - start_date (text)  # dd/mm/YYYY
  - end_date (text)    # dd/mm/YYYY
  - notes (text)

Set SUPABASE_URL and SUPABASE_KEY in env before running.
"""

from typing import List, Dict, Optional
from .supabase_client import get_supabase


def _table(name: str):
    return get_supabase().table(name)


def get_bookings_by_date(date_str: str) -> List[Dict]:
    """Return list of bookings for a given date (formatted dd/mm/YYYY)."""
    res = _table("bookings").select("*").eq("date", date_str).execute()
    return res.data or []


def get_all_bookings() -> List[Dict]:
    res = _table("bookings").select("*").execute()
    return res.data or []


def find_booking_by_date_and_timeslot(date_str: str, timeslot: str) -> Optional[Dict]:
    res = (
        _table("bookings")
        .select("*")
        .eq("date", date_str)
        .eq("timeslot", timeslot)
        .limit(1)
        .execute()
    )
    data = res.data or []
    return data[0] if data else None


def create_booking(payload: Dict) -> Dict:
    """Insert a booking record. Payload should match bookings table columns."""
    res = _table("bookings").insert(payload).execute()
    data = res.data or []
    return data[0] if data else {}


# --- Stay bookings ---
def get_all_stays() -> List[Dict]:
    res = _table("stay_bookings").select("*").execute()
    return res.data or []


def create_stay(payload: Dict) -> Dict:
    res = _table("stay_bookings").insert(payload).execute()
    data = res.data or []
    return data[0] if data else {}


def find_all_stays():
    """Alias for get_all_stays kept for readability in app code."""
    return get_all_stays()