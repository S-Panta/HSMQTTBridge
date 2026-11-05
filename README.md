# HSMQTTBridge

HSMQTTBridge is a multithreaded service written in Python that bridges an **MQTT broker** with [HydroServer](https://github.com/hydroserver2/hydroserver)**. It subscribes to MQTT topics, processes incoming JSON payloads, and submits valid observations to their corresponding HydroServer datastreams through the HydroServer API. The MQTT subscription and forwarding topics are configurable through the `.env` file.

## MQTT Configuration
- This service can be used against any running instance of broker. If broker url is not given, `test.mosquitto.org` shall be used. This however is not recommended.
- A running instance of HydroServer is needed. HydroServer can be installed locally or you can point to the instance that you're trying to store your observed data.
- If you are using any publishers ( a python script, an Arduino Client), make sure your payload confines to the json schema as shown below. For Arduino Library, it is suggested that you use [HydroServerArduinoClient](https://github.com/S-Panta/HydroServerArduinoClient) along with this service.
```json
{
  "Datastream": { "@iot.id": "019eae3f-3450-70db-b5d2-a55879b4d681" },
  "result": 23.4,
  "phenomenonTime": "2026-08-06T17:43:34Z"
}
```

## Requirements
- Python 3.11+
- A running MQTT broker (e.g. Mosquitto)
- A HydroServer instance and a workspace API key

## Installation

### Locally
- Create virtual environment and install all dependencies.
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```
- Create .env file and write configuration according to your need. Look at `settings.py` for the defaults.

```bash
cp .env.example .env 
mkdir -p data
python main.py
```
- Create data folder to store your buffer data and start the program
```bash
mkdir -p data
python main.py
```

### With Docker
- Since docker takes it's environment variable from .env file, make sure to create your own env file and add your configuration to it.
```bash
docker build -t hsmqttbridge:latest .
docker compose up -d
```
