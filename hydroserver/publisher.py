# pylint: disable=too-few-public-methods
import os
import requests
from hydroserverpy import HydroServer

from dotenv import load_dotenv
import pandas as pd

load_dotenv()


class HydroServerPublisher:
    """Class for publishing subscribed information to HydroServer"""

    HYDROSERVER_URL = os.getenv("HYDROSERVER_URL")
    EMAIL = os.getenv("HYDROSEVER_USER")
    PASSWORD = os.getenv("HYDROSEVER_PASSWORD")
    # API_KEY = ""
    # # API_KEY = "123"

    def __init__(self):
        self.payload = None
        self.hydroserver = HydroServer(
            host=self.HYDROSERVER_URL, email=self.EMAIL, password=self.PASSWORD
        )

    def post_observation_to_hydroserver(self, payload):

        # test_payload
        datastream_uuid = "019f246b-c5b9-7b45-aac6-261adc526b55"

        # need a class to validate payload
        payload["Datastream"]["@iot.id"] = datastream_uuid
        print(payload)

        try:
            datastream = self.hydroserver.datastreams.get(uid=datastream_uuid)
            observation = pd.DataFrame(
                {
                    "phenomenon_time": [payload["phenomenonTime"]],
                    "result": [payload["result"]],
                }
            )
            print(datastream.load_observations(observation))
        except requests.exceptions.HTTPError as e:
            print(e)
