from dataclasses import dataclass
from typing import Optional


@dataclass
class PendingObservation:
    """data class for representing observation pending to store in upstream repository"""

    id: int
    observation: str
    topic: str
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    status_code: Optional[str] = None
    retry_count: int = 0
