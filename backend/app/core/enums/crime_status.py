from enum import Enum

class CrimeStatus(str, Enum):
    OPEN = "OPEN"
    UNDER_INVESTIGATION = "UNDER_INVESTIGATION"
    CLOSED = "CLOSED"
    ARCHIVED = "ARCHIVED"
