"""Tests for TransactionsStream.get_records() multi-window catch-up.

.. note::

   Confirmed bug: singer-sdk's ``Stream.sync()`` calls ``_sync_records()``
   (and therefore ``get_records()``) exactly ONCE per tap invocation, then
   ``TapFireblocks.sync_all()`` calls ``stream.finalize_state_progress_markers()``
   exactly once more, and the process exits. Since the forward-windowing
   scheme (``tx_window_start_ms``) only advances by one ``WINDOW_HOURS``
   step per ``finalize_state_progress_markers`` call, a single tap
   invocation used to advance exactly ONE day — a real backfill would need
   to be re-invoked externally, once per day, which nothing does.

   These tests exercise ``get_records()`` end-to-end (using the *real*
   ``get_url_params`` and the *real* ``TransactionsStream.
   finalize_state_progress_markers`` advance-or-clear logic) across
   several simulated days, stubbing out only the network fetch
   (``request_records``) and the base SDK's generic bookmark-promotion
   call (``FireblocksStream.finalize_state_progress_markers``, which needs
   a fully wired tap/state-writer stack we don't want to construct here —
   see ``test_client.py`` for why that's mocked the same way).
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from tap_fireblocks.client import FireblocksStream
from tap_fireblocks.streams import TransactionsStream

WINDOW_MS = TransactionsStream.WINDOW_HOURS * 3600 * 1000


def _mock_tap(config: dict) -> MagicMock:
    """Return a minimal mock Tap that satisfies Stream.__init__."""
    tap = MagicMock()
    tap.config = config
    tap.logger = MagicMock()
    tap.logger.getChild.return_value = MagicMock()
    return tap


def _make_fake_request_records(stream: TransactionsStream, seen_windows: list):
    """Fake ``request_records`` that exercises the real ``get_url_params``.

    Only the HTTP fetch is stubbed: it reads the (after, before) window
    that the real ``get_url_params`` computes from current state, records
    it for assertions, and yields one fake record inside that window —
    exactly as the real Fireblocks API would for a non-empty window.
    """

    def fake_request_records(context):
        params = stream.get_url_params(context, None)
        after = int(params["after"])
        before = int(params["before"])
        seen_windows.append((after, before))
        yield {"id": f"tx-{after}", "createdAt": after, "status": "COMPLETED"}

    return fake_request_records


class TestMultiWindowCatchup:
    """A single get_records() call must walk ALL windows up to 'now'."""

    def test_single_call_advances_through_multiple_windows(self, mock_config):
        """4 days between bookmark and 'now' -> 4 windows, one call."""
        stream = TransactionsStream(_mock_tap(mock_config))

        start = datetime(2024, 1, 1, tzinfo=timezone.utc)
        fixed_now = datetime(2024, 1, 5, tzinfo=timezone.utc)  # exactly +4 windows
        start_ms = int(start.timestamp() * 1000)

        state: dict = {}
        seen_windows: list = []
        fake_request_records = _make_fake_request_records(stream, seen_windows)

        with (
            patch("tap_fireblocks.streams.datetime") as mock_datetime,
            patch.object(TransactionsStream, "get_context_state", return_value=state),
            patch.object(
                TransactionsStream,
                "get_starting_replication_key_value",
                return_value=start_ms,
            ),
            patch.object(
                TransactionsStream,
                "request_records",
                side_effect=fake_request_records,
            ),
            # Bypass the base SDK's generic bookmark promotion / STATE
            # message writer, which needs a real tap_state/state-writer
            # stack. TransactionsStream's own advance-or-clear logic
            # (the thing under test) still runs for real.
            patch.object(FireblocksStream, "finalize_state_progress_markers"),
        ):
            mock_datetime.now.return_value = fixed_now

            records = list(stream.get_records(context=None))

        assert len(records) == 4
        assert seen_windows == [
            (start_ms + 0 * WINDOW_MS, start_ms + 1 * WINDOW_MS),
            (start_ms + 1 * WINDOW_MS, start_ms + 2 * WINDOW_MS),
            (start_ms + 2 * WINDOW_MS, start_ms + 3 * WINDOW_MS),
            (start_ms + 3 * WINDOW_MS, start_ms + 4 * WINDOW_MS),
        ]
        # Caught up: the custom progress key must be cleared so the next
        # invocation switches to normal incremental sync.
        assert TransactionsStream.STATE_PROGRESS_KEY not in state

    def test_records_span_all_simulated_days(self, mock_config):
        """The yielded records' createdAt values cover every window, not
        just the first one."""
        stream = TransactionsStream(_mock_tap(mock_config))

        start = datetime(2024, 3, 1, tzinfo=timezone.utc)
        fixed_now = datetime(2024, 3, 4, tzinfo=timezone.utc)  # +3 windows
        start_ms = int(start.timestamp() * 1000)

        state: dict = {}
        seen_windows: list = []
        fake_request_records = _make_fake_request_records(stream, seen_windows)

        with (
            patch("tap_fireblocks.streams.datetime") as mock_datetime,
            patch.object(TransactionsStream, "get_context_state", return_value=state),
            patch.object(
                TransactionsStream,
                "get_starting_replication_key_value",
                return_value=start_ms,
            ),
            patch.object(
                TransactionsStream,
                "request_records",
                side_effect=fake_request_records,
            ),
            patch.object(FireblocksStream, "finalize_state_progress_markers"),
        ):
            mock_datetime.now.return_value = fixed_now

            records = list(stream.get_records(context=None))

        created_at_values = sorted(r["createdAt"] for r in records)
        assert created_at_values == [
            start_ms,
            start_ms + WINDOW_MS,
            start_ms + 2 * WINDOW_MS,
        ]
        assert state.get(TransactionsStream.STATE_PROGRESS_KEY) is None

    def test_no_bookmark_no_start_date_fetches_once(self, mock_config):
        """No bookmark/start_date at all -> windowing never activates, so
        get_records() makes exactly one (unbounded) request and stops."""
        stream = TransactionsStream(_mock_tap(mock_config))
        state: dict = {}
        call_count = 0

        def fake_request_records(context):
            nonlocal call_count
            call_count += 1
            yield {"id": "tx-full", "createdAt": 0, "status": "COMPLETED"}

        with (
            patch.object(TransactionsStream, "get_context_state", return_value=state),
            patch.object(
                TransactionsStream,
                "get_starting_replication_key_value",
                return_value=None,
            ),
            patch.object(
                TransactionsStream,
                "request_records",
                side_effect=fake_request_records,
            ),
        ):
            records = list(stream.get_records(context=None))

        assert call_count == 1
        assert len(records) == 1
        assert TransactionsStream.STATE_PROGRESS_KEY not in state


class TestMultiWindowSafetyCap:
    """Guard against an infinite loop if the window never catches up."""

    def test_raises_when_iteration_cap_exceeded(self, mock_config):
        stream = TransactionsStream(_mock_tap(mock_config))
        stream.MAX_WINDOW_ITERATIONS = 3  # small cap so the test is fast

        start = datetime(2024, 1, 1, tzinfo=timezone.utc)
        # Far-future "now": real catch-up would need far more than 3
        # windows, so the safety cap must trip before that happens.
        fixed_now = datetime(2030, 1, 1, tzinfo=timezone.utc)
        start_ms = int(start.timestamp() * 1000)

        state: dict = {}
        seen_windows: list = []
        fake_request_records = _make_fake_request_records(stream, seen_windows)

        with (
            patch("tap_fireblocks.streams.datetime") as mock_datetime,
            patch.object(TransactionsStream, "get_context_state", return_value=state),
            patch.object(
                TransactionsStream,
                "get_starting_replication_key_value",
                return_value=start_ms,
            ),
            patch.object(
                TransactionsStream,
                "request_records",
                side_effect=fake_request_records,
            ),
            patch.object(FireblocksStream, "finalize_state_progress_markers"),
        ):
            mock_datetime.now.return_value = fixed_now

            with pytest.raises(RuntimeError, match="exceeded"):
                list(stream.get_records(context=None))

        # It should fail loud after exactly MAX_WINDOW_ITERATIONS windows,
        # not hang or silently truncate.
        assert len(seen_windows) == stream.MAX_WINDOW_ITERATIONS
