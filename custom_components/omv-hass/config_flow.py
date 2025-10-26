import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from .const import DOMAIN

DATA_SCHEMA = vol.Schema({
    vol.Required("host"): str,
    vol.Required("username"): str,
    vol.Required("password"): str,
})

class OpenMediaVaultConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    async def async_step_user(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="OpenMediaVault", data=user_input)
        return self.async_show_form(step_id="user", data_schema=DATA_SCHEMA)
