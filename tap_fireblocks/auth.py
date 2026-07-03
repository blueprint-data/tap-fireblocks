"""RS256 JWT request signing for the Fireblocks API."""

from __future__ import annotations

import hashlib
import os
import time
import uuid
from pathlib import Path
from typing import Any

import jwt
import requests
from dotenv import load_dotenv
from singer_sdk.authenticators import APIAuthenticatorBase


class FireblocksAuthenticator(APIAuthenticatorBase):
    """Signs each request with a fresh RS256 JWT.

    Fireblocks requires uri/nonce/iat/exp/sub/bodyHash claims, signed with the
    workspace's RSA private key. exp must be within 30s of iat, so the token
    cannot be cached/reused across requests like a normal bearer token.

    Auth is applied per-request via ``authenticate_request()``, which reads the
    request's URL and body to produce the JWT — not via static ``auth_headers``.
    """

    def __init__(self, stream: Any) -> None:
        super().__init__(stream=stream)

        # Load .env so FB_API_KEY / FB_PRIVATE_KEY are available
        # without needing to source .env manually.
        env_path = Path(".env")
        if env_path.exists():
            load_dotenv(env_path)

        self._api_key: str = stream.config.get("api_key") or os.environ["FB_API_KEY"]
        raw_key: str = (
            stream.config.get("secret_key")
            or os.environ.get("FB_PRIVATE_KEY")
            or os.environ.get("TAP_FIREBLOCKS_SECRET_KEY", "")
        )

        # Accept PEM content directly or a file path to a PEM.
        if raw_key.strip().startswith("-----BEGIN"):
            self._private_key: str = raw_key
        else:
            with open(raw_key) as f:
                self._private_key = f.read()

    def _sign(self, uri: str, body: bytes = b"") -> str:
        now = int(time.time())
        claims = {
            "uri": uri,
            "nonce": uuid.uuid4().int,
            "iat": now,
            "exp": now + 25,
            "sub": self._api_key,
            "bodyHash": hashlib.sha256(body).hexdigest(),
        }
        return jwt.encode(claims, self._private_key, algorithm="RS256")

    def authenticate_request(
        self,
        request: requests.PreparedRequest,
    ) -> requests.PreparedRequest:
        """Sign the request with a JWT for its specific URI + body."""
        token = self._sign(
            uri=request.path_url,
            body=request.body if request.body else b"",
        )
        request.headers["X-API-Key"] = self._api_key
        request.headers["Authorization"] = f"Bearer {token}"
        return request
