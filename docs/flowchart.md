```mermaid
%%{init: {
  "flowchart": {
    "nodeSpacing": 50,
    "rankSpacing": 75,
    "padding": 20,
}}%%
flowchart TD
    ARDUINO["Mayfly/ArduinoUno Datalogger"]
    CR350["CR350"]
    MQTT[("MQTT Broker")]
    BRIDGE["HSMQTTBridge"]
    HYDROSERVER["HydroServer Client"]
    DB[("Cache Database")]
    WORKER["Retry <br/>Every 30 min"]

    ARDUINO -->|Publish observation| MQTT
    CR350 -->|Publish observation| MQTT

    BRIDGE -->|Subscribe to topics| MQTT
    BRIDGE -->|Publish observation| HYDROSERVER

    HYDROSERVER -->|Status code 200| DONE([Published to HydroServer])
    HYDROSERVER -->|Status code != 200| CACHE([Store payload<br/>marked as pending])
    CACHE --> DB

    DB --> WORKER
    WORKER -->|Retry publish| HYDROSERVER

    HYDROSERVER -->|Retry success| COMPLETE["Mark payload status as posted.<br/>Remove from Cache"]
    COMPLETE -.-> DB

    style ARDUINO fill:#1565C0,stroke:#42A5F5,color:#FFFFFF
    style CR350 fill:#1565C0,stroke:#42A5F5,color:#FFFFFF

    style MQTT fill:#1565C0,stroke:#42A5F5,color:#FFFFFF
    style BRIDGE fill:#1565C0,stroke:#42A5F5,color:#FFFFFF
    style HYDROSERVER fill:#1565C0,stroke:#42A5F5,color:#FFFFFF
    style CACHE fill:#1565C0,stroke:#42A5F5,color:#FFFFFF

    style DB fill:#6D4C41,stroke:#A1887F,color:#FFFFFF,stroke-width:2px
    style WORKER fill:#6A1B9A,stroke:#AB47BC,color:#FFFFFF

    style DONE fill:#2E7D32,stroke:#66BB6A,color:#FFFFFF
    style COMPLETE fill:#2E7D32,stroke:#66BB6A,color:#FFFFFF```
