"""Configuration de vmc_stiebel : l'utilisateur saisit ses identifiants MyStiebel dans l'interface."""
from __future__ import annotations

import uuid
from collections.abc import Mapping
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import TextSelector, TextSelectorConfig, TextSelectorType

from .api import ApiError, AuthError, MyStiebelLecture
from .const import CONF_CLIENT_ID, CONF_INSTALLATION_ID, DOMAIN

MOT_DE_PASSE = TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD))
SCHEMA = vol.Schema({
    vol.Required(CONF_USERNAME): TextSelector(TextSelectorConfig(type=TextSelectorType.EMAIL)),
    vol.Required(CONF_PASSWORD): MOT_DE_PASSE,
})


class VmcStiebelConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def _verifier(self, username: str, password: str, client_id: str) -> list[dict[str, Any]]:
        api = MyStiebelLecture(async_get_clientsession(self.hass), username, password, client_id)
        # Seules les installations au profil LWZx80 (VMC VRC-W) sont proposées
        return [i for i in await api.installations()
                if "LWZ" in str((i.get("profile") or {}).get("name", ""))]

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            client_id = str(uuid.uuid4())
            try:
                vmc = await self._verifier(user_input[CONF_USERNAME], user_input[CONF_PASSWORD], client_id)
            except AuthError:
                errors["base"] = "invalid_auth"
            except ApiError:
                errors["base"] = "cannot_connect"
            else:
                if len(vmc) != 1:
                    errors["base"] = "no_device"
                else:
                    await self.async_set_unique_id(str(vmc[0]["id"]))
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(
                        title="VMC double flux",
                        data={**user_input, CONF_CLIENT_ID: client_id, CONF_INSTALLATION_ID: vmc[0]["id"]},
                    )
        return self.async_show_form(step_id="user", data_schema=SCHEMA, errors=errors)

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> ConfigFlowResult:
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        entry = self._get_reauth_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                await self._verifier(entry.data[CONF_USERNAME], user_input[CONF_PASSWORD], entry.data[CONF_CLIENT_ID])
            except AuthError:
                errors["base"] = "invalid_auth"
            except ApiError:
                errors["base"] = "cannot_connect"
            else:
                return self.async_update_reload_and_abort(entry, data_updates={CONF_PASSWORD: user_input[CONF_PASSWORD]})
        return self.async_show_form(step_id="reauth_confirm",
                                    data_schema=vol.Schema({vol.Required(CONF_PASSWORD): MOT_DE_PASSE}), errors=errors)
