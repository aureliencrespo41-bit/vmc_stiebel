"""Capteurs binaires de vmc_stiebel."""
from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import VmcConfigEntry
from .const import REG_BYPASS, REG_INTENSIF_RESTANT
from .coordinator import VmcCoordinator
from .entity import VmcEntite


async def async_setup_entry(hass: HomeAssistant, entry: VmcConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator = entry.runtime_data
    async_add_entities([VmcEnLigne(coordinator), VmcIntensif(coordinator), VmcAlarme(coordinator),
                        VmcBypass(coordinator)])


class VmcEnLigne(VmcEntite, BinarySensorEntity):
    """VMC connectée au cloud (isOnline de la liste des installations)."""

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    def __init__(self, coordinator: VmcCoordinator) -> None:
        super().__init__(coordinator, "en_ligne", "En ligne")

    @property
    def is_on(self) -> bool | None:
        return self.coordinator.data.installation.get("isOnline")

    @property
    def extra_state_attributes(self) -> dict:
        return {"derniere_connexion_utc": self.coordinator.data.installation.get("lastOnlineUtc")}


class VmcIntensif(VmcEntite, BinarySensorEntity):
    """Intensif en cours = temps restant (registre 2557) > 0."""

    _attr_device_class = BinarySensorDeviceClass.RUNNING
    _attr_icon = "mdi:fan-plus"

    def __init__(self, coordinator: VmcCoordinator) -> None:
        super().__init__(coordinator, "intensif_en_cours", "Intensif en cours")

    @property
    def is_on(self) -> bool | None:
        v = self.coordinator.data.registres.get(REG_INTENSIF_RESTANT)
        return None if v is None else v > 0


class VmcBypass(VmcEntite, BinarySensorEntity):
    """Bypass ouvert = registre 2555 à 1 (état réel du volet, pas le mode choisi à la console)."""

    _attr_device_class = BinarySensorDeviceClass.OPENING

    def __init__(self, coordinator: VmcCoordinator) -> None:
        super().__init__(coordinator, "bypass", "Bypass")

    @property
    def is_on(self) -> bool | None:
        v = self.coordinator.data.registres.get(REG_BYPASS)
        return None if v is None else v > 0

    @property
    def icon(self) -> str:
        return "mdi:valve-open" if self.is_on else "mdi:valve-closed"


class VmcAlarme(VmcEntite, BinarySensorEntity):
    """Problème = au moins une alarme active (normale ou critique)."""

    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(self, coordinator: VmcCoordinator) -> None:
        super().__init__(coordinator, "alarme", "Alarme")

    @property
    def is_on(self) -> bool | None:
        status = self.coordinator.data.installation.get("status") or {}
        if "activeAlarms" not in status:
            return None
        return (status.get("activeAlarms") or 0) + (status.get("activeCriticalAlarms") or 0) > 0
