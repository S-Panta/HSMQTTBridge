# Architecture

## Purpose

Environmental dataloggers in the field publish observations over MQTT, which is lightweight, tolerates poor links, and is supported by constrained devices. HydroServer takes data through an HTTP/SensorThings-style API. HSMQTTBridge sits between the two. It turns an MQTT stream into HydroServer observations, and it absorbs HydroServer outages so field devices never need retry logic of their own.

## Components

| Component | File | Responsibility |
|---|---|---|
| `Config` | `config.py` | Loads typed settings from env / `.env` |
| `MQTTConsumer` | `mqtt/consumer.py` | Connects to the broker, subscribes, decodes bytes to `str`, enqueues `(topic, payload)` |
| `taskqueue` | `queue_manager.py` | Unbounded `queue.Queue` shared by the consumer and the router |
| `MessageRouter` | `message_router.py` | Dequeues, filters by topic suffix, parses JSON, calls the publisher, caches retryable failures |
| `Publisher` / `PublishError` | `publisher/base_publisher.py` | Publisher interface and the failure value type |
| `HydroServerPublisher` | `publisher/hydroserver/hydroserver_publisher.py` | Validates the payload, resolves the datastream (cached), uploads through `hydroserverpy`, classifies errors |
| `Observation` | `publisher/hydroserver/models.py` | Pydantic schema for incoming payloads |
| `FailedObservationStore` | `database/failed_observation_store.py` | SQLite CRUD for failed observations |
| `FailedObservation` | `database/model.py` | Row dataclass |
| `RetryWorker` | `publisher/hydroserver/retry_worker.py` | Periodically re-uploads cached observations in per-topic batches |

## Threading model

| Thread | Started by | Runs | Lifetime |
|---|---|---|---|
| `MainThread` | Python | `MQTTConsumer.connect()` → `client.loop_forever()` (network I/O and paho callbacks) | Until the broker loop exits or raises |
| `message_router` | `main.py` (daemon) | `MessageRouter.route_incoming_message()`, a blocking `taskqueue.get()` loop | Process lifetime |
| `retry_worker` | `main.py` (daemon) | `RetryWorker.run()`, which does a retry pass and then `Event.wait(retry_interval)` | Until `stop()` sets the event |

Paho callbacks run on the network loop thread. Doing HTTP work in `on_message` would stall keepalives and delay other messages, so the callback only enqueues (see [ADR-0001](adr/0001-decouple-mqtt-consumer-with-queue.md)). The router and the retry worker both call the same `HydroServerPublisher` and both open their own SQLite connections per operation.

On shutdown, the `finally` block in `main.py` stops the MQTT client, signals the retry worker through its `threading.Event`, and joins it for up to 10 seconds. The router thread is a daemon and is not joined.

## Life of an observation

1. A datalogger publishes JSON to the broker, e.g. on `uwrl/site-1/temperature`.
2. `MQTTConsumer.on_message` decodes the bytes as UTF-8 (the message is dropped if that fails) and puts `(topic, payload)` on `taskqueue`.
3. `MessageRouter` dequeues the message. Topics that don't end in `temperature` are ignored. Invalid JSON is logged and dropped.
4. `HydroServerPublisher.push_observation_to_upstream` validates the payload with Pydantic, resolves the datastream (memoised), and calls `datastream.load_observations(...)` with a one-row DataFrame.
5. The publisher returns `None` on success or a `PublishError`. If `cache_data` is `True`, the router writes the original payload, the topic and the error details to SQLite. Otherwise the observation is dropped with a log line.
6. Every `retry_interval` seconds, `RetryWorker` reads all cached rows, skips any with `retry_count >= max_retry_attempt`, groups the rest by topic, and calls `batch_upload(chunk)` for each group.
7. If a batch succeeds, its rows are deleted. If it fails, each row's `retry_count` goes up by one and the latest error is recorded.

The same flow is drawn in [flowchart.md](flowchart.md) and [sequencediagram.md](sequencediagram.md).

## Failure model

| Failure | Where handled | Outcome |
|---|---|---|
| Broker unreachable at startup | `MQTTConsumer.connect` | Logged and re-raised; `main` shuts down |
| Non-UTF-8 payload | `on_message` | Logged, dropped |
| Invalid JSON | `MessageRouter` | Logged, dropped |
| Schema violation (bad UUID, non-numeric result, bad time, missing field) | `HydroServerPublisher` | `PublishError(cache_data=False)`, dropped |
| Network error, timeout, connection refused (`RequestException`) | `HydroServerPublisher` | Cached for retry |
| HTTP 429 Too Many Requests | `HydroServerPublisher` | Intended to be cached for retry (see [known issues](known-issues.md#1-http-429-is-never-actually-cached)) |
| Other HTTP errors (401, 403, 404, 5xx) | `HydroServerPublisher` | Dropped |
| Cached observation fails `max_retry_attempt` times | `RetryWorker` | Skipped on later passes; the row stays in SQLite |

## SQLite schema

```sql
CREATE TABLE IF NOT EXISTS failed_observation (
    id            INTEGER PRIMARY KEY,
    observation   TEXT NOT NULL,          -- original JSON payload
    topic         TEXT NOT NULL,
    error_type    TEXT,                   -- exception class name
    error_message TEXT,
    status_code   INTEGER,                -- 0 when there was no HTTP response
    retry_count   INTEGER NOT NULL DEFAULT 0,
    last_retry    TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

The database runs in WAL journal mode.

## Deployment

- A single process, packaged as a `python:3.11-alpine` image running as a non-root `bridge` user.
- `docker-compose.yml` passes configuration as environment variables and mounts `./data` for the SQLite file.
- The service is stateless apart from the SQLite cache and the in-memory datastream cache, which is rebuilt on demand.
