# pylint: disable=redefined-outer-name,protected-access
from uuid import UUID
from unittest.mock import patch, MagicMock
from datetime import datetime
import requests
import pytest
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


def test_validate_observation__phenomenontime_is_not_valid(
    hydroserverpublisher, observation_payload
):
    observation_payload["phenomenonTime"] = "not-a-valid-datetime"
    with pytest.raises(ValidationError) as excinfo:
        hydroserverpublisher._HydroServerPublisher__validate_observation(
            observation_payload
        )
    error = excinfo.value.errors(include_url=False, include_input=False)[0]
    assert error["type"] == "datetime_from_date_parsing"
    assert error["loc"] == ("phenomenonTime",)


def test_get_datastream_nonexistent_datastream(hydroserverpublisher):
    datastream_uuid = UUID("12345678-1234-5678-1234-567812345678")
    with patch.object(
        hydroserverpublisher.hydroserver.datastreams,
        "get",
        side_effect=requests.exceptions.HTTPError("Datastream not found"),
    ):

        with pytest.raises(requests.exceptions.HTTPError):
            hydroserverpublisher._HydroServerPublisher__get_datastream(datastream_uuid)
    assert datastream_uuid not in hydroserverpublisher.datastreams


def test_get_datastream_reuses_existing_datastream_from_cache(hydroserverpublisher):
    datastream_uuid = UUID("12345678-1234-5678-1234-567812345678")
    # this repesent a datastream object returned by hydroserver
    datastream = MagicMock()
    with patch.object(
        hydroserverpublisher.hydroserver.datastreams, "get", return_value=datastream
    ) as mock_hydroserver_get_datastream:
        assert len(hydroserverpublisher.datastreams) == 0
        for _ in range(3):
            hydroserverpublisher._HydroServerPublisher__get_datastream(datastream_uuid)
        assert len(hydroserverpublisher.datastreams) == 1
        mock_hydroserver_get_datastream.assert_called_once_with(datastream_uuid)


def test_get_datastream_multiple_hydroserver_request_for_different_datastream(
    hydroserverpublisher,
):
    test_temperature_uuid = UUID("12345678-1234-5678-1234-567812345678")
    temperature_datastream = MagicMock()
    temperature_datastream.id = test_temperature_uuid

    ph_datastream = MagicMock()
    test_ph_uuid = UUID("12345678-1234-5678-1234-567812345670")
    ph_datastream.id = test_ph_uuid
    with patch.object(
        hydroserverpublisher.hydroserver.datastreams,
        "get",
        side_effect=[temperature_datastream, ph_datastream],
    ) as mock_hydroserver_get_datastream:
        hydroserverpublisher._HydroServerPublisher__get_datastream(
            test_temperature_uuid
        )
        hydroserverpublisher._HydroServerPublisher__get_datastream(test_ph_uuid)

        assert len(hydroserverpublisher.datastreams) == 2
    assert mock_hydroserver_get_datastream.call_count == 2


def test_post_observation_to_hydroserver(observation_payload, hydroserverpublisher):
    datastream = MagicMock()
    with patch.object(
        hydroserverpublisher,
        "_HydroServerPublisher__get_datastream",
        return_value=datastream,
    ):
        result = hydroserverpublisher.post_observation_to_hydroserver(
            observation_payload
        )
    assert result is None
    datastream.load_observations.assert_called_once()
