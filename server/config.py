import os

from dotenv import load_dotenv

# All secrets come from the .env file, never from the code
load_dotenv()

SESSION_SECRET = os.environ["SESSION_SECRET"]
HTTPS_ONLY = os.getenv("HTTPS_ONLY", "false").lower() == "true"

SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./readings.db")

MQTT_HOST = os.getenv("MQTT_HOST", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", "8883"))
MQTT_TLS = os.getenv("MQTT_TLS", "true").lower() == "true"
MQTT_USERNAME = os.getenv("MQTT_USERNAME", "")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD", "")
MQTT_ROOM = os.getenv("MQTT_ROOM", "room1")

TOPIC_READINGS = f"{MQTT_ROOM}/readings"
TOPIC_WINDOW_CMD = f"{MQTT_ROOM}/window/cmd"
TOPIC_WINDOW_STATE = f"{MQTT_ROOM}/window/state"

DEFAULT_OPEN_AT = float(os.getenv("OPEN_AT", "25.0"))
DEFAULT_CLOSE_AT = float(os.getenv("CLOSE_AT", "23.0"))
