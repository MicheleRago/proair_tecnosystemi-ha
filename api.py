import aiohttp
import hashlib
import base64
import json
import logging
import asyncio
from typing import Any
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from .const import SALT, API_BASE_URL, API_LOGIN_URL, DEFAULT_PIN

_LOGGER = logging.getLogger(__name__)

class ProAirError(Exception):
    """Base exception for ProAir errors."""

class ProAirAuthError(ProAirError):
    """Authentication invalid."""

class ProAirConnectionError(ProAirError):
    """Connection error."""

class ProAirCrypto:
    def __init__(self, device_id: str):
        key_input = device_id[:8] + SALT
        self.key = hashlib.sha256(key_input.encode()).digest()
        self.iv = b'\x00' * 16

    def decrypt(self, data_b64: str) -> str:
        try:
            raw = base64.b64decode(data_b64)
            cipher = AES.new(self.key, AES.MODE_CBC, self.iv)
            return unpad(cipher.decrypt(raw), 16).decode('utf-8').strip()
        except Exception as e:
            _LOGGER.error("Decryption error: %s", e)
            raise ProAirError("Decryption failed") from e

    def encrypt(self, text: str) -> str:
        try:
            cipher = AES.new(self.key, AES.MODE_CBC, self.iv)
            ct_bytes = cipher.encrypt(pad(text.encode(), 16))
            return base64.b64encode(ct_bytes).decode().replace("\n", "").replace("\r", "")
        except Exception as e:
             _LOGGER.error("Encryption error: %s", e)
             raise ProAirError("Encryption failed") from e

class ProAirAPI:
    def __init__(self, session: aiohttp.ClientSession, email: str, password: str, device_id: str) -> None:
        self.session = session
        self.email = email
        self.password = password
        self.device_id = device_id
        self.crypto = ProAirCrypto(device_id)
        self.token: str | None = None
        self.serial: str | None = None
        self._lock = asyncio.Lock()

    def _update_token_local(self) -> str:
        """Increment current token locally."""
        if not self.token:
            return ""
        try:
            plain = self.crypto.decrypt(self.token)
            parts = plain.split('_')
            base = "_".join(parts[:-1])
            count = int(parts[-1])
            self.token = self.crypto.encrypt(f"{base}_{count + 1}")
            return self.token
        except Exception as e:
            _LOGGER.error("Token increment error: %s", e)
            return self.token or ""

    def _get_auth_headers(self, token: str) -> dict[str, str]:
        """Generate auth headers."""
        user_auth = base64.b64encode(f"{self.email}:PwdProAir".encode()).decode()
        return {
            "Token": token,
            "Authorization": f"Basic {user_auth}",
            "UserObj-Agent": "benincapp",
            "User-Agent": "Tecnosystemi/2.2.3"
        }

    async def login(self) -> bool:
        """Perform login and get initial token."""
        auth_init = base64.b64encode(b"UsrProAir:PwdProAir").decode()
        headers = {
            "Authorization": f"Basic {auth_init}", 
            "Token": "Ga5mM61KCm5Bk18lhD5J999jC2Mu0Vaf", 
            "User-Agent": "Tecnosystemi/2.2.3"
        }
        payload = {
            "Username": self.email, 
            "Password": self.password, 
            "DeviceId": self.device_id, 
            "Platform": "apns"
        }
        
        try:
            async with self.session.post(API_LOGIN_URL, json=payload, headers=headers) as resp:
                if resp.status != 200:
                    raise ProAirAuthError(f"Login failed: {resp.status}")
                
                data = await resp.json()
                if "Token" in data:
                    self.token = data["Token"]
                    # Usually "ListPlants" -> "ListDevices" -> "Serial"
                    if data.get("ListPlants") and data["ListPlants"][0].get("ListDevices"):
                        self.serial = data["ListPlants"][0]["ListDevices"][0]["Serial"]
                        return True
                raise ProAirAuthError("Token or Serial not found in login response")
        except aiohttp.ClientError as e:
            raise ProAirConnectionError(f"Connection error during login: {e}") from e

    async def _make_request(self, method: str, url: str, **kwargs: Any) -> dict[str, Any]:
        """Centralized request logic with token refresh and error handling."""
        async with self._lock:
            if not self.token:
                await self.login()

            # Extract headers once to avoid popping in loop
            active_kwargs = kwargs.copy()
            passed_headers = active_kwargs.pop("headers", None)

            # Retry loop for connection errors
            for attempt in range(3):
                current_token = self._update_token_local()
                headers = self._get_auth_headers(current_token)
                
                if passed_headers:
                    headers.update(passed_headers)
                
                try:
                    async with self.session.request(method, url, headers=headers, **active_kwargs) as resp:
                        if resp.status == 401:
                            _LOGGER.debug("401 Unauthorized, performing re-login")
                            await self.login()
                            current_token = self._update_token_local()
                            headers = self._get_auth_headers(current_token)
                            if passed_headers:
                                headers.update(passed_headers)
                                
                            # Retry immediately with new token
                            async with self.session.request(method, url, headers=headers, **active_kwargs) as resp2:
                                resp = resp2
                        
                        data: dict[str, Any] = await resp.json()
                        
                        if data and data.get("Token"):
                            self.token = data["Token"]
                        
                        if resp.status != 200:
                             _LOGGER.error("API error %s: %s", resp.status, data)
                             # We could raise an exception here depending on API behavior, 
                             # but keeping it consistent with legacy behavior of returning data + False return in logic
                        
                        _LOGGER.debug("API Response for %s: %s", url, data)
                        return data

                except aiohttp.ClientError as e:
                    if attempt < 2:
                         _LOGGER.debug("Connection error (attempt %d/3): %s. Retrying...", attempt + 1, e)
                         await asyncio.sleep(1)
                    else:
                         raise ProAirConnectionError(f"Communication error: {e}") from e
            
            raise ProAirConnectionError("Unknown error after retries")

    async def get_state(self) -> dict[str, Any]:
        """Fetch system state."""
        if not self.serial:
            await self.login()
        url = f"{API_BASE_URL}/GetCUState?cuSerial={self.serial}&PIN={DEFAULT_PIN}"
        return await self._make_request("GET", url)

    async def set_temperature(self, zone_id: int, zone_name: str, temp: float, is_off: bool = False) -> bool:
        """Set temperature for a zone."""
        if not self.serial:
            await self.login()

        cmd = {
            "shu_set": 2, 
            "is_off": 1 if is_off else 0, 
            "c": "upd_zona", 
            "t_set": int(temp * 10), 
            "id_zona": zone_id, 
            "is_crono": 0, 
            "fan_set": -1, 
            "name": zone_name, 
            "pin": DEFAULT_PIN
        }
        payload = {
            "Serial": self.serial, 
            "ZoneId": zone_id, 
            "Cmd": json.dumps(cmd, separators=(',', ':')), 
            "Pin": DEFAULT_PIN, 
            "Name": zone_name, 
            "Icon": 0
        }
        
        url = f"{API_BASE_URL}/UpdateZonaData?create_command=true"
        # Content-Type header is needed for this POST
        data = await self._make_request("POST", url, json=payload, headers={"Content-Type": "application/json"})
        
        # Original logic returned True if status 200 (handled in make_request mostly)
        # We assume if we got data back, it was successful enough? 
        # API returns 200 even on logical errors sometimes, so we check existence of data
        return bool(data)
