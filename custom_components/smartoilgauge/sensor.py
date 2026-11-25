"""Sensor platform for Smart Oil Gauge."""
from __future__ import annotations

from datetime import datetime
import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, UnitOfVolume
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


def _num(val):
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


async def async_setup_entry(hass, entry, async_add_entities):
    _, coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = []
    for tank_id in coordinator.data:
        for cls in (GallonsSensor, PercentSensor, BatterySensor, LastReadSensor):
            entities.append(cls(coordinator, tank_id))
    async_add_entities(entities)


class _Base(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True
    key = ""

    def __init__(self, coordinator, tank_id: str) -> None:
        super().__init__(coordinator)
        self._tank_id = tank_id
        self._attr_unique_id = f"smartoilgauge_{tank_id}_{self.key}"
        name = self.tank.get("tank_name") or f"Tank {tank_id}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, tank_id)},
            "name": f"{name} Oil Tank",
            "manufacturer": "Connected Consumer Fuel",
            "model": "Smart Oil Gauge",
        }

    @property
    def tank(self) -> dict:
        return (self.coordinator.data or {}).get(self._tank_id, {})

    @property
    def available(self) -> bool:
        return super().available and bool(self.tank)


class GallonsSensor(_Base):
    key = "gallons"
    _attr_name = "Oil level"
    _attr_device_class = SensorDeviceClass.VOLUME_STORAGE
    _attr_native_unit_of_measurement = UnitOfVolume.GALLONS
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 1
    _attr_icon = "mdi:oil"

    @property
    def native_value(self):
        return _num(self.tank.get("sensor_gallons"))

    @property
    def extra_state_attributes(self):
        t = self.tank
        return {
            "tank_capacity_gal": _num(t.get("nominal")),
            "sensor_status": t.get("sensor_status"),
        }


class PercentSensor(_Base):
    key = "percent"
    _attr_name = "Oil percent"
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 0
    _attr_icon = "mdi:gauge"

    @property
    def native_value(self):
        gal, cap = _num(self.tank.get("sensor_gallons")), _num(self.tank.get("nominal"))
        if gal is None or not cap:
            return None
        return round(gal / cap * 100, 1)


class BatterySensor(_Base):
    key = "battery"
    _attr_name = "Battery"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = ["good", "ok", "poor"]
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def native_value(self):
        val = (self.tank.get("battery") or "").strip().lower()
        return val if val in self._attr_options else None

    @property
    def icon(self):
        return {"good": "mdi:battery", "ok": "mdi:battery-50"}.get(
            self.native_value, "mdi:battery-alert"
        )


class LastReadSensor(_Base):
    key = "last_read"
    _attr_name = "Last reading"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def native_value(self) -> datetime | None:
        raw = self.tank.get("sensor_rt")
        if not raw:
            return None
        parsed = dt_util.parse_datetime(str(raw).replace(" ", "T", 1))
        if parsed is None:
            return None
        if parsed.tzinfo is None:  # app reports local time
            parsed = parsed.replace(tzinfo=dt_util.get_default_time_zone())
        return parsed
