# Room Temperature & Humidity Monitor

## What it does

A DHT22 sensor on a Raspberry Pi reads the temperature and humidity of a room. Each reading is sent to a server using MQTT (a publish-subscribe service). The server saves the readings in a database and shows them on a login-protected webpage, with the current reading and a graph of past readings.

## How it works

1. The DHT22 sensor reads the temperature and humidity.
2. The Raspberry Pi publishes the reading to the server over MQTT.
3. The FastAPI server subscribes to the readings and saves them in a database.
4. A logged-in user can view the current reading and a history graph on the dashboard.

## Hardware

- Raspberry Pi
- DHT22 temperature/humidity sensor

## Tech stack

- FastAPI (web server)
- MQTT (publish-subscribe communication)
- Database (readings storage)
- Hosted on AWS

## Security

- Data is encrypted in transit and at rest
- Dashboard access requires login
- MQTT channels are secured
