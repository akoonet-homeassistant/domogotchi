"""Capteurs Domogotchi."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import DomogotchiConfigEntry
from .const import BUTTON_KEYS, DOMAIN
from .engine import MOODS, STAGE_NAMES, PetState
from .entity import DomogotchiEntity


@dataclass(frozen=True, kw_only=True)
class DomogotchiSensorDescription(SensorEntityDescription):
    value_fn: Callable[[PetState], Any]


def _pct(attr: str) -> Callable[[PetState], float]:
    return lambda p: round(getattr(p, attr), 1)


GAUGES = (
    ("satiete", "satiety", "mdi:food-drumstick"),
    ("bonheur", "happiness", "mdi:emoticon-happy-outline"),
    ("energie", "energy", "mdi:battery-heart-variant"),
    ("sante", "health", "mdi:heart-pulse"),
    ("proprete", "cleanliness", "mdi:broom"),
)

SENSORS: tuple[DomogotchiSensorDescription, ...] = (
    *(
        DomogotchiSensorDescription(
            key=key,
            icon=icon,
            native_unit_of_measurement=PERCENTAGE,
            state_class=SensorStateClass.MEASUREMENT,
            suggested_display_precision=0,
            value_fn=_pct(attr),
        )
        for key, attr, icon in GAUGES
    ),
    DomogotchiSensorDescription(
        key="age",
        icon="mdi:cake-variant-outline",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.DAYS,
        suggested_display_precision=1,
        value_fn=lambda p: round(p.age_minutes / 1440, 2),
    ),
    DomogotchiSensorDescription(
        key="stade",
        icon="mdi:home-variant-outline",
        device_class=SensorDeviceClass.ENUM,
        options=STAGE_NAMES,
        value_fn=lambda p: p.stage,
    ),
    DomogotchiSensorDescription(
        key="humeur",
        icon="mdi:home-heart",
        device_class=SensorDeviceClass.ENUM,
        options=MOODS,
        value_fn=lambda p: p.mood,
    ),
    DomogotchiSensorDescription(
        key="generation",
        icon="mdi:family-tree",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda p: p.generation,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DomogotchiConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(DomogotchiSensor(coordinator, d) for d in SENSORS)


class DomogotchiSensor(DomogotchiEntity, SensorEntity):
    entity_description: DomogotchiSensorDescription

    def __init__(self, coordinator, description: DomogotchiSensorDescription) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> Any:
        return self.entity_description.value_fn(self.coordinator.pet)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Le capteur Humeur porte tout ce dont la carte a besoin."""
        if self.entity_description.key != "humeur":
            return None
        pet = self.coordinator.pet
        entry_id = self.coordinator.config_entry.entry_id
        registry = er.async_get(self.hass)
        buttons = {
            key: registry.async_get_entity_id("button", DOMAIN, f"{entry_id}_{key}")
            for key in BUTTON_KEYS
        }
        hatch_at = None
        if pet.alive and pet.is_egg:
            hatch_at = (dt_util.now() + timedelta(minutes=pet.minutes_to_hatch)).isoformat()
        return {
            "nom": self.coordinator.config_entry.title,
            "eclosion_le": hatch_at,
            "config_entry_id": entry_id,
            "stade": pet.stage,
            "age_heures": round(pet.age_hours, 1),
            "generation": pet.generation,
            "satiete": round(pet.satiety),
            "bonheur": round(pet.happiness),
            "energie": round(pet.energy),
            "sante": round(pet.health),
            "proprete": round(pet.cleanliness),
            "endormi": pet.asleep,
            "malade": pet.sick,
            "vivant": pet.alive,
            "froid": bool(pet.flags.get("cold")),
            "chaud": bool(pet.flags.get("hot")),
            "seul": bool(pet.flags.get("alone")),
            "stresse": bool(pet.flags.get("stressed")),
            "mauvais_temps": bool(pet.flags.get("bad_weather")),
            "beau_temps": bool(pet.flags.get("good_weather")),
            "dernier_evenement": pet.last_event,
            "dernier_evenement_le": pet.last_event_at,
            "naissance": pet.born,
            "boutons": buttons,
        }
