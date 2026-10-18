import csv
import sqlite3
from pathlib import Path
from datetime import datetime
from contextlib import closing

project = Path(__file__).resolve().parent
exports = project / "exports"
exports.mkdir(exist_ok=True)
output = exports / datetime.now().strftime("readings-%Y%m%d-%H%M%S-%f.csv")

with closing(sqlite3.connect(
    (project / "bms.db").as_uri() + "?mode=ro", uri=True
)) as db:
    cursor = db.execute(
        "SELECT id, received_at, room, metric, value, unit "
        "FROM readings ORDER BY id"
    )
    with output.open("x", encoding="utf-8-sig", newline="") as file:
        writer = csv.writer(file, delimiter=";")
        writer.writerow([column[0] for column in cursor.description])
        count = 0
        for row in cursor:
            writer.writerow(row)
            count += 1

print("CSV:", output)
print("Exported readings:", count)
