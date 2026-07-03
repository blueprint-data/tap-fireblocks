# tap-fireblocks

Singer tap for the [Fireblocks API](https://developers.fireblocks.com). Extracts transactions, vault accounts, asset balances, network connections, and exchange accounts from your Fireblocks workspace.

Built with the [Meltano SDK](https://sdk.meltano.com) for Python.

## Prerequisites

- Python 3.9+
- A Fireblocks workspace (production or sandbox)
- An [API user](https://developers.fireblocks.com/docs/manage-api-keys) with at least read permissions

## Quick start

### 1. Set up credentials

Create a `.env` file in the project root (it's gitignored):

```bash
# ── Fireblocks ────────────────────────────────────────────
FB_API_KEY=your-api-key-uuid

# Paste your full PEM private key between the quotes (dotenv supports multi-line values)
FB_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----
MII...
-----END PRIVATE KEY-----"

FB_BASE_URL=https://api.fireblocks.io
```

> **URLs by region:**
> - US: `https://api.fireblocks.io`
> - EU: `https://eu-api.fireblocks.io`
> - EU2: `https://eu2-api.fireblocks.io`
> - Sandbox: `https://sandbox-api.fireblocks.io`

### 2. Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### 3. Run

```bash
tap-fireblocks --config config.local.json > output.json
```

Or with a local config file instead of `.env`:

```json
{
  "api_key": "your-api-key",
  "secret_key": "-----BEGIN PRIVATE KEY-----\nMII...\n-----END PRIVATE KEY-----",
  "base_url": "https://api.fireblocks.io"
}
```

### 4. See available streams

```bash
tap-fireblocks --config config.local.json --discover
```

## Streams

| Stream | Endpoint | Description |
|--------|----------|-------------|
| `transactions` | `GET /v1/transactions` | Transaction history with pagination |
| `vault_accounts` | `GET /v1/vault/accounts_paged` | Vault accounts with per-asset balances |
| `vault_assets` | `GET /v1/vault/assets` | Consolidated balance per asset |
| `network_connections` | `GET /v1/network_connections` | Connections to other Fireblocks workspaces |
| `exchange_accounts` | `GET /v1/exchange_accounts` | Connected exchange accounts |

## Authentication

Fireblocks uses **per-request RS256 JWT signing** — every request gets a fresh token with:
- `uri` — the request path
- `nonce` — unique per request
- `iat` / `exp` — issued/expiry (max 30s window)
- `sub` — your API key
- `bodyHash` — SHA-256 of the request body

The token is signed with your RSA 4096 private key. See [Fireblocks auth docs](https://developers.fireblocks.com/reference/signing-a-request-jwt-structure).

## Credential sources (priority order)

1. `--config` file JSON (`secret_key`, `api_key`) 
2. `.env` file in project root (`FB_API_KEY`, `FB_PRIVATE_KEY`)
3. Environment variables (`FB_API_KEY`, `FB_PRIVATE_KEY`, `TAP_FIREBLOCKS_SECRET_KEY`)

The `.env` is loaded automatically by the tap — no need to `source .env` manually.

## Testing

```bash
source .venv/bin/activate
python -m pytest tests/ -v
```

34+ unit tests cover JWT signing, pagination, schema definitions, and auth flow.

## Development

```bash
pip install -e ".[dev]"
# Run against real API
tap-fireblocks --config config.local.json --discover
```

## Publishing to MeltanoHub

Once ready for release:

1. Make the repo public
2. Add an MIT or Apache 2.0 license
3. Submit a PR to [MeltanoHub](https://github.com/meltano/hub) adding `tap-fireblocks` to the catalog

## License

To be determined by Blueprint Data.
