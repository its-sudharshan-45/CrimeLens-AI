from enum import Enum

class InvestigationStatus(str, Enum):
    OPEN = "OPEN"
    UNDER_INVESTIGATION = "UNDER_INVESTIGATION"
    WAITING_FOR_EVIDENCE = "WAITING_FOR_EVIDENCE"
    ON_HOLD = "ON_HOLD"
    CLOSED = "CLOSED"
    ARCHIVED = "ARCHIVED"
