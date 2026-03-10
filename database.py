import sqlite3
from datetime import datetime, date
from contextlib import contextmanager

DB_PATH = "barbershop.db"


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS appointments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                username TEXT,
                full_name TEXT,
                phone TEXT,
                master_id INTEGER NOT NULL,
                master_name TEXT NOT NULL,
                service_id INTEGER NOT NULL,
                service_name TEXT NOT NULL,
                service_price INTEGER NOT NULL,
                appointment_date TEXT NOT NULL,
                appointment_time TEXT NOT NULL,
                status TEXT DEFAULT 'active',
                created_at TEXT DEFAULT (datetime('now'))
            );
        """)


def get_booked_slots(master_id: int, appointment_date: str) -> list[str]:
    """Возвращает список занятых слотов для мастера на дату."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT appointment_time FROM appointments WHERE master_id=? AND appointment_date=? AND status='active'",
            (master_id, appointment_date)
        ).fetchall()
    return [row["appointment_time"] for row in rows]


def create_appointment(
    user_id: int,
    username: str,
    full_name: str,
    phone: str,
    master_id: int,
    master_name: str,
    service_id: int,
    service_name: str,
    service_price: int,
    appointment_date: str,
    appointment_time: str,
) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO appointments
               (user_id, username, full_name, phone, master_id, master_name,
                service_id, service_name, service_price, appointment_date, appointment_time)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (user_id, username, full_name, phone, master_id, master_name,
             service_id, service_name, service_price, appointment_date, appointment_time)
        )
        return cur.lastrowid


def get_user_appointments(user_id: int) -> list:
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT * FROM appointments
               WHERE user_id=? AND status='active'
               ORDER BY appointment_date, appointment_time""",
            (user_id,)
        ).fetchall()
    return [dict(r) for r in rows]


def cancel_appointment(appointment_id: int, user_id: int) -> bool:
    with get_conn() as conn:
        cur = conn.execute(
            "UPDATE appointments SET status='cancelled' WHERE id=? AND user_id=? AND status='active'",
            (appointment_id, user_id)
        )
        return cur.rowcount > 0


def get_all_appointments_for_date(appointment_date: str) -> list:
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT * FROM appointments WHERE appointment_date=? AND status='active'
               ORDER BY master_id, appointment_time""",
            (appointment_date,)
        ).fetchall()
    return [dict(r) for r in rows]


def get_appointment_by_id(appointment_id: int) -> dict | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM appointments WHERE id=?", (appointment_id,)).fetchone()
    return dict(row) if row else None
