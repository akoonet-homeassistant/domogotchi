"""Boutons Domogotchi : nourrir, jouer, nettoyer, soigner."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import DomogotchiConfigEntry, engine
from .entity import DomogotchiEntity


@dataclass(frozen=True, kw_only=True)
class DomogotchiButtonDescription(ButtonEntityDescription):
    action: Callable


BUTTONS = (
    DomogotchiButtonDescription(key="nourrir", icon="mdi:food-drumstick", action=engine.feed),
    DomogotchiButtonDescription(key="jouer", icon="mdi:soccer", action=engine.play),
    DomogotchiButtonDescription(key="nettoyer", icon="mdi:broom", action=engine.clean),
    DomogotchiButtonDescription(key="soigner", icon="mdi:medical-bag", action=engine.heal),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DomogotchiConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(DomogotchiButton(coordinator, d) for d in BUTTONS)


class DomogotchiButton(DomogotchiEntity, ButtonEntity):
    entity_description: DomogotchiButtonDescription

    def __init__(self, coordinator, description: DomogotchiButtonDescription) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    async def async_press(self) -> None:
        await self.coordinator.async_do(self.entity_description.action)
