import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import aiohttp_client
from .api import ProAirAPI
from .const import DOMAIN, CONF_USERNAME, CONF_PASSWORD, CONF_DEVICE_ID

class ProAirConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Gestisce il flusso di configurazione ProAir."""
    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Primo step: inserimento credenziali."""
        errors = {}
        
        if user_input is not None:
            session = aiohttp_client.async_get_clientsession(self.hass)
            api = ProAirAPI(
                session,
                user_input[CONF_USERNAME], 
                user_input[CONF_PASSWORD], 
                user_input[CONF_DEVICE_ID]
            )
            try:
                # Validazione credenziali
                if await api.login():
                    return self.async_create_entry(
                        title=user_input[CONF_USERNAME], 
                        data=user_input
                    )
                errors["base"] = "invalid_auth"
            except Exception:
                errors["base"] = "cannot_connect"

        # Schema dei campi richiesti nel popup
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_USERNAME): str,
                vol.Required(CONF_PASSWORD): str,
                vol.Required(CONF_DEVICE_ID): str,
            }),
            errors=errors,
        )
