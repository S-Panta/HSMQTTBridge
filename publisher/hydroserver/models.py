from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field


class Datastream(BaseModel):
    """Represents a datastream identifier"""

    datastream_id: UUID = Field(alias="@iot.id")


class Observation(BaseModel):
    """Represents a observation payload"""

    result: float
    phenomenonTime: datetime
    Datastream: Datastream
