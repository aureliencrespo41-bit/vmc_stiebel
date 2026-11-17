"""Sélecteur du niveau de ventilation de vmc_stiebel : écrit le mode demandé (registre 2565).

Le 0 (« Protection humidité » à la console : ventilateurs arrêtés, redémarrage automatique si
l'humidité devient élevée) ne se choisit pas ici : il passe par le bouton « Protection humidité »
(à mettre derrière une confirmation sur le tableau de bord). Il n'apparaît dans la liste que pour afficher cet état.
« 3 · Intensif 30 min » écrit 3 : la VMC lance l'intensif pour la durée réglée (2563, 30 min) puis
revient d'elle-même au niveau précédent ; choisir un autre niveau l'interrompt (testé le 17/11/2026).
"""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import VmcConfigEntry
from .const import REG_NIVEAU, REG_NIVEAU_BIS
from .coordinator import VmcCoordinator
from .entity import VmcEntite

PROTECTION = "0 · Protection humidité"
OPTIONS = {1: "1 · Réduit", 2: "2 · Normal", 3: "3 · Intensif 30 min", 4: "Programme horaire"}
VALEUR_DE = {libelle: valeur for valeur, libelle in OPTIONS.items()}


async def async_setup_entry(hass: HomeAssistant, entry: VmcConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    async_add_entities([VmcNiveauSelect(entry.runtime_data)])


class VmcNiveauSelect(VmcEntite, SelectEntity):
    """Mode demandé (2565) : 1, 2, 3 ou programme horaire (4) ; 0 affiché seulement."""

    _attr_icon = "mdi:fan"

    def __init__(self, coordinator: VmcCoordinator) -> None:
        super().__init__(coordinator, "niveau_ventilation_select", "Niveau de ventilation")

    def _mode(self) -> int | None:
        v = self.coordinator.data.registres.get(REG_NIVEAU_BIS)
        return None if v is None else int(v)

    @property
    def options(self) -> list[str]:
        # HA n'affiche qu'une option de la liste : le 0 n'y figure que lorsqu'il est actif
        return [PROTECTION, *OPTIONS.values()] if self._mode() == 0 else list(OPTIONS.values())

    @property
    def current_option(self) -> str | None:
        m = self._mode()
        return PROTECTION if m == 0 else OPTIONS.get(m)

    @property
    def extra_state_attributes(self) -> dict:
        reg = self.coordinator.data.registres
        return {
            "mode_demande_2565": None if reg.get(REG_NIVEAU_BIS) is None else int(reg[REG_NIVEAU_BIS]),
            "niveau_applique_2564": None if reg.get(REG_NIVEAU) is None else int(reg[REG_NIVEAU]),
            "ecriture_bloquee": self.coordinator.ecriture_bloquee,
        }

    async def async_select_option(self, option: str) -> None:
        if option == PROTECTION:
            return  # déjà en protection humidité : rien à écrire
        if option not in VALEUR_DE:  # HA le vérifie déjà ; double garde-fou
            raise ValueError(f"option inconnue : {option}")
        await self.coordinator.async_ecrire_mode(VALEUR_DE[option])
