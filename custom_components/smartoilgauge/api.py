"""Smart Oil Gauge (Connected Consumer Fuel) web-app client.

No Home Assistant imports, so it can be tested on its own (see test_login.py).
Uses its OWN aiohttp session/cookie jar: the upstream version shared HA's
global session, so a leftover PHPSESSID made login.php redirect straight to
the app (no form, hence "could not find login nonce").
"""
from __future__ import annotations

import asyncio
import json
import logging
import re

import aiohttp

_LOGGER = logging.getLogger(__name__)

ORIGIN = "https://app.smartoilgauge.com"
LOGIN_URL = f"{ORIGIN}/login.php"
APP_URL = f"{ORIGIN}/app.php"
AJAX_URL = f"{ORIGIN}/ajax/main_ajax.php"
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0 Safari/537.36"
)
NONCE_RE = re.compile(
    r"""name=['"]ccf_nonce['"][^>]*value=['"]([^'"]+)['"]"""
    r"""|value=['"]([^'"]+)['"][^>]*name=['"]ccf_nonce['"]"""
)


class SmartOilGaugeError(Exception):
    """Cannot reach or parse the service."""


class SmartOilGaugeAuthError(SmartOilGaugeError):
    """Credentials rejected."""


class SmartOilGaugeClient:
    """Logs in to app.smartoilgauge.com and reads the tank list."""

    def __init__(self, username: str, password: str) -> None:
        self._username = username
        self._password = password
        self._session: aiohttp.ClientSession | None = None

    def _sess(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                cookie_jar=aiohttp.CookieJar(),
                headers={"User-Agent": UA},
                timeout=aiohttp.ClientTimeout(total=20),
            )
        return self._session

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    async def login(self) -> None:
        """Log in. Raises SmartOilGaugeAuthError / SmartOilGaugeError."""
        sess = self._sess()
        sess.cookie_jar.clear()
        try:
            async with sess.get(LOGIN_URL) as resp:
                html = await resp.text()
            m = NONCE_RE.search(html)
            if not m:
                raise SmartOilGaugeError(
                    f"login form not found (HTTP {resp.status}, url {resp.url})"
                )
            nonce = m.group(1) or m.group(2)
            async with sess.post(
                LOGIN_URL,
                data={
                    "username": self._username,
                    "user_pass": self._password,
                    "ccf_nonce": nonce,
                    "remember": "on",
                },
                headers={"Referer": LOGIN_URL, "Origin": ORIGIN},
            ) as resp:
                body = await resp.text()
                final_url = str(resp.url)
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise SmartOilGaugeError(f"connection error: {err}") from err

        # Still on the login form means the credentials were rejected.
        if NONCE_RE.search(body) and "login.php" in final_url:
            raise SmartOilGaugeAuthError("username or password rejected")
        if await self._fetch_tanks() is None:
            raise SmartOilGaugeAuthError("logged in but tank list was refused")

    async def _fetch_tanks(self) -> list[dict] | None:
        """Return the tank list, or None if the session is not logged in."""
        try:
            async with self._sess().post(
                AJAX_URL,
                data={"action": "get_tanks_list", "tank_id": "0"},
                headers={
                    "Referer": APP_URL,
                    "Origin": ORIGIN,
                    "X-Requested-With": "XMLHttpRequest",
                },
            ) as resp:
                text = await resp.text()
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise SmartOilGaugeError(f"connection error: {err}") from err
        try:
            data = json.loads(text)
        except ValueError:
            _LOGGER.debug("Non-JSON tank response: %.200s", text)
            return None
        if isinstance(data, dict) and data.get("result") == "ok":
            return data.get("tanks") or []
        _LOGGER.debug("Tank response not ok: %.200s", text)
        return None

    async def get_tanks(self) -> list[dict]:
        """Tank list, logging in again if the session expired."""
        tanks = await self._fetch_tanks()
        if tanks is None:
            await self.login()
            tanks = await self._fetch_tanks()
        if tanks is None:
            raise SmartOilGaugeError("tank list unavailable after re-login")
        return tanks
