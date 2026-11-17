# vmc_stiebel – STIEBEL ELTRON VRC-W ventilation in Home Assistant (MyStiebel cloud)

Unofficial Home Assistant custom integration for the **STIEBEL ELTRON VRC-W 450 Premium** heat-recovery
ventilation unit (MVHR) with built-in Wi-Fi, through the **MyStiebel cloud** (the same cloud as the
MyStiebel app). In the cloud this unit uses the installation profile **"LWZx80"**.

Derived from [MyStiebel](https://github.com/sanderkwantes/mystiebel) by Sander Kwantes (Apache 2.0),
which supports the WWK hot-water heat pump. See `NOTICE.md`.

> ⚠️ Unofficial, undocumented API, tested on **one** VRC-W 450 Premium only. Use at your own risk.
> Entity names and code comments are in French (the author's language).

## What it does

- Reads registers **2553-2565** every 2 minutes and the installation info (online, alarms, firmware)
  every 5 minutes.
- Lets you change **one** thing: the requested ventilation mode (register 2565), through a `select`
  and a `button`.
- No local access: the unit only exposes a proprietary TLS port on the LAN, no Modbus, HTTP or MQTT.

## Installation

1. Copy `custom_components/vmc_stiebel/` into the `custom_components/` folder of your Home Assistant
   configuration (or add this repository to HACS as a custom repository, type "Integration").
2. Restart Home Assistant.
3. Settings → Devices & services → Add integration → **VMC Stiebel**, then enter your MyStiebel
   e-mail and password. Only an installation whose profile name contains "LWZ" is accepted (exactly one).
4. A wrong password later triggers the standard re-authentication flow.

Your credentials are stored in the Home Assistant config entry only (as for any cloud integration).

## Entities

| Entity (French name) | Meaning |
|---|---|
| sensor "Humidité air extrait" | extract air humidity, % (2553) |
| sensor "Température air extrait" | extract air temperature, °C (2554) |
| sensor "Niveau appliqué" | fan level actually applied, 0-3 (2564) |
| sensor "Mode demandé" (diagnostic) | requested mode, 0-4 (2565) |
| sensor "Intensif temps restant" | intensive ventilation time left, min (2557) |
| sensor "Intensif durée réglée" (diagnostic) | intensive ventilation duration setting, min (2563) |
| sensor "Filtre jours restants" | days before filter change (2558) |
| sensors "Registre 2556 / 2559-2562" (diagnostic) | unknown, always 0 so far |
| sensor "Alarmes actives" (diagnostic) | active alarms count (cloud `status`) |
| binary_sensor "En ligne" | unit connected to the cloud |
| binary_sensor "Intensif en cours" | 2557 > 0 |
| binary_sensor "Bypass" | bypass damper open (2555 = 1) |
| binary_sensor "Alarme" | at least one active alarm |
| select "Niveau de ventilation" | writes 2565: `1 · Réduit`, `2 · Normal`, `3 · Intensif 30 min`, `Programme horaire` (4) |
| button "Protection humidité" | writes 0 to 2565 |

The select does not offer 0; it only shows `0 · Protection humidité` while the unit is in that mode.
Put the button behind a confirmation on your dashboard.

## Known registers (profile LWZx80)

| Register | Role | Range (from the cloud) |
|---|---|---|
| 2553 | extract air relative humidity, % | |
| 2554 | extract air temperature, °C | |
| 2555 | **bypass state**: 0 closed, 1 open (follows the real damper, not the bypass mode chosen on the console) | |
| 2556 | unknown, always 0 | |
| 2557 | intensive ventilation time remaining, min (countdown) | 0-240 |
| 2558 | days before filter change | |
| 2559-2562 | unknown, always 0 | |
| 2563 | intensive ventilation duration setting, min (30) | |
| 2564 | **applied** fan level 0-3 (3 during intensive) — **read-only**: `setValues` is refused with `errorCode -32802` | 0-3 |
| 2565 | **requested mode**, **writable**: 0 = humidity protection, 1-2 = fan levels, 3 = 30-min intensive, 4 = time program | 0-4 |

- Writing **3** to 2565 starts the intensive ventilation for the duration in 2563 (30 min), then the unit
  goes back to its previous mode by itself; writing another value interrupts it. This is what the
  app's "start intensive" button does.
- **0 = "Protection humidité"**: fans stop and restart by themselves if the humidity gets high.
  **This is not a power cut** — switch the unit off at the breaker before changing the filter or
  opening it.
- In time-program mode (4), 2564 follows the level applied by the program.
- Scanned read-only from 0 to 65599: apart from 2553-2565, only system registers from 65523 upwards
  (software versions, IDs) answer. The **bypass mode** (console setting) and the console values
  (outdoor air, supply/exhaust temperatures, fan speeds, flows, pressures) are **not** in the cloud.
- Non-existent registers come back with `displayValue: null`; `getValues` also returns
  `minDisplayValue` / `maxDisplayValue`.

## Write safeguards

- Only the JSON-RPC methods `Login`, `getValues` and `setValues` can be sent (whitelist; no `Subscribe`).
- `setValues` is only possible on register **2565**, with an **integer from 0 to 4**, checked
  **before** anything is sent.
- One value per call, **no retry**, one write at a time, at least 10 s between two writes.
- A write is accepted only if the reply is exactly a list for register 2565 without `errorCode`
  (observed: `[{"registerIndex": 2565}]`). Any other reply or any error **blocks all further writes**
  until the integration is reloaded, and creates a persistent notification. Reading continues.
- The value is re-read 40 s after a write (the unit applies it in less than 30 s).
- Every write is appended to `vmc_stiebel_writes.log` in the configuration folder (time, value,
  previous value, reply; installation id masked) and to the Home Assistant log.

## Limits

- Cloud only: no data and no control when the MyStiebel cloud or your Internet connection is down.
- Values lag a few minutes behind the unit; polling every 2 minutes.
- The bypass can only be read (state), not set; its mode is not exposed.
- Flow rates, outdoor temperature and fan speeds are not available.
- Tested on a VRC-W 450 Premium only; other LWZ profiles may use different registers.
- The API may change at any time and break the integration.

## Credits and license

Apache License 2.0 — see `LICENSE` and `NOTICE.md`. Based on the work of Sander Kwantes
([MyStiebel](https://github.com/sanderkwantes/mystiebel)). Not affiliated with STIEBEL ELTRON.
