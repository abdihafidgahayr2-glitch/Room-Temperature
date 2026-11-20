# AI Chat Log

AI use in this assessment is "Open Use" (see the I-CA brief). I used Claude to help me plan, write code and fix problems. This log shows what I asked for and what I did myself.

| Date | Tool | What I asked | What I did with it |
|---|---|---|---|
| 12 Nov | Claude | Checked my README against the brief | Added more detail about the database, MQTT, TLS, logins and secrets |
| 12 Nov | Claude | How to add my lecturer's feedback (open a window when the room is too warm) | Decided to use a servo with two temperatures (open at 25, close at 23) so it doesn't keep flapping |
| 12 Nov | Claude | Wrote the starter code for the server, the Pi script, the EC2 install script and the docs | Used it as my starting point. Ran it locally and tested the login and dashboard |
| 12 Nov | Claude | Rewrote the server to match my lecturer's fastapi_intro | Asked for this so the code follows what we did in class and I can explain it |
| 12 Nov | Claude | Help with errors running the server (OneDrive reloading, broken .venv, port clash with my group project) | Moved the project out of OneDrive, rebuilt the .venv, fixed the port issue |
| 12 Nov | Claude | Help splitting my work into commits | Made the commits myself and pushed to my existing GitHub repo |
| 16–17 Nov | Claude | How to wire the DHT22 to the Pi | Found the right jumper wires and wired it myself (3.3V, GND, GPIO4) |
| 19 Nov | Claude | How to set up Raspberry Pi OS without a screen | Bought an SD card, flashed it with Raspberry Pi Imager, set up Wi-Fi and SSH, connected from my laptop |
| 19 Nov | Claude | Help with library errors when reading the sensor (gpiod missing) | Installed the missing packages and got my first reading: 18.5°C, 73% |
| 20 Nov | Claude | How to set up Mosquitto on the Pi and connect it to my server | Installed and configured Mosquitto, set up the .env files on the Pi and laptop, fixed SSH drops (Wi-Fi power saving) |

## What I did myself
- Picked the project idea and the hardware
- Bought the SD card and set up the Pi from scratch
- Wired the sensor to the Pi and tested it
- Set up Mosquitto on the Pi and got readings showing on my dashboard
- Tested the window open/close from the dashboard and checked the Pi got the commands
- Recorded a short video showing the sensor working end to end
- Tested everything locally on Windows and fixed setup problems along the way
- Made all the commits and pushed to GitHub

## Next
- Deploy to AWS EC2 with a domain and HTTPS
- Secure MQTT with TLS, passwords and ACLs
- Add the servo
- Fritzing sketch and screencast