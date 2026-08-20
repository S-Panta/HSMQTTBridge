# pylint: disable=redefined-outer-name,protected-access
from uuid import UUID
from unittest.mock import patch, MagicMock
from datetime import datetime
import requests
import pytest
from pydantic import ValidationError

from publisher.hydroserver.hydroserver_publisher import (
    HydroServerPublisher,
    PublishError,
)


@pytest.fixture
def hydroserver_publisher():
    with patch("publisher.hydroserver.hydroserver_publisher.HydroServer"):
        yield HydroServerPublisher(
            "https://test.hydroserver.com",
            "test-api-key",
        )


@pytest.fixture
def observation_payload():
    return {
        "Datastream": {"@iot.id": "019eae3f-3450-70db-b5d2-a55879b4d683"},
        "result": 32.1,
        "phenomenonTime": "2026-08-06T17:43:34Z",
    }


def test_validate_observation_valid_payload(hydroserver_publisher, observation_payload):
    result = hydroserver_publisher._HydroServerPublisher__validate_observation(
        observation_payload
    )
    assert result is not None
    assert result.result == observation_payload["result"]
    expected_time = datetime.fromisoformat(
        observation_payload["phenomenonTime"].replace("Z", "+00:00")
    )
    assert result.phenomenonTime == expected_time
    assert result.Datastream.datastream_id == UUID(
        observation_payload["Datastream"]["@iot.id"]
    )


@pytest.mark.parametrize("invalid_datastream_id", ["123", ""])
def test_validate_observation_invalid_datastream_id(
    hydroserver_publisher, observation_payload, invalid_datastream_id
):
    observation_payload["Datastream"]["@iot.id"] = invalid_datastream_id

    with pytest.raises(ValidationError) as excinfo:
        hydroserver_publisher._HydroServerPublisher__validate_observation(
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
    hydroserver_publisher, observation_payload, missing_field
):
    observation_payload.pop(missing_field)

    with pytest.raises(ValidationError) as excinfo:
        hydroserver_publisher._HydroServerPublisher__validate_observation(
            observation_payload
        )

    error = excinfo.value.errors()[0]
    assert error["type"] == "missing"
    assert error["msg"] == "Field required"
    assert error["loc"] == (missing_field,)


def test_validate_observation__result_is_not_float(
    hydroserver_publisher, observation_payload
):
    observation_payload["result"] = "randomstring"
    with pytest.raises(ValidationError) as excinfo:
        hydroserver_publisher._HydroServerPublisher__validate_observation(
            observation_payload
        )
    error = excinfo.value.errors(include_url=False, include_input=False)[0]
    assert error["type"] == "float_parsing"
    assert error["loc"] == ("result",)


def test_validate_observation__phenomenontime_is_not_valid(
    hydroserver_publisher, observation_payload
):
    observation_payload["phenomenonTime"] = "not-a-valid-datetime"
    with pytest.raises(ValidationError) as excinfo:
        hydroserver_publisher._HydroServerPublisher__validate_observation(
            observation_payload
        )
    error = excinfo.value.errors(include_url=False, include_input=False)[0]
    assert error["type"] == "datetime_from_date_parsing"
    assert error["loc"] == ("phenomenonTime",)


def test_get_datastream_nonexistent_datastream(hydroserver_publisher):
    datastream_uuid = UUID("12345678-1234-5678-1234-567812345678")

    error = requests.exceptions.HTTPError("Datastream not found")
    hydroserver_publisher.hydroserver.datastreams.get.side_effect = error

    with pytest.raises(requests.exceptions.HTTPError):
        hydroserver_publisher._HydroServerPublisher__get_datastream(datastream_uuid)
    assert datastream_uuid not in hydroserver_publisher.datastreams


def test_get_datastream_reuses_existing_datastream_from_cache(hydroserver_publisher):
    datastream_uuid = UUID("12345678-1234-5678-1234-567812345678")
    assert len(hydroserver_publisher.datastreams) == 0
    for _ in range(3):
        hydroserver_publisher._HydroServerPublisher__get_datastream(datastream_uuid)
    assert len(hydroserver_publisher.datastreams) == 1
    hydroserver_publisher.hydroserver.datastreams.get.assert_called_once_with(
        datastream_uuid
    )


def test_get_datastream_multiple_hydroserver_request_for_different_datastream(
    hydroserver_publisher,
):
    test_temperature_uuid = UUID("12345678-1234-5678-1234-567812345678")
    test_ph_uuid = UUID("12345678-1234-5678-1234-567812345670")
    with patch.object(
        hydroserver_publisher.hydroserver.datastreams,
        "get",
    ) as mock_hydroserver_get_datastream_from_hydroserver:
        hydroserver_publisher._HydroServerPublisher__get_datastream(
            test_temperature_uuid
        )
        hydroserver_publisher._HydroServerPublisher__get_datastream(test_ph_uuid)

        assert len(hydroserver_publisher.datastreams) == 2
    assert mock_hydroserver_get_datastream_from_hydroserver.call_count == 2


def test_post_observation_to_hydroserver(observation_payload, hydroserver_publisher):
    datastream = hydroserver_publisher.hydroserver.datastreams.get.return_value

    result = hydroserver_publisher.push_observation_to_upstream(observation_payload)
    assert result is None
    datastream.load_observations.assert_called_once()


def test_invalid_observation_is_not_cached(observation_payload, hydroserver_publisher):
    observation_payload["phenomenonTime"] = "not-a-valid-datetime"
    result = hydroserver_publisher.push_observation_to_upstream(observation_payload)
    assert isinstance(result, PublishError)
    assert result.status_code == 0
    assert result.error_type == "ValidationError"
    assert result.cache_data is False


@pytest.mark.parametrize(
    "status_code,cache_data",
    [
        (429, True),
        (401, False),
        (404, False),
    ],
)
def test_valid_observation_for_all_http_errors(
    observation_payload, hydroserver_publisher, status_code, cache_data
):

    response = MagicMock()
    response.status_code = status_code
    http_error = requests.exceptions.HTTPError()
    http_error.response = response
    datastream = hydroserver_publisher.hydroserver.datastreams.get.return_value

    datastream.load_observations.side_effect = http_error
    with patch.object(
        hydroserver_publisher,
        "_HydroServerPublisher__get_datastream",
        return_value=datastream,
    ):
        result = hydroserver_publisher.push_observation_to_upstream(observation_payload)
    assert result.error_type == "HTTPError"
    assert result.cache_data is cache_data


def test_post_observation_caches_observation_on_request_exception(
    observation_payload, hydroserver_publisher
):
    response = MagicMock()
    response.status_code = 0
    error = requests.exceptions.RequestException()
    error.response = response
    datastream = hydroserver_publisher.hydroserver.datastreams.get.return_value
    datastream.load_observations.side_effect = error
    with patch.object(
        hydroserver_publisher,
        "_HydroServerPublisher__get_datastream",
        return_value=datastream,
    ):
        result = hydroserver_publisher.push_observation_to_upstream(observation_payload)
    assert result.error_type == "RequestException"
    assert result.cache_data is True


def test_post_observation_datastream_not_found_in_hydroserver(
    observation_payload, hydroserver_publisher
):
    response = MagicMock()
    response.status_code = 404
    http_error = requests.exceptions.HTTPError(
        "404 Client Error: Datastream does not exist"
    )
    http_error.response = response
    hydroserver_publisher.hydroserver.datastreams.get.side_effect = http_error
    result = hydroserver_publisher.push_observation_to_upstream(observation_payload)
    assert result.error_type == "HTTPError"
    assert result.cache_data is False


def test_post_observation_reuses_cached_datastream_for_same_datastream(
    observation_payload, hydroserver_publisher
):
    hydroserver_publisher.push_observation_to_upstream(observation_payload)
    hydroserver_publisher.push_observation_to_upstream(observation_payload)
    hydroserver_publisher.hydroserver.datastreams.get.assert_called_once()
    assert len(hydroserver_publisher.datastreams) == 1
