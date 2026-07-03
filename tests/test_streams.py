"""Tests for streams.py — schema and stream definitions."""

from __future__ import annotations

from tap_fireblocks.streams import (
    ExchangeAccountsStream,
    NetworkConnectionsStream,
    TransactionsStream,
    VaultAccountsStream,
    VaultAssetsStream,
)


class TestTransactionsSchema:
    """Verify the TransactionsStream schema shape."""

    def test_schema_is_dict(self):
        schema = TransactionsStream.schema
        assert isinstance(schema, dict)

    def test_id_is_required(self):
        assert TransactionsStream.primary_keys == ["id"]

    def test_required_fields(self):
        schema = TransactionsStream.schema
        props = schema.get("properties", {})
        assert props["id"]["type"] == ["string"]

    def test_schema_has_expected_fields(self):
        schema = TransactionsStream.schema
        props = schema.get("properties", {})
        expected = {"id", "status", "assetId", "createdAt", "lastUpdated"}
        assert expected.issubset(props.keys())

    def test_path(self):
        assert TransactionsStream.path == "/v1/transactions"


class TestVaultAccountsSchema:
    def test_primary_key(self):
        assert VaultAccountsStream.primary_keys == ["id"]

    def test_records_jsonpath(self):
        assert VaultAccountsStream.records_jsonpath == "$.accounts[*]"

    def test_path(self):
        assert VaultAccountsStream.path == "/v1/vault/accounts_paged"

    def test_has_assets(self):
        schema = VaultAccountsStream.schema
        props = schema.get("properties", {})
        assert "assets" in props
        assert "name" in props


class TestVaultAssetsSchema:
    def test_primary_key(self):
        assert VaultAssetsStream.primary_keys == ["id"]

    def test_path(self):
        assert VaultAssetsStream.path == "/v1/vault/assets"

    def test_has_fields(self):
        props = VaultAssetsStream.schema.get("properties", {})
        assert "total" in props
        assert "available" in props


class TestNetworkConnectionsSchema:
    def test_primary_key(self):
        assert NetworkConnectionsStream.primary_keys == ["id"]

    def test_path(self):
        assert NetworkConnectionsStream.path == "/v1/network_connections"


class TestExchangeAccountsSchema:
    def test_primary_key(self):
        assert ExchangeAccountsStream.primary_keys == ["id"]

    def test_path(self):
        assert ExchangeAccountsStream.path == "/v1/exchange_accounts"
