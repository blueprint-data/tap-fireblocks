"""Tests for client.py — FireblocksStream base behavior.

.. note::

   These tests validate **unit-level** behavior of ``get_url_params()``.
   The bookmark/``start_date`` resolution is mocked because the full
   singer-sdk state machine is exercised in the integration tests and at
   runtime.  The SDK's ``_write_starting_replication_value`` converts
   ``start_date`` into a string bookmark (``STARTING_MARKER``) and integer
   replication-key values are stored as raw JSON-safe ints — both paths
   are covered below.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from tap_fireblocks.streams import TransactionsStream, VaultAccountsStream


def _mock_tap(config: dict) -> MagicMock:
    """Return a minimal mock Tap that satisfies Stream.__init__."""
    tap = MagicMock()
    tap.config = config
    tap.logger = MagicMock()
    tap.logger.getChild.return_value = MagicMock()
    return tap


class TestGetUrlParams:
    """Verify get_url_params incremental filtering behavior."""

    def test_incremental_int_bookmark_emits_after(self, mock_config):
        """Integer bookmark (e.g. ms timestamp from previous sync) is
        passed directly as ``after`` without datetime conversion."""
        stream = TransactionsStream(_mock_tap(mock_config))

        with patch.object(
            TransactionsStream,
            "get_starting_replication_key_value",
            return_value=1704067200000,  # 2024-01-01T00:00:00Z in ms
        ) as mock_rkv:
            params = stream.get_url_params(context=None, next_page_token=None)

        mock_rkv.assert_called_once_with(None)
        assert params["after"] == "1704067200000"

    def test_incremental_start_date_string_emits_after(self, mock_config):
        """String start_date (first run, no prior bookmark) is parsed as
        ISO datetime and converted to a ms timestamp for ``after``."""
        stream = TransactionsStream(_mock_tap(mock_config))

        with patch.object(
            TransactionsStream,
            "get_starting_replication_key_value",
            return_value="2024-01-01",
        ) as mock_rkv:
            params = stream.get_url_params(context=None, next_page_token=None)

        mock_rkv.assert_called_once_with(None)
        assert params["after"] == "1704067200000"

    def test_incremental_no_bookmark_no_start_date(self, mock_config):
        """When no bookmark and no start_date exist, ``after`` is omitted."""
        stream = TransactionsStream(_mock_tap(mock_config))

        with patch.object(
            TransactionsStream,
            "get_starting_replication_key_value",
            return_value=None,
        ) as mock_rkv:
            params = stream.get_url_params(context=None, next_page_token=None)

        mock_rkv.assert_called_once_with(None)
        assert "after" not in params

    def test_full_table_stream_skips_after_param(self, mock_config):
        """VaultAccountsStream (replication_key=None) must NOT call
        get_starting_replication_key_value and must NOT include after."""
        stream = VaultAccountsStream(_mock_tap(mock_config))

        with patch.object(
            VaultAccountsStream,
            "get_starting_replication_key_value",
            return_value=None,
        ) as mock_rkv:
            params = stream.get_url_params(context=None, next_page_token=None)

        mock_rkv.assert_not_called()
        assert "after" not in params

    def test_next_page_token_cursor_is_not_clobbered_by_bookmark(
        self, mock_config
    ):
        """Regression test: once pagination has a next_page_token, Fireblocks'
        own cursor (carried under the same ``after`` key) MUST win. Overwriting
        it with the static bookmark value froze pagination in production —
        every page re-requested the same static ``after``, so the API kept
        returning the same page forever."""
        stream = TransactionsStream(_mock_tap(mock_config))
        next_page_token = "https://api.fireblocks.io/v1/transactions?after=1700000000000&limit=200"

        with patch.object(
            TransactionsStream,
            "get_starting_replication_key_value",
            return_value=1767225600000,  # static bookmark, e.g. 2026-01-01
        ) as mock_rkv:
            params = stream.get_url_params(
                context=None, next_page_token=next_page_token
            )

        mock_rkv.assert_not_called()
        assert params["after"] == "1700000000000"
        assert params["limit"] == "200"
