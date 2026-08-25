# HSMQTTBridge
A lightweight Python service to bridge MQTT broker and [HydroServer](https://github.com/hydroserver2/hydroserver),

## How it works

1. **MQTT Consumer** subscribes to a configurable topic filter (e.g. `uwrl/#`) and pushes incoming 
   `(topic, payload)` pairs onto an internal queue.
2. **Message Router** consumes the queue on a background thread, parses each payload as JSON, and 
   routes it based on topic suffix (e.g. topics ending in `temperature`) to the HydroServer publisher.
3. **HydroServer Publisher** pushes parsed observations to HydroServer via its HTTP API.
4. **Failed Observation Store** persists any observation that fails to publish (e.g. HydroServer is 
   down or unreachable) to a local SQLite database instead of dropping it.
5. **Retry Worker** runs on its own background thread, periodically retrying cached failed 
   observations until they're successfully delivered.

## Requirements

- Python 3.x
- A running MQTT broker (e.g. Mosquitto)
- A HydroServer instance and API key

See `requirements.txt` for Python dependencies.

## To run the service

```bash
pip install -r requirements.txt
python main.py
```
