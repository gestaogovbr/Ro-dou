"""API authentication and authenticated user context extraction."""

from __future__ import annotations

import hmac
from collections.abc import Callable

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .config import AuthConfig
from .models import AuthenticatedUser


def build_auth_dependency(
    config: AuthConfig,
) -> Callable[..., AuthenticatedUser]:
    bearer = HTTPBearer(auto_error=False)

    def authenticate(
        credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
        x_user_name: str | None = Header(default=None, max_length=200),
    ) -> AuthenticatedUser:
        if config.api_token:
            expected = config.api_token.get_secret_value()
            supplied = credentials.credentials if credentials else ""
            if not hmac.compare_digest(supplied, expected):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or missing API credential",
                )
            return AuthenticatedUser(name=x_user_name.strip() if x_user_name else None)
        # Anonymous development access may search public DOU data, but it must
        # not turn a self-asserted header into authenticated identity context.
        return AuthenticatedUser()

    return authenticate
