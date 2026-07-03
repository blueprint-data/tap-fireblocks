"""Fireblocks stream definitions."""

from __future__ import annotations

from singer_sdk import typing as th

from tap_fireblocks.client import FireblocksStream
from tap_fireblocks.pagination import NextPageHeaderPaginator


# ── Shared types ───────────────────────────────────────────

PeerPath = th.ObjectType(
    th.Property("id", th.StringType),
    th.Property("type", th.StringType),
    th.Property("name", th.StringType),
    th.Property("subType", th.StringType),
)

Tag = th.ObjectType(
    th.Property("id", th.StringType),
    th.Property("label", th.StringType),
)

PeerPathWithTags = th.ObjectType(
    th.Property("id", th.StringType),
    th.Property("type", th.StringType),
    th.Property("name", th.StringType),
    th.Property("subType", th.StringType),
    th.Property("tags", th.ArrayType(Tag)),
)

VaultAssetBalance = th.ObjectType(
    th.Property("id", th.StringType),
    th.Property("total", th.StringType),
    th.Property("balance", th.StringType),
    th.Property("lockedAmount", th.StringType),
    th.Property("available", th.StringType),
    th.Property("pending", th.StringType),
    th.Property("frozen", th.StringType),
    th.Property("staked", th.StringType),
    th.Property("blockHeight", th.StringType),
    th.Property("blockHash", th.StringType),
)

AmountInfo = th.ObjectType(
    th.Property("amount", th.StringType),
    th.Property("requestedAmount", th.StringType),
    th.Property("netAmount", th.StringType),
    th.Property("amountUSD", th.StringType),
)

FeeInfo = th.ObjectType(
    th.Property("networkFee", th.StringType),
    th.Property("gasPrice", th.StringType),
    th.Property("fee", th.StringType),
    th.Property("feeUSD", th.StringType),
)

BlockInfo = th.ObjectType(
    th.Property("blockHeight", th.StringType),
    th.Property("blockHash", th.StringType),
)

NetworkRecord = th.ObjectType(
    th.Property("source", PeerPath),
    th.Property("destination", PeerPath),
    th.Property("txHash", th.StringType),
    th.Property("networkFee", th.StringType),
    th.Property("assetId", th.StringType),
    th.Property("netAmount", th.StringType),
    th.Property("isDropped", th.BooleanType),
    th.Property("type", th.StringType),
    th.Property("destinationAddress", th.StringType),
    th.Property("amountUSD", th.StringType),
)

NetworkIdInfo = th.ObjectType(
    th.Property("id", th.StringType),
    th.Property("name", th.StringType),
)


# ── Streams ────────────────────────────────────────────────


class TransactionsStream(FireblocksStream):
    """Transaction history."""

    name = "transactions"
    path = "/v1/transactions"
    primary_keys = ["id"]
    replication_key = "createdAt"

    schema = th.PropertiesList(
        th.Property("id", th.StringType, required=True),
        th.Property("status", th.StringType),
        th.Property("assetId", th.StringType),
        th.Property("createdAt", th.IntegerType),
        th.Property("lastUpdated", th.IntegerType),
        th.Property("source", PeerPathWithTags),
        th.Property("destination", PeerPath),
        th.Property("amount", th.NumberType),
        th.Property("fee", th.NumberType),
        th.Property("networkFee", th.NumberType),
        th.Property("netAmount", th.NumberType),
        th.Property("sourceAddress", th.StringType),
        th.Property("destinationAddress", th.StringType),
        th.Property("destinationAddressDescription", th.StringType),
        th.Property("destinationTag", th.StringType),
        th.Property("txHash", th.StringType),
        th.Property("subStatus", th.StringType),
        th.Property("signedBy", th.ArrayType(th.StringType)),
        th.Property("createdBy", th.StringType),
        th.Property("rejectedBy", th.StringType),
        th.Property("amountUSD", th.NumberType),
        th.Property("addressType", th.StringType),
        th.Property("note", th.StringType),
        th.Property("exchangeTxId", th.StringType),
        th.Property("requestedAmount", th.NumberType),
        th.Property("feeCurrency", th.StringType),
        th.Property("operation", th.StringType),
        th.Property("customerRefId", th.StringType),
        th.Property("numOfConfirmations", th.IntegerType),
        th.Property("amountInfo", AmountInfo),
        th.Property("feeInfo", FeeInfo),
        th.Property("blockInfo", BlockInfo),
        th.Property("externalTxId", th.StringType),
        th.Property("networkRecords", th.ArrayType(NetworkRecord)),
        th.Property("assetType", th.StringType),
        th.Property("nonce", th.StringType),
    ).to_dict()


class VaultAccountsStream(FireblocksStream):
    """Vault accounts with per-asset balances."""

    name = "vault_accounts"
    path = "/v1/vault/accounts_paged"
    primary_keys = ["id"]
    records_jsonpath = "$.accounts[*]"
    replication_key = None

    schema = th.PropertiesList(
        th.Property("id", th.StringType, required=True),
        th.Property("name", th.StringType),
        th.Property("hiddenOnUI", th.BooleanType),
        th.Property("autoFuel", th.BooleanType),
        th.Property("customerRefId", th.StringType),
        th.Property("assets", th.ArrayType(VaultAssetBalance)),
    ).to_dict()

    def get_new_paginator(self):
        return NextPageHeaderPaginator()


class VaultAssetsStream(FireblocksStream):
    """Consolidated balance per asset across all vaults."""

    name = "vault_assets"
    path = "/v1/vault/assets"
    primary_keys = ["id"]
    replication_key = None

    schema = th.PropertiesList(
        th.Property("id", th.StringType, required=True),
        th.Property("total", th.StringType),
        th.Property("available", th.StringType),
        th.Property("pending", th.StringType),
        th.Property("lockedAmount", th.StringType),
        th.Property("frozen", th.StringType),
        th.Property("blockHeight", th.StringType),
        th.Property("blockHash", th.StringType),
    ).to_dict()


class NetworkConnectionsStream(FireblocksStream):
    """Connections to other Fireblocks workspaces."""

    name = "network_connections"
    path = "/v1/network_connections"
    primary_keys = ["id"]
    replication_key = None

    schema = th.PropertiesList(
        th.Property("id", th.StringType, required=True),
        th.Property("remoteNetworkId", NetworkIdInfo),
        th.Property("localNetworkId", NetworkIdInfo),
        th.Property("status", th.StringType),
    ).to_dict()


class ExchangeAccountsStream(FireblocksStream):
    """Connected exchange accounts."""

    name = "exchange_accounts"
    path = "/v1/exchange_accounts"
    primary_keys = ["id"]
    replication_key = None

    schema = th.PropertiesList(
        th.Property("id", th.StringType, required=True),
        th.Property("name", th.StringType),
        th.Property("type", th.StringType),
        th.Property("status", th.StringType),
        th.Property(
            "assets",
            th.ArrayType(
                th.ObjectType(
                    th.Property("id", th.StringType),
                    th.Property("total", th.StringType),
                    th.Property("available", th.StringType),
                    th.Property("lockedAmount", th.StringType),
                    th.Property("btcValue", th.StringType),
                )
            ),
        ),
    ).to_dict()
