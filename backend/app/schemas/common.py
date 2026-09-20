"""
Common Pydantic schemas shared across multiple API domains.

PaginatedResponse[T]
--------------------
Generic response envelope used by all paginated list endpoints.
Automatically serialised by FastAPI when used as response_model.

paginate(result) helper
-----------------------
Converts a repository PaginatedResult dataclass into a plain dict that
FastAPI can serialise through PaginatedResponse[T].  Items are left as
ORM objects — FastAPI + from_attributes=True handles the final conversion.
"""
from typing import Generic, List, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """
    Standard paginated list response for all collection endpoints.

    Fields
    ------
    items       The current page of results.
    total       Total number of records matching the query (all pages).
    page        Current page number (1-indexed).
    page_size   Maximum results per page.
    total_pages Computed total number of pages.
    has_next    True if there is a subsequent page.
    has_prev    True if there is a preceding page.
    """

    items: List[T]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool

    model_config = ConfigDict(from_attributes=True)


def paginate(result) -> dict:
    """
    Convert a PaginatedResult dataclass (repository layer) into a plain dict
    that FastAPI serialises via PaginatedResponse[T].

    Parameters
    ----------
    result  A PaginatedResult instance returned by any repository get_all().
    """
    return {
        "items": result.items,
        "total": result.total,
        "page": result.page,
        "page_size": result.page_size,
        "total_pages": result.total_pages,
        "has_next": result.has_next,
        "has_prev": result.has_prev,
    }
