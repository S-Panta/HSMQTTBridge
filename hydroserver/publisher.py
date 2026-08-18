# pylint: disable=too-few-public-methods
from uuid import UUID
from datetime import datetime
from typing import NamedTuple
import requests
from hydroserverpy import HydroServer

from pydantic import BaseModel, Field, ValidationError

import pandas as pd


class Datastream(BaseModel):
    """Represents a datastream identifier"""

    datastream_id: UUID = Field(alias="@iot.id")


class Observation(BaseModel):
    """Represents a observation payload"""

    result: float
    phenomenonTime: datetime
    Datastream: Datastream


class PublishObservationError(NamedTuple):
    """Represents an error that occurred while publishing an observation to HydroServer."""

    cache_data: bool
    error_type: str
    error_message: str
    status_code: int

    @classmethod
    def handle_exception(cls, error, cache_data=True):
        response = getattr(error, "response", None)
        if response is None:
            status_code = 0
        else:
            status_code = response.status_code
        return cls(
            cache_data=cache_data,
            error_type=type(error).__name__,
            error_message=str(error),
            status_code=status_code,
        )


class HydroServerPublisher:
    """Class for publishing subscribed information to HydroServer"""

    def __init__(self, base_url, api_key):
        self.hydroserver = HydroServer(host=base_url, apikey=api_key)
        # This is for storing the datastreams
        self.datastreams = {}

    def __validate_observation(self, payload):
        return Observation.model_validate(payload)

    def __get_datastream(self, datastream_uuid):
        datastream = self.datastreams.get(datastream_uuid)
        if datastream is not None:
            return datastream

        datastream = self.hydroserver.datastreams.get(datastream_uuid)
        self.datastreams[datastream_uuid] = datastream
        return datastream

    def post_observation_to_hydroserver(self, payload):
        try:
            payload = self.__validate_observation(payload)
        except ValidationError as error:
            # if incoming payload is not correct, it make no sense to either post or store in cache
            # to do: log this in future
            # print(error.errors(include_url=False, include_input=False))
            return PublishObservationError.handle_exception(
                cache_data=False,
                error=error,
            )

        datastream_uuid = payload.Datastream.datastream_id
        observation = pd.DataFrame(
            {
                "phenomenon_time": [payload.phenomenonTime],
                "result": [payload.result],
            }
        )

        try:
            datastream = self.__get_datastream(datastream_uuid)

            datastream.load_observations(observation)

        except requests.exceptions.HTTPError as http_error:
            print("http error occurred")
            status_code = (
                http_error.response.status_code if http_error.response else None
            )

            # not all HTTPError response should be retried
            cache_data = status_code == 429
            return PublishObservationError.handle_exception(
                cache_data=cache_data, error=http_error
            )

        except requests.exceptions.RequestException as error:
            print("request exception")
            return PublishObservationError.handle_exception(
                cache_data=True, error=error
            )
        return None
