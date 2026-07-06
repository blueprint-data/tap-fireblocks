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

from tap_fireblocks.client import FireblocksStream
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


class TestGetUrlParams:
    """Verify get_url_params incremental filtering behavior.

    .. note::

       Tests that exercise the ``TransactionsStream`` override must also
       patch ``get_context_state`` to return a plain dict, because the
       mock tap does not provide a real ``tap_name`` string (required by
       ``StreamStateManager.__init__``).  The state dict is only used to
       read/write the custom ``tx_window_start_ms`` key.
    """

    # -- Incremental stream tests (first request) -----------------------

    def test_incremental_int_bookmark_emits_after(self, mock_config):
        stream = TransactionsStream(_mock_tap(mock_config))

        with (
            patch.object(TransactionsStream, "get_context_state", return_value={}),
            patch.object(
                TransactionsStream,
                "get_starting_replication_key_value",
                return_value=1704067200000,
            ) as mock_rkv,
        ):
            params = stream.get_url_params(context=None, next_page_token=None)

        mock_rkv.assert_called_once_with(None)
        assert params["after"] == "1704067200000"
        assert "before" in params

    def test_incremental_start_date_string_emits_after(self, mock_config):
        stream = TransactionsStream(_mock_tap(mock_config))

        with (
            patch.object(TransactionsStream, "get_context_state", return_value={}),
            patch.object(
                TransactionsStream,
                "get_starting_replication_key_value",
                return_value="2024-01-01",
            ) as mock_rkv,
        ):
            params = stream.get_url_params(context=None, next_page_token=None)

        mock_rkv.assert_called_once_with(None)
        assert params["after"] == "1704067200000"
        assert "before" in params

    def test_incremental_no_bookmark_no_start_date(self, mock_config):
        stream = TransactionsStream(_mock_tap(mock_config))

        with (
            patch.object(TransactionsStream, "get_context_state", return_value={}),
            patch.object(
                TransactionsStream,
                "get_starting_replication_key_value",
                return_value=None,
            ) as mock_rkv,
        ):
            params = stream.get_url_params(context=None, next_page_token=None)

        mock_rkv.assert_called_once_with(None)
        assert "after" not in params
        assert "before" not in params

    # -- Backfill mode -------------------------------------------------

    def test_backfill_mode_uses_bounded_window(self, mock_config):
        """When ``tx_window_start_ms`` exists in state, the override
        returns a bounded window (after + before) instead of calling
        ``get_starting_replication_key_value``."""
        stream = TransactionsStream(_mock_tap(mock_config))
        window_start = 1704067200000  # 2024-01-01

        with patch.object(
            TransactionsStream,
            "get_context_state",
            return_value={"tx_window_start_ms": window_start},
        ):
            params = stream.get_url_params(context=None, next_page_token=None)

        assert params["after"] == str(window_start)
        assert "before" in params
        # before should be after + 24h (86400000ms)
        expected_before = window_start + 24 * 3600 * 1000
        assert int(params["before"]) >= expected_before
        assert int(params["before"]) <= expected_before + 5000  # clock skew

    def test_backfill_mode_triggers_progress_advance(self, mock_config):
        """After a successful window, ``finalize_state_progress_markers``
        should advance ``tx_window_start_ms`` by 24h."""
        stream = TransactionsStream(_mock_tap(mock_config))
        window_start = 1704067200000
        state = {TransactionsStream.STATE_PROGRESS_KEY: window_start}

        # Patch super to avoid SDK state-manager logger issues in tests.
        with patch.object(FireblocksStream, "finalize_state_progress_markers"):
            stream.finalize_state_progress_markers(state=state)

        assert (
            state[TransactionsStream.STATE_PROGRESS_KEY]
            == window_start + 24 * 3600 * 1000
        )

    # -- Full-table stream (same as base class) ------------------------

    def test_full_table_stream_skips_after_param(self, mock_config):
        stream = VaultAccountsStream(_mock_tap(mock_config))

        with patch.object(
            VaultAccountsStream,
            "get_starting_replication_key_value",
            return_value=None,
        ) as mock_rkv:
            params = stream.get_url_params(context=None, next_page_token=None)

        mock_rkv.assert_not_called()
        assert "after" not in params

    # -- Pagination: cursor MUST NOT be clobbered ----------------------

    def test_next_page_token_cursor_is_not_clobbered_by_bookmark(self, mock_config):
        stream = TransactionsStream(_mock_tap(mock_config))
        next_page_token = (
            "https://api.fireblocks.io/v1/transactions?after=1700000000000&limit=200"
        )

        # next_page_token triggers early return → get_context_state is
        # never called, so we only need the replication-key mock.
        with patch.object(
            TransactionsStream,
            "get_starting_replication_key_value",
            return_value=1767225600000,
        ) as mock_rkv:
            params = stream.get_url_params(
                context=None, next_page_token=next_page_token
            )

        mock_rkv.assert_not_called()
        assert params["after"] == "1700000000000"
        assert params["limit"] == "200"
