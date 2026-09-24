from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Config(BaseSettings):
    """class for storing config"""

    model_config = SettingsConfigDict(
        env_file=".env",
    )

    # hydroserver config
    hydroserver_url: str = Field(default="https://playground.hydroserver.org/")
    workspace_api_key: str

    # # broker config
    mqtt_broker_url: str = Field(default="test.mosquitto.org")
    mqtt_broker_port: int = Field(default=1883)
    mqtt_topic_filter: str = Field(default="#")
    mqtt_client_id: str = Field(default="hsmqttbridge")
    mqtt_keepalive: int = Field(default=60)
    mqtt_username: str | None = None
    mqtt_password: str | None = None

    # database
    db_path: Path

    # logging level
    log_level: str = Field(default="INFO")

    # retry worker
    max_retry_attempt: int = Field(default=10)
    retry_interval: int = Field(default=1800)


config = Config()
