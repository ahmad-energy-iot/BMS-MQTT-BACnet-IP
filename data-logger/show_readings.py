import sqlite3
from pathlib import Path
from contextlib import closing

db_path = Path(__file__).resolve().parent / "bms.db"

with closing(sqlite3.connect(db_path.as_uri() + "?mode=ro", uri=True)) as connection:
    cursor = connection.execute("""
        SELECT received_at, room, metric, value, unit
        FROM readings
        ORDER BY id ASC
    """)

    print("Time | Room | Metric | Value | Unit")
    count = 0
    for row in cursor:
        print(*row, sep=" | ")
        count += 1

    print("Total readings:", count)
