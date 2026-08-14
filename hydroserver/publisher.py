# pylint: disable=too-few-public-methods
from uuid import UUID
from datetime import datetime
import requests
from hydroserverpy import HydroServer

from pydantic import BaseModel, Field, ValidationError

from dotenv import load_dotenv
import pandas as pd

load_dotenv()


class Datastream(BaseModel):
    """Represents a datastream identifier"""

    datastream_id: UUID = Field(alias="@iot.id")


class Observation(BaseModel):
    """Represents a observation payload"""

    result: float
    phenomenonTime: datetime
    Datastream: Datastream


class HydroServerPublisher:
    """Class for publishing subscribed information to HydroServer"""

    def __init__(self, url, api_key):
        self.hydroserver = HydroServer(host=url, apikey=api_key)
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
            print(error.errors(include_url=False, include_input=False))
            return

        datastream_uuid = payload.Datastream.datastream_id

        try:
            datastream = self.__get_datastream(datastream_uuid)
        except requests.exceptions.HTTPError as e:
            # the exception can be cause for either incorrect datastream id or incorrect auth
            print(f"Request failed: {e}")
            return

        try:
            observation = pd.DataFrame(
                {
                    "phenomenon_time": [payload.phenomenonTime],
                    "result": [payload.result],
                }
            )
            # none response of load_observations means successful POST
            datastream.load_observations(observation)
        # the exceptions here would be for duplicate timestamp reposting
        except requests.exceptions.HTTPError as e:
            print(e)
