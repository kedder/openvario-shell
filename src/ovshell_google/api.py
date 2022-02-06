from abc import abstractmethod
from dataclasses import dataclass
from typing import Protocol, Optional


@dataclass
class OAuth2DeviceCode:
    device_code: str
    user_code: str
    expires_in: int
    interval: int
    verification_url: str


@dataclass
class OAuth2Token:
    access_token: str
    expires_in: int
    refresh_token: str
    scope: str
    token_type: str
    id_token: Optional[str] = None


class OAuth2Error(Exception):
    pass


class GoogleOAuth2(Protocol):
    @abstractmethod
    async def request_code(self) -> OAuth2DeviceCode:
        pass

    async def get_token(self, device_code: str) -> Optional[OAuth2Token]:
        """Return token or indicate that authorization is still pending

        If None is returned, that means "continue polling" - authorization is still
        pending.

        If user refuses to authorize the request, raise OAuth2Error
        """
