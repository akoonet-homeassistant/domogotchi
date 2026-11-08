"""Domogotchi : une créature-maison à faire vivre dans Home Assistant."""

from __future__ import annotations

from pathlib import Path

import voluptuous as vol

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .const import ATTR_CONFIG_ENTRY_ID, CARD_URL, DOMAIN, SERVICE_RESET, VERSION
from .coordinator import DomogotchiCoordinator

PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR, Platform.BUTTON]
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

type DomogotchiConfigEntry = ConfigEntry[DomogotchiCoordinator]

RESET_SCHEMA = vol.Schema({vol.Optional(ATTR_CONFIG_ENTRY_ID): cv.string})


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Enregistre la carte et le service (une seule fois)."""
    if getattr(hass, "http", None) is not None:
        card = Path(__file__).parent / "frontend" / "domogotchi-card.js"
        await hass.http.async_register_static_paths(
            [StaticPathConfig(CARD_URL, str(card), False)]
        )
        add_extra_js_url(hass, f"{CARD_URL}?v={VERSION}")

    async def _reset(call: ServiceCall) -> None:
        wanted = call.data.get(ATTR_CONFIG_ENTRY_ID)
        entries = [
            e
            for e in hass.config_entries.async_entries(DOMAIN)
            if e.state is ConfigEntryState.LOADED and (wanted is None or e.entry_id == wanted)
        ]
        if not entries:
            raise ServiceValidationError(
                translation_domain=DOMAIN, translation_key="no_creature"
            )
        for entry in entries:
            await entry.runtime_data.async_reborn()

    hass.services.async_register(DOMAIN, SERVICE_RESET, _reset, schema=RESET_SCHEMA)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: DomogotchiConfigEntry) -> bool:
    coordinator = DomogotchiCoordinator(hass, entry)
    await coordinator.async_load()
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    entry.async_on_unload(coordinator.async_watch_house())
    entry.async_on_unload(entry.add_update_listener(_async_reload))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def _async_reload(hass: HomeAssistant, entry: DomogotchiConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: DomogotchiConfigEntry) -> bool:
    await entry.runtime_data.async_save_now()
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_entry(hass: HomeAssistant, entry: DomogotchiConfigEntry) -> None:
    coordinator = DomogotchiCoordinator(hass, entry)
    await coordinator.async_remove_store()
