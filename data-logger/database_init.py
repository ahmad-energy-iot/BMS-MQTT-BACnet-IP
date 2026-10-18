import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "bms.db"

with sqlite3.connect(DB_PATH) as connection:
    connection.execute("""
        CREATE TABLE IF NOT EXISTS readings (
            id INTEGER PRIMARY KEY,
            received_at TEXT NOT NULL,
            room TEXT NOT NULL,
            metric TEXT NOT NULL,
            value REAL NOT NULL,
            unit TEXT NOT NULL
        )
    """)

print(f"Datenbank bereit: {DB_PATH}")
print("Tabelle 'readings' bereit.")
