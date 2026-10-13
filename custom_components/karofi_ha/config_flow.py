"""Config flow (đăng nhập tài khoản Karofi 365) + reauth + options."""
from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import KarofiApi, KarofiApiError, KarofiAuthError
from .const import (
    CONF_PASSWORD,
    CONF_PHONE,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
)
from .models import iter_house_devices

_LOGGER = logging.getLogger(__name__)


async def _validate(hass: HomeAssistant, phone: str, password: str) -> tuple[str | None, dict]:
    """Đăng nhập thử. Trả (error_key, info) — info có user_id, devices."""
    api = KarofiApi(async_get_clientsession(hass), phone, password)
    try:
        await api.login()
        houses = await api.get_houses()
    except KarofiAuthError:
        return "invalid_auth", {}
    except KarofiApiError:
        return "cannot_connect", {}
    except Exception:  # noqa: BLE001
        _LOGGER.exception("karofi: lỗi không xác định khi đăng nhập")
        return "unknown", {}
    devices = [dev.get("seriNumber") for _h, _r, dev in iter_house_devices(houses)]
    return None, {"user_id": api.user_id, "devices": devices}


def _mask(phone: str) -> str:
    return phone[:3] + "****" + phone[-3:] if len(phone) >= 7 else phone


class KarofiConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            phone = user_input[CONF_PHONE].strip().replace(" ", "")
            error, info = await _validate(self.hass, phone, user_input[CONF_PASSWORD])
            if error is None and not info["devices"]:
                error = "no_devices"
            if error is None:
                await self.async_set_unique_id(str(info["user_id"] or phone))
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"Karofi 365 ({_mask(phone)})",
                    data={CONF_PHONE: phone, CONF_PASSWORD: user_input[CONF_PASSWORD]},
                )
            errors["base"] = error

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {vol.Required(CONF_PHONE): str, vol.Required(CONF_PASSWORD): str}
            ),
            errors=errors,
        )

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> ConfigFlowResult:
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        entry = self._get_reauth_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            phone = entry.data[CONF_PHONE]
            error, _info = await _validate(self.hass, phone, user_input[CONF_PASSWORD])
            if error is None:
                return self.async_update_reload_and_abort(
                    entry, data_updates={CONF_PASSWORD: user_input[CONF_PASSWORD]}
                )
            errors["base"] = error
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_PASSWORD): str}),
            description_placeholders={"phone": _mask(entry.data[CONF_PHONE])},
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return KarofiOptionsFlow()


class KarofiOptionsFlow(OptionsFlow):
    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        current = self.config_entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_SCAN_INTERVAL, default=current): vol.All(
                        vol.Coerce(int), vol.Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL)
                    )
                }
            ),
        )
