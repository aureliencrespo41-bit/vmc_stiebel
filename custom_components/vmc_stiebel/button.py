"""Bouton de vmc_stiebel : « Protection humidité » (écrit 0 dans le mode demandé, registre 2565).

Les ventilateurs s'arrêtent et redémarrent d'eux-mêmes si l'humidité devient élevée. Ce n'est pas
une coupure : pour changer le filtre ou intervenir dans la VMC, couper au disjoncteur.
"""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import VmcConfigEntry
from .coordinator import VmcCoordinator
from .entity import VmcEntite


async def async_setup_entry(hass: HomeAssistant, entry: VmcConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    async_add_entities([VmcProtectionHumidite(entry.runtime_data)])


class VmcProtectionHumidite(VmcEntite, ButtonEntity):
    """Passe la VMC en protection humidité (2565 = 0), avec les garde-fous du coordinateur."""

    _attr_icon = "mdi:fan-off"

    def __init__(self, coordinator: VmcCoordinator) -> None:
        super().__init__(coordinator, "protection_humidite", "Protection humidité")

    async def async_press(self) -> None:
        await self.coordinator.async_ecrire_mode(0)
