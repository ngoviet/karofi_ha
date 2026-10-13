"""Client REST cho cloud Karofi 365 (`365api.karofi.com`).

Giao thức RE từ app Karofi 365 v2.2.98 (xem docs/api-notes.md):

    POST app/user/signin            {"email": "", "phone", "password", "country": "VI"}
                                    → {"code": 200, "data": {"token", "refreshToken", "userId"}}
    GET  app/house/houseInformation ?page=1&size=50  → nhà → phòng → thiết bị (+properties)
    GET  app/device/detail/{serial} → đủ property (kể cả iro_ketn / iro_vx)

Header: `Authorization: Bearer <token>`. Token là JWT sống 365 ngày; khi server trả
HTTP 401 thì đăng nhập lại 1 lần rồi gọi lại.

Lỗi có HAI dạng (đo thật):
    HTTP 200 {"code": 400, "message": "Account not registered", "data": []}
    HTTP 500 {"error": {"code": 500, "message": "...", "data": "ValidationError: ..."}}
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp

from .const import (
    ACCEPT_LANGUAGE,
    API_BASE,
    COUNTRY_VN,
    REQUEST_TIMEOUT,
    USER_AGENT,
)

_LOGGER = logging.getLogger(__name__)


class KarofiApiError(Exception):
    """Lỗi mạng / server."""


class KarofiAuthError(KarofiApiError):
    """Sai tài khoản / mật khẩu, hoặc token bị từ chối sau khi đăng nhập lại."""


class KarofiApi:
    """Gọi REST API Karofi 365 bằng tài khoản app."""

    def __init__(self, session: aiohttp.ClientSession, phone: str, password: str) -> None:
        self._session = session
        self._phone = phone.strip()
        self._password = password
        self._token: str | None = None
        self._login_lock = asyncio.Lock()
        self.user_id: int | None = None

    @property
    def phone(self) -> str:
        return self._phone

    async def login(self) -> dict[str, Any]:
        """Đăng nhập, lưu token. Trả `data` của signin."""
        async with self._login_lock:
            body = await self._raw(
                "POST",
                "app/user/signin",
                json={
                    # App gửi SĐT ở `phone` khi quốc gia là VN, `email` để rỗng
                    # (LoginBloc.login → AppStringExtension.isIsoVNCode).
                    "email": "",
                    "phone": self._phone,
                    "password": self._password,
                    "country": COUNTRY_VN,
                },
                auth=False,
            )
            data = body.get("data") if isinstance(body, dict) else None
            if not isinstance(data, dict) or not data.get("token"):
                raise KarofiAuthError(_message(body) or "đăng nhập thất bại")
            self._token = data["token"]
            self.user_id = data.get("userId")
            return data

    async def get_houses(self) -> dict[str, Any]:
        return await self._call(
            "GET", "app/house/houseInformation", params={"page": 1, "size": 50}
        )

    async def get_device_detail(self, serial: str) -> dict[str, Any]:
        # App ghép "app/device/detail" + "/" + id; với máy lọc id là SERIAL —
        # gọi bằng id số thì server trả 500.
        body = await self._call("GET", f"app/device/detail/{serial}")
        data = body.get("data")
        if not isinstance(data, dict):
            raise KarofiApiError(f"device/detail {serial}: thiếu data")
        return data

    async def _call(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        if self._token is None:
            await self.login()
        try:
            return await self._raw(method, path, **kwargs)
        except _Unauthorized:
            _LOGGER.debug("karofi: token bị từ chối ở %s, đăng nhập lại", path)
            await self.login()
            try:
                return await self._raw(method, path, **kwargs)
            except _Unauthorized as err:
                raise KarofiAuthError("token bị từ chối sau khi đăng nhập lại") from err

    async def _raw(
        self,
        method: str,
        path: str,
        *,
        auth: bool = True,
        **kwargs: Any,
    ) -> dict[str, Any]:
        headers = {"User-Agent": USER_AGENT, "Accept-Language": ACCEPT_LANGUAGE}
        if auth and self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        try:
            async with asyncio.timeout(REQUEST_TIMEOUT):
                async with self._session.request(
                    method, API_BASE + path, headers=headers, **kwargs
                ) as resp:
                    if resp.status == 401:
                        raise _Unauthorized
                    try:
                        body = await resp.json(content_type=None)
                    except ValueError as err:
                        raise KarofiApiError(
                            f"{path}: HTTP {resp.status}, không phải JSON"
                        ) from err
        except (aiohttp.ClientError, TimeoutError) as err:
            raise KarofiApiError(f"{path}: {err!r}") from err

        if not isinstance(body, dict):
            raise KarofiApiError(f"{path}: response không phải object")
        if "error" in body:
            err = body["error"] or {}
            if err.get("code") == 401:
                raise _Unauthorized
            if path == "app/user/signin" and "ValidationError" in str(err.get("data")):
                # vd. SĐT sai định dạng → server trả 500 ValidationError, không phải 400
                raise KarofiAuthError(str(err.get("data")))
            raise KarofiApiError(
                f"{path}: {err.get('code')} {err.get('message')} {err.get('data')}"
            )
        if body.get("code") != 200:
            if path == "app/user/signin":
                raise KarofiAuthError(_message(body) or "đăng nhập thất bại")
            raise KarofiApiError(f"{path}: {body.get('code')} {_message(body)}")
        return body


class _Unauthorized(Exception):
    """HTTP 401 / error.code 401 — nội bộ, để _call đăng nhập lại."""


def _message(body: Any) -> str | None:
    if isinstance(body, dict):
        return body.get("message") or (body.get("error") or {}).get("message")
    return None
