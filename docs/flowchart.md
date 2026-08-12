```mermaid
flowchart TD
    MAYFLY["Mayfly Datalogger"]
    UNO["Arduino Uno"]
    CR350["CR350"]

    WRAPPER["HydroServerArduinoClient"]
    CR350_BUILTIN["Built-in CR350 Interface"]

    MQTT[("MQTT Broker")]
    BRIDGE["HSMQTTBridge"]
    HYDRO["HydroServer"]
    DB[("Cache Database")]
    WORKER["Retry <br/>Every 30 min"]

    MAYFLY --> WRAPPER
    UNO -->WRAPPER

    WRAPPER -->|Publish observation| MQTT

    CR350 -->CR350_BUILTIN
    CR350_BUILTIN -->|Publish observation| MQTT

    BRIDGE -->|Subscribe to topics| MQTT
    BRIDGE -->|Publish observation| HYDRO

    HYDRO -->|Status code 200| DONE([Published])
    HYDRO -->|Status code != 200| CACHE([Store payload<br/>marked as pending])
    CACHE --> DB

    DB --> WORKER
    WORKER -->|Retry publish| HYDRO

    HYDRO -->|Retry success| COMPLETE["Mark payload status as posted.<br/>Remove from Cache"]
    COMPLETE -.-> DB

    %% Devices
    style MAYFLY fill:#1565C0,stroke:#42A5F5,color:#FFFFFF
    style UNO fill:#1565C0,stroke:#42A5F5,color:#FFFFFF
    style CR350 fill:#1565C0,stroke:#42A5F5,color:#FFFFFF

    %% Communication interfaces
    style WRAPPER fill:#00838F,stroke:#4DD0E1,color:#FFFFFF
    style CR350_BUILTIN fill:#00838F,stroke:#4DD0E1,color:#FFFFFF

    %% Core system
    style MQTT fill:#1565C0,stroke:#42A5F5,color:#FFFFFF
    style BRIDGE fill:#1565C0,stroke:#42A5F5,color:#FFFFFF
    style HYDRO fill:#1565C0,stroke:#42A5F5,color:#FFFFFF
    style CACHE fill:#1565C0,stroke:#42A5F5,color:#FFFFFF

    %% Persistence / retry
    style DB fill:#6D4C41,stroke:#A1887F,color:#FFFFFF,stroke-width:2px
    style WORKER fill:#6A1B9A,stroke:#AB47BC,color:#FFFFFF

    %% Success
    style DONE fill:#2E7D32,stroke:#66BB6A,color:#FFFFFF
    style COMPLETE fill:#2E7D32,stroke:#66BB6A,color:#FFFFFF```
