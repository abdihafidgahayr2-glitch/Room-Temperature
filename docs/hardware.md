# Hardware & Wiring

## Parts
- Raspberry Pi (any model with a 40-pin header) + power supply + microSD with Raspberry Pi OS
- DHT22 (AM2302) temperature/humidity sensor
- 10 kΩ resistor (not needed if your DHT22 is on a 3-pin breakout board, which has one built in)
- SG90 micro servo + a cardboard/popsicle-stick "window" on a hinge
- Breadboard + jumper wires

## Wiring

| From | To (Pi physical pin) |
|---|---|
| DHT22 VCC (pin 1) | 3.3 V (pin 1) |
| DHT22 DATA (pin 2) | GPIO4 (pin 7) |
| 10 kΩ resistor | between DHT22 DATA and 3.3 V (pull-up) |
| DHT22 pin 3 | not connected |
| DHT22 GND (pin 4) | GND (pin 6) |
| Servo red (power) | 5 V (pin 2) |
| Servo brown (ground) | GND (pin 9) |
| Servo orange (signal) | GPIO18 (pin 12) |

## Fritzing sketch
1. Open Fritzing → Breadboard view.
2. Search the parts bin for "Raspberry Pi 4" (or your model), "DHT22", "resistor" (set to 10 kΩ) and "servo".
3. Wire them as in the table above. Use red for power, black for ground, and other colours for signals.
4. File → Export → as Image (PNG) and save it as `docs/fritzing.png`. Also commit the `.fzz` file.

## Pi setup checklist (security of the device)
- [ ] Change the default password: `passwd`
- [ ] SSH with keys only: set `PasswordAuthentication no` in `/etc/ssh/sshd_config`
- [ ] `sudo apt update && sudo apt full-upgrade`
- [ ] Copy `pi/.env.example` to `pi/.env` and add the MQTT password from the EC2 installer
