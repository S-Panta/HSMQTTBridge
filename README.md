# HSMQTTBridge

A lightweight Python service that bridges an **MQTT broker** and **[HydroServer](https://github.com/hydroserver2/hydroserver)**.

Field dataloggers (e.g. Mayfly / Arduino Uno, Campbell CR350) publish sensor observations to an MQTT broker. HSMQTTBridge subscribes to those topics, validates each observation, and loads it into the matching HydroServer datastream. If HydroServer can't be reached, the observation is saved to a local SQLite cache and retried later, so short outages don't lose data.

## How it works

1. **MQTT consumer** (`mqtt/consumer.py`) subscribes to a configurable topic filter (e.g. `uwrl/#`) and puts each incoming `(topic, payload)` pair on an in-memory queue. The paho network callback does nothing else, so it never blocks.
2. **Message router** (`message_router.py`) takes messages off the queue on a background thread, parses the JSON, and routes on the topic suffix (currently topics ending in `temperature`) to the HydroServer publisher.
3. **HydroServer publisher** (`publisher/hydroserver/`) validates the payload with Pydantic and loads it into HydroServer through `hydroserverpy`. It returns `None` on success or a `PublishError` that says whether the observation is worth retrying.
4. **Failed observation store** (`database/`) keeps retryable failures (network errors, rate limiting) in SQLite instead of dropping them.
5. **Retry worker** (`publisher/hydroserver/retry_worker.py`) runs on its own thread. Every `RETRY_INTERVAL` it groups cached observations by topic, uploads each group as one batch, then deletes the rows that went through or bumps their retry count.

The diagrams in [`docs/flowchart.md`](docs/flowchart.md) and [`docs/sequencediagram.md`](docs/sequencediagram.md) show the flow. The reasons behind each part are written up in [`docs/`](docs/README.md).

## Message contract

**Topic:** `<site>/<client>/<variable>`, for example `uwrl/test-publisher-1/temperature`. The last segment names the observed variable and decides how the message is routed.

**Payload:** JSON in the SensorThings-style shape HydroServer uses:

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

Payloads that fail validation are logged and dropped. They are never cached, because retrying them can't succeed.

## Project layout

```
.
├── main.py                     # Entry point: wires components, starts threads
├── config.py                   # Pydantic settings (env vars / .env)
├── queue_manager.py            # Shared in-memory queue (consumer -> router)
├── message_router.py           # Topic-based routing to publishers
├── mqtt/consumer.py            # paho-mqtt subscriber
├── publisher/
│   ├── base_publisher.py       # Publisher ABC + PublishError result type
│   └── hydroserver/
│       ├── hydroserver_publisher.py  # Validation + upload via hydroserverpy
│       ├── models.py                 # Pydantic observation model
│       └── retry_worker.py           # Periodic batch retry of cached failures
├── database/
│   ├── failed_observation_store.py   # SQLite persistence for failures
│   └── model.py                      # FailedObservation dataclass
├── tests/unit/                 # pytest unit tests
├── docs/                       # Diagrams + design decision records
├── Dockerfile / docker-compose.yml
└── .github/workflows/ci.yml    # black, pylint, pytest
```

## Requirements

- Python 3.11+ (the Docker image uses 3.11, CI uses 3.13)
- An MQTT broker (e.g. Mosquitto)
- A HydroServer instance and a workspace API key

## Configuration

Settings are read from environment variables or a `.env` file in the working directory (see `.env.example`). Names are case-insensitive.

| Variable | Required | Default | Description |
|---|---|---|---|
| `HYDROSERVER_URL` | no | `https://playground.hydroserver.org/` | HydroServer base URL |
| `WORKSPACE_API_KEY` | **yes** | – | HydroServer workspace API key |
| `MQTT_BROKER_URL` | no | `test.mosquitto.org` | Broker host |
| `MQTT_BROKER_PORT` | no | `1883` | Broker port |
| `MQTT_TOPIC_FILTER` | no | `#` | Subscription filter, e.g. `uwrl/#` |
| `MQTT_CLIENT_ID` | no | `hsmqttbridge` | MQTT client id\* |
| `MQTT_KEEPALIVE` | no | `60` | Keepalive in seconds\* |
| `MQTT_USERNAME` / `MQTT_PASSWORD` | no | – | Broker credentials\* |
| `DB_PATH` | **yes** | – | Path to the SQLite cache file, e.g. `data/observation.db` |
| `LOG_LEVEL` | no | `INFO` | Python logging level |
| `MAX_RETRY_ATTEMPT` | **yes** | – | Retries allowed per cached observation\* |
| `RETRY_INTERVAL` | **yes** | – | Seconds between retry runs\* |

\* The service reads these settings but `main.py` doesn't pass them to the components yet, so the hard-coded defaults are used. See [known issues](docs/known-issues.md).

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

`docker-compose.yml` mounts `./data` to `/app/data`, so set `DB_PATH=/app/data/observation.db` to keep the cache when the container is recreated.

### Sending test data

`test_publisher.py` publishes a few sample temperature readings to a broker on `localhost:1883`:

```bash
python test_publisher.py
```

## Development

```bash
pytest -v                 # unit tests (tests/)
black --check .           # formatting
pylint .                  # linting (see .pylintrc)
```

CI (`.github/workflows/ci.yml`) runs all three on every push and non-draft PR to `main`.

## Documentation

- [`docs/README.md`](docs/README.md): documentation index
- [`docs/architecture.md`](docs/architecture.md): components, threading model, data lifecycle
- [`docs/adr/`](docs/adr/): Architecture Decision Records, one per design decision
- [`docs/known-issues.md`](docs/known-issues.md): current gaps and suggested fixes
