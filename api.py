import aiohttp
import hashlib
import base64
import json
import logging
import asyncio
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
    def __init__(self, session: aiohttp.ClientSession, email: str, password: str, device_id: str):
        self.session = session
        self.email = email
        self.password = password
        self.device_id = device_id
        self.crypto = ProAirCrypto(device_id)
        self.token = None
        self.serial = None
        self._lock = asyncio.Lock()

    def _update_token_local(self) -> str:
        """Increment current token locally."""
        if not self.token:
            return None
        try:
            plain = self.crypto.decrypt(self.token)
            parts = plain.split('_')
            base = "_".join(parts[:-1])
            count = int(parts[-1])
            self.token = self.crypto.encrypt(f"{base}_{count + 1}")
            return self.token
        except Exception as e:
            _LOGGER.error("Token increment error: %s", e)
            return self.token

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
                    if data.get("ListPlants") and data["ListPlants"][0].get("ListDevices"):
                        self.serial = data["ListPlants"][0]["ListDevices"][0]["Serial"]
                        return True
                raise ProAirAuthError("Token or Serial not found in login response")
        except aiohttp.ClientError as e:
            raise ProAirConnectionError(f"Connection error during login: {e}") from e

    async def get_state(self) -> dict:
        """Fetch system state."""
        async with self._lock:
            if not self.token: 
                await self.login()
            
            current_token = self._update_token_local()
            if not current_token:
                 await self.login()
                 current_token = self.token

            user_auth = base64.b64encode(f"{self.email}:PwdProAir".encode()).decode()
            headers = {
                "Token": current_token, 
                "Authorization": f"Basic {user_auth}", 
                "UserObj-Agent": "benincapp", 
                "User-Agent": "Tecnosystemi/2.2.3"
            }
            
            url = f"{API_BASE_URL}/GetCUState?cuSerial={self.serial}&PIN={DEFAULT_PIN}"
            
            try:
                async with self.session.get(url, headers=headers) as resp:
                    if resp.status == 401:
                        _LOGGER.warning("401 Unauthorized, re-login")
                        await self.login()
                        current_token = self._update_token_local()
                        headers["Token"] = current_token
                        async with self.session.get(url, headers=headers) as resp2:
                            data = await resp2.json()
                    else:
                        data = await resp.json()
                    
                    if data and data.get("Token"):
                        self.token = data["Token"]
                    return data
            except aiohttp.ClientError as e:
                raise ProAirConnectionError(f"Error fetching state: {e}") from e

    async def set_temperature(self, zone_id: int, zone_name: str, temp: float, is_off: bool = False) -> bool:
        """Set temperature for a zone."""
        async with self._lock:
            current_token = self._update_token_local()
            
            user_auth = base64.b64encode(f"{self.email}:PwdProAir".encode()).decode()
            headers = {
                "Token": current_token, 
                "Authorization": f"Basic {user_auth}", 
                "UserObj-Agent": "benincapp", 
                "Content-Type": "application/json"
            }
            
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
            
            try:
                async with self.session.post(f"{API_BASE_URL}/UpdateZonaData?create_command=true", json=payload, headers=headers) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data.get("Token"): 
                            self.token = data["Token"]
                        return True
                    _LOGGER.error("Error setting temperature, status: %s", resp.status)
                    return False
            except aiohttp.ClientError as e:
                raise ProAirConnectionError(f"Error setting temperature: {e}") from e
