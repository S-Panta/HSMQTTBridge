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

    @classmethod
    def validate_payload(cls, payload):
        try:
            return cls.model_validate(payload)
        except ValidationError as e:
            # # to:do : a error class for proper message format
            for err in e.errors(include_url=False, include_input=False):
                loc = ".".join(str(p) for p in err["loc"])
                print(f"{loc}: {err['msg']}")
            return None
