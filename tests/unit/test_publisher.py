from unittest.mock import patch
import requests

import pytest
from uuid import UUID
from pydantic import ValidationError

from hydroserver.publisher import HydroServerPublisher


@pytest.fixture
def hydroserverpublisher():
    with patch("hydroserver.publisher.HydroServer"):
        yield HydroServerPublisher(
            "https://test.hydroserver.com",
            "test-api-key",
        )


@pytest.fixture
def observation_payload():
    return {
        "Datastream": {"@iot.id": "019eae3f-3450-70db-b5d2-a55879b4d681"},
        "result": 32.1,
        "phenomenonTime": "2026-08-06T17:43:34Z",
    }


def test_validate_observation_valid_payload(hydroserverpublisher, observation_payload):
    result = hydroserverpublisher._HydroServerPublisher__validate_observation(
        observation_payload
    )

    assert result is not None
    assert result.result == 32.1
    assert result.phenomenonTime == "2026-08-06T17:43:34Z"
    assert result.Datastream.datastream_id == UUID(
        "019eae3f-3450-70db-b5d2-a55879b4d681"
    )


@pytest.mark.parametrize("invalid_datastream_id", ["123", ""])
def test_validate_observation_invalid_datastream_id(
    hydroserverpublisher, observation_payload, invalid_datastream_id
):
    observation_payload["Datastream"]["@iot.id"] = invalid_datastream_id

    with pytest.raises(ValidationError) as excinfo:
        hydroserverpublisher._HydroServerPublisher__validate_observation(
            observation_payload
        )
    error = excinfo.value.errors(include_url=False, include_input=False)[0]
    assert error["type"] == "uuid_parsing"
    assert error["loc"] == ("Datastream", "@iot.id")


@pytest.mark.parametrize(
    "missing_field",
    [
        "Datastream",
        "result",
        "phenomenonTime",
    ],
)
def test_validate_observation_missing_required_field(
    hydroserverpublisher, observation_payload, missing_field
):
    observation_payload.pop(missing_field)

    with pytest.raises(ValidationError) as excinfo:
        hydroserverpublisher._HydroServerPublisher__validate_observation(
            observation_payload
        )

    error = excinfo.value.errors()[0]
    assert error["type"] == "missing"
    assert error["msg"] == "Field required"
    assert error["loc"] == (missing_field,)


def test_validate_observation__result_is_not_float(
    hydroserverpublisher, observation_payload
):
    observation_payload["result"] = "randomstring"
    with pytest.raises(ValidationError) as excinfo:
        hydroserverpublisher._HydroServerPublisher__validate_observation(
            observation_payload
        )
    error = excinfo.value.errors(include_url=False, include_input=False)[0]
    assert error["type"] == "float_parsing"
    assert error["loc"] == ("result",)


def test_validate_observation__phenomenontime_is_not_string(
    hydroserverpublisher, observation_payload
):
    observation_payload["phenomenonTime"] = 2025
    with pytest.raises(ValidationError) as excinfo:
        hydroserverpublisher._HydroServerPublisher__validate_observation(
            observation_payload
        )
    error = excinfo.value.errors(include_url=False, include_input=False)[0]
    assert error["type"] == "string_type"
    assert error["msg"] == "Input should be a valid string"
    assert error["loc"] == ("phenomenonTime",)


def test_get_datastream_nonexistent_datastream(hydroserverpublisher):
    datastream_uuid = UUID("12345678-1234-5678-1234-567812345678")
    side_effect = requests.exceptions.HTTPError("404 Client Error: Not Found")
    with patch.object(
        hydroserverpublisher.hydroserver.datastreams,
        "get",
        side_effect=requests.exceptions.HTTPError("Datastream not found"),
    ) as mock_get:

        with pytest.raises(requests.exceptions.HTTPError):
            hydroserverpublisher._HydroServerPublisher__get_datastream(datastream_uuid)
    assert datastream_uuid not in hydroserverpublisher.datastreams
