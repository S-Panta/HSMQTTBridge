from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class BufferedObservation:
    """Represents an observation that failed upstream upload."""

    id: int
    observation: dict[str, Any]
    topic: str
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    status_code: Optional[str] = None
    retry_count: int = 0
