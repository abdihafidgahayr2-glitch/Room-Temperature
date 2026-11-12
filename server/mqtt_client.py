"""MQTT side of the server.

Subscribes to:  room1/readings       (Pi -> server)  save reading, decide on window
                room1/window/state   (Pi -> server)  record what the window actually did
Publishes to:   room1/window/cmd     (server -> Pi)  {"window": "open"|"close", "reason": ...}
"""
import json
import logging
import ssl

import paho.mqtt.client as mqtt
from sqlalchemy import select

import config
import models
from database import SessionLocal

log = logging.getLogger("mqtt")

client: mqtt.Client | None = None


def get_thresholds(db) -> tuple[float, float]:
    result = db.execute(select(models.Setting).where(models.Setting.id == 1))
    setting = result.scalars().first()
    if setting:
        return setting.open_at, setting.close_at
    return config.DEFAULT_OPEN_AT, config.DEFAULT_CLOSE_AT


def get_window_state(db) -> str:
    result = db.execute(select(models.WindowEvent).order_by(models.WindowEvent.date_timestamp.desc()))
    last_event = result.scalars().first()
    if last_event:
        return last_event.state
    return "closed"


def send_window_command(action: str, reason: str) -> bool:
    if client is None or not client.is_connected():
        log.warning("Not connected to broker, cannot send %s", action)
        return False
    payload = json.dumps({"window": action, "reason": reason})
    client.publish(config.TOPIC_WINDOW_CMD, payload, qos=1)
    log.info("Sent window command: %s", payload)
    return True


def handle_reading(data: dict):
    temperature = float(data["temperature"])
    humidity = float(data["humidity"])
    with SessionLocal() as db:
        # One row per sensor value, same as the Reading model in class
        db.add(models.Reading(sensor="temperature", content=temperature))
        db.add(models.Reading(sensor="humidity", content=humidity))
        db.commit()

        open_at, close_at = get_thresholds(db)
        window_state = get_window_state(db)
        # Two thresholds so the window doesn't keep flapping open/closed around one number
        if temperature >= open_at and window_state == "closed":
            send_window_command("open", "auto")
        elif temperature <= close_at and window_state == "open":
            send_window_command("close", "auto")


def handle_window_state(data: dict):
    state = data.get("state")
    if state not in ("open", "closed"):
        return
    with SessionLocal() as db:
        db.add(models.WindowEvent(state=state, reason=str(data.get("reason", "auto"))[:20]))
        db.commit()


def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code.is_failure:
        log.error("MQTT connect failed: %s", reason_code)
        return
    log.info("Connected to MQTT broker")
    client.subscribe([(config.TOPIC_READINGS, 1), (config.TOPIC_WINDOW_STATE, 1)])


def on_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload)
        if msg.topic == config.TOPIC_READINGS:
            handle_reading(data)
        elif msg.topic == config.TOPIC_WINDOW_STATE:
            handle_window_state(data)
    except (ValueError, KeyError, TypeError) as e:
        log.warning("Bad message on %s: %s", msg.topic, e)


def start():
    global client
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="room-monitor-server")
    if config.MQTT_USERNAME:
        client.username_pw_set(config.MQTT_USERNAME, config.MQTT_PASSWORD)
    if config.MQTT_TLS:
        # Encrypts everything between the broker and this server
        client.tls_set(cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLS_CLIENT)
    client.on_connect = on_connect
    client.on_message = on_message
    client.reconnect_delay_set(min_delay=1, max_delay=30)
    try:
        client.connect_async(config.MQTT_HOST, config.MQTT_PORT, keepalive=60)
        client.loop_start()  # runs in a background thread
    except Exception as e:  # website still works without the broker
        log.error("Could not start MQTT client: %s", e)


def stop():
    if client is not None:
        client.loop_stop()
        client.disconnect()
