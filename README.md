# Room Temperature & Humidity Monitor

**Student:** Abdihafid Gahayr · **Module:** IoT (Software Development, DkIT) · **I-CA 2026-27**

**Live site:** https://YOUR-DOMAIN (replace)
**Repository:** https://github.com/YOUR-USERNAME/iot_ica_abdihafid_gahayr (replace)

## What it does

A DHT22 sensor on a Raspberry Pi reads the temperature and humidity of a room. Each reading is published over **MQTT** to a broker on an AWS EC2 server. The **FastAPI** server subscribes, saves every reading in a **PostgreSQL** database, and shows them on a login-protected dashboard with the current reading and a 24-hour graph.

If the room gets too warm, the server publishes a command over MQTT and a **servo opens the window**. When the room cools down, it closes again. The user can also open/close the window by hand and change the thresholds from the dashboard.

## How it works

1. The Pi reads the DHT22 every 30 s and publishes `{"temperature": 24.1, "humidity": 48}` to `room1/readings`.
2. The FastAPI server (subscribed to `room1/readings`) saves the reading to PostgreSQL.
3. The server checks the thresholds: temperature ≥ 25 °C and window closed → publish `{"window": "open"}` to `room1/window/cmd`; ≤ 23 °C and window open → `close`. Using two thresholds stops the window flapping.
4. The Pi (subscribed to `room1/window/cmd`) moves the servo, then publishes the real state to `room1/window/state`.
5. A logged-in user sees the live values, window state and history graph at `https://YOUR-DOMAIN`.

See [docs/architecture.md](docs/architecture.md) for the diagram.

## Hardware

| Part | Connection |
|---|---|
| Raspberry Pi | Runs `pi/room_sensor.py` |
| DHT22 | Data → GPIO4 (pin 7), 10 kΩ pull-up to 3.3 V |
| SG90 servo ("window") | Signal → GPIO18 (pin 12), 5 V, GND |

Wiring and Fritzing notes: [docs/hardware.md](docs/hardware.md).

## Tech stack

| Layer | Technology |
|---|---|
| IoT device | Raspberry Pi, Python, `adafruit-circuitpython-dht`, `gpiozero`, `paho-mqtt` |
| Pub-sub | Mosquitto MQTT broker on EC2, TLS on port 8883 |
| Backend | FastAPI, SQLAlchemy, paho-mqtt |
| Frontend | Jinja2 templates, Bootstrap 5, Chart.js |
| Database | PostgreSQL (on the EC2 instance, localhost only) |
| Web server | Nginx reverse proxy with a Let's Encrypt HTTPS certificate |
| Cloud | AWS EC2 (Ubuntu 24.04), Elastic IP, custom domain |

## Security

**In transit**
- Browser ↔ Nginx: HTTPS only (HTTP redirects to HTTPS, HSTS header).
- Pi ↔ broker and server ↔ broker: MQTT over **TLS on 8883**. Plain port 1883 is not opened.
- Nginx ↔ FastAPI and FastAPI ↔ PostgreSQL stay on `localhost` and never leave the server.

**At rest**
- The EC2 root volume (EBS) is **encrypted** (AWS KMS), so the database files on disk are encrypted.
- User passwords are stored as **bcrypt hashes**, never in plain text.

**Access control**
- **Webserver:** every page and API endpoint requires login (session cookie: `HttpOnly`, `Secure`, `SameSite=Strict`). There is no public sign-up page; users are created with `create_user.py`. FastAPI's `/docs` is turned off.
- **MQTT channels:** anonymous access is disabled. The `server` and `pi` users each have their own password, and **ACLs** limit what each can do. Only the server can publish window commands, and only the Pi can publish readings.
- **Database:** PostgreSQL only listens on localhost and uses a dedicated `roomapp` user with a random password (not the default `postgres` user).
- **Server:** UFW firewall only allows 22, 80, 443 and 8883. SSH uses key-only login. The FastAPI app runs as a non-root user and only listens on 127.0.0.1.
- **IoT device:** default `pi` password changed, SSH key login only, MQTT credentials kept in `.env`.
- **Secrets:** all passwords and keys live in `.env` files, which are in `.gitignore` and never committed.

## Project structure

```
server/
  main.py          FastAPI app: page routes, /api routes, error handlers
  database.py      SQLAlchemy engine, SessionLocal, get_db
  models.py        User, Reading, WindowEvent, Setting
  schemas.py       Pydantic request/response models
  auth.py          bcrypt password hashing + get_current_user (login check)
  mqtt_client.py   Subscribes to readings, sends window commands
  config.py        Loads settings and secrets from .env
  create_user.py   Creates the first login from the terminal
  templates/       layout.html, home.html, login.html, error.html
  static/          css/main.css, js/dashboard.js, icons/
pi/
  room_sensor.py   Reads the DHT22, publishes over MQTT, moves the servo
deploy/
  setup_ec2.sh     One-time installer for the EC2 server
docs/              Architecture, hardware and AWS notes
```

## Running it

**Server (local testing)**
```bash
cd server
cp .env.example .env          # fill in SESSION_SECRET
uv sync
uv run python create_user.py
uv run fastapi dev main.py
```

**Raspberry Pi**
```bash
cd pi
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # fill in MQTT details
python room_sensor.py         # or: python room_sensor.py --simulate
```

**EC2:** see [docs/aws-and-domain.md](docs/aws-and-domain.md), then run `sudo bash deploy/setup_ec2.sh <domain> <email> <repo-url>`.

## Known issues

- The DHT22 sometimes fails a read; the Pi retries up to 5 times before skipping that reading.
- If the broker is down, readings taken during that time are lost (no local buffering on the Pi yet).
- The servo is a model of a window opener, not a real actuator.
