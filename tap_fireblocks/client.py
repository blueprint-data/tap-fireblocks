"""Base REST stream for the Fireblocks API."""

from __future__ import annotations

from datetime import datetime, timezone
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

        For incremental streams (e.g. transactions), also passes the stored
        bookmark as the ``after`` filter so the API only returns records
        created after the last sync — avoiding an ever-growing full fetch.
        """
        params: dict = {}
        if next_page_token and next_page_token.startswith("http"):
            parsed = urlparse(next_page_token)
            qs = parse_qs(parsed.query)
            # parse_qs returns lists; flatten to single values
            params = {k: v[0] for k, v in qs.items()}

        # Pass the last-seen replication value to the API as a filter.
        # Falls back to start_date config on the very first run; skips the
        # parameter entirely when neither a bookmark nor start_date exists.
        if self.replication_key is not None:
            start_value = self.get_starting_replication_key_value(context)
            if start_value is not None:
                if isinstance(start_value, (int, float)):
                    params["after"] = str(int(start_value))
                else:
                    # Parse ISO datetime string (from start_date config).
                    dt = datetime.fromisoformat(
                        str(start_value).replace("Z", "+00:00"),
                    )
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    params["after"] = str(int(dt.timestamp() * 1000))

        return params
