# HSMQTTBridge

A lightweight Python service that bridges an **MQTT broker** and **[HydroServer](https://github.com/hydroserver2/hydroserver)**.
 Field dataloggers (e.g. Mayfly / Arduino Uno, Campbell CR350) that publish sensor observations on MQTT broker on their respective topics. HSMQTTBridge subscribes to those topics, validates each observation, and loads it into the matching HydroServer datastream. If HydroServer can't be reached, the observation is saved to a local SQLite retry buffer and uploaded again later, so short outages don't lose data.
 Not all observation are buffered and saved to the database for retry. Below are the rules on the action that HSMQTTBridge performs depending on the response status code.

| Outcome | Retries |
|---|---|
| Payload fails validation (bad UUID, missing field, non-numeric result, bad timestamp) | No, logged and dropped |
| HTTP `408`, `429`, `449`, `500`, `502`, `503`, `504` | Yes, stored in the retry buffer |
| Any other HTTP error (e.g. `404` unknown datastream, `409` duplicate) | No |
| Connection-level errors (`requests.RequestException`: timeouts, DNS, refused connection) | Yes, stored with status code `0` because these errors have no HTTP response |

The table applies to the first publish attempt. Once an observation is in the buffer, any failed retry (whatever the status code) only increments its `retry_count`, except `404`, which is deleted on the next run. Rows stop being retried once they reach `MAX_RETRY_ATTEMPT`.

## Payload Structure

**Topic:** Observation Topic: `site/device-id/sensor-id/observed-variable`


LWT Topic: any topic ending with `/lwt`
All MQTT publishers should configure a last will and testament so the broker announces when a device's connection is lost.

**Payload:** Each observation is published as a JSON payload:

```json
{
  "Datastream": { "@iot.id": "019eae3f-3450-70db-b5d2-a55879b4d681" },
  "result": 23.4,
  "phenomenonTime": "2026-08-06T17:43:34Z"
}
```

| Field | Type | Notes |
|---|---|---|
| `Datastream.@iot.id` | UUID | Must be an existing HydroServer datastream |
| `result` | float | Measured value |
| `phenomenonTime` | ISO-8601 datetime | Time of the observation |


## Requirements

- Python 3.11+ (the Docker image uses 3.11, CI uses 3.13)
- A running MQTT broker (e.g. Mosquitto)
- A HydroServer instance and a workspace API key

Python dependencies are pinned in `requirements.txt` (this also includes the dev tools black, pylint and pytest).


## Installation

### Locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env 
mkdir -p data
python main.py
```

### With Docker

```bash
docker build -t hsmqttbridge:latest .
docker compose up -d
```

The image runs as a non-root `bridge` user with working directory `/hsmqttbridge`. `docker-compose.yml` mounts  `.env` and the `data` folder into the container. Set `DB_PATH=data/observation.db` as retry buffer path.