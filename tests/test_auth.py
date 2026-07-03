"""Tests for auth.py — RS256 JWT signing."""

from __future__ import annotations

import hashlib
import json
from unittest.mock import MagicMock

import jwt
import pytest
from cryptography.hazmat.primitives import serialization

from tap_fireblocks.auth import FireblocksAuthenticator


@pytest.fixture
def auth(mock_config) -> FireblocksAuthenticator:
    """Build a FireblocksAuthenticator backed by a mock stream."""
    stream = MagicMock()
    stream.config = mock_config
    return FireblocksAuthenticator(stream)


def _load_public_key(pem: str):
    """Derive the RS256 public key from a private key PEM."""
    private = serialization.load_pem_private_key(pem.encode(), password=None)
    return private.public_key()


class TestJWTClaims:
    """Verify the structure and shape of signed JWTs."""

    def decode(self, token: str, rsa_private_key_pem: str) -> dict:
        """Decode + verify a JWT using the matching public key."""
        return jwt.decode(
            token,
            _load_public_key(rsa_private_key_pem),
            algorithms=["RS256"],
        )

    def test_returns_valid_jwt(self, auth, rsa_private_key_pem):
        """_sign() returns a 3-segment RS256-signed JWT that verifies."""
        token = auth._sign(uri="/v1/transactions")
        claims = self.decode(token, rsa_private_key_pem)
        assert isinstance(claims, dict)

    def test_claims_include_required_fields(self, auth, rsa_private_key_pem):
        """JWT must contain uri, nonce, iat, exp, sub, bodyHash."""
        token = auth._sign(uri="/v1/transactions", body=b'{"foo":"bar"}')
        claims = self.decode(token, rsa_private_key_pem)
        for field in ("uri", "nonce", "iat", "exp", "sub", "bodyHash"):
            assert field in claims, f"Missing claim: {field}"

    def test_uri_matches_request(self, auth, rsa_private_key_pem):
        """The uri claim matches what was passed to _sign()."""
        token = auth._sign(uri="/v1/transactions?limit=10")
        claims = self.decode(token, rsa_private_key_pem)
        assert claims["uri"] == "/v1/transactions?limit=10"

    def test_sub_matches_api_key(self, auth, rsa_private_key_pem, api_key):
        """The sub claim equals the configured API key."""
        token = auth._sign(uri="/v1/transactions")
        claims = self.decode(token, rsa_private_key_pem)
        assert claims["sub"] == api_key

    def test_bodyHash_matches_sha256(self, auth, rsa_private_key_pem):
        """bodyHash is hex-encoded SHA-256 of the request body."""
        body = json.dumps({"foo": "bar"}).encode()
        token = auth._sign(uri="/v1/transactions", body=body)
        claims = self.decode(token, rsa_private_key_pem)
        expected = hashlib.sha256(body).hexdigest()
        assert claims["bodyHash"] == expected

    def test_bodyHash_empty_body(self, auth, rsa_private_key_pem):
        """bodyHash of empty body is sha256 of b''."""
        token = auth._sign(uri="/v1/transactions")
        claims = self.decode(token, rsa_private_key_pem)
        expected = hashlib.sha256(b"").hexdigest()
        assert claims["bodyHash"] == expected

    def test_exp_within_30s_of_iat(self, auth, rsa_private_key_pem):
        """exp - iat must be <= 30s (Fireblocks requirement)."""
        token = auth._sign(uri="/v1/transactions")
        claims = self.decode(token, rsa_private_key_pem)
        assert claims["exp"] - claims["iat"] <= 30

    def test_nonce_is_unique(self, auth, rsa_private_key_pem):
        """Each call produces a different nonce."""
        t1 = auth._sign(uri="/v1/transactions")
        t2 = auth._sign(uri="/v1/transactions")
        c1 = self.decode(t1, rsa_private_key_pem)
        c2 = self.decode(t2, rsa_private_key_pem)
        assert c1["nonce"] != c2["nonce"]

    def test_nonce_is_int(self, auth, rsa_private_key_pem):
        """nonce is an integer (uuid4().int)."""
        token = auth._sign(uri="/v1/transactions")
        claims = self.decode(token, rsa_private_key_pem)
        assert isinstance(claims["nonce"], int)


class TestAuthenticateRequest:
    """Per-request signing via authenticate_request()."""

    def test_sets_auth_headers(self, auth, api_key):
        """authenticate_request adds X-API-Key and Authorization headers."""
        import requests

        req = requests.Request(
            "GET", "https://api.fireblocks.io/v1/transactions"
        ).prepare()
        auth.authenticate_request(req)
        assert req.headers["X-API-Key"] == api_key
        assert req.headers["Authorization"].startswith("Bearer ")

    def test_authorization_is_jwt(self, auth, rsa_private_key_pem):
        """Authorization value is a valid RS256 JWT."""
        import requests

        req = requests.Request(
            "GET", "https://api.fireblocks.io/v1/transactions"
        ).prepare()
        auth.authenticate_request(req)
        token = req.headers["Authorization"].removeprefix("Bearer ")
        claims = jwt.decode(
            token,
            _load_public_key(rsa_private_key_pem),
            algorithms=["RS256"],
        )
        assert claims["uri"] == "/v1/transactions"
