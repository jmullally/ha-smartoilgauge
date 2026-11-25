"""Config flow for Smart Oil Gauge."""
import voluptuous as vol
from homeassistant import config_entries

from .api import SmartOilGaugeAuthError, SmartOilGaugeClient, SmartOilGaugeError
from .const import DOMAIN

DATA_SCHEMA = vol.Schema(
    {vol.Required("username"): str, vol.Required("password"): str}
)


async def _validate(username: str, password: str) -> str | None:
    client = SmartOilGaugeClient(username, password)
    try:
        await client.login()
    except SmartOilGaugeAuthError:
        return "invalid_auth"
    except SmartOilGaugeError:
        return "cannot_connect"
    finally:
        await client.close()
    return None


class SmartOilGaugeConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            await self.async_set_unique_id(user_input["username"].lower())
            self._abort_if_unique_id_configured()
            error = await _validate(user_input["username"], user_input["password"])
            if error is None:
                return self.async_create_entry(title="Smart Oil Gauge", data=user_input)
            errors["base"] = error
        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )

    async def async_step_reauth(self, entry_data):
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input=None):
        errors = {}
        entry = self._get_reauth_entry()
        if user_input is not None:
            data = {**entry.data, "password": user_input["password"]}
            error = await _validate(data["username"], data["password"])
            if error is None:
                return self.async_update_reload_and_abort(entry, data=data)
            errors["base"] = error
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required("password"): str}),
            errors=errors,
        )
