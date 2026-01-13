import logging
from typing import Any
from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorDeviceClass,
)
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .coordinator import ProAirDataUpdateCoordinator
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up the ProAir binary sensor platform."""
    coordinator: ProAirDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    
    entities = [
        ProAirSystemBinarySensor(coordinator, "IsCooling", "Cooling Mode", BinarySensorDeviceClass.COLD),
        ProAirSystemBinarySensor(coordinator, "IsOFF", "System Off", BinarySensorDeviceClass.POWER),
        ProAirSystemBinarySensor(coordinator, "Errors", "System Error", BinarySensorDeviceClass.PROBLEM),
    ]
    
    async_add_entities(entities, True)

class ProAirSystemBinarySensor(CoordinatorEntity[ProAirDataUpdateCoordinator], BinarySensorEntity):
    """Representation of a ProAir System Binary Sensor."""

    def __init__(
        self, 
        coordinator: ProAirDataUpdateCoordinator, 
        key: str, 
        name: str, 
        device_class: BinarySensorDeviceClass | None = None
    ) -> None:
        super().__init__(coordinator)
        self._key = key
        self._name_suffix = name
        self._attr_device_class = device_class
        self._attr_unique_id = f"proair_{coordinator.api.serial}_{key.lower()}"
        self._attr_name = f"ProAir {name}"

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""
        val = self.coordinator.data.get(self._key)
        
        if self._key == "Errors":
            return bool(val and int(str(val)) > 0)
            
        return bool(val)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        return {
            "last_update": self.coordinator.data.get("last_update")
        }
