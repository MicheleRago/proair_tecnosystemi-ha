import aiohttp
import hashlib
import base64
import json
import logging
import asyncio
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from .const import SALT

_LOGGER = logging.getLogger(__name__)

class ProAirCrypto:
    def __init__(self, device_id):
        key_input = device_id[:8] + SALT
        self.key = hashlib.sha256(key_input.encode()).digest()
        self.iv = b'\x00' * 16

    def decrypt(self, data_b64):
        raw = base64.b64decode(data_b64)
        cipher = AES.new(self.key, AES.MODE_CBC, self.iv)
        return unpad(cipher.decrypt(raw), 16).decode('utf-8').strip()

    def encrypt(self, text):
        cipher = AES.new(self.key, AES.MODE_CBC, self.iv)
        ct_bytes = cipher.encrypt(pad(text.encode(), 16))
        return base64.b64encode(ct_bytes).decode().replace("\n", "").replace("\r", "")

class ProAirAPI:
    def __init__(self, email, password, device_id):
        self.email = email
        self.password = password
        self.device_id = device_id
        self.crypto = ProAirCrypto(device_id)
        self.token = None
        self.serial = None
        self.session = aiohttp.ClientSession()
        self._lock = asyncio.Lock()

    def _update_token_local(self):
        """Incrementa il token internamente senza dipendere dalla risposta del server."""
        try:
            plain = self.crypto.decrypt(self.token)
            parts = plain.split('_')
            base = "_".join(parts[:-1])
            count = int(parts[-1])
            self.token = self.crypto.encrypt(f"{base}_{count + 1}")
            return self.token
        except Exception as e:
            _LOGGER.error("Errore incremento token: %s", e)
            return self.token

    async def login(self):
        url = "https://proair.azurewebsites.net/apiTS/v2/Login"
        auth_init = base64.b64encode(b"UsrProAir:PwdProAir").decode()
        headers = {"Authorization": f"Basic {auth_init}", "Token": "Ga5mM61KCm5Bk18lhD5J999jC2Mu0Vaf", "User-Agent": "Tecnosystemi/2.2.3"}
        payload = {"Username": self.email, "Password": self.password, "DeviceId": self.device_id, "Platform": "apns"}
        
        async with self.session.post(url, json=payload, headers=headers) as resp:
            data = await resp.json()
            if "Token" in data:
                self.token = data["Token"]
                self.serial = data["ListPlants"][0]["ListDevices"][0]["Serial"]
                return True
            return False

    async def get_state(self):
        async with self._lock:
            if not self.token: await self.login()
            
            # Incrementiamo il token locale prima della chiamata
            current_token = self._update_token_local()
            
            user_auth = base64.b64encode(f"{self.email}:PwdProAir".encode()).decode()
            headers = {
                "Token": current_token, 
                "Authorization": f"Basic {user_auth}", 
                "UserObj-Agent": "benincapp", 
                "User-Agent": "Tecnosystemi/2.2.3"
            }
            
            url = f"https://proair.azurewebsites.net/api/v1/GetCUState?cuSerial={self.serial}&PIN=2226"
            async with self.session.get(url, headers=headers) as resp:
                if resp.status == 401:
                    _LOGGER.warning("401 rilevato, rieseguo login")
                    await self.login()
                    current_token = self._update_token_local()
                    headers["Token"] = current_token
                    async with self.session.get(url, headers=headers) as resp2:
                        return await resp2.json()
                
                data = await resp.json()
                # Se il server dovesse mai ridarci un token lo salviamo, 
                # altrimenti teniamo quello incrementato da noi
                if data and data.get("Token"):
                    self.token = data["Token"]
                return data

    async def set_temperature(self, zone_id, zone_name, temp):
        async with self._lock:
            # Incrementiamo il token locale prima della POST
            current_token = self._update_token_local()
            
            user_auth = base64.b64encode(f"{self.email}:PwdProAir".encode()).decode()
            headers = {
                "Token": current_token, 
                "Authorization": f"Basic {user_auth}", 
                "UserObj-Agent": "benincapp", 
                "Content-Type": "application/json"
            }
            
            cmd = {"shu_set": 2, "is_off": 0, "c": "upd_zona", "t_set": int(temp * 10), "id_zona": zone_id, "is_crono": 0, "fan_set": -1, "name": zone_name, "pin": "2226"}
            payload = {"Serial": self.serial, "ZoneId": zone_id, "Cmd": json.dumps(cmd, separators=(',', ':')), "Pin": "2226", "Name": zone_name, "Icon": 0}
            
            async with self.session.post("https://proair.azurewebsites.net/api/v1/UpdateZonaData?create_command=true", json=payload, headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("Token"): self.token = data["Token"]
                    return True
                return False
