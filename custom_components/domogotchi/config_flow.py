"""Assistant de configuration Domogotchi."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_COMFORT_MAX,
    CONF_COMFORT_MIN,
    CONF_LIGHTS,
    CONF_NAME,
    CONF_POWER,
    CONF_POWER_THRESHOLD,
    CONF_PRESENCE,
    CONF_TEMPERATURE,
    CONF_WEATHER,
    DEFAULT_COMFORT_MAX,
    DEFAULT_COMFORT_MIN,
    DEFAULT_NAME,
    DEFAULT_POWER_THRESHOLD,
    DOMAIN,
)


def _house_schema(current: dict[str, Any]) -> dict:
    """Champs communs : les liens avec la maison réelle, tous facultatifs."""

    def sv(key: str, default=None) -> dict:
        value = current.get(key, default)
        return {"suggested_value": value} if value not in (None, [], "") else {}

    return {
        vol.Optional(CONF_LIGHTS, description=sv(CONF_LIGHTS)): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=["light", "switch"], multiple=True)
        ),
        vol.Optional(CONF_TEMPERATURE, description=sv(CONF_TEMPERATURE)): selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor", device_class=SensorDeviceClass.TEMPERATURE)
        ),
        vol.Optional(
            CONF_COMFORT_MIN, default=current.get(CONF_COMFORT_MIN, DEFAULT_COMFORT_MIN)
        ): selector.NumberSelector(
            selector.NumberSelectorConfig(min=5, max=30, step=0.5, unit_of_measurement="°C", mode=selector.NumberSelectorMode.BOX)
        ),
        vol.Optional(
            CONF_COMFORT_MAX, default=current.get(CONF_COMFORT_MAX, DEFAULT_COMFORT_MAX)
        ): selector.NumberSelector(
            selector.NumberSelectorConfig(min=10, max=35, step=0.5, unit_of_measurement="°C", mode=selector.NumberSelectorMode.BOX)
        ),
        vol.Optional(CONF_PRESENCE, description=sv(CONF_PRESENCE)): selector.EntitySelector(
            selector.EntitySelectorConfig(
                domain=["person", "device_tracker", "binary_sensor", "input_boolean", "zone"], multiple=True
            )
        ),
        vol.Optional(CONF_POWER, description=sv(CONF_POWER)): selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor", device_class=SensorDeviceClass.POWER)
        ),
        vol.Optional(
            CONF_POWER_THRESHOLD, default=current.get(CONF_POWER_THRESHOLD, DEFAULT_POWER_THRESHOLD)
        ): selector.NumberSelector(
            selector.NumberSelectorConfig(min=100, max=36000, step=100, unit_of_measurement="W", mode=selector.NumberSelectorMode.BOX)
        ),
        vol.Optional(CONF_WEATHER, description=sv(CONF_WEATHER)): selector.EntitySelector(
            selector.EntitySelectorConfig(domain="weather")
        ),
    }


def _validate(user_input: dict[str, Any]) -> dict[str, str]:
    errors: dict[str, str] = {}
    if float(user_input.get(CONF_COMFORT_MIN, DEFAULT_COMFORT_MIN)) >= float(
        user_input.get(CONF_COMFORT_MAX, DEFAULT_COMFORT_MAX)
    ):
        errors[CONF_COMFORT_MAX] = "comfort_range"
    return errors


class DomogotchiConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            errors = _validate(user_input)
            if not errors:
                name = user_input.pop(CONF_NAME).strip() or DEFAULT_NAME
                return self.async_create_entry(title=name, data={CONF_NAME: name}, options=user_input)
        schema = vol.Schema(
            {vol.Required(CONF_NAME, default=DEFAULT_NAME): selector.TextSelector(), **_house_schema(user_input or {})}
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return DomogotchiOptionsFlow()


class DomogotchiOptionsFlow(OptionsFlow):
    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            errors = _validate(user_input)
            if not errors:
                return self.async_create_entry(data=user_input)
        current = user_input or dict(self.config_entry.options)
        return self.async_show_form(
            step_id="init", data_schema=vol.Schema(_house_schema(current)), errors=errors
        )
