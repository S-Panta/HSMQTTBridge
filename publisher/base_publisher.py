from abc import ABC, abstractmethod
from typing import NamedTuple


class PublishError(NamedTuple):
    """Represents exception occurred while publishing."""

    cache_data: bool
    error_type: str
    error_message: str
    status_code: int

    @classmethod
    def handle_exception(cls, error, cache_data=True):
        response = getattr(error, "response", None)

        status_code = response.status_code if response is not None else 0

        return cls(
            cache_data=cache_data,
            error_type=type(error).__name__,
            error_message=str(error),
            status_code=status_code,
        )


class Publisher(ABC):
    """Base class for all publishers."""

    @abstractmethod
    def push_observation_to_upstream(self, payload) -> PublishError | None:
        """Publish data and return an error if publishing fails."""
        raise NotImplementedError
