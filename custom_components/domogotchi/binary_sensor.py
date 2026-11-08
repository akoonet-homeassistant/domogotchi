"""Capteurs binaires Domogotchi."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import DomogotchiConfigEntry
from .engine import PetState
from .entity import DomogotchiEntity


@dataclass(frozen=True, kw_only=True)
class DomogotchiBinaryDescription(BinarySensorEntityDescription):
    value_fn: Callable[[PetState], bool]


BINARY_SENSORS = (
    DomogotchiBinaryDescription(
        key="malade",
        icon="mdi:emoticon-sick-outline",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=lambda p: p.sick,
    ),
    DomogotchiBinaryDescription(
        key="endormi",
        icon="mdi:sleep",
        value_fn=lambda p: p.alive and p.asleep,
    ),
    DomogotchiBinaryDescription(
        key="vivant",
        icon="mdi:home-heart",
        value_fn=lambda p: p.alive,
    ),
    DomogotchiBinaryDescription(
        key="besoin_attention",
        icon="mdi:bell-ring-outline",
        value_fn=lambda p: p.alive
        and not p.is_egg
        and (p.sick or min(p.satiety, p.happiness, p.cleanliness) < 25 or p.energy < 15),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DomogotchiConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(DomogotchiBinarySensor(coordinator, d) for d in BINARY_SENSORS)


class DomogotchiBinarySensor(DomogotchiEntity, BinarySensorEntity):
    entity_description: DomogotchiBinaryDescription

    def __init__(self, coordinator, description: DomogotchiBinaryDescription) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool:
        return self.entity_description.value_fn(self.coordinator.pet)
