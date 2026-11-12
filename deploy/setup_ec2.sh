#!/usr/bin/env bash
# One-time installer for a fresh Ubuntu 24.04 EC2 instance.
# Installs: Nginx (HTTPS reverse proxy), Let's Encrypt cert, PostgreSQL, Mosquitto (MQTT over TLS
# with passwords + ACLs), the FastAPI app as a systemd service, and the UFW firewall.
#
# Usage (on the EC2 instance):
#   sudo bash setup_ec2.sh <your-domain> <your-email> <github-repo-url>
# Example:
#   sudo bash setup_ec2.sh roommonitor.me me@example.com https://github.com/you/iot_ica_abdihafid_gahayr.git
#
# Before running: the domain's DNS A record must point at this instance's Elastic IP,
# and the security group must allow 22, 80, 443 and 8883.
set -euo pipefail

DOMAIN="${1:?domain required}"
EMAIL="${2:?email required}"
REPO="${3:?repo url required}"
APP_DIR=/opt/room-monitor
APP_USER=roomapp

gen() { openssl rand -hex 24; }

echo "==> Installing packages"
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get -y upgrade
DEBIAN_FRONTEND=noninteractive apt-get -y install nginx postgresql mosquitto mosquitto-clients \
    certbot python3-certbot-nginx ufw git curl openssl
curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR=/usr/local/bin sh

echo "==> Firewall (only SSH, HTTP/HTTPS and MQTT over TLS)"
ufw allow OpenSSH
ufw allow 'Nginx Full'
ufw allow 8883/tcp
ufw --force enable

echo "==> App user + code"
id -u "$APP_USER" >/dev/null 2>&1 || useradd --system --create-home --shell /usr/sbin/nologin "$APP_USER"
[ -d "$APP_DIR" ] || git clone "$REPO" "$APP_DIR"
chown -R "$APP_USER:$APP_USER" "$APP_DIR"

echo "==> PostgreSQL (listens on localhost only, non-default user + random password)"
DB_PASS=$(gen)
sudo -u postgres psql -v ON_ERROR_STOP=1 <<SQL
CREATE USER roomapp WITH PASSWORD '${DB_PASS}';
CREATE DATABASE roommonitor OWNER roomapp;
SQL

echo "==> MQTT users"
SERVER_MQTT_PASS=$(gen)
PI_MQTT_PASS=$(gen)

echo "==> Writing server .env (readable only by the app user)"
cat > "$APP_DIR/server/.env" <<ENV
SESSION_SECRET=$(openssl rand -hex 32)
DATABASE_URL=postgresql+psycopg://roomapp:${DB_PASS}@localhost:5432/roommonitor
HTTPS_ONLY=true
MQTT_HOST=${DOMAIN}
MQTT_PORT=8883
MQTT_TLS=true
MQTT_USERNAME=server
MQTT_PASSWORD=${SERVER_MQTT_PASS}
MQTT_ROOM=room1
OPEN_AT=25.0
CLOSE_AT=23.0
ENV
chown "$APP_USER:$APP_USER" "$APP_DIR/server/.env"
chmod 600 "$APP_DIR/server/.env"

echo "==> Python dependencies"
sudo -u "$APP_USER" -H uv sync --project "$APP_DIR/server"

echo "==> systemd service (app only listens on 127.0.0.1, Nginx is the only way in)"
cat > /etc/systemd/system/room-monitor.service <<UNIT
[Unit]
Description=Room Monitor FastAPI app
After=network.target postgresql.service mosquitto.service

[Service]
User=${APP_USER}
WorkingDirectory=${APP_DIR}/server
ExecStart=${APP_DIR}/server/.venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000 --proxy-headers --forwarded-allow-ips 127.0.0.1
Restart=always
NoNewPrivileges=true
ProtectSystem=full

[Install]
WantedBy=multi-user.target
UNIT

echo "==> Nginx reverse proxy"
rm -f /etc/nginx/sites-enabled/default
cat > /etc/nginx/sites-available/room-monitor <<NGINX
server {
    listen 80;
    server_name ${DOMAIN};
    server_tokens off;

    add_header X-Content-Type-Options nosniff always;
    add_header X-Frame-Options DENY always;
    add_header Referrer-Policy same-origin always;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
NGINX
ln -sf /etc/nginx/sites-available/room-monitor /etc/nginx/sites-enabled/room-monitor
nginx -t && systemctl reload nginx

echo "==> HTTPS certificate (Let's Encrypt) + redirect HTTP -> HTTPS"
certbot --nginx -d "$DOMAIN" -m "$EMAIL" --agree-tos --non-interactive --redirect
# HSTS once HTTPS works
sed -i '/server_tokens off;/a \    add_header Strict-Transport-Security "max-age=31536000" always;' /etc/nginx/sites-available/room-monitor
nginx -t && systemctl reload nginx

echo "==> Mosquitto: TLS only, no anonymous, passwords + ACLs"
mkdir -p /etc/mosquitto/certs
cat > /etc/letsencrypt/renewal-hooks/deploy/mosquitto.sh <<HOOK
#!/bin/sh
cp /etc/letsencrypt/live/${DOMAIN}/fullchain.pem /etc/mosquitto/certs/fullchain.pem
cp /etc/letsencrypt/live/${DOMAIN}/privkey.pem   /etc/mosquitto/certs/privkey.pem
chown mosquitto:mosquitto /etc/mosquitto/certs/*.pem
chmod 600 /etc/mosquitto/certs/privkey.pem
systemctl restart mosquitto
HOOK
chmod +x /etc/letsencrypt/renewal-hooks/deploy/mosquitto.sh

rm -f /etc/mosquitto/passwd
mosquitto_passwd -b -c /etc/mosquitto/passwd server "$SERVER_MQTT_PASS"
mosquitto_passwd -b    /etc/mosquitto/passwd pi     "$PI_MQTT_PASS"

cat > /etc/mosquitto/acl <<ACL
# Server: reads readings + window state, sends window commands
user server
topic read  room1/readings
topic read  room1/window/state
topic write room1/window/cmd

# Pi: sends readings + window state, receives window commands
user pi
topic write room1/readings
topic write room1/window/state
topic read  room1/window/cmd
ACL

cat > /etc/mosquitto/conf.d/room-monitor.conf <<CONF
per_listener_settings false
allow_anonymous false
password_file /etc/mosquitto/passwd
acl_file /etc/mosquitto/acl

# Only listener: MQTT over TLS on 8883 (no plain 1883)
listener 8883
certfile /etc/mosquitto/certs/fullchain.pem
keyfile  /etc/mosquitto/certs/privkey.pem
tls_version tlsv1.2
CONF
chown mosquitto:mosquitto /etc/mosquitto/passwd /etc/mosquitto/acl
chmod 600 /etc/mosquitto/passwd /etc/mosquitto/acl
/etc/letsencrypt/renewal-hooks/deploy/mosquitto.sh   # copies certs + restarts mosquitto

echo "==> Starting app"
systemctl daemon-reload
systemctl enable --now room-monitor

cat <<DONE

=====================================================================
 Done. Site: https://${DOMAIN}

 Create your login:
   cd ${APP_DIR}/server && sudo -u ${APP_USER} -H uv run python create_user.py

 Put this in pi/.env on the Raspberry Pi (shown ONCE, save it now):
   MQTT_HOST=${DOMAIN}
   MQTT_USERNAME=pi
   MQTT_PASSWORD=${PI_MQTT_PASS}

 Logs:  journalctl -u room-monitor -f     |     journalctl -u mosquitto -f
=====================================================================
DONE
