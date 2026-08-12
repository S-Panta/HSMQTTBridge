from unittest.mock import patch
import pytest

from hydroserver.publisher import HydroServerPublisher

# @pytest.fixture

# # def mock_hydroserver():


@pytest.fixture
def valid_payload():
    return {
        "Datastream": {"@iot.id": "019eae3f-3450-70db-b5d2-a55879b4d681"},
        "result": 32.1,
        "phenomenonTime": "2026-08-06T17:43:34Z",
    }


@pytest.fixture
def invalid_payload():
    return {
        "Datastream": {"@iot.id": "019eae3f-3450-70db-b5d2-a55879b4d681"},
        "phenomenonTime": "2026-08-06T17:43:34Z",
    }


def test_validate_observation_correct_payload(valid_payload):
    with patch("hydroserver.publisher.HydroServer"):
        hydroserverpublisher = HydroServerPublisher()

        result = hydroserverpublisher._HydroServerPublisher__validate_observation(
            valid_payload
        )

        assert result is not None


def test_validate_observation_payload_mismatch(invalid_payload):
    with patch("hydroserver.publisher.HydroServer"):
        hydroserverpublisher = HydroServerPublisher()

        result = hydroserverpublisher._HydroServerPublisher__validate_observation(
            invalid_payload
        )

        assert result is None


def test_validate_observation_wrong_datastream_id():
    with patch("hydroserver.publisher.HydroServer"):
        hydroserverpublisher = HydroServerPublisher()
        invalid_payload = {
            "Datastream": {"@iot.id": "123"},
            "result": 32.1,
            "phenomenonTime": "2026-08-06T17:43:34Z",
        }
        result = hydroserverpublisher._HydroServerPublisher__validate_observation(
            invalid_payload
        )
        print(result)
