"""Base REST stream for the Fireblocks API."""

from __future__ import annotations

from urllib.parse import parse_qs, urlparse

from singer_sdk.streams import RESTStream

from tap_fireblocks.auth import FireblocksAuthenticator
from tap_fireblocks.pagination import NextPageHeaderPaginator


class FireblocksStream(RESTStream):
    """Base stream for Fireblocks."""

    @property
    def url_base(self) -> str:
        return self.config.get("base_url", "https://api.fireblocks.io")

    @property
    def authenticator(self) -> FireblocksAuthenticator:
        return FireblocksAuthenticator(self)

    def get_new_paginator(self) -> NextPageHeaderPaginator:
        return NextPageHeaderPaginator()

    def get_url_params(self, context, next_page_token) -> dict:
        """Parse pagination params from the next-page URL.

        Fireblocks returns a full URL in the ``next-page`` response header.
        When present, extract its query parameters so the next request uses
        the correct cursor.
        """
        if next_page_token and next_page_token.startswith("http"):
            parsed = urlparse(next_page_token)
            qs = parse_qs(parsed.query)
            # parse_qs returns lists; flatten to single values
            return {k: v[0] for k, v in qs.items()}
        return {}
