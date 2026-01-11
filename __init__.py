from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from .api import ProAirAPI
from .const import DOMAIN

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Configura l'integrazione partendo da una Config Entry (UI)."""
    api = ProAirAPI(
        entry.data["username"], 
        entry.data["password"], 
        entry.data["device_id"]
    )
    
    # Eseguiamo il login iniziale per validare e recuperare il seriale
    await api.login()
    
    # Salviamo l'istanza API nel dizionario globale di HA per renderla accessibile a climate.py
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = api
    
    # Avviamo la piattaforma climate
    await hass.config_entries.async_forward_entry_setups(entry, ["climate"])
    
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Rimuove l'integrazione e pulisce la memoria quando viene eliminata dalla UI."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, ["climate"])
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
