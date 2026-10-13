"""API, config flow, setup và entity — HTTP được mock bằng aioclient_mock."""
from __future__ import annotations

import pytest
from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.karofi_ha.api import KarofiApi, KarofiApiError, KarofiAuthError
from custom_components.karofi_ha.const import DOMAIN

from .conftest import API, PHONE, SERIAL, SIGNIN_OK, detail_payload, houses_payload


async def test_login_body_matches_app(hass: HomeAssistant, cloud):
    api = KarofiApi(async_get_clientsession(hass), PHONE, "pw")
    await api.login()
    method, url, body, _headers = cloud.mock_calls[0]
    assert method == "POST" and str(url).endswith("app/user/signin")
    assert body == {"email": "", "phone": PHONE, "password": "pw", "country": "VI"}
    assert api.user_id == 4242


async def test_detail_sends_bearer(hass: HomeAssistant, cloud):
    api = KarofiApi(async_get_clientsession(hass), PHONE, "pw")
    data = await api.get_device_detail(SERIAL)
    assert data["seriNumber"] == SERIAL
    headers = cloud.mock_calls[-1][3]
    assert headers["Authorization"] == "Bearer tok-1"


async def test_wrong_password_is_auth_error(hass: HomeAssistant, aioclient_mock):
    aioclient_mock.post(
        API + "app/user/signin",
        json={"code": 400, "message": "Account not registered", "data": []},
    )
    api = KarofiApi(async_get_clientsession(hass), PHONE, "bad")
    with pytest.raises(KarofiAuthError):
        await api.login()


async def test_401_relogins_once(hass: HomeAssistant, aioclient_mock):
    aioclient_mock.post(API + "app/user/signin", json=SIGNIN_OK)
    aioclient_mock.get(
        API + f"app/device/detail/{SERIAL}",
        status=401,
        json={"error": {"code": 401, "message": "Chưa xác thực", "data": None}},
    )
    api = KarofiApi(async_get_clientsession(hass), PHONE, "pw")
    with pytest.raises(KarofiAuthError):
        await api.get_device_detail(SERIAL)
    signins = [c for c in aioclient_mock.mock_calls if str(c[1]).endswith("signin")]
    assert len(signins) == 2  # lần đầu + 1 lần đăng nhập lại


async def test_server_500_is_api_error(hass: HomeAssistant, aioclient_mock):
    aioclient_mock.post(API + "app/user/signin", json=SIGNIN_OK)
    aioclient_mock.get(
        API + f"app/device/detail/{SERIAL}",
        status=500,
        json={"error": {"code": 500, "message": "Lỗi xảy ra với Server", "data": None}},
    )
    api = KarofiApi(async_get_clientsession(hass), PHONE, "pw")
    with pytest.raises(KarofiApiError) as exc:
        await api.get_device_detail(SERIAL)
    assert not isinstance(exc.value, KarofiAuthError)


async def test_config_flow_creates_entry(hass: HomeAssistant, cloud):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"phone": "090 000 0001", "password": "pw"}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {"phone": PHONE, "password": "pw"}
    assert result["result"].unique_id == "4242"
    assert "0900000001" not in result["title"]


async def test_config_flow_invalid_auth(hass: HomeAssistant, aioclient_mock):
    aioclient_mock.post(
        API + "app/user/signin",
        json={"code": 400, "message": "Account not registered", "data": []},
    )
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"phone": PHONE, "password": "x"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}


async def _setup(hass: HomeAssistant) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN, unique_id="4242", data={"phone": PHONE, "password": "pw"}
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


def _state(hass: HomeAssistant, platform: str, key: str):
    from homeassistant.helpers import entity_registry as er

    entity_id = er.async_get(hass).async_get_entity_id(platform, DOMAIN, f"{SERIAL}_{key}")
    assert entity_id, key
    return hass.states.get(entity_id)


async def test_setup_creates_entities(hass: HomeAssistant, cloud):
    entry = await _setup(hass)
    assert entry.state is ConfigEntryState.LOADED

    assert _state(hass, "sensor", "tds").state == "3"
    assert _state(hass, "sensor", "water_quality").state == "good"
    status = _state(hass, "sensor", "status")
    assert status.state == "pump_overrun"
    assert status.attributes["error_codes"] == [1]
    ro = _state(hass, "sensor", "core_4_days_left")
    assert ro.state == "631"
    assert ro.attributes["core_name"] == "KAROFI SMAX RO PURIFIM"
    assert _state(hass, "sensor", "core_4_percent_left").state == "58.4"
    assert _state(hass, "binary_sensor", "core_1_replace").state == "on"
    assert _state(hass, "binary_sensor", "core_4_replace").state == "off"
    assert _state(hass, "binary_sensor", "online").state == "on"
    assert _state(hass, "binary_sensor", "water_inlet").state == "on"
    assert _state(hass, "binary_sensor", "pump").state == "off"
    assert _state(hass, "binary_sensor", "tank_full").state == "unknown"
    assert _state(hass, "binary_sensor", "problem").state == "on"
    assert _state(hass, "binary_sensor", "leak").state == "off"

    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_one_device_detail_error_does_not_fail_account(
    hass: HomeAssistant, aioclient_mock
):
    from homeassistant.helpers import entity_registry as er

    serial2 = "41A00000002"
    aioclient_mock.post(API + "app/user/signin", json=SIGNIN_OK)
    aioclient_mock.get(API + "app/house/houseInformation", json=houses_payload(SERIAL, serial2))
    aioclient_mock.get(API + f"app/device/detail/{SERIAL}", json=detail_payload())
    aioclient_mock.get(
        API + f"app/device/detail/{serial2}",
        status=500,
        json={"error": {"code": 500, "message": "Lỗi xảy ra với Server", "data": None}},
    )
    entry = await _setup(hass)
    assert entry.state is ConfigEntryState.LOADED
    assert _state(hass, "sensor", "tds").state == "3"
    registry = er.async_get(hass)
    assert registry.async_get_entity_id("sensor", DOMAIN, f"{serial2}_tds") is None
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_blank_error_codes_reports_unknown(hass: HomeAssistant, aioclient_mock):
    aioclient_mock.post(API + "app/user/signin", json=SIGNIN_OK)
    aioclient_mock.get(API + "app/house/houseInformation", json=houses_payload())
    aioclient_mock.get(API + f"app/device/detail/{SERIAL}", json=detail_payload(iro_errs=""))
    entry = await _setup(hass)
    assert _state(hass, "sensor", "status").state == "unknown"
    assert _state(hass, "binary_sensor", "problem").state == "unknown"
    assert _state(hass, "binary_sensor", "leak").state == "unknown"
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_offline_device_keeps_connectivity_available(hass: HomeAssistant, aioclient_mock):
    payload = detail_payload()
    payload["data"]["status"] = 0
    aioclient_mock.post(API + "app/user/signin", json=SIGNIN_OK)
    aioclient_mock.get(API + "app/house/houseInformation", json=houses_payload())
    aioclient_mock.get(API + f"app/device/detail/{SERIAL}", json=payload)
    await _setup(hass)
    assert _state(hass, "binary_sensor", "online").state == "off"
    assert _state(hass, "sensor", "tds").state == "unavailable"


async def test_setup_auth_failure_starts_reauth(hass: HomeAssistant, aioclient_mock):
    aioclient_mock.post(
        API + "app/user/signin",
        json={"code": 400, "message": "Account not registered", "data": []},
    )
    entry = MockConfigEntry(
        domain=DOMAIN, unique_id="4242", data={"phone": PHONE, "password": "pw"}
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.SETUP_ERROR
    flows = hass.config_entries.flow.async_progress()
    assert any(f["context"]["source"] == "reauth" for f in flows)
