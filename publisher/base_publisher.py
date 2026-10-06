from abc import ABC, abstractmethod
from typing import NamedTuple


class PublishFailure(NamedTuple):
    """Represents an error occurred when a publish attempt failed."""

    should_retry: bool
    error_type: str
    error_message: str
    status_code: int

    @classmethod
    def from_exception(cls, error, should_retry=True):
        response = getattr(error, "response", None)

        status_code = response.status_code if response is not None else 0

        return cls(
            should_retry=should_retry,
            error_type=type(error).__name__,
            error_message=str(error),
            status_code=status_code,
        )


class Publisher(ABC):
    """Base class for all publishers."""

    @abstractmethod
    def post_observation(self, payload) -> PublishFailure | None:
        """Publish data and return an error if publishing fails."""
        raise NotImplementedError
