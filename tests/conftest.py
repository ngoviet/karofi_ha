"""Fixture chung. Payload mô phỏng ĐÚNG hình dạng response thật của 365api.karofi.com
(KAQ-U98, đo 2026-10-13) — kể cả chỗ "kỳ quặc": house list trả mảng dạng chuỗi phẩy,
detail trả mảng thật; `iro_ketn`/`iro_vx` rỗng; `iro_errs` là mảng chuỗi.
Serial/SĐT là giả.
"""
from __future__ import annotations

import copy
import sys

import pytest

pytest_plugins = "pytest_homeassistant_custom_component"

if sys.platform == "win32":
    # PHACC chặn socket trước mỗi test; Windows không có AF_UNIX nên event loop
    # dựng self-pipe bằng AF_INET → bị chặn. Test ở đây mock HTTP, không gọi mạng.
    import pytest_socket

    pytest_socket.disable_socket = lambda *args, **kwargs: None

API = "https://365api.karofi.com/api/"
SERIAL = "41A00000001"
PHONE = "0900000001"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield


MODELS = {
    "id": 73,
    "name": "KAQ-U98",
    "displayName": "KAQ-U98",
    "image": "https://365static.karofi.com/device/model/thumbnail/x.png",
    "theme": 1,
    "params": [
        {"name": "KAROFI SMAX PRO V1", "position": 1},
        {"name": "KAROFI SMAX PRO V2", "position": 2},
        {"name": "KAROFI SMAX PRO V3", "position": 3},
        {"name": "KAROFI SMAX RO PURIFIM", "position": 4},
        {"name": "KAROFI SMAX HP 6.0", "position": 5},
    ],
}


def _p(code, value):
    return {"id": 0, "code": code, "name": code.upper(), "aliaName": None, "value": value}


def detail_payload(**overrides) -> dict:
    props = {
        "F_OTA_STATUS": "SUCCESS",
        "rssi": "-46",
        "iro_errs": ["1"],
        "iro_tds": "3",
        "iro_rsft": "",
        "iro_lTime": ["0", "0", "0", "15144", "0"],
        "iro_vx": "",
        "iro_hsd": ["8640", "8640", "8640", "25920", "8640"],
        "iro_rtt": ["1200", "1200", "1200", "3600", "1200"],
        "iro_rtr": ["1026", "1026", "1026", "3426", "1026"],
        "iro_nuocIn": "1",
        "iro_ketn": "",
        "iro_bom": "0",
    }
    props.update(overrides)
    return {
        "code": 200,
        "message": "OK",
        "data": {
            "id": 100001,
            "seriNumber": SERIAL,
            "firmwareVersion": "2006",
            "hardwareVersion": "11",
            "status": 1,
            "aliaName": None,
            "mcuFirmVer": "5",
            "models": copy.deepcopy(MODELS),
            "room": {"id": 300001, "name": "Thiết bị chưa gán phòng", "houseId": 200001},
            "deviceType": {"id": 19, "name": "Aiotec_41", "supplier": {"id": 1, "name": "Makipos"}},
            "properties": [_p(k, v) for k, v in props.items()],
        },
    }


def houses_payload() -> dict:
    return {
        "code": 200,
        "message": "OK",
        "data": {
            "total": 1,
            "list_label": {},
            "data": [
                {
                    "id": 200001,
                    "name": "Nhà Của Tôi",
                    "devicesCount": 1,
                    "rooms": [
                        {
                            "id": 300001,
                            "name": "Thiết bị chưa gán phòng",
                            "devices": [
                                {
                                    "id": 100001,
                                    "seriNumber": SERIAL,
                                    "status": 1,
                                    "firmwareVersion": "2006",
                                    "aliaName": None,
                                    "models": copy.deepcopy(MODELS),
                                    "Devices_Type": {"id": 19, "name": "Aiotec_41"},
                                    "properties": [
                                        _p("iro_errs", "1"),
                                        _p("iro_tds", "3"),
                                        _p("iro_hsd", "8640,8640,8640,25920,8640"),
                                        _p("iro_lTime", "0,0,0,15144,0"),
                                        _p("iro_rtt", "1200,1200,1200,3600,1200"),
                                        _p("iro_rtr", "1026,1026,1026,3426,1026"),
                                        _p("iro_nuocIn", "1"),
                                        _p("iro_bom", "0"),
                                        _p("rssi", "-46"),
                                    ],
                                }
                            ],
                        }
                    ],
                }
            ],
        },
    }


SIGNIN_OK = {
    "code": 200,
    "message": "OK",
    "data": {"userId": 4242, "token": "tok-1", "refreshToken": "ref-1", "currentRole": None},
}


@pytest.fixture
def cloud(aioclient_mock):
    """Cloud Karofi giả lập: signin + houses + detail đều OK."""
    aioclient_mock.post(API + "app/user/signin", json=SIGNIN_OK)
    aioclient_mock.get(API + "app/house/houseInformation", json=houses_payload())
    aioclient_mock.get(API + f"app/device/detail/{SERIAL}", json=detail_payload())
    return aioclient_mock
