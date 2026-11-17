# NOTICE

**vmc_stiebel** – Home Assistant custom integration for the STIEBEL ELTRON VRC-W 450 Premium
ventilation unit (MyStiebel cloud profile "LWZx80").

This work is derived from **MyStiebel** (https://github.com/sanderkwantes/mystiebel) by
Sander Kwantes (@sanderkwantes), version 1.2.1, licensed under the Apache License 2.0
(see `LICENSE`).

Parts taken from MyStiebel: the authentication flow (`/api/v1/Jwt/login`), the installation list
(`/api/v1/InstallationsInfo/own`), the WebSocket JSON-RPC exchange (`Login`, `getValues`,
`setValues` message format) and the app headers. They live in `api.py`.

Changes compared to the original (2026-11):
- code rewritten and reduced to the VRC-W: one short-lived WebSocket connection per read or write
  instead of a permanent connection, no `Subscribe`;
- the WWK parameter file was replaced by the VRC-W registers 2553-2565, identified by read-only scans;
- writing is limited to ONE register (2565, requested mode) and to the values 0-4, checked before
  anything is sent (see README);
- credentials are kept in the standard Home Assistant config entry.

This project is not affiliated with STIEBEL ELTRON or with the author of MyStiebel. The MyStiebel
API is undocumented and may change without notice.
