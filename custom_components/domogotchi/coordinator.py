"""Coordinateur Domogotchi : fait vivre la créature minute par minute."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN, UnitOfPower
from homeassistant.core import Event, EventStateChangedData, HomeAssistant, callback
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from . import engine
from .const import (
    CONF_COMFORT_MAX,
    CONF_COMFORT_MIN,
    CONF_LIGHTS,
    CONF_POWER,
    CONF_POWER_THRESHOLD,
    CONF_PRESENCE,
    CONF_TEMPERATURE,
    CONF_WEATHER,
    DEFAULT_COMFORT_MAX,
    DEFAULT_COMFORT_MIN,
    DEFAULT_POWER_THRESHOLD,
    DOMAIN,
    STORAGE_VERSION,
)

_LOGGER = logging.getLogger(__name__)
_INVALID = (STATE_UNAVAILABLE, STATE_UNKNOWN, None, "")


class DomogotchiCoordinator(DataUpdateCoordinator[engine.PetState]):
    """Porte l'état de la créature et l'avance à chaque minute."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{DOMAIN}_{entry.entry_id}",
            update_interval=timedelta(minutes=1),
        )
        self._store: Store[dict] = Store(hass, STORAGE_VERSION, f"{DOMAIN}.{entry.entry_id}")
        now = dt_util.now()
        self.pet = engine.PetState(born=now.isoformat(), last_event_at=now.isoformat())
        self._last_tick: datetime = now

    # --- persistance -------------------------------------------------------
    async def async_load(self) -> None:
        data = await self._store.async_load()
        if not data:
            return
        try:
            self.pet = engine.PetState.from_dict(data["pet"])
            last = dt_util.parse_datetime(data.get("last_tick", ""))
            if last is not None:
                self._last_tick = last
        except (KeyError, TypeError, ValueError) as err:
            _LOGGER.warning("État Domogotchi illisible, nouvel œuf : %s", err)

    def _data_to_save(self) -> dict:
        return {"pet": self.pet.to_dict(), "last_tick": self._last_tick.isoformat()}

    async def async_save_now(self) -> None:
        await self._store.async_save(self._data_to_save())

    async def async_remove_store(self) -> None:
        await self._store.async_remove()

    # --- lecture de la maison ---------------------------------------------
    def _opt(self, key: str, default=None):
        return self.config_entry.options.get(key, default)

    def _float_state(self, entity_id: str | None) -> float | None:
        if not entity_id or (st := self.hass.states.get(entity_id)) is None or st.state in _INVALID:
            return None
        try:
            return float(st.state)
        except ValueError:
            return None

    def _lights_on(self) -> bool | None:
        states = [self.hass.states.get(e) for e in self._opt(CONF_LIGHTS, []) or []]
        valid = [s for s in states if s is not None and s.state not in _INVALID]
        if not valid:
            return None
        return any(s.state == "on" for s in valid)

    def _someone_home(self) -> bool | None:
        entities = self._opt(CONF_PRESENCE, []) or []
        if not entities:
            return None
        seen = False
        for entity_id in entities:
            st = self.hass.states.get(entity_id)
            if st is None or st.state in _INVALID:
                continue
            seen = True
            domain = entity_id.split(".", 1)[0]
            if domain in ("person", "device_tracker") and st.state == "home":
                return True
            if domain in ("binary_sensor", "input_boolean") and st.state == "on":
                return True
            if domain == "zone":
                try:
                    if int(float(st.state)) > 0:
                        return True
                except ValueError:
                    pass
        return False if seen else None

    def _power_w(self) -> float | None:
        entity_id = self._opt(CONF_POWER)
        value = self._float_state(entity_id)
        if value is None:
            return None
        st = self.hass.states.get(entity_id)
        if st and st.attributes.get("unit_of_measurement") == UnitOfPower.KILO_WATT:
            value *= 1000
        return value

    def _weather(self) -> str | None:
        entity_id = self._opt(CONF_WEATHER)
        if not entity_id or (st := self.hass.states.get(entity_id)) is None:
            return None
        return None if st.state in _INVALID else st.state

    def build_context(self, now: datetime) -> engine.Context:
        return engine.Context(
            lights_on=self._lights_on(),
            temperature=self._float_state(self._opt(CONF_TEMPERATURE)),
            someone_home=self._someone_home(),
            power_w=self._power_w(),
            weather=self._weather(),
            hour=now.hour,
            comfort_min=float(self._opt(CONF_COMFORT_MIN, DEFAULT_COMFORT_MIN)),
            comfort_max=float(self._opt(CONF_COMFORT_MAX, DEFAULT_COMFORT_MAX)),
            power_threshold=float(self._opt(CONF_POWER_THRESHOLD, DEFAULT_POWER_THRESHOLD)),
        )

    # --- boucle ------------------------------------------------------------
    async def _async_update_data(self) -> engine.PetState:
        now = dt_util.now()
        minutes = max(0.0, (now - self._last_tick).total_seconds() / 60)
        self._last_tick = now
        engine.tick(self.pet, minutes, self.build_context(now), now)
        self._store.async_delay_save(self._data_to_save, 30)
        return self.pet

    @callback
    def async_watch_house(self) -> Callable[[], None]:
        """Réagit tout de suite quand les lumières ou la présence changent."""
        watched = list(self._opt(CONF_LIGHTS, []) or []) + list(self._opt(CONF_PRESENCE, []) or [])
        if not watched:
            return lambda: None

        @callback
        def _changed(event: Event[EventStateChangedData]) -> None:
            self.hass.async_create_task(self.async_request_refresh())

        return async_track_state_change_event(self.hass, watched, _changed)

    async def async_do(self, action: Callable[[engine.PetState, datetime], engine.PetState]) -> None:
        """Applique une action après avoir mis la simulation à jour."""
        await self.async_refresh()
        result = action(self.pet, dt_util.now())
        self.pet = result
        self._store.async_delay_save(self._data_to_save, 5)
        self.async_set_updated_data(self.pet)

    async def async_reborn(self) -> None:
        now = dt_util.now()
        self.pet = engine.reborn(self.pet, now)
        self._last_tick = now
        await self.async_save_now()
        self.async_set_updated_data(self.pet)
