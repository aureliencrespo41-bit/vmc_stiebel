"""vmc_stiebel : VMC STIEBEL ELTRON VRC-W 450 Premium via le cloud MyStiebel.

Lecture des registres ; une seule écriture possible : le mode demandé (registre 2565),
par le sélecteur de niveau et le bouton « Protection humidité » (0).

Dérivé de sanderkwantes/mystiebel v1.2.1 (Apache 2.0), voir NOTICE.md et LICENSE.
"""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import MyStiebelLecture
from .const import CONF_CLIENT_ID
from .coordinator import VmcCoordinator

PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR, Platform.SELECT, Platform.BUTTON]

type VmcConfigEntry = ConfigEntry[VmcCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: VmcConfigEntry) -> bool:
    api = MyStiebelLecture(async_get_clientsession(hass), entry.data[CONF_USERNAME],
                           entry.data[CONF_PASSWORD], entry.data[CONF_CLIENT_ID])
    coordinator = VmcCoordinator(hass, entry, api)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: VmcConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
