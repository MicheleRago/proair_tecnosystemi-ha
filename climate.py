import logging
from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import HVACMode, ClimateEntityFeature
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Questa è la funzione che Home Assistant chiama ora tramite il Config Flow
async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the ProAir climate platform from a config entry."""
    # Recuperiamo l'API salvata nell'__init__.py tramite l'entry_id
    api = hass.data[DOMAIN][entry.entry_id]
    
    # Recuperiamo lo stato iniziale per creare le entità
    data = await api.get_state()
    
    if data and "Zones" in data:
        _LOGGER.info("Rilevate %s zone ProAir", len(data["Zones"]))
        async_add_entities([ProAirZone(api, zone) for zone in data["Zones"]], True)
    else:
        _LOGGER.error("Nessuna zona rilevata durante il setup iniziale")

class ProAirZone(ClimateEntity):
    def __init__(self, api, zone_data):
        self._api = api
        self._id = zone_data["ZoneId"]
        self._name = zone_data["Name"]
        self._attr_unique_id = f"proair_{api.serial}_{zone_data['ZoneId']}"
        self._state_data = zone_data
        
        # Caratteristiche del termostato
        self._attr_hvac_modes = [HVACMode.HEAT, HVACMode.OFF]
        self._attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE
        self._attr_target_temperature_step = 1.0
        self._attr_min_temp = 10.0
        self._attr_max_temp = 35.0

    @property
    def name(self):
        return self._name

    @property
    def temperature_unit(self):
        return "°C"

    @property
    def hvac_mode(self):
        # IsOFF nel JSON è booleano (True/False)
        return HVACMode.OFF if self._state_data.get("IsOFF") is True else HVACMode.HEAT

    @property
    def current_temperature(self):
        return float(self._state_data.get("Temp", 0)) / 10

    @property
    def target_temperature(self):
        return float(self._state_data.get("SetTemp", 0)) / 10

    @property
    def current_humidity(self):
        # Umd nel JSON (es. 461 -> 46.1%)
        val = self._state_data.get("Umd")
        if val is not None:
            return float(val) / 10
        return None

    async def async_set_temperature(self, **kwargs):
        """Imposta una nuova temperatura target."""
        temp = int(round(kwargs.get("temperature")))
        _LOGGER.debug("Invio comando temperatura per %s: %s gradi", self._name, temp)
        
        if await self._api.set_temperature(self._id, self._name, temp):
            self._state_data["SetTemp"] = temp * 10
            self.async_write_ha_state()

    async def async_update(self):
        """Aggiorna i dati della zona dal cloud."""
        data = await self._api.get_state()
        if data and "Zones" in data:
            for zone in data["Zones"]:
                if zone["ZoneId"] == self._id:
                    self._state_data = zone
