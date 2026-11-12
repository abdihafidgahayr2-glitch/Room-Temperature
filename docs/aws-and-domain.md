# AWS EC2 + Domain Setup

## 1. Get a domain
- Free option: the **GitHub Student Developer Pack** includes a free domain for a year (e.g. Namecheap `.me`). Otherwise buy a cheap one (~€2–10).

## 2. Launch the EC2 instance (AWS Console → EC2 → Launch instance)
| Setting | Value |
|---|---|
| Name | room-monitor |
| AMI | Ubuntu Server 24.04 LTS |
| Type | t2.micro / t3.micro (free tier) |
| Key pair | create a new one and download the `.pem` (never commit it) |
| Storage | 8–20 GB gp3, **Advanced → Encrypted: Yes** (this is your encryption at rest) |

**Security group (inbound rules):**
| Port | Source | Why |
|---|---|---|
| 22 (SSH) | My IP only | admin |
| 80 (HTTP) | 0.0.0.0/0 | Let's Encrypt + redirect to HTTPS |
| 443 (HTTPS) | 0.0.0.0/0 | website |
| 8883 (MQTT TLS) | 0.0.0.0/0 | Pi → broker |

## 3. Elastic IP
EC2 → Elastic IPs → Allocate → Associate with the instance. This keeps the IP from changing when you restart.

## 4. Point the domain at it
At your domain registrar, add an **A record**: host `@` → your Elastic IP. Check it with `nslookup your-domain`. DNS can take a few minutes to update.

## 5. Run the installer
```bash
ssh -i room-monitor.pem ubuntu@your-domain
git clone https://github.com/YOU/iot_ica_abdihafid_gahayr.git
sudo bash iot_ica_abdihafid_gahayr/deploy/setup_ec2.sh your-domain you@email.com https://github.com/YOU/iot_ica_abdihafid_gahayr.git
```
At the end the script prints the Pi's MQTT password **once**, so copy it straight away. Then create your login:
```bash
cd /opt/room-monitor/server && sudo -u roomapp -H uv run python create_user.py
```

## 6. Harden SSH
In `/etc/ssh/sshd_config`, check `PasswordAuthentication no` and `PermitRootLogin no`, then run `sudo systemctl restart ssh`.

## 7. Test
- `https://your-domain` → login page with a valid padlock
- From your laptop: `mosquitto_sub -h your-domain -p 8883 -t '#'` should be **refused** (no username). This is a good demo for the screencast.
- `journalctl -u room-monitor -f` should show "Connected to MQTT broker".

## Updating after a git push
```bash
cd /opt/room-monitor && sudo -u roomapp git pull && sudo -u roomapp -H uv sync --project server && sudo systemctl restart room-monitor
```
