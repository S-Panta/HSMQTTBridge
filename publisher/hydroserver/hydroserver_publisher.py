import requests
from hydroserverpy import HydroServer

import pandas as pd
from pydantic import ValidationError

from publisher.base_publisher import Publisher, PublishError
from publisher.hydroserver.models import Observation


class HydroServerPublisher(Publisher):
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

    def __load_observation(self, datastream_uuid, observations):
        try:
            datastream = self.__get_datastream(datastream_uuid)
            datastream.load_observations(observations)

        except requests.exceptions.HTTPError as http_error:
            print("http error occurred")
            # print(http_error)
            status_code = (
                http_error.response.status_code if http_error.response else None
            )
            # not all HTTPError response should be retried
            cache_data = status_code == 429
            return PublishError.handle_exception(
                cache_data=cache_data, error=http_error
            )

        except requests.exceptions.RequestException as error:
            print("request exception")
            return PublishError.handle_exception(cache_data=True, error=error)
        return None

    def push_observation_to_upstream(self, payload):
        try:
            payload = self.__validate_observation(payload)
        except ValidationError as error:
            # if incoming payload is not correct, it make no sense to either post or store in cache
            # to do: log this in future
            # print(error.errors(include_url=False, include_input=False))
            return PublishError.handle_exception(
                cache_data=False,
                error=error,
            )

        datastream_uuid = str(payload.Datastream.datastream_id)
        observation = pd.DataFrame(
            {
                "phenomenon_time": [payload.phenomenonTime],
                "result": [payload.result],
            }
        )
        return self.__load_observation(datastream_uuid, observation)

    def batch_upload(self, chunked_payload):
        """This operation is for retry worker
        HTTP 404 and other error data are thrown out in earlier process.
        Thus,parsing and getting getdatastream error verification is not needed
        """
        datastream_id = chunked_payload[0].observation["Datastream"]["@iot.id"]
        observations = pd.DataFrame(
            [
                {
                    "phenomenon_time": obs.observation["phenomenonTime"],
                    "result": obs.observation["result"],
                }
                for obs in chunked_payload
            ]
        )
        return self.__load_observation(datastream_id, observations)
