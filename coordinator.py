import logging
from datetime import timedelta
import async_timeout

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant.exceptions import ConfigEntryAuthFailed # Import this!

from .api import ProAirAPI, ProAirAuthError, ProAirConnectionError
from .const import DOMAIN, UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)

class ProAirDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching ProAir data."""

    def __init__(self, hass: HomeAssistant, api: ProAirAPI):
        """Initialize."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=UPDATE_INTERVAL),
        )
        self.api = api

    async def _async_update_data(self):
        """Fetch data from API endpoint."""
        try:
            # Note: asyncio.timeout is preferred over async_timeout in newer HA versions, 
            # but async_timeout is safer for compatibility if we don't know the strictly required version.
            # However standard practice is keeping it simple.
            async with async_timeout.timeout(30):
                data = await self.api.get_state()
                if data:
                    from datetime import datetime
                    data["last_update"] = datetime.now().isoformat()
                return data
        except ProAirAuthError as err:
            raise ConfigEntryAuthFailed from err
        except ProAirConnectionError as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err
