import voluptuous as vol
from homeassistant import config_entries
from .api import ProAirAPI
from .const import DOMAIN

class ProAirConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Gestisce il flusso di configurazione ProAir."""
    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Primo step: inserimento credenziali."""
        errors = {}
        
        if user_input is not None:
            api = ProAirAPI(
                user_input["username"], 
                user_input["password"], 
                user_input["device_id"]
            )
            try:
                # Validazione credenziali
                if await api.login():
                    return self.async_create_entry(
                        title=user_input["username"], 
                        data=user_input
                    )
                errors["base"] = "invalid_auth"
            except Exception:
                errors["base"] = "cannot_connect"

        # Schema dei campi richiesti nel popup
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("username"): str,
                vol.Required("password"): str,
                vol.Required("device_id"): str,
            }),
            errors=errors,
        )
