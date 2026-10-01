import logging
import requests
from hydroserverpy import HydroServer

import pandas as pd
from pydantic import ValidationError

from publisher.base_publisher import Publisher, PublishFailure
from publisher.hydroserver.models import Observation

logger = logging.getLogger(__name__)


class HydroServerPublisher(Publisher):
    """Class for publishing subscribed information to HydroServer"""

    def __init__(self, base_url, api_key):
        self.hydroserver = HydroServer(host=base_url, apikey=api_key)
        # This is for storing the datastreams
        self.datastreams = {}
        logger.info(
            "HydroServer publisher host=%s initialized",
            base_url,
        )

    def _validate_observation(self, payload):
        return Observation.model_validate(payload)

    def _get_datastream(self, datastream_uuid):
        datastream = self.datastreams.get(datastream_uuid)
        if datastream is not None:
            logger.info(
                "Using datastream object stored locally for datastream_id = %s",
                datastream_uuid,
            )
            return datastream
        datastream = self.hydroserver.datastreams.get(datastream_uuid)

        self.datastreams[datastream_uuid] = datastream
        return datastream

    def _load_observation(self, datastream_uuid, observations):
        try:
            datastream = self._get_datastream(datastream_uuid)
            datastream.load_observations(observations)
        except requests.exceptions.HTTPError as http_error:
            # not all HTTPError response should be retried.
            # A status code of 409 means the payload exists in the Hydroserver.
            # Only cache when status code matches retry_status_code
            status_code = http_error.response.status_code
            retry_status_code = [408, 429, 449, 500, 502, 503, 504]
            should_retry = False
            if status_code in retry_status_code:
                should_retry = True

            logger.error(
                "HTTP error occurred "
                "datastream_id = %s status_code = %s should retry = %s error = %s",
                datastream_uuid,
                status_code,
                should_retry,
                http_error,
            )
            return PublishFailure.from_exception(http_error, should_retry)

        except requests.exceptions.RequestException as error:
            logger.debug(
                "Connection request failed error_type = %s error = %s",
                type(error).__name__,
                error,
            )
            # Retry every connection request exception
            return PublishFailure.from_exception(error)
        return None

    def push_observation_to_upstream(self, payload):
        try:
            payload = self._validate_observation(payload)
        except ValidationError as error:
            # if incoming payload is not correct, it make no sense to either post or store in cache
            # to do: log this in future
            # print(error.errors(include_url=False, include_input=False))
            logger.warning(
                "Invalid observation: %s",
                error.errors(include_url=False, include_input=False),
            )

            return PublishFailure.from_exception(error, should_retry=False)

        datastream_uuid = str(payload.Datastream.datastream_id)
        observation = pd.DataFrame(
            {
                "phenomenon_time": [payload.phenomenonTime],
                "result": [payload.result],
            }
        )
        return self._load_observation(datastream_uuid, observation)

    def batch_upload(self, chunked_payload):
        """This operation is for retry worker
        HTTP 404 and other invalid payload error are thrown out in earlier process.
        Therefore parsing is not necessary again.
        """
        if not chunked_payload:
            logger.warning("Payload chunk is empty")
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
        return self._load_observation(datastream_id, observations)
