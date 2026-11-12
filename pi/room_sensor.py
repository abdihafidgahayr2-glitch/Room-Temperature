"""Runs on the Raspberry Pi.

- Reads the DHT22 every INTERVAL seconds and publishes to <room>/readings
- Listens on <room>/window/cmd and moves the servo (the "window")
- Reports what the window did on <room>/window/state

Run with real hardware:   python room_sensor.py
Run without hardware:     python room_sensor.py --simulate
"""
import argparse
import json
import os
import random
import ssl
import time

import paho.mqtt.client as mqtt
from dotenv import load_dotenv

load_dotenv()

HOST = os.environ["MQTT_HOST"]
PORT = int(os.getenv("MQTT_PORT", "8883"))
USERNAME = os.getenv("MQTT_USERNAME", "")
PASSWORD = os.getenv("MQTT_PASSWORD", "")
USE_TLS = os.getenv("MQTT_TLS", "true").lower() in ("1", "true", "yes")
ROOM = os.getenv("MQTT_ROOM", "room1")
INTERVAL = int(os.getenv("INTERVAL", "30"))

TOPIC_READINGS = f"{ROOM}/readings"
TOPIC_CMD = f"{ROOM}/window/cmd"
TOPIC_STATE = f"{ROOM}/window/state"

DHT_PIN = 4     # GPIO4 (physical pin 7) -> DHT22 data
SERVO_PIN = 18  # GPIO18 (physical pin 12) -> servo signal (PWM)

parser = argparse.ArgumentParser()
parser.add_argument("--simulate", action="store_true", help="fake sensor + servo, no hardware needed")
args = parser.parse_args()


# ---------- Hardware (or fake hardware) ----------

if args.simulate:
    class Sensor:
        def __init__(self):
            self.temp = 22.0

        def read(self):
            self.temp += random.uniform(-0.3, 0.6) if window["state"] == "closed" else random.uniform(-0.8, 0.1)
            return round(self.temp, 1), round(random.uniform(40, 55), 1)

    class Window:
        def open(self):  print("[sim] servo -> OPEN")
        def close(self): print("[sim] servo -> CLOSED")
else:
    import adafruit_dht
    import board
    from gpiozero import AngularServo

    class Sensor:
        def __init__(self):
            self.dht = adafruit_dht.DHT22(getattr(board, f"D{DHT_PIN}"))

        def read(self):
            # DHT22 often fails a single read; retry a few times
            for _ in range(5):
                try:
                    t, h = self.dht.temperature, self.dht.humidity
                    if t is not None and h is not None:
                        return round(t, 1), round(h, 1)
                except RuntimeError:
                    pass
                time.sleep(2)
            return None

    class Window:
        def __init__(self):
            self.servo = AngularServo(SERVO_PIN, min_angle=0, max_angle=180,
                                      min_pulse_width=0.0005, max_pulse_width=0.0025)
            self.close()

        def open(self):  self.servo.angle = 90
        def close(self): self.servo.angle = 0

sensor = Sensor()
win = Window()
window = {"state": "closed"}


# ---------- MQTT ----------

def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code.is_failure:
        print("Connect failed:", reason_code)
        return
    print("Connected to broker")
    client.subscribe(TOPIC_CMD, qos=1)
    report_state(client, "startup")


def report_state(client, reason):
    client.publish(TOPIC_STATE, json.dumps({"state": window["state"], "reason": reason}), qos=1, retain=True)


def on_message(client, userdata, msg):
    try:
        cmd = json.loads(msg.payload)
    except ValueError:
        return
    action, reason = cmd.get("window"), cmd.get("reason", "auto")
    if action == "open":
        win.open(); window["state"] = "open"
    elif action == "close":
        win.close(); window["state"] = "closed"
    else:
        return
    print(f"Window {window['state']} ({reason})")
    report_state(client, reason)


client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"pi-{ROOM}")
if USERNAME:
    client.username_pw_set(USERNAME, PASSWORD)
if USE_TLS:  # always true on the real EC2 setup; false only for local testing at home
    client.tls_set(cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLS_CLIENT)  # encrypted in transit
client.on_connect = on_connect
client.on_message = on_message
client.connect(HOST, PORT, keepalive=60)
client.loop_start()

try:
    while True:
        result = sensor.read()
        if result:
            temp, hum = result
            client.publish(TOPIC_READINGS, json.dumps({"temperature": temp, "humidity": hum}), qos=1)
            print(f"Published {temp} °C, {hum} %")
        else:
            print("Sensor read failed")
        time.sleep(INTERVAL)
except KeyboardInterrupt:
    pass
finally:
    client.loop_stop()
    client.disconnect()
