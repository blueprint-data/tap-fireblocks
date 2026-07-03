"""Fireblocks Singer tap."""

from __future__ import annotations

from singer_sdk import Tap
from singer_sdk import typing as th

from tap_fireblocks.streams import (
    ExchangeAccountsStream,
    NetworkConnectionsStream,
    TransactionsStream,
    VaultAccountsStream,
    VaultAssetsStream,
)


class TapFireblocks(Tap):
    """Singer tap for the Fireblocks API."""

    name = "tap-fireblocks"

    config_jsonschema = th.PropertiesList(
        th.Property("api_key", th.StringType, required=True, secret=True),
        th.Property("secret_key", th.StringType, secret=True),
        th.Property("base_url", th.StringType),
        th.Property("start_date", th.DateType),
    ).to_dict()

    def discover_streams(self) -> list:
        return [
            TransactionsStream(self),
            VaultAccountsStream(self),
            VaultAssetsStream(self),
            NetworkConnectionsStream(self),
            ExchangeAccountsStream(self),
        ]


if __name__ == "__main__":
    TapFireblocks.cli()
