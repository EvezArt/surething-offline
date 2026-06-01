from __future__ import annotations

import hmac
import os
from typing import Annotated

from fastapi import Header, HTTPException

OPERATOR_API_TOKEN_ENV = "OPERATOR_API_TOKEN"


def _get_expected_token() -> str | None:
    token = os.getenv(OPERATOR_API_TOKEN_ENV, "").strip()
    return token or None


def require_operator_token(
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
) -> None:
    expected = _get_expected_token()
    if not expected:
        return

    if not authorization:
        raise HTTPException(401, "Missing Authorization header")

    prefix = "Bearer "
    if not authorization.startswith(prefix):
        raise HTTPException(401, "Authorization must use Bearer token")

    provided = authorization[len(prefix):].strip()
    if not hmac.compare_digest(provided, expected):
        raise HTTPException(403, "Invalid operator token")
