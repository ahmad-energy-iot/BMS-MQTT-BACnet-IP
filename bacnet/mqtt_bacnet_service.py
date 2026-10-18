import json
from pathlib import Path
import asyncio
import math
from getpass import getpass

import paho.mqtt.client as mqtt

from bacpypes3.app import Application
from bacpypes3.argparse import SimpleArgumentParser
from bacpypes3.local.analog import AnalogValueObject


DATA_TIMEOUT_SECONDS = 15

POINTS = {
    "bms/room1/temperature": {
        "instance": 1,
        "name": "Room1_Temperature",
        "units": "degreesCelsius",
        "display_unit": "°C",
    },
    "bms/room1/humidity": {
        "instance": 2,
        "name": "Room1_Humidity",
        "units": "percentRelativeHumidity",
        "display_unit": "%",
    },
}


async def main():
    args = SimpleArgumentParser().parse_args()

    config_path = Path.home() / ".config" / "bms-logger" / "mqtt.json"
    config = json.loads(config_path.read_text())
    username = config["username"]
    password = config["password"]

    loop = asyncio.get_running_loop()
    app = Application.from_args(args)
    objects = {}
    last_received = {}

    def mark_unavailable(topic):
        point = objects[topic]
        point.outOfService = True
        point.statusFlags = [0, 0, 0, 1]

    def update_point(topic, value):
        point = objects[topic]
        point.presentValue = value
        point.outOfService = False
        point.statusFlags = [0, 0, 0, 0]
        last_received[topic] = loop.time()

        config = POINTS[topic]
        print(
            f"MQTT -> BACnet | {config['name']} | "
            f"{value} {config['display_unit']}",
            flush=True,
        )

    def on_connect(client, userdata, flags, reason_code, properties):
        if reason_code.is_failure:
            print(f"MQTT abgelehnt: {reason_code}", flush=True)
            return

        for topic in POINTS:
            client.subscribe(topic)

        print("MQTT verbunden", flush=True)

    def on_disconnect(client, userdata, flags, reason_code, properties):
        for topic in POINTS:
            loop.call_soon_threadsafe(mark_unavailable, topic)

        print("MQTT getrennt", flush=True)

    def on_message(client, userdata, message):
        if message.topic not in POINTS or message.retain:
            return

        try:
            value = float(message.payload.decode("utf-8"))
        except (UnicodeDecodeError, ValueError):
            return

        if not math.isfinite(value):
            return

        if message.topic == "bms/room1/humidity":
            if not 0 <= value <= 100:
                return

        loop.call_soon_threadsafe(
            update_point, message.topic, value
        )

    client = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id="bms-mqtt-bacnet-bridge",
    )
    client.username_pw_set(username, password)
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message

    try:
        for topic, config in POINTS.items():
            point = AnalogValueObject(
                objectIdentifier=("analog-value", config["instance"]),
                objectName=config["name"],
                presentValue=0.0,
                units=config["units"],
                statusFlags=[0, 0, 0, 1],
                outOfService=True,
            )
            app.add_object(point)
            objects[topic] = point

        client.connect("127.0.0.1", 1883, 60)
        client.loop_start()

        print("BACnet bridge running; waiting for MQTT data", flush=True)

        while True:
            await asyncio.sleep(1)

            for topic, received_at in list(last_received.items()):
                if loop.time() - received_at >= DATA_TIMEOUT_SECONDS:
                    mark_unavailable(topic)

    finally:
        client.disconnect()
        client.loop_stop()
        app.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBridge stopped.")
