"""Tests for pagination.py — next-page response header paginator."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from tap_fireblocks.pagination import NextPageHeaderPaginator


@pytest.fixture
def paginator() -> NextPageHeaderPaginator:
    return NextPageHeaderPaginator()


def _fake_response(headers: dict | None = None) -> MagicMock:
    resp = MagicMock()
    resp.headers = headers or {}
    return resp


class TestNextPageHeaderPaginator:
    def test_has_next_page(self, paginator):
        """Has more when next-page header is present."""
        resp = _fake_response(
            {"next-page": "https://api.fireblocks.io/v1/transactions?after=abc"}
        )
        assert paginator.has_more(resp) is True

    def test_no_next_page_when_absent(self, paginator):
        """No more when next-page header is missing."""
        resp = _fake_response({})
        assert paginator.has_more(resp) is False

    def test_no_next_page_when_empty(self, paginator):
        """No more when next-page header is present but empty."""
        resp = _fake_response({"next-page": ""})
        assert paginator.has_more(resp) is False

    def test_get_next_returns_url(self, paginator):
        """get_next returns the full URL from the header."""
        url = "https://api.fireblocks.io/v1/transactions?after=xyz"
        resp = _fake_response({"next-page": url})
        assert paginator.get_next(resp) == url

    def test_get_next_none_when_absent(self, paginator):
        """get_next returns None when header is absent."""
        resp = _fake_response({})
        assert paginator.get_next(resp) is None

    def test_get_next_none_when_empty(self, paginator):
        """get_next returns None when header value is empty string."""
        resp = _fake_response({"next-page": ""})
        assert paginator.get_next(resp) is None

    def test_initial_value_is_none(self):
        """Paginator starts with None (no next page yet)."""
        p = NextPageHeaderPaginator()
        assert p.current_value is None
