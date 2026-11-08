"""Constantes Domogotchi."""

from __future__ import annotations

DOMAIN = "domogotchi"
VERSION = "2026.11.2"

CONF_NAME = "name"
CONF_LIGHTS = "lights"
CONF_TEMPERATURE = "temperature_sensor"
CONF_PRESENCE = "presence"
CONF_POWER = "power_sensor"
CONF_POWER_THRESHOLD = "power_threshold"
CONF_WEATHER = "weather"
CONF_COMFORT_MIN = "comfort_min"
CONF_COMFORT_MAX = "comfort_max"

DEFAULT_NAME = "Domo"
DEFAULT_POWER_THRESHOLD = 3000
DEFAULT_COMFORT_MIN = 18.0
DEFAULT_COMFORT_MAX = 24.0

STORAGE_VERSION = 1
CARD_URL = "/domogotchi_static/domogotchi-card.js"

SERVICE_RESET = "reset"
ATTR_CONFIG_ENTRY_ID = "config_entry_id"

BUTTON_KEYS = ("nourrir", "jouer", "nettoyer", "soigner")
