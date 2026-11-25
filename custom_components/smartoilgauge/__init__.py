"""Smart Oil Gauge integration for Home Assistant."""
from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import SmartOilGaugeAuthError, SmartOilGaugeClient, SmartOilGaugeError
from .const import DOMAIN, SCAN_INTERVAL_MINUTES

_LOGGER = logging.getLogger(__name__)
PLATFORMS = ["sensor"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    client = SmartOilGaugeClient(entry.data["username"], entry.data["password"])
    try:
        await client.login()
    except SmartOilGaugeAuthError as err:
        await client.close()
        raise ConfigEntryAuthFailed(str(err)) from err
    except SmartOilGaugeError as err:
        await client.close()
        raise ConfigEntryNotReady(str(err)) from err

    async def async_update_data():
        try:
            tanks = await client.get_tanks()
        except SmartOilGaugeAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except SmartOilGaugeError as err:
            raise UpdateFailed(str(err)) from err
        _LOGGER.debug("Smart Oil Gauge tanks: %s", tanks)
        return {str(t.get("tank_id")): t for t in tanks}

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=DOMAIN,
        update_method=async_update_data,
        update_interval=timedelta(minutes=SCAN_INTERVAL_MINUTES),
    )
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = (client, coordinator)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        client, _ = hass.data[DOMAIN].pop(entry.entry_id)
        await client.close()
    return unload_ok
