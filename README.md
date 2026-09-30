# HSMQTTBridge

A lightweight Python service that bridges an **MQTT broker** and **[HydroServer](https://github.com/hydroserver2/hydroserver)**.

Field dataloggers (e.g. Mayfly / Arduino Uno, Campbell CR350) publish sensor observations to an MQTT broker. HSMQTTBridge subscribes to those topics, validates each observation, and loads it into the matching HydroServer datastream. If HydroServer can't be reached, the observation is saved to a local SQLite retry buffer and uploaded again later, so short outages don't lose data.

## How it works

1. **MQTT consumer** (`mqtt_consumer.py`) connects to the broker with paho-mqtt (callback API v2), subscribes to `MQTT_TOPIC_FILTER` (e.g. `uwrl/#`) and puts each incoming `(topic, payload)` pair on a shared in-memory queue (`queue_manager.py`). The paho callback does nothing else, so it never blocks the network loop.
2. **Message router** (`message_router.py`) takes messages off the queue on a background thread (`message_router`):
   - topics ending in `/lwt` (last-will messages) are reserved for a future notification service and are currently skipped;
   - topics matching `HYDROSERVER_TOPIC_ROUTES` (an MQTT topic filter, `#` by default) are parsed as JSON and handed to the HydroServer publisher. Invalid JSON is logged and dropped.
3. **HydroServer publisher** (`publisher/hydroserver/publisher.py`) validates the payload with Pydantic (`models.py`), looks up the datastream through `hydroserverpy` (datastream objects are cached in memory after the first lookup), and loads the observation. It returns `None` on success or a `PublishFailure` that records the error and whether the observation is worth retrying.
4. **Retry buffer** (`database/retry_buffer.py`) stores retryable failures in a SQLite table (`buffered_observations`, WAL mode) together with the topic, error type/message, HTTP status code and retry count.
5. **Retry worker** (`publisher/hydroserver/retry_worker.py`) runs on its own thread (`retry_worker`). Every `RETRY_INTERVAL` seconds it reads the buffer, groups observations by topic, uploads each group as one batch, then deletes the rows that went through or increments their retry count. Rows that have reached `MAX_RETRY_ATTEMPT` are skipped (they stay in the database for inspection).

### What gets retried

| Outcome | Retries |
|---|---|
| Success | – |
| Payload fails validation (bad UUID, missing field, non-numeric result, bad timestamp) | No, logged and dropped |
| HTTP `408`, `429`, `449`, `500`, `502`, `503`, `504` | Yes, stored in the retry buffer |
| Any other HTTP error (e.g. `404` unknown datastream, `409` duplicate) | No |
| Connection-level errors (`requests.RequestException`: timeouts, DNS, refused connection) | Yes |

The diagrams in [`docs/flowchart.md`](docs/flowchart.md) and [`docs/sequencediagram.md`](docs/sequencediagram.md) show the overall flow.

## Message contract

**Topic:** Observation Topic: `site/device-id/sensor-id/observed-variable` and LWT Topics are any topics ending with `/lwt`

**Payload:** The payload send as mqtt payload by the publishers are: 

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

Each topic should carry observations for a single datastream: the retry worker batches by topic and uploads each batch to the datastream of its first observation.


## Requirements

- Python 3.11+ (the Docker image uses 3.11, CI uses 3.13)
- An MQTT broker (e.g. Mosquitto)
- A HydroServer instance and a workspace API key

Python dependencies are pinned in `requirements.txt` (paho-mqtt, hydroserverpy, pydantic, pydantic-settings, pandas, requests, plus black, pylint and pytest for development).

## Configuration

Settings are read from environment variables or a `.env` file in the working directory (see `.env.example`). Names are case-insensitive.

| Variable | Required | Default | Description |
|---|---|---|---|
| `HYDROSERVER_URL` | no | `https://playground.hydroserver.org/` | HydroServer base URL |
| `WORKSPACE_API_KEY` | **yes** | – | HydroServer workspace API key |
| `MQTT_BROKER_URL` | no | `test.mosquitto.org` | Broker host |
| `MQTT_BROKER_PORT` | no | `1883` | Broker port |
| `MQTT_TOPIC_FILTER` | no | `#` | Subscription filter, e.g. `uwrl/#` (whole site) or `uwrl/client/#` (one client) |
| `MQTT_CLIENT_ID` | no | `hsmqttbridge` | MQTT client id |
| `MQTT_KEEPALIVE` | no | `60` | Keepalive in seconds |
| `MQTT_USERNAME` / `MQTT_PASSWORD` | no | – | Broker credentials (only used if a username is set) |
| `HYDROSERVER_TOPIC_ROUTES` | no | `#` | MQTT topic filter for topics routed to HydroServer, e.g. `+/+/temperature` |
| `DB_PATH` | **yes** | – | Path to the SQLite retry buffer, e.g. `data/observation.db` |
| `LOG_LEVEL` | no | `INFO` | Python logging level |
| `MAX_RETRY_ATTEMPT` | no | `10` | Retries allowed per buffered observation |
| `RETRY_INTERVAL` | no | `1800` | Seconds between retry runs (30 min) |

`HYDROSERVER_TOPIC_ROUTES` are used to route the topic into HydroServer. You can use mqtt topic filter for this. For example, if you want only the topics from certain publisher to Hydroserver, use `uwrl/client-1/#` or if you want from only one sensor, use `uwrl/client-1/dts-12` and so on. You can be as much flexible with mqtt topics as the topic design for the clients carry the information of site, device detail, sensor information and the value that it measures.
## Running

### Locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # then fill in values
mkdir -p data
python main.py
```

### With Docker

```bash
docker build -t mqtt_bridge:latest .
docker compose up -d
```

The image runs as a non-root `bridge` user. `.env` is excluded from the image, so configuration comes from `docker-compose.yml`, which passes `HYDROSERVER_URL`, `WORKSPACE_API_KEY`, `MQTT_BROKER_URL`, `MQTT_TOPIC_FILTER`, `DB_PATH`, `LOG_LEVEL`, `MAX_RETRY_ATTEMPT` and `RETRY_INTERVAL` through from your shell or `.env` (add any other variables you need there). The compose file mounts `./data` to `/app/data`, so set `DB_PATH=/app/data/observation.db` to keep the retry buffer when the container is recreated.


## Known limitations

- The notification service for `/lwt` (last-will) topics is not implemented yet; those messages are only logged.