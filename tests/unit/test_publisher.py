from unittest.mock import patch
import pytest
from uuid import UUID

from hydroserver.publisher import HydroServerPublisher


def test_validate_observation_correct_payload():
    valid_payload = {
        "Datastream": {"@iot.id": "019eae3f-3450-70db-b5d2-a55879b4d681"},
        "result": 32.1,
        "phenomenonTime": "2026-08-06T17:43:34Z",
    }
    with patch("hydroserver.publisher.HydroServer"):
        hydroserverpublisher = HydroServerPublisher()

        result = hydroserverpublisher._HydroServerPublisher__validate_observation(
            valid_payload
        )

        assert result is not None
        assert result.result == 32.1
        assert result.phenomenonTime == "2026-08-06T17:43:34Z"
        assert result.Datastream.datastream_id == UUID(
            "019eae3f-3450-70db-b5d2-a55879b4d681"
        )


def test_validate_observation_invalid_datastream_id():
    payload_not_datastream_id = {
        "Datastream": {"@iot.id": "123"},
        "result": 32.1,
        "phenomenonTime": "2026-08-06T17:43:34Z",
    }
    with patch("hydroserver.publisher.HydroServer"):
        hydroserverpublisher = HydroServerPublisher()

        result = hydroserverpublisher._HydroServerPublisher__validate_observation(
            payload_not_datastream_id
        )
        assert result is None


@pytest.mark.parametrize(
    "missing_payload_key",
    [
        {
            "result": 32.1,
            "phenomenonTime": "2026-08-06T17:43:34Z",
        },
        {
            "Datastream": {"@iot.id": "019eae3f-3450-70db-b5d2-a55879b4d680"},
            "phenomenonTime": "2026-08-06T17:43:34Z",
        },
        {
            "Datastream": {"@iot.id": "019eae3f-3450-70db-b5d2-a55879b4d680"},
            "result": 32.1,
        },
    ],
)
def test_validate_observation_missing_required_field(missing_payload_key):
    with patch("hydroserver.publisher.HydroServer"):
        hydroserverpublisher = HydroServerPublisher()

        result = hydroserverpublisher._HydroServerPublisher__validate_observation(
            missing_payload_key
        )

        assert result is None
