from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import aiohttp_client

from .api import ProAirAPI
from .coordinator import ProAirDataUpdateCoordinator
from .const import DOMAIN, CONF_USERNAME, CONF_PASSWORD, CONF_DEVICE_ID

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up the integration from a Config Entry."""
    
    session = aiohttp_client.async_get_clientsession(hass)
    
    api = ProAirAPI(
        session,
        entry.data[CONF_USERNAME], 
        entry.data[CONF_PASSWORD], 
        entry.data[CONF_DEVICE_ID]
    )
    
    # Perform login to retrieve serial number and validate credentials
    await api.login()
    
    coordinator = ProAirDataUpdateCoordinator(hass, api)
    
    # First data refresh
    await coordinator.async_config_entry_first_refresh()
    
    # Save the coordinator
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator
    
    # Start climate and sensor platforms
    await hass.config_entries.async_forward_entry_setups(entry, ["climate", "sensor", "binary_sensor"])
    
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Remove the integration and clean up."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, ["climate", "sensor", "binary_sensor"])
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
