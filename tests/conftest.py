"""Test fixtures for tap-fireblocks."""

from __future__ import annotations

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


@pytest.fixture(scope="session")
def rsa_private_key_pem() -> str:
    """Generate a throwaway RSA 2048 private key for testing.

    Never use this key outside of tests!
    """
    key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    return key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()


@pytest.fixture
def api_key() -> str:
    return "test-api-key-12345"


@pytest.fixture
def mock_config(api_key, rsa_private_key_pem) -> dict:
    return {
        "api_key": api_key,
        "secret_key": rsa_private_key_pem,
        "base_url": "https://api.fireblocks.io",
    }
