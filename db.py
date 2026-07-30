import sqlite3
from datetime import datetime

DB_PATH = "applications.db"

def get_connection():
    return sqlite3.connect(DB_PATH)

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company TEXT,
            role TEXT,
            job_link TEXT,
            jd_text TEXT,
            resume_filename TEXT,
            resume_text TEXT,
            date_applied TEXT,
            status TEXT DEFAULT 'applied',
            notes TEXT
        )
    """)
    conn.commit()
    conn.close()

# ---------------- CREATE ----------------
def add_application(company, role, job_link, jd_text, resume_filename, resume_text, notes=""):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO applications 
        (company, role, job_link, jd_text, resume_filename, resume_text, date_applied, status, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        company, role, job_link, jd_text, resume_filename, resume_text,
        datetime.now().strftime("%Y-%m-%d"), "applied", notes
    ))
    conn.commit()
    app_id = cursor.lastrowid
    conn.close()
    return app_id

# ---------------- READ ----------------
def get_all_applications():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, company, role, job_link, resume_filename, date_applied, status 
        FROM applications ORDER BY date_applied DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_application_by_id(app_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM applications WHERE id = ?", (app_id,))
    row = cursor.fetchone()
    conn.close()
    return row

# ---------------- UPDATE ----------------
def update_application(app_id, **fields):
    """
    Update any subset of fields for an application.
    Usage: update_application(3, status="interview", notes="Called back for round 2")
    """
    if not fields:
        return False

    allowed = {"company", "role", "job_link", "jd_text", "resume_filename", "resume_text", "status", "notes"}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return False

    set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
    values = list(updates.values()) + [app_id]

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(f"UPDATE applications SET {set_clause} WHERE id = ?", values)
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0

def update_status(app_id, new_status):
    return update_application(app_id, status=new_status)

# ---------------- DELETE ----------------
def delete_application(app_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM applications WHERE id = ?", (app_id,))
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0

if __name__ == "__main__":
    init_db()
    print("✅ Database initialized: applications.db")