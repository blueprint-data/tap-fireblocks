"""Pagination for endpoints that return the next page as a response header."""

from __future__ import annotations

from singer_sdk.pagination import BaseAPIPaginator


class NextPageHeaderPaginator(BaseAPIPaginator[str | None]):
    """Follows the `next-page` response header until it's absent.

    Fireblocks puts the full next-page URL in a header, not in the JSON body,
    so none of singer_sdk's built-in paginators (HATEOAS, offset, JSONPath) fit.
    """

    def __init__(self) -> None:
        super().__init__(None)

    def has_more(self, response) -> bool:
        return self.get_next(response) is not None

    def get_next(self, response) -> str | None:
        return response.headers.get("next-page") or None
