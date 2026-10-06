# HSMQTTBridge

A lightweight Python service that bridges an **MQTT broker** and **[HydroServer](https://github.com/hydroserver2/hydroserver)**.
 Field dataloggers (e.g. Mayfly / Arduino Uno, Campbell CR350) that publish sensor observations on MQTT broker on their respective topics. HSMQTTBridge subscribes to those topics, validates each observation, and loads it into the matching HydroServer datastream. If HydroServer can't be reached, the observation is saved to a local SQLite retry buffer and uploaded again later, so short outages don't lose data.

## How it works

1. **MQTT consumer** (`mqtt_consumer.py`) connects to the broker with paho-mqtt (callback API v2), subscribes to `MQTT_TOPIC_FILTER` (e.g. `uwrl/#`) and puts each incoming `(topic, payload)` pair on a shared in-memory `queue.Queue`, which `main.py` creates and passes to both the consumer and the router.
2. **Message router** (`message_router.py`) takes messages off the queue on a background thread (`message_router`):
   - topics ending in `/lwt` (last-will messages) are not sent to HydroServer;
   - topics matching any filter in `HYDROSERVER_TOPIC_ROUTES` (a list of MQTT topic filters) are handed to the HydroServer publisher. Invalid JSON is logged and dropped;
   - topics that match no route are ignored.
3. **HydroServer publisher** (`publisher/hydroserver/publisher.py`) validates the payload with Pydantic (`models.py`), looks up the datastream through `hydroserverpy` (datastream objects are cached in memory after the first lookup), and loads the observation. It returns `None` on success or a `PublishFailure` that records the error and whether the observation is worth retrying.
4. **Retry buffer** (`database/retry_buffer.py`) stores retryable failures in a SQLite table `buffered_observations` together with the topic, error type/message, HTTP status code and retry count.
5. **Retry worker** (`publisher/hydroserver/retry_worker.py`) runs on its own thread (`retry_worker`). It runs once at startup and then every `RETRY_INTERVAL` seconds. On Every run it does the following:
   - reads the buffer and deletes any row whose last error was HTTP `404` (unknown datastream);
   - skips rows that have reached `MAX_RETRY_ATTEMPT` (they stay in the database for inspection);
   - groups the remaining observations by topic and uploads each group as one batch;
   - deletes the batch from retry buffer on each successful post to HydroServer , or increments their `retry_count` and records the new error.

### What gets retried

| Outcome | Retries |
|---|---|
| Payload fails validation (bad UUID, missing field, non-numeric result, bad timestamp) | No, logged and dropped |
| HTTP `408`, `429`, `449`, `500`, `502`, `503`, `504` | Yes, stored in the retry buffer |
| Any other HTTP error (e.g. `404` unknown datastream, `409` duplicate) | No |
| Connection-level errors (`requests.RequestException`: timeouts, DNS, refused connection) | Yes, stored with status code `0` because these errors have no HTTP response |

The table applies to the first publish attempt. Once an observation is in the buffer, any failed retry (whatever the status code) only increments its `retry_count`, except `404`, which is deleted on the next run. Rows stop being retried once they reach `MAX_RETRY_ATTEMPT`.

The diagrams in [`docs/flowchart.md`](docs/flowchart.md) and [`docs/sequencediagram.md`](docs/sequencediagram.md) give a high-level view of the flow; they omit the queue/router step and the exact retry rules described above.

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

## Configuration

Settings are read from environment variables or a `.env` file in the working directory (see `.env.example`). Variable names are case-insensitive. Empty values (e.g. `MQTT_BROKER_PORT=`) are not treated as unset, so remove or comment out any variable you want to leave at its default.

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
| `HYDROSERVER_TOPIC_ROUTES` | **yes** | – | JSON list of MQTT topic filters routed to HydroServer, e.g. `["uwrl/+/+/temperature"]`  |
| `DB_PATH` | **yes** | – | Path to the SQLite retry buffer, e.g. `data/observation.db` |
| `LOG_LEVEL` | no | `INFO` | Python logging level, in upper case (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `MAX_RETRY_ATTEMPT` | no | `10` | Retries allowed per buffered observation |
| `RETRY_INTERVAL` | no | `1800` | Seconds between retry runs (30 min) |

### Routing topics to HydroServer

`HYDROSERVER_TOPIC_ROUTES` decides which received messages are sent to HydroServer. It must be a JSON **list** of MQTT topic filters; a message is routed if its topic matches **any** filter in the list. 

```
HYDROSERVER_TOPIC_ROUTES=["uwrl/+/+/temperature", "uwrl/+/+/humidity"]
```

Filters follow the MQTT topic wildcard subscription rules: `+` matches exactly one level, `#` matches any number of levels and must be the last level, and a filter without wildcards matches only that exact topic. 

| Route | Sends to HydroServer |
|---|---|
| `["#"]` | everything the bridge receives |
| `["uwrl/#"]` | every topic from site `uwrl` |
| `["uwrl/client-1/#"]` | every sensor on device `client-1` |
| `["uwrl/client-1/dts-12/+"]` | every variable from sensor `dts-12` |
| `["uwrl/+/+/temperature"]` | temperature from every device and sensor |
| `["uwrl/client-1/dts-12/temperature"]` | that one topic only |


## Running

### Locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then fill in WORKSPACE_API_KEY, DB_PATH, HYDROSERVER_TOPIC_ROUTES
mkdir -p data
python main.py
```


### With Docker

```bash
docker build -t hsmqttbridge:latest .
docker compose up -d
```

The image runs as a non-root `bridge` user with working directory `/hsmqttbridge`. `docker-compose.yml` mounts  `.env` and the `data` folder into the container. Set `DB_PATH=data/observation.db` so the retry buffer lands in the mounted folder.