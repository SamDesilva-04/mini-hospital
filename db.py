import sqlite3, pathlib

DB = pathlib.Path(__file__).parent / "hospital.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS patients(
  patient_id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, age INTEGER,
  gender TEXT, phone TEXT, complaint TEXT);
CREATE TABLE IF NOT EXISTS appointments(
  appt_id INTEGER PRIMARY KEY AUTOINCREMENT, patient_id INTEGER, doctor TEXT,
  slot TEXT, reason TEXT);
CREATE TABLE IF NOT EXISTS diagnoses(
  diag_id INTEGER PRIMARY KEY AUTOINCREMENT, patient_id INTEGER,
  diagnosis TEXT, notes TEXT);
CREATE TABLE IF NOT EXISTS scan_orders(
  order_id INTEGER PRIMARY KEY AUTOINCREMENT, patient_id INTEGER,
  scan_type TEXT, status TEXT DEFAULT 'pending', findings TEXT);
CREATE TABLE IF NOT EXISTS prescriptions(
  rx_id INTEGER PRIMARY KEY AUTOINCREMENT, patient_id INTEGER,
  medication TEXT, dosage TEXT, instructions TEXT);
"""

def _conn():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c

def write(sql, params=()):
    with _conn() as c:
        return c.execute(sql, params).lastrowid

def read(sql, params=()):
    with _conn() as c:
        return [dict(r) for r in c.execute(sql, params).fetchall()]

def init():
    with _conn() as c:
        c.executescript(SCHEMA)
    if not read("SELECT 1 FROM patients LIMIT 1"):  # synthetic seed data
        write("INSERT INTO patients(name,age,gender,phone,complaint) VALUES(?,?,?,?,?)",
              ("Asha Rao", 34, "F", "555-0101", "Persistent cough and fever for 5 days"))
        write("INSERT INTO patients(name,age,gender,phone,complaint) VALUES(?,?,?,?,?)",
              ("Ravi Kumar", 52, "M", "555-0102", "Chest tightness on climbing stairs"))
    seed_diet()

def seed_diet():
    import diet_kb
    diet_kb.seed()


def patient_exists(pid):
    return bool(read("SELECT 1 FROM patients WHERE patient_id=?", (pid,)))
