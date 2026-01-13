import logging
from typing import Any
from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import HVACMode, ClimateEntityFeature
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from .coordinator import ProAirDataUpdateCoordinator
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up the ProAir climate platform from a config entry."""
    coordinator: ProAirDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    
    # Non chiamiamo più api.get_state() qui, usiamo i dati del coordinator
    if coordinator.data and "Zones" in coordinator.data:
        _LOGGER.info("Rilevate %s zone ProAir", len(coordinator.data["Zones"]))
        async_add_entities([ProAirZone(coordinator, zone) for zone in coordinator.data["Zones"]], True)
    else:
        _LOGGER.error("Nessuna zona rilevata o dati non disponibili")

class ProAirZone(CoordinatorEntity[ProAirDataUpdateCoordinator], ClimateEntity):
    def __init__(self, coordinator: ProAirDataUpdateCoordinator, zone_data: dict[str, Any]) -> None:
        super().__init__(coordinator)
        self._api = coordinator.api
        self._id = zone_data["ZoneId"]
        self._name = zone_data["Name"]
        self._attr_unique_id = f"proair_{coordinator.api.serial}_{zone_data['ZoneId']}"
        
        # Caratteristiche del termostato
        self._attr_hvac_modes = [HVACMode.HEAT, HVACMode.OFF]
        self._attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE
        self._attr_target_temperature_step = 0.5 # API dice int(temp * 10), ma UI HA preferisce 0.5 o 0.1
        self._attr_min_temp = 10.0
        self._attr_max_temp = 35.0

    @property
    def _zone_data(self) -> dict[str, Any]:
        """Ottiene i dati aggiornati per questa zona dal coordinator."""
        for zone in self.coordinator.data.get("Zones", []):
            if zone["ZoneId"] == self._id:
                return zone
        return {}

    @property
    def name(self) -> str:
        return self._name

    @property
    def temperature_unit(self) -> str:
        return "°C"

    @property
    def hvac_mode(self) -> HVACMode:
        # IsOFF nel JSON è booleano
        return HVACMode.OFF if self._zone_data.get("IsOFF") is True else HVACMode.HEAT

    @property
    def current_temperature(self) -> float | None:
        val = self._zone_data.get("Temp")
        if val is not None:
             return float(val) / 10
        return None

    @property
    def target_temperature(self) -> float | None:
        val = self._zone_data.get("SetTemp")
        if val is not None:
            return float(val) / 10
        return None

    @property
    def current_humidity(self) -> float | None:
        val = self._zone_data.get("Umd")
        if val is not None:
            return float(val) / 10
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        return {
            "last_update": self.coordinator.data.get("last_update")
        }

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Imposta una nuova temperatura target."""
        temp = kwargs.get("temperature")
        if temp is None:
            return
            
        _LOGGER.debug("Invio comando temperatura per %s: %s gradi", self._name, temp)
        
        if await self._api.set_temperature(self._id, self._name, temp):
            # Richiediamo un aggiornamento immediato dopo il comando
            await self.coordinator.async_request_refresh()
    
    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Accende o spegne la zona."""
        _LOGGER.debug("Impostazione modalità HVAC per %s: %s", self._name, hvac_mode)
        
        is_off = (hvac_mode == HVACMode.OFF)
        temp = self.target_temperature
        
        if temp is not None and await self._api.set_temperature(self._id, self._name, temp, is_off):
             await self.coordinator.async_request_refresh()
