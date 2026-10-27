# Karofi 365 for Home Assistant

<!-- readme-axi type=ha -->

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/docs/faq/custom_repositories/)
[![Validate](https://github.com/ngoviet/karofi_ha/actions/workflows/validate.yml/badge.svg)](https://github.com/ngoviet/karofi_ha/actions/workflows/validate.yml)
[![Test](https://github.com/ngoviet/karofi_ha/actions/workflows/test.yml/badge.svg)](https://github.com/ngoviet/karofi_ha/actions/workflows/test.yml)
[![License: MIT](https://img.shields.io/github/license/ngoviet/karofi_ha)](LICENSE)

**English** · [Tiếng Việt](README.vi.md)

Brings a **Karofi water purifier** (Wi-Fi models managed with the **Karofi 365** app) into
Home Assistant through the `365api.karofi.com` cloud: TDS and water quality, machine status
and alerts, and the remaining life of every filter. The protocol was reverse-engineered from
the Karofi 365 app v2.2.98 — details in [docs/api-notes.md](docs/api-notes.md).

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=ngoviet&repository=karofi_ha&category=integration)

> 🇻🇳 Built and maintained by one person in Việt Nam — if it saves you time, please
> [support the project](#support-the-project).

## Features

- **Phase 1 — read-only.** No control, no filter reset.
- **Water** — TDS (ppm) and a water-quality rating with the same thresholds as the app.
- **Status and alerts** — machine status from the error codes, a general alert, water leak,
  inlet water, pump, tank full and flush valve.
- **Filters** — days remaining, percentage and a "replace" alert for every filter, using the
  app's warning thresholds.
- **Diagnostics** — connection and Wi-Fi signal.
- **No extra dependencies**, UI setup (config flow), re-authentication, options (update
  interval), diagnostics, English and Vietnamese UI.

## Supported devices

Tested on **KAQ-U98** (type `Aiotec_41`). Other purifiers that use the `iro_*` property set
work too; the older K365 line (`mlt_*`) is not supported yet. Requires **Home Assistant
2026.9** or newer.

## Installation

1. HACS → *Custom repositories* → add this repository (type *Integration*) → install
   **Karofi 365**, or copy `custom_components/karofi_ha` into `/config/custom_components/`.
2. Restart Home Assistant.

## Configuration

*Settings → Devices & Services → Add Integration → Karofi 365* → enter the phone number and
password of your Karofi 365 app account.

Options: update interval (default 60 s, 30–900 s).

## Entities

One set per purifier:

| Entity | Source | Notes |
|---|---|---|
| TDS (ppm) | `iro_tds` | |
| Water quality | TDS | Good (< 50) · Check water source (< 100) · Unsafe — same thresholds as the app |
| Status | `iro_errs` | Normal / Pump ran over 5 hours / Weak inlet water / Tank empty / No inlet water / Water leak / High TDS. Attribute `error_codes` |
| Alert (problem) | `iro_errs` | On when there is any error |
| Water leak (moisture) | error 5 | |
| Inlet water | `iro_nuocIn` | |
| Pump (running) | `iro_bom` | |
| Tank full · Flush valve | `iro_ketn` · `iro_vx` | `unknown` if the machine does not report them (KAQ-U98 does not) |
| Filter N remaining (days) | `iro_lTime / 24` | Attributes: filter name, total days, pump hours left/total |
| Filter N % | min(% by schedule, % by pump hours) | |
| Filter N replace (problem) | < 15 days left **or** < 50 pump hours left | Same warning thresholds as the app |
| Connection · Wi-Fi signal | `status`, `rssi` | Diagnostic |

## Troubleshooting

- **Cloud only** — needs internet access to `365api.karofi.com`; there is no local control.
- **Status, Alert and Water leak are `unknown`** — `iro_errs` empty or missing means the
  machine has not reported yet, so these entities are `unknown` (not "Normal" / off). A real
  empty array (`[]`) or all `"0"` is still normal.
- **Tank full / Flush valve are `unknown`** — the machine does not report them (KAQ-U98 does
  not).
- When reporting an issue, attach the integration's **diagnostics** (*Devices & Services →
  Karofi 365 → ⋮ → Download diagnostics*).

## Development

```bash
pip install -r requirements_test.txt
pytest
```

Deploy straight to HA over SSH: copy `.env.example` → `.env`, fill in `HA_HOST`/`HA_USER`/`HA_PASS`,
then run `python tools/deploy.py` and restart HA.

<!-- support:start -->
## Support the project

<p align="center">
  <img src="https://raw.githubusercontent.com/ngoviet/.github/main/assets/support/banner.svg" width="720" alt="Built and maintained by one person in Việt Nam">
</p>

<p align="center">
  <a href="https://buymeacoffee.com/ngoviet"><img src="https://raw.githubusercontent.com/ngoviet/.github/main/assets/support/btn-coffee.svg" height="56" alt="Buy me a coffee"></a>
  &nbsp;
  <a href="https://github.com/sponsors/ngoviet"><img src="https://raw.githubusercontent.com/ngoviet/.github/main/assets/support/btn-sponsors.svg" height="56" alt="GitHub Sponsors"></a>
</p>

<p align="center">
  <img src="https://raw.githubusercontent.com/ngoviet/.github/main/assets/support/vietqr-card.svg" width="300" alt="VietQR — MB Bank — NGO DUC VIET — 911051212">
  &nbsp;
  <img src="https://raw.githubusercontent.com/ngoviet/.github/main/assets/support/crypto-card.svg" width="300" alt="Crypto — BNB Smart Chain (BEP20) — 0xcbf0402b232cb24b4d998f09a4884f87b5f74750">
</p>

<p align="center"><b>Crypto wallet, BNB Smart Chain (BEP20) only:</b><br><code>0xcbf0402b232cb24b4d998f09a4884f87b5f74750</code></p>

<p align="center"><sub>🇻🇳 VietQR: scan with any Vietnamese banking app, transfer note <code>Ung ho karofi_ha</code>. Thank you for keeping this project alive!</sub></p>
<!-- support:end -->

## License

[MIT](LICENSE) © Ngô Đức Việt. Not affiliated with Karofi.
