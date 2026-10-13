"""Diagnostics: property thô + lõi lọc đã phân tích (che SĐT/mật khẩu/serial)."""
from __future__ import annotations

from dataclasses import asdict
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from . import KarofiConfigEntry
from .const import CONF_PASSWORD, CONF_PHONE

TO_REDACT = {CONF_PHONE, CONF_PASSWORD, "serial", "house"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: KarofiConfigEntry
) -> dict[str, Any]:
    coordinator = entry.runtime_data
    devices = []
    for dev in (coordinator.data or {}).values():
        item = asdict(dev)
        item["derived"] = {
            "status": dev.status,
            "error_codes": dev.error_codes,
            "water_quality": dev.water_quality,
            "cores": [
                {
                    "position": c.position,
                    "days_left": c.days_left,
                    "days_total": c.days_total,
                    "percent_left": c.percent_left,
                    "needs_replacement": c.needs_replacement,
                }
                for c in dev.cores
            ],
        }
        devices.append(item)
    return async_redact_data(
        {
            "entry": {"data": dict(entry.data), "options": dict(entry.options)},
            "last_update_success": coordinator.last_update_success,
            "last_update_success_time": str(coordinator.last_update_success_time),
            "failed_updates": coordinator.failed_updates,
            "devices": devices,
        },
        TO_REDACT,
    )
