"""Coordinateur de vmc_stiebel : registres toutes les 2 min, installation toutes les 5 min,
et écriture du mode demandé (registre 2565) avec garde-fous."""
from __future__ import annotations

import asyncio
import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from homeassistant.components import persistent_notification
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import ApiError, AuthError, MyStiebelLecture
from .const import (
    CONF_INSTALLATION_ID,
    DELAI_ENTRE_ECRITURES,
    DOMAIN,
    INTERVALLE_INSTALLATION,
    INTERVALLE_REGISTRES,
    JOURNAL_ECRITURES,
    REG_NIVEAU_BIS,
    REGISTRES,
    RELECTURE_APRES_ECRITURE,
)

_LOGGER = logging.getLogger(__name__)


@dataclass
class DonneesVmc:
    registres: dict[int, float | None] = field(default_factory=dict)
    installation: dict[str, Any] = field(default_factory=dict)


class VmcCoordinator(DataUpdateCoordinator[DonneesVmc]):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, api: MyStiebelLecture) -> None:
        super().__init__(hass, _LOGGER, config_entry=entry, name=DOMAIN, update_interval=INTERVALLE_REGISTRES)
        self.api = api
        self.installation_id = entry.data[CONF_INSTALLATION_ID]
        self._installation: dict[str, Any] = {}
        self._installation_lue: datetime | None = None
        # Écriture : une à la fois, espacées, et bloquées après la première erreur jusqu'au rechargement
        self._verrou = asyncio.Lock()
        self._derniere_ecriture: datetime | None = None
        self.ecriture_bloquee: str | None = None
        self._annuler_relecture = None
        entry.async_on_unload(self._annuler)

    async def _async_update_data(self) -> DonneesVmc:
        try:
            maintenant = datetime.now()
            if self._installation_lue is None or maintenant - self._installation_lue >= INTERVALLE_INSTALLATION:
                trouvee = next((i for i in await self.api.installations()
                                if str(i.get("id")) == str(self.installation_id)), None)
                if trouvee is None:
                    raise UpdateFailed("installation introuvable dans le compte MyStiebel")
                self._installation, self._installation_lue = trouvee, maintenant
            registres = await self.api.lire(self.installation_id, REGISTRES)
        except AuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except ApiError as err:
            raise UpdateFailed(str(err)) from err
        return DonneesVmc(registres=registres, installation=self._installation)

    async def async_ecrire_mode(self, valeur: int) -> None:
        """Écrit le mode demandé (2565). Toute erreur bloque les écritures jusqu'au rechargement."""
        if self.ecriture_bloquee:
            raise HomeAssistantError(
                f"Écriture bloquée après une erreur ({self.ecriture_bloquee}). "
                "Rechargez l'intégration VMC Stiebel pour réessayer.")
        if self._verrou.locked():
            raise HomeAssistantError("Une écriture est déjà en cours.")
        async with self._verrou:
            if self._derniere_ecriture is not None:
                attente = DELAI_ENTRE_ECRITURES - (datetime.now() - self._derniere_ecriture).total_seconds()
                if attente > 0:
                    raise HomeAssistantError(f"Patientez {int(attente) + 1} s avant un nouveau changement.")
            self._derniere_ecriture = datetime.now()
            avant = self.data.registres.get(REG_NIVEAU_BIS) if self.data else None
            try:
                reponse = await self.api.ecrire(self.installation_id, REG_NIVEAU_BIS, valeur)
            except Exception as err:  # noqa: BLE001 - toute erreur : arrêt des écritures
                self.ecriture_bloquee = f"{type(err).__name__} : {err}"
                await self._journal({"registre": REG_NIVEAU_BIS, "valeur": valeur, "avant": avant,
                                     "resultat": "ERREUR", "detail": self.ecriture_bloquee})
                _LOGGER.error("Écriture du registre %s = %s refusée, écritures bloquées : %s",
                              REG_NIVEAU_BIS, valeur, err)
                persistent_notification.async_create(
                    self.hass,
                    f"L'écriture du niveau de ventilation ({valeur}) a échoué : {err}.\n\n"
                    "Les changements de niveau depuis HA sont **bloqués** jusqu'au rechargement de "
                    "l'intégration (Paramètres → Appareils et services → VMC Stiebel → ⋮ → Recharger). "
                    "La lecture continue. Vérifiez le niveau sur la console ou dans l'appli.",
                    title="VMC – écriture refusée", notification_id=f"{DOMAIN}_ecriture_refusee")
                self.async_update_listeners()
                raise HomeAssistantError(f"Écriture refusée : {err}") from err
            await self._journal({"registre": REG_NIVEAU_BIS, "valeur": valeur, "avant": avant,
                                 "resultat": "acceptée", "reponse": reponse})
            _LOGGER.info("Registre %s = %s écrit (avant : %s)", REG_NIVEAU_BIS, valeur, avant)
            # Affichage immédiat, puis relecture pour confirmer ce que la VMC a appliqué
            self.data.registres[REG_NIVEAU_BIS] = float(valeur)
            self.async_update_listeners()
            if self._annuler_relecture:
                self._annuler_relecture()
            self._annuler_relecture = async_call_later(self.hass, RELECTURE_APRES_ECRITURE, self._relire)

    async def _relire(self, _maintenant) -> None:
        self._annuler_relecture = None
        await self.async_request_refresh()

    def _annuler(self) -> None:
        if self._annuler_relecture:
            self._annuler_relecture()
            self._annuler_relecture = None

    async def _journal(self, donnees: dict[str, Any]) -> None:
        """Ajoute une ligne au journal des écritures (sans identifiant d'installation ni jeton)."""
        ligne = f"{datetime.now().isoformat(timespec='seconds')} {json.dumps(donnees, ensure_ascii=False)}\n"
        ligne = ligne.replace(str(self.installation_id), "***")
        chemin = self.hass.config.path(JOURNAL_ECRITURES)

        def _ecrire() -> None:
            os.makedirs(os.path.dirname(chemin), exist_ok=True)
            with open(chemin, "a", encoding="utf-8") as f:
                f.write(ligne)

        try:
            await self.hass.async_add_executor_job(_ecrire)
        except OSError as err:
            _LOGGER.warning("Journal des écritures impossible à écrire : %s", err)
