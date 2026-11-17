"""Client MyStiebel : lecture, et une seule écriture possible (mode demandé, registre 2565).

Dérivé de sanderkwantes/mystiebel v1.2.1 (mystiebel_auth.py, websocket_client.py), Apache 2.0,
voir NOTICE.md. Modifié : connexion WebSocket ponctuelle (ouverte, lue ou écrite, refermée),
uniquement les méthodes Login, getValues et setValues ; setValues seulement par ecrire(), limité
à REGISTRES_ECRITURE / VALEURS_ECRITURE, une valeur par appel, sans nouvelle tentative.
"""
from __future__ import annotations

import base64
import json
import logging
import random
from datetime import datetime, timedelta
from typing import Any

import aiohttp

from .const import (
    APP_HEADERS,
    AUTH_URL,
    INSTALL_URL,
    METHODES_AUTORISEES,
    REGISTRES_ECRITURE,
    VALEURS_ECRITURE,
    WS_URL,
)

_LOGGER = logging.getLogger(__name__)
_TIMEOUT = aiohttp.ClientTimeout(total=30)


class AuthError(Exception):
    """Identifiants refusés par MyStiebel."""


class ApiError(Exception):
    """Erreur de communication avec le cloud MyStiebel."""


class EcritureRefusee(ApiError):
    """Écriture refusée par le cloud, ou réponse inattendue à setValues."""


class MyStiebelLecture:
    """Connexion, liste des installations, lecture de registres et écriture limitée (ecrire)."""

    def __init__(self, session: aiohttp.ClientSession, username: str, password: str, client_id: str) -> None:
        self._session = session
        self._username = username
        self._password = password
        self._client_id = client_id
        self._token: str | None = None
        self._expire: datetime | None = None

    async def _jeton(self) -> str:
        if self._token and self._expire and datetime.now() < self._expire - timedelta(minutes=5):
            return self._token
        payload = {"userName": self._username, "password": self._password,
                   "clientId": self._client_id, "rememberMe": True}
        try:
            async with self._session.post(AUTH_URL, json=payload, headers=APP_HEADERS, timeout=_TIMEOUT) as r:
                if r.status in (400, 401, 403):
                    raise AuthError(f"connexion refusée (HTTP {r.status})")
                r.raise_for_status()
                token = (await r.json()).get("token")
        except aiohttp.ClientError as err:
            raise ApiError(f"connexion : {err}") from err
        if not token:
            raise AuthError("aucun jeton reçu")
        self._token, self._expire = token, _expiration(token)
        return token

    def oublier_jeton(self) -> None:
        self._token = self._expire = None

    async def installations(self) -> list[dict[str, Any]]:
        headers = {**APP_HEADERS, "Authorization": f"Bearer {await self._jeton()}"}
        try:
            async with self._session.post(INSTALL_URL, json={"includeWithPendingUserAccesses": True},
                                          headers=headers, timeout=_TIMEOUT) as r:
                if r.status == 401:
                    self.oublier_jeton()
                    raise ApiError("jeton refusé")
                r.raise_for_status()
                return (await r.json()).get("items", [])
        except aiohttp.ClientError as err:
            raise ApiError(f"installations : {err}") from err

    async def lire(self, installation_id: int | str, registres: list[int]) -> dict[int, float | None]:
        """Ouvre le WebSocket, se connecte, lit les registres demandés, referme."""
        token = await self._jeton()
        headers = {**APP_HEADERS, "Authorization": f"Bearer {token}"}
        try:
            async with self._session.ws_connect(WS_URL, headers=headers) as ws:
                rep = await _envoyer(ws, "Login", {"clientId": installation_id, "jwt": token})
                if rep.get("result") is not True:
                    self.oublier_jeton()
                    raise ApiError("login WebSocket refusé")
                rep = await _envoyer(ws, "getValues", {"installationId": installation_id, "fields": registres})
        except (aiohttp.ClientError, TimeoutError) as err:
            raise ApiError(f"WebSocket : {err}") from err
        if "error" in rep:
            raise ApiError(f"getValues : {rep['error']}")
        valeurs: dict[int, float | None] = {}
        for champ in (rep.get("result") or {}).get("fields", []):
            brut = champ.get("displayValue")
            try:
                valeurs[int(champ["registerIndex"])] = None if brut is None else float(brut)
            except (KeyError, TypeError, ValueError):
                continue
        return valeurs

    async def ecrire(self, installation_id: int | str, registre: int, valeur: int) -> list[dict[str, Any]]:
        """Écrit UNE valeur dans UN registre autorisé. Aucune nouvelle tentative.

        Vérifié avant tout envoi : registre dans REGISTRES_ECRITURE, valeur entière dans VALEURS_ECRITURE.
        Accepté seulement si la réponse est une liste ne portant que sur ce registre, sans errorCode
        (forme vue le 17/11/2026 : [{"registerIndex": 2565}]). Sinon EcritureRefusee.
        """
        if registre not in REGISTRES_ECRITURE:
            raise EcritureRefusee(f"registre {registre} non modifiable")
        if isinstance(valeur, bool) or not isinstance(valeur, int) or valeur not in VALEURS_ECRITURE:
            raise EcritureRefusee(f"valeur {valeur!r} refusée (0 à 4 seulement)")
        token = await self._jeton()
        headers = {**APP_HEADERS, "Authorization": f"Bearer {token}"}
        try:
            async with self._session.ws_connect(WS_URL, headers=headers) as ws:
                rep = await _envoyer(ws, "Login", {"clientId": installation_id, "jwt": token})
                if rep.get("result") is not True:
                    self.oublier_jeton()
                    raise ApiError("login WebSocket refusé")
                rep = await _envoyer(ws, "setValues", {
                    "installationId": installation_id, "UUID": self._client_id,
                    "listenWithValuesChanged": True,
                    "fields": [{"registerIndex": registre, "displayValue": valeur}]})
        except (aiohttp.ClientError, TimeoutError) as err:
            raise ApiError(f"WebSocket : {err}") from err
        if "error" in rep:
            raise EcritureRefusee(f"setValues : {rep['error']}")
        res = rep.get("result")
        if not isinstance(res, list) or not res or not all(isinstance(x, dict) for x in res):
            raise EcritureRefusee(f"réponse inattendue : {res!r}")
        codes = sorted({x.get("errorCode") for x in res if x.get("errorCode") not in (None, 0)})
        if codes:
            raise EcritureRefusee(f"refusée par le cloud (errorCode {codes})")
        if not all(str(x.get("registerIndex")) == str(registre) for x in res):
            raise EcritureRefusee(f"réponse sur un autre registre : {res!r}")
        return res


async def _envoyer(ws: aiohttp.ClientWebSocketResponse, methode: str, params: dict[str, Any]) -> dict[str, Any]:
    if methode not in METHODES_AUTORISEES:
        raise RuntimeError(f"méthode interdite : {methode}")
    if methode == "Login":
        mid = 1
    elif methode == "setValues":  # identifiant long, comme mystiebel (SET_VALUE_MSG)
        mid = random.randint(1_000_000_000, 9_999_999_999)
    else:
        mid = random.randint(1_000_000, 9_999_999)
    await ws.send_json({"jsonrpc": "2.0", "id": mid, "method": methode, "params": params})
    while True:
        msg = await ws.receive(timeout=30)
        if msg.type != aiohttp.WSMsgType.TEXT:
            raise ApiError(f"WebSocket fermé ({msg.type})")
        data = json.loads(msg.data)
        if data.get("id") == mid:
            return data


def _expiration(token: str) -> datetime:
    try:
        partie = token.split(".")[1]
        charge = json.loads(base64.urlsafe_b64decode(partie + "=" * (-len(partie) % 4)))
        return datetime.fromtimestamp(float(charge["exp"]))
    except Exception:  # noqa: BLE001 - jeton opaque : 24 h par défaut, comme mystiebel
        return datetime.now() + timedelta(hours=24)
