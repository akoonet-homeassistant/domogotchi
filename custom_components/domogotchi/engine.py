"""Moteur de simulation Domogotchi.

Module volontairement indépendant de Home Assistant : il ne manipule que des
nombres et des chaînes, ce qui permet de le tester seul.

Toutes les vitesses sont des règles de jeu, pas des mesures : elles sont
regroupées ici pour être ajustées facilement.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime

# --- Règles de jeu (points par minute, échelle 0-100) -----------------------
HUNGER_RATE_AWAKE = 100 / (20 * 60)  # ~3 repas par jour
HUNGER_RATE_ASLEEP = HUNGER_RATE_AWAKE / 2
ENERGY_DRAIN = 100 / (16 * 60)  # 16 h d'éveil vident la batterie
ENERGY_RECOVERY = 100 / (7 * 60)  # 7 h de sommeil la remplissent
HAPPINESS_DRAIN = 100 / (24 * 60)  # ~2 parties de jeu par jour
HAPPINESS_DRAIN_ASLEEP = HAPPINESS_DRAIN / 4
CLEANLINESS_DRAIN = 100 / (30 * 60)  # un ménage par jour suffit
LONELY_DRAIN = 0.05
DISCOMFORT_DRAIN = 0.05
STRESS_DRAIN = 0.05
WEATHER_BAD_DRAIN = 0.03
WEATHER_GOOD_BOOST = 0.03
HEALTH_DRAIN = 100 / (48 * 60)  # par facteur de négligence actif
HEALTH_RECOVERY = 0.02
SICK_THRESHOLD = 30.0
EXTREME_COLD = 14.0
EXTREME_HOT = 28.0
MAX_CATCH_UP_MINUTES = 12 * 60  # rattrapage plafonné après un arrêt de HA

# Stades : (âge minimal en heures, nom)
STAGES: list[tuple[float, str]] = [
    (0.0, "oeuf"),
    (0.5, "cabane"),
    (24.0, "maisonnette"),
    (72.0, "maison"),
    (168.0, "villa"),
]

BAD_WEATHER = {"rainy", "pouring", "lightning", "lightning-rainy", "hail", "snowy", "snowy-rainy", "windy", "windy-variant", "exceptional"}
GOOD_WEATHER = {"sunny", "clear-night"}

MOODS = [
    "mort",
    "oeuf",
    "malade",
    "endormi",
    "affame",
    "fatigue",
    "froid",
    "chaud",
    "sale",
    "seul",
    "stresse",
    "triste",
    "content",
    "heureux",
]

STAGE_NAMES = [name for _, name in STAGES] + ["mort"]


@dataclass
class Context:
    """Ce que la maison réelle dit à la créature à cet instant."""

    lights_on: bool | None = None
    temperature: float | None = None
    someone_home: bool | None = None
    power_w: float | None = None
    weather: str | None = None
    hour: int = 12
    comfort_min: float = 18.0
    comfort_max: float = 24.0
    power_threshold: float = 3000.0

    @property
    def asleep(self) -> bool:
        if self.lights_on is not None:
            return not self.lights_on
        return self.hour >= 22 or self.hour < 7

    @property
    def cold(self) -> bool:
        return self.temperature is not None and self.temperature < self.comfort_min

    @property
    def hot(self) -> bool:
        return self.temperature is not None and self.temperature > self.comfort_max

    @property
    def alone(self) -> bool:
        return self.someone_home is False

    @property
    def stressed(self) -> bool:
        return self.power_w is not None and self.power_w > self.power_threshold


@dataclass
class PetState:
    """État persistant de la créature."""

    born: str = field(default_factory=lambda: datetime.now().isoformat())
    age_minutes: float = 0.0
    satiety: float = 80.0
    happiness: float = 80.0
    energy: float = 80.0
    health: float = 100.0
    cleanliness: float = 100.0
    sick: bool = False
    alive: bool = True
    asleep: bool = False
    generation: int = 1
    last_event: str = "eclosion"
    last_event_at: str = field(default_factory=lambda: datetime.now().isoformat())
    flags: dict = field(default_factory=dict)

    # --- dérivés -----------------------------------------------------------
    @property
    def age_hours(self) -> float:
        return self.age_minutes / 60

    @property
    def stage(self) -> str:
        if not self.alive:
            return "mort"
        current = STAGES[0][1]
        for min_hours, name in STAGES:
            if self.age_hours >= min_hours:
                current = name
        return current

    @property
    def is_egg(self) -> bool:
        return self.stage == "oeuf"

    @property
    def mood(self) -> str:
        if not self.alive:
            return "mort"
        if self.is_egg:
            return "oeuf"
        if self.sick:
            return "malade"
        if self.asleep:
            return "endormi"
        f = self.flags
        if self.satiety < 25:
            return "affame"
        if self.energy < 20:
            return "fatigue"
        if f.get("cold"):
            return "froid"
        if f.get("hot"):
            return "chaud"
        if self.cleanliness < 30:
            return "sale"
        if f.get("alone"):
            return "seul"
        if f.get("stressed"):
            return "stresse"
        if self.happiness < 35:
            return "triste"
        if min(self.satiety, self.happiness, self.energy, self.health) >= 70:
            return "heureux"
        return "content"

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> PetState:
        known = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        return cls(**known)


def _clamp(value: float) -> float:
    return max(0.0, min(100.0, value))


def _event(state: PetState, name: str, now: datetime) -> None:
    state.last_event = name
    state.last_event_at = now.isoformat()


def tick(state: PetState, minutes: float, ctx: Context, now: datetime | None = None) -> PetState:
    """Fait avancer la simulation de `minutes` minutes."""
    now = now or datetime.now()
    if not state.alive or minutes <= 0:
        return state
    minutes = min(minutes, MAX_CATCH_UP_MINUTES)

    was_egg = state.is_egg
    state.age_minutes += minutes
    state.flags = {
        "cold": ctx.cold,
        "hot": ctx.hot,
        "alone": ctx.alone,
        "stressed": ctx.stressed,
        "bad_weather": (ctx.weather or "") in BAD_WEATHER,
        "good_weather": (ctx.weather or "") in GOOD_WEATHER,
    }
    if was_egg:
        if not state.is_egg:
            _event(state, "eclosion", now)
        return state

    asleep = ctx.asleep
    if asleep != state.asleep:
        state.asleep = asleep
        _event(state, "endormi" if asleep else "reveil", now)

    m = minutes
    if asleep:
        state.satiety -= HUNGER_RATE_ASLEEP * m
        state.energy += ENERGY_RECOVERY * m
        state.happiness -= HAPPINESS_DRAIN_ASLEEP * m
    else:
        state.satiety -= HUNGER_RATE_AWAKE * m
        state.energy -= ENERGY_DRAIN * m
        state.happiness -= HAPPINESS_DRAIN * m
        if ctx.alone:
            state.happiness -= LONELY_DRAIN * m
        if ctx.stressed:
            state.happiness -= STRESS_DRAIN * m
        if state.flags["bad_weather"]:
            state.happiness -= WEATHER_BAD_DRAIN * m
        elif state.flags["good_weather"]:
            state.happiness += WEATHER_GOOD_BOOST * m
    if ctx.cold or ctx.hot:
        state.happiness -= DISCOMFORT_DRAIN * m
    state.cleanliness -= CLEANLINESS_DRAIN * m

    # Santé : chaque facteur de négligence actif la fait baisser.
    neglect = 0
    neglect += state.satiety <= 0
    neglect += state.cleanliness < 10
    neglect += state.energy <= 0
    neglect += state.happiness <= 0
    neglect += ctx.temperature is not None and (ctx.temperature < EXTREME_COLD or ctx.temperature > EXTREME_HOT)
    if neglect:
        state.health -= HEALTH_DRAIN * neglect * m
    elif not state.sick and min(state.satiety, state.happiness, state.energy, state.cleanliness) > 50:
        state.health += HEALTH_RECOVERY * m

    for attr in ("satiety", "happiness", "energy", "health", "cleanliness"):
        setattr(state, attr, _clamp(getattr(state, attr)))

    if not state.sick and state.health < SICK_THRESHOLD:
        state.sick = True
        _event(state, "malade", now)
    if state.health <= 0:
        state.alive = False
        state.sick = False
        _event(state, "mort", now)
    return state


# --- Actions -------------------------------------------------------------
def _can_act(state: PetState, now: datetime, allow_asleep: bool = False) -> bool:
    if not state.alive:
        _event(state, "refus_mort", now)
        return False
    if state.is_egg:
        _event(state, "refus_oeuf", now)
        return False
    if state.asleep and not allow_asleep:
        _event(state, "refus_dort", now)
        return False
    return True


def feed(state: PetState, now: datetime | None = None) -> PetState:
    now = now or datetime.now()
    if not _can_act(state, now):
        return state
    if state.satiety > 90:
        state.health = _clamp(state.health - 5)
        state.happiness = _clamp(state.happiness - 5)
        _event(state, "trop_mange", now)
        return state
    state.satiety = _clamp(state.satiety + 35)
    state.happiness = _clamp(state.happiness + 5)
    state.cleanliness = _clamp(state.cleanliness - 3)
    _event(state, "nourri", now)
    return state


def play(state: PetState, now: datetime | None = None) -> PetState:
    now = now or datetime.now()
    if not _can_act(state, now):
        return state
    if state.sick or state.energy < 10:
        _event(state, "refus_fatigue", now)
        return state
    state.happiness = _clamp(state.happiness + 30)
    state.energy = _clamp(state.energy - 10)
    state.satiety = _clamp(state.satiety - 5)
    _event(state, "joue", now)
    return state


def clean(state: PetState, now: datetime | None = None) -> PetState:
    now = now or datetime.now()
    if not _can_act(state, now, allow_asleep=True):
        return state
    state.cleanliness = 100.0
    _event(state, "nettoye", now)
    return state


def heal(state: PetState, now: datetime | None = None) -> PetState:
    now = now or datetime.now()
    if not _can_act(state, now, allow_asleep=True):
        return state
    if not state.sick and state.health >= 80:
        _event(state, "refus_pas_malade", now)
        return state
    state.health = _clamp(state.health + 30)
    if state.health >= SICK_THRESHOLD:
        state.sick = False
    state.happiness = _clamp(state.happiness - 5)  # personne n'aime le docteur
    _event(state, "soigne", now)
    return state


def reborn(state: PetState, now: datetime | None = None) -> PetState:
    now = now or datetime.now()
    fresh = PetState(generation=state.generation + 1)
    fresh.born = now.isoformat()
    _event(fresh, "nouvel_oeuf", now)
    return fresh
