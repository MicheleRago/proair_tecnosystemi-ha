import logging
from typing import Any
from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from .coordinator import ProAirDataUpdateCoordinator
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up the ProAir sensor platform."""
    coordinator: ProAirDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    
    if coordinator.data and "Zones" in coordinator.data:
        sensors = []
        for zone in coordinator.data["Zones"]:
            # Check if humidity data is available (some older zones might not have it)
            if zone.get("Umd") is not None:
                sensors.append(ProAirHumiditySensor(coordinator, zone))
        
        # Add System Sensors
        sensors.extend([
            ProAirSystemSensor(coordinator, "FWVer", "Firmware Version", None),
            ProAirSystemSensor(coordinator, "Serial", "Serial Number", None),
            ProAirSystemSensor(coordinator, "OperatingModeCooling", "Operating Mode", None), 
        ])

        if sensors:
            async_add_entities(sensors, True)
    
class ProAirHumiditySensor(CoordinatorEntity[ProAirDataUpdateCoordinator], SensorEntity):
    """Representation of a ProAir Humidity Sensor."""

    _attr_device_class = SensorDeviceClass.HUMIDITY
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = PERCENTAGE

    def __init__(self, coordinator: ProAirDataUpdateCoordinator, zone_data: dict[str, Any]) -> None:
        super().__init__(coordinator)
        self._id = zone_data["ZoneId"]
        self._name = zone_data["Name"]
        self._attr_unique_id = f"proair_{coordinator.api.serial}_{zone_data['ZoneId']}_humidity"
        self._attr_name = f"{zone_data['Name']} Humidity"

    @property
    def _zone_data(self) -> dict[str, Any]:
        """Get updated zone data."""
        for zone in self.coordinator.data.get("Zones", []):
            if zone["ZoneId"] == self._id:
                return zone
        return {}

    @property
    def native_value(self) -> float | None:
        """Return the state of the sensor."""
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

class ProAirSystemSensor(CoordinatorEntity[ProAirDataUpdateCoordinator], SensorEntity):
    """Representation of a ProAir System Sensor."""

    def __init__(
        self, 
        coordinator: ProAirDataUpdateCoordinator, 
        key: str, 
        name: str, 
        device_class: SensorDeviceClass | None = None
    ) -> None:
        super().__init__(coordinator)
        self._key = key
        self._name_suffix = name
        self._attr_device_class = device_class
        self._attr_unique_id = f"proair_{coordinator.api.serial}_{key.lower()}"
        self._attr_name = f"ProAir {name}"

    @property
    def native_value(self) -> str | None:
        """Return the state of the sensor."""
        val = self.coordinator.data.get(self._key)
        if val is not None:
            return str(val)
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        return {
            "last_update": self.coordinator.data.get("last_update")
        }
