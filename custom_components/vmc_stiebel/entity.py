"""Entité de base : un appareil « VMC double flux » par installation."""
from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import VmcCoordinator


class VmcEntite(CoordinatorEntity[VmcCoordinator]):
    _attr_has_entity_name = True

    def __init__(self, coordinator: VmcCoordinator, cle: str, nom: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.installation_id}_{cle}"
        self._attr_name = nom
        firmware = (coordinator.data.installation.get("firmware") or {}) if coordinator.data else {}
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, str(coordinator.installation_id))},
            name="VMC double flux",
            manufacturer="STIEBEL ELTRON",
            model="VRC-W 450 Premium (LWZx80)",
            sw_version=f"{firmware.get('normalizedFirmwareVersion')} · Wi-Fi {firmware.get('normalizedCommunicationFirmwareVersion')}",
        )
