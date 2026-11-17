"""Capteurs de vmc_stiebel."""
from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, EntityCategory, UnitOfTemperature, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import VmcConfigEntry
from .const import (
    REG_FILTRE_JOURS,
    REG_HUMIDITE,
    REG_INCONNUS,
    REG_INTENSIF_DUREE,
    REG_INTENSIF_RESTANT,
    REG_NIVEAU,
    REG_NIVEAU_BIS,
    REG_TEMPERATURE,
)
from .coordinator import VmcCoordinator
from .entity import VmcEntite


@dataclass(frozen=True, kw_only=True)
class Registre(SensorEntityDescription):
    registre: int
    entier: bool = False


CAPTEURS = [
    Registre(key="humidite_air_extrait", name="Humidité air extrait", registre=REG_HUMIDITE,
             device_class=SensorDeviceClass.HUMIDITY, native_unit_of_measurement=PERCENTAGE,
             state_class=SensorStateClass.MEASUREMENT),
    Registre(key="temperature_air_extrait", name="Température air extrait", registre=REG_TEMPERATURE,
             device_class=SensorDeviceClass.TEMPERATURE, native_unit_of_measurement=UnitOfTemperature.CELSIUS,
             state_class=SensorStateClass.MEASUREMENT),
    Registre(key="niveau_ventilation", name="Niveau appliqué", registre=REG_NIVEAU, entier=True,
             icon="mdi:fan", state_class=SensorStateClass.MEASUREMENT),
    Registre(key="intensif_temps_restant", name="Intensif temps restant", registre=REG_INTENSIF_RESTANT,
             entier=True, icon="mdi:timer-sand", native_unit_of_measurement=UnitOfTime.MINUTES,
             state_class=SensorStateClass.MEASUREMENT),
    Registre(key="filtre_jours_restants", name="Filtre jours restants", registre=REG_FILTRE_JOURS,
             entier=True, icon="mdi:air-filter", native_unit_of_measurement=UnitOfTime.DAYS,
             state_class=SensorStateClass.MEASUREMENT),
    Registre(key="intensif_duree", name="Intensif durée réglée", registre=REG_INTENSIF_DUREE, entier=True,
             icon="mdi:timer-cog-outline", native_unit_of_measurement=UnitOfTime.MINUTES,
             state_class=SensorStateClass.MEASUREMENT, entity_category=EntityCategory.DIAGNOSTIC),
    # Mode demandé (2565, écrit par le sélecteur) et registres inconnus : activés mais en diagnostic
    Registre(key="registre_2565", name="Mode demandé", registre=REG_NIVEAU_BIS, entier=True,
             state_class=SensorStateClass.MEASUREMENT, entity_category=EntityCategory.DIAGNOSTIC),
    *[Registre(key=f"registre_{r}", name=f"Registre {r}", registre=r,
               state_class=SensorStateClass.MEASUREMENT, entity_category=EntityCategory.DIAGNOSTIC)
      for r in REG_INCONNUS],
]


async def async_setup_entry(hass: HomeAssistant, entry: VmcConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator = entry.runtime_data
    entites: list[SensorEntity] = [VmcCapteur(coordinator, d) for d in CAPTEURS]
    entites.append(VmcAlarmes(coordinator))
    async_add_entities(entites)


class VmcCapteur(VmcEntite, SensorEntity):
    entity_description: Registre

    def __init__(self, coordinator: VmcCoordinator, description: Registre) -> None:
        super().__init__(coordinator, description.key, description.name)
        self.entity_description = description

    @property
    def native_value(self) -> float | int | None:
        v = self.coordinator.data.registres.get(self.entity_description.registre)
        if v is None:
            return None
        return int(v) if self.entity_description.entier else v


class VmcAlarmes(VmcEntite, SensorEntity):
    """Nombre d'alarmes actives d'après la liste des installations (status)."""

    _attr_icon = "mdi:alert-outline"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: VmcCoordinator) -> None:
        super().__init__(coordinator, "alarmes_actives", "Alarmes actives")

    @property
    def native_value(self) -> int | None:
        status = self.coordinator.data.installation.get("status") or {}
        return status.get("activeAlarms")

    @property
    def extra_state_attributes(self) -> dict:
        status = self.coordinator.data.installation.get("status") or {}
        return {k: status.get(k) for k in
                ("activeCriticalAlarms", "unreadErrors", "unreadWarnings", "unreadInfo")}
