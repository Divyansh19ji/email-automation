import sqlite3
import csv
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any
from config import DATA_DIR

DB_PATH = DATA_DIR / "outreach.db"

class Tracker:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS leads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company TEXT NOT NULL,
                    contact_name TEXT,
                    email TEXT NOT NULL,
                    role TEXT,
                    website TEXT,
                    notes TEXT,
                    subject TEXT,
                    body TEXT,
                    status TEXT DEFAULT 'PENDING',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    sent_at TIMESTAMP,
                    error_message TEXT,
                    UNIQUE(email)
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS send_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    lead_id INTEGER,
                    email TEXT NOT NULL,
                    status TEXT NOT NULL,
                    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    error_message TEXT,
                    FOREIGN KEY (lead_id) REFERENCES leads (id)
                )
            """)
            conn.commit()

    def add_lead(self, company: str, email: str, contact_name: str = "", 
                 role: str = "Software Engineer Intern", website: str = "", 
                 notes: str = "") -> Dict[str, Any]:
        email = email.strip().lower()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO leads (company, contact_name, email, role, website, notes, status)
                VALUES (?, ?, ?, ?, ?, ?, 'PENDING')
                ON CONFLICT(email) DO UPDATE SET
                    company = excluded.company,
                    contact_name = excluded.contact_name,
                    role = excluded.role,
                    website = excluded.website,
                    notes = excluded.notes
            """, (company.strip(), contact_name.strip(), email, role.strip(), website.strip(), notes.strip()))
            conn.commit()
            lead_id = cursor.lastrowid
            return self.get_lead(lead_id)

    def import_from_csv(self, csv_path: str) -> Dict[str, int]:
        path = Path(csv_path)
        if not path.exists():
            raise FileNotFoundError(f"CSV file not found: {csv_path}")

        with open(path, "r", encoding="utf-8-sig") as f:
            return self.import_from_csv_text(f.read())

    def import_from_csv_text(self, csv_text: str) -> Dict[str, int]:
        import io
        imported = 0
        skipped = 0
        reader = csv.DictReader(io.StringIO(csv_text))
        for row in reader:
            norm_row = {k.strip().lower(): v.strip() for k, v in row.items() if k and v}
            company = norm_row.get("company", "") or norm_row.get("company_name", "")
            email = norm_row.get("email", "") or norm_row.get("contact_email", "")
            if not company or not email or "@" not in email:
                skipped += 1
                continue

            contact_name = norm_row.get("contact_name", "") or norm_row.get("name", "") or norm_row.get("founder", "")
            role = norm_row.get("role", "") or norm_row.get("position", "") or "Software Engineer Intern"
            website = norm_row.get("website", "") or norm_row.get("url", "")
            notes = norm_row.get("notes", "") or norm_row.get("description", "") or norm_row.get("tech_stack", "")

            try:
                self.add_lead(
                    company=company,
                    email=email,
                    contact_name=contact_name,
                    role=role,
                    website=website,
                    notes=notes
                )
                imported += 1
            except Exception:
                skipped += 1
        return {"imported": imported, "skipped": skipped}

    def get_lead(self, lead_id: int) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM leads WHERE id = ?", (lead_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_all_leads(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if status:
                cursor.execute("SELECT * FROM leads WHERE status = ? ORDER BY id DESC", (status.upper(),))
            else:
                cursor.execute("SELECT * FROM leads ORDER BY id DESC")
            return [dict(row) for row in cursor.fetchall()]

    def update_draft(self, lead_id: int, subject: str, body: str) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE leads
                SET subject = ?, body = ?, status = 'DRAFTED'
                WHERE id = ?
            """, (subject.strip(), body.strip(), lead_id))
            conn.commit()
            return cursor.rowcount > 0

    def mark_lead_sent(self, lead_id: int, status: str = "SENT", error_message: Optional[str] = None):
        now = datetime.now().isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE leads
                SET status = ?, sent_at = ?, error_message = ?
                WHERE id = ?
            """, (status, now if status == "SENT" else None, error_message, lead_id))
            
            cursor.execute("SELECT email FROM leads WHERE id = ?", (lead_id,))
            row = cursor.fetchone()
            email = row["email"] if row else "unknown"

            cursor.execute("""
                INSERT INTO send_logs (lead_id, email, status, error_message)
                VALUES (?, ?, ?, ?)
            """, (lead_id, email, status, error_message))
            conn.commit()

    def check_already_sent(self, email: str) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM leads WHERE lower(email) = ? AND status = 'SENT'", (email.strip().lower(),))
            return cursor.fetchone() is not None

    def delete_lead(self, lead_id: int) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM leads WHERE id = ?", (lead_id,))
            conn.commit()
            return cursor.rowcount > 0

    def get_stats(self) -> Dict[str, Any]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM leads")
            total = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM leads WHERE status = 'PENDING'")
            pending = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM leads WHERE status = 'DRAFTED'")
            drafted = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM leads WHERE status = 'SENT'")
            sent = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM leads WHERE status = 'FAILED'")
            failed = cursor.fetchone()[0]

            today_date = datetime.now().strftime("%Y-%m-%d")
            cursor.execute("SELECT COUNT(*) FROM send_logs WHERE status = 'SENT' AND date(sent_at) = date('now')")
            sent_today = cursor.fetchone()[0]

            return {
                "total_leads": total,
                "pending": pending,
                "drafted": drafted,
                "sent": sent,
                "failed": failed,
                "sent_today": sent_today
            }

    def export_csv(self, export_path: str):
        leads = self.get_all_leads()
        if not leads:
            return
        fieldnames = list(leads[0].keys())
        with open(export_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(leads)
