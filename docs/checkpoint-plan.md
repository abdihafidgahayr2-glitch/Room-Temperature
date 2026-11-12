# Checkpoint – what to show tomorrow

## Tonight (in this order, ~3–4 h)
1. **GitHub (15 min):** create the repo `iot_ica_abdihafid_gahayr`, add your lecturer, and push this folder in small commits (see below).
2. **Backend + frontend + DB locally (45 min):**
   `cd server && cp .env.example .env` → set `SESSION_SECRET`, `MQTT_TLS=false`, `MQTT_HOST=localhost`
   `uv sync && uv run python create_user.py && uv run fastapi dev main.py`
   Log in at http://127.0.0.1:8000 and check the dashboard loads. It will be empty until readings arrive.
3. **AWS (60–90 min):** follow `docs/aws-and-domain.md`: launch EC2 with an encrypted disk, Elastic IP, domain A record, then run `setup_ec2.sh`.
4. **Pi (30–60 min):** if you have the hardware, wire it (`docs/hardware.md`) and run `room_sensor.py`. If not, run `python room_sensor.py --simulate` on your laptop. It publishes to the real broker the same way.
5. **Fritzing sketch + architecture diagram:** paste `docs/architecture.md` into GitHub, which renders the Mermaid diagram. Or redraw it in draw.io.

## Talking points (one line each)
| Area | What to say / show |
|---|---|
| Frontend | Login page + dashboard (live values, 24 h graph, window buttons, thresholds) – Jinja2 + Bootstrap 5 + Chart.js |
| Backend | FastAPI: login with sessions, every route protected, JSON API, MQTT subscriber in a background thread |
| Hardware | Pi + DHT22 on GPIO4 + SG90 servo on GPIO18 as the window (teacher's feedback) |
| DB | PostgreSQL, 4 tables (user, reading, window_event, setting) – same SQLAlchemy style as class, localhost only, bcrypt passwords |
| Domain | Custom domain → Elastic IP, HTTPS via Let's Encrypt |
| Cloud / EC2 installer | `deploy/setup_ec2.sh` installs Nginx, certbot, PostgreSQL, Mosquitto (TLS + ACLs) and the systemd service, and sets up the UFW firewall |

If something isn't finished, say what's next. Checkpoints are marked on progress.

## Commit messages (Chris Beams rules: imperative, ≤50 chars, capitalised, no full stop)
```
Add project README and gitignore
Add database setup, models and schemas
Add password hashing and login check
Add MQTT client with window threshold logic
Add FastAPI routes, templates and dashboard
Add Raspberry Pi sensor and servo script
Add EC2 installer for Nginx, Mosquitto, Postgres
Add hardware wiring and AWS setup docs
```
