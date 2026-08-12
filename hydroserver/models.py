# pylint: disable=too-few-public-methods
from uuid import UUID
from pydantic import BaseModel, Field, ValidationError


class Datastream(BaseModel):
    """Represents a datastream identifier"""

    datastream_id: UUID = Field(alias="@iot.id")


class Observation(BaseModel):
    """Represents a observation payload"""

    result: float
    phenomenonTime: str
    Datastream: Datastream
