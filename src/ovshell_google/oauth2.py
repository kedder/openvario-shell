from typing import Optional

import requests

from . import api, credentials


class GoogleOAuth2Impl(api.GoogleOAuth2):
    async def request_code(self) -> api.OAuth2DeviceCode:
        scopes = [
            "profile",
            # "https://www.googleapis.com/auth/gmail.send",
            "https://mail.google.com/",
            # "https://www.googleapis.com/auth/userinfo.profile",
            # "https://www.googleapis.com/auth/userinfo.emails",
            # "https://www.googleapis.com/auth/drive.file",
            # "https://www.googleapis.com/auth/drive",
        ]
        url = "https://oauth2.googleapis.com/device/code"
        params = {
            "client_id": credentials.CLIENT_ID,
            "scope": " ".join(scopes),
        }
        resp = requests.post(url, data=params)
        respdata = resp.json()
        if "error" in respdata:
            raise api.OAuth2Error(respdata["error"])
        return api.OAuth2DeviceCode(**respdata)

    async def get_token(self, device_code: str) -> Optional[api.OAuth2Token]:
        url = "https://oauth2.googleapis.com/token"
        params = {
            "client_id": credentials.CLIENT_ID,
            "client_secret": credentials.CLIENT_SECRET,
            "device_code": device_code,
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
        }
        resp = requests.post(url, data=params)
        respdata = resp.json()
        if "error" in respdata:
            err = respdata["error"]
            if err == "authorization_pending":
                return None
            else:
                raise api.OAuth2Error(f"{err}: {respdata['error_description']}")

        return api.OAuth2Token(**respdata)
