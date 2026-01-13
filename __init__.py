from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import aiohttp_client

from .api import ProAirAPI
from .coordinator import ProAirDataUpdateCoordinator
from .const import DOMAIN, CONF_USERNAME, CONF_PASSWORD, CONF_DEVICE_ID

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Configura l'integrazione partendo da una Config Entry (UI)."""
    
    session = aiohttp_client.async_get_clientsession(hass)
    
    api = ProAirAPI(
        session,
        entry.data[CONF_USERNAME], 
        entry.data[CONF_PASSWORD], 
        entry.data[CONF_DEVICE_ID]
    )
    
    # Eseguiamo il login per recuperare il serial number e validare credenziali
    await api.login()
    
    coordinator = ProAirDataUpdateCoordinator(hass, api)
    
    # Primo aggiornamento dati
    await coordinator.async_config_entry_first_refresh()
    
    # Salviamo il coordinator
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator
    
    # Avviamo la piattaforma climate e sensor
    await hass.config_entries.async_forward_entry_setups(entry, ["climate", "sensor"])
    
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Rimuove l'integrazione e pulisce la memoria."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, ["climate", "sensor"])
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
