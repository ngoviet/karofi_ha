"""Karofi 365 — máy lọc nước Karofi qua cloud app Karofi 365 (Phase 1: chỉ đọc)."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import KarofiApi, KarofiApiError, KarofiAuthError
from .const import (
    CONF_PASSWORD,
    CONF_PHONE,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from .coordinator import KarofiCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BINARY_SENSOR]

type KarofiConfigEntry = ConfigEntry[KarofiCoordinator]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup_entry(hass: HomeAssistant, entry: KarofiConfigEntry) -> bool:
    # Xác thực bằng Bearer token (không cookie) → dùng session chung của HA được.
    api = KarofiApi(
        async_get_clientsession(hass), entry.data[CONF_PHONE], entry.data[CONF_PASSWORD]
    )
    try:
        await api.login()
    except KarofiAuthError as err:
        raise ConfigEntryAuthFailed(str(err)) from err
    except KarofiApiError as err:
        raise ConfigEntryNotReady(str(err)) from err

    interval = int(entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL))
    coordinator = KarofiCoordinator(hass, api, entry, interval)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    _LOGGER.info("Karofi 365 ready: %d máy lọc %s", len(coordinator.data), list(coordinator.data))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: KarofiConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_update_listener(hass: HomeAssistant, entry: KarofiConfigEntry) -> None:
    """Đổi options → reload entry (không cần restart HA)."""
    await hass.config_entries.async_reload(entry.entry_id)
