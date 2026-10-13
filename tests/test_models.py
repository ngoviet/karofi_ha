"""Phân tích dữ liệu thiết bị — dùng số liệu thật của KAQ-U98."""
from __future__ import annotations

from custom_components.karofi_ha.models import (
    iter_house_devices,
    parse_device,
)

from .conftest import SERIAL, detail_payload, houses_payload


def test_detail_payload_parses_real_values():
    dev = parse_device(detail_payload()["data"])
    assert dev.serial == SERIAL
    assert dev.model == "KAQ-U98"
    assert dev.device_type == "Aiotec_41"
    assert dev.online is True
    assert dev.firmware == "2006" and dev.hardware == "11"
    assert dev.tds == 3
    assert dev.water_quality == "good"
    assert dev.rssi == -46
    assert dev.water_inlet is True
    assert dev.pump_running is False
    # iro_ketn / iro_vx rỗng → chưa biết, KHÔNG phải False
    assert dev.tank_full is None
    assert dev.flushing is None
    assert dev.error_codes == [1]
    assert dev.status == "pump_overrun"


def test_cores_units_and_replacement():
    dev = parse_device(detail_payload()["data"])
    assert [c.name for c in dev.cores][:1] == ["KAROFI SMAX PRO V1"]
    ro = dev.cores[3]
    assert ro.position == 4
    assert ro.days_total == 1080  # 25920 h
    assert ro.days_left == 631  # 15144 h
    assert ro.pump_hours_left == 3426 and ro.pump_hours_total == 3600
    assert ro.percent_left == 58.4  # min(58.4 % lịch, 95.2 % bơm)
    assert ro.needs_replacement is False
    first = dev.cores[0]
    assert first.days_left == 0 and first.days_total == 360
    assert first.percent_left == 0.0
    assert first.needs_replacement is True


def test_house_list_comma_format_matches_detail():
    rows = list(iter_house_devices(houses_payload()))
    assert len(rows) == 1
    house, room, raw = rows[0]
    dev = parse_device(raw, house, room)
    ref = parse_device(detail_payload()["data"])
    assert dev.house == "Nhà Của Tôi"
    assert [(c.hours_left, c.hours_total, c.pump_hours_left) for c in dev.cores] == [
        (c.hours_left, c.hours_total, c.pump_hours_left) for c in ref.cores
    ]
    assert dev.error_codes == [1]


def test_quality_thresholds_and_errors():
    assert parse_device(detail_payload(iro_tds="49")["data"]).water_quality == "good"
    assert parse_device(detail_payload(iro_tds="50")["data"]).water_quality == "check_source"
    assert parse_device(detail_payload(iro_tds="100")["data"]).water_quality == "unsafe"
    assert parse_device(detail_payload(iro_tds="")["data"]).water_quality is None
    dev = parse_device(detail_payload(iro_errs=["5", "100", "77"])["data"])
    assert dev.error_codes == [5, 77, 100]
    assert dev.errors == ["leak", "unknown_error", "high_tds"]
    assert parse_device(detail_payload(iro_errs=[])["data"]).status == "normal"
    assert parse_device(detail_payload(iro_errs=["0"])["data"]).status == "normal"


def test_tank_flag_is_inverted():
    # Server: 0 = "Đầy bình", 1 = "Chưa đầy"
    assert parse_device(detail_payload(iro_ketn="0")["data"]).tank_full is True
    assert parse_device(detail_payload(iro_ketn="1")["data"]).tank_full is False


def test_offline_device():
    payload = detail_payload()["data"]
    payload["status"] = 0
    assert parse_device(payload).online is False
