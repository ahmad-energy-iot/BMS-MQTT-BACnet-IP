import json
from datetime import datetime
from getpass import getpass
from pathlib import Path
from contextlib import closing
import math
import sqlite3
import time

import paho.mqtt.client as mqtt


DB_PATH = Path(__file__).resolve().parent / "bms.db"

SAVE_INTERVAL_SECONDS = 60
CLEANUP_INTERVAL_SECONDS = 60

last_saved = {}
last_cleanup = None

TOPICS = {
    "bms/room1/temperature": "°C",
    "bms/room1/humidity": "%",
}


def cleanup_old_readings():
    with closing(sqlite3.connect(DB_PATH)) as connection:
        with connection:
            cursor = connection.execute("""
                DELETE FROM readings
                WHERE julianday(received_at)
                    < julianday('now', '-3 days')
            """)

            deleted = cursor.rowcount

    if deleted:
        print(f"Alte Messungen gelöscht: {deleted}", flush=True)


def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code.is_failure:
        print(f"Verbindung abgelehnt: {reason_code}", flush=True)
        client.disconnect()
        return

    print("MQTT verbunden", flush=True)

    for topic in TOPICS:
        client.subscribe(topic)


def on_message(client, userdata, message):
    global last_cleanup

    now = time.monotonic()

    if (
        last_cleanup is None
        or now - last_cleanup >= CLEANUP_INTERVAL_SECONDS
    ):
        cleanup_old_readings()
        last_cleanup = now

    if message.topic not in TOPICS or message.retain:
        return

    try:
        value = float(message.payload.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        print("Ungültige Messung ignoriert.", flush=True)
        return

    if not math.isfinite(value):
        print("Ungültige Messung ignoriert.", flush=True)
        return

    previous_save = last_saved.get(message.topic)

    if (
        previous_save is not None
        and now - previous_save < SAVE_INTERVAL_SECONDS
    ):
        return

    received_at = datetime.now().astimezone().isoformat(
        timespec="seconds"
    )
    metric = message.topic.rsplit("/", 1)[1]
    unit = TOPICS[message.topic]

    with closing(sqlite3.connect(DB_PATH)) as connection:
        with connection:
            connection.execute(
                """
                INSERT INTO readings
                    (received_at, room, metric, value, unit)
                VALUES (?, ?, ?, ?, ?)
                """,
                (received_at, "room1", metric, value, unit),
            )

    last_saved[message.topic] = now

    print(
        f"Gespeichert | {received_at} | room1 | "
        f"{metric} | {value} {unit}",
        flush=True,
    )


config_path = Path.home() / ".config" / "bms-logger" / "mqtt.json"
with config_path.open(encoding="utf-8") as config_file:
    credentials = json.load(config_file)
username = credentials["username"]
password = credentials["password"]

client = mqtt.Client(
    callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
    client_id="bms-python-logger",
)
client.username_pw_set(username, password)
client.on_connect = on_connect
client.on_message = on_message

try:
    cleanup_old_readings()
    last_cleanup = time.monotonic()

    client.connect("127.0.0.1", 1883, 60)
    client.loop_forever()

except KeyboardInterrupt:
    print("\nProgramm beendet.")

except (OSError, sqlite3.Error) as error:
    print(f"Fehler: {error}")

finally:
    client.disconnect()
