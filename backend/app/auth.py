"""The secret API key check shared by every endpoint."""

import secrets

from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader

from . import config

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)  # adds the Authorize button in /docs


def require_api_key(x_api_key: str | None = Security(api_key_header)) -> None:
    """Requests must carry the secret key in the X-API-Key header."""
    if not config.API_KEY:
        raise HTTPException(500, "API_KEY is not set on the server")
    if not secrets.compare_digest(x_api_key or "", config.API_KEY):
        raise HTTPException(401, "Missing or wrong API key")
