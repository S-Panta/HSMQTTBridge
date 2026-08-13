# pylint: disable=too-few-public-methods
import os
from .models import Observation
import requests
from hydroserverpy import HydroServer
from pydantic import ValidationError

from dotenv import load_dotenv
import pandas as pd

load_dotenv()


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


class HydroServerPublisher:
    """Class for publishing subscribed information to HydroServer"""

    HYDROSERVER_URL = os.getenv("HYDROSERVER_URL")
    EMAIL = os.getenv("HYDROSERVER_USER")
    PASSWORD = os.getenv("HYDROSERVER_PASSWORD")

    def __init__(self):
        self.hydroserver = HydroServer(
            host=self.HYDROSERVER_URL, email=self.EMAIL, password=self.PASSWORD
        )
        self.datastreams = {}

    def __validate_observation(self, payload):
        try:
            return Observation.model_validate(payload)
        except ValidationError as e:
            # to:do : a error class for proper message format
            print("this is the outputtttttttttttttttttt")
            for err in e.errors(include_url=False, include_input=False):
                loc = ".".join(str(p) for p in err["loc"])
                print(f"{loc}: {err['msg']}")
            return None

    def __get_datastream(self, datastream_uuid):
        datastream = self.datastreams.get(datastream_uuid)

        if datastream is not None:
            return datastream

        try:
            datastream = self.hydroserver.datastreams.get(datastream_uuid)
        except requests.exceptions.HTTPError as e:
            # Only parsed object get here therefore Value Error won't be shown here
            print(e)

        self.datastreams[datastream_uuid] = datastream
        return datastream

    def post_observation_to_hydroserver(self, payload):
        payload = self.__validate_observation(payload)
        if payload is None:
            # do nothing
            # if incoming payload is not correct, it make no sense to either post or store in cache
            # to do: log this in future
            return
        datastream_uuid = payload.Datastream.datastream_id
        datastream = self.__get_datastream(datastream_uuid)

        try:
            observation = pd.DataFrame(
                {
                    "phenomenon_time": [payload.phenomenonTime],
                    "result": [payload.result],
                }
            )
            datastream.load_observations(observation)

        except requests.exceptions.HTTPError as e:
            print(e)


# publisher = HydroServerPublisher()
# invalid_payload = {
#     "Datastream": {"@iot.id": "019eae3f-3450-70db-b5d2-a55879b4d680"},
#     "result": 32.1,
#     "phenomenonTime": "2026-08-06T17:43:34Z",
# }
# valid_payload = {
#     "Datastream": {"@iot.id": "019eae3f-3450-70db-b5d2-a55879b4d681"},
#     "result": 32.1,
#     "phenomenonTime": "2026-08-06T17:43:34Z",
# }
# # print(publisher.post_observation_to_hydroserver(invalid_payload))
# # print("...................................................")
# # print(publisher.post_observation_to_hydroserver(valid_payload))
