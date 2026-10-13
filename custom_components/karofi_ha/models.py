"""Phân tích JSON thiết bị Karofi thành dataclass — thuần Python, không phụ thuộc HA.

Hai endpoint trả CÙNG property nhưng KHÁC định dạng (đo trên KAQ-U98, 2026-10-13):

    house/houseInformation  →  "iro_hsd": "8640,8640,8640,25920,8640"   (chuỗi phẩy)
    device/detail/{serial}  →  "iro_hsd": ["8640", "8640", ...]          (mảng)

và `device/detail` có thêm `iro_ketn`, `iro_vx`, `iro_rsft`, hardwareVersion, mcuFirmVer.
Giá trị rỗng `""` nghĩa là máy chưa báo → None (không phải 0).

Ý nghĩa các mảng lõi lọc (mỗi phần tử = 1 lõi, theo `models.params[].position`), suy ra từ
HydrogenWaterPurifierBloc._getCoreInfoOnline(lTime, names, rtr, rtt, listHSD: hsd):
    iro_hsd   tuổi thọ lõi theo lịch (giờ)          app hiển thị /24 → ngày
    iro_lTime thời gian CÒN LẠI theo lịch (giờ)      app cảnh báo khi /24 < 15 ngày
    iro_rtt   tổng giờ chạy bơm cho phép của lõi
    iro_rtr   giờ chạy bơm CÒN LẠI                  app cảnh báo khi < 50
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .const import (
    CORE_WARN_DAYS,
    CORE_WARN_PUMP_HOURS,
    ERROR_CODES,
    ERROR_NONE,
    ERROR_UNKNOWN,
    TDS_CHECK_BELOW,
    TDS_GOOD_BELOW,
)


def _as_list(value: Any) -> list[str]:
    if value is None or value == "":
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value]
    return [v.strip() for v in str(value).split(",")]


def _as_int(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return int(str(value).strip())
    except ValueError:
        try:
            return int(float(str(value).strip()))
        except ValueError:
            return None


def _flag(value: Any) -> bool | None:
    """'1' → True, '0' → False, '' / None → None."""
    num = _as_int(value)
    return None if num is None else num == 1


def _pick(items: list[str], idx: int) -> int | None:
    return _as_int(items[idx]) if idx < len(items) else None


def _pct(part: int | None, whole: int | None) -> float | None:
    if part is None or not whole:
        return None
    return round(max(0.0, min(100.0, part * 100 / whole)), 1)


def property_values(device: dict[str, Any]) -> dict[str, Any]:
    """{code: value} từ mảng `properties` (bỏ qua phần tử thiếu code)."""
    return {
        p["code"]: p.get("value")
        for p in device.get("properties") or []
        if isinstance(p, dict) and p.get("code")
    }


@dataclass(slots=True)
class FilterCore:
    """Một lõi lọc (vị trí 1..n)."""

    position: int
    name: str
    hours_left: int | None
    hours_total: int | None
    pump_hours_left: int | None
    pump_hours_total: int | None

    @property
    def days_left(self) -> int | None:
        return None if self.hours_left is None else max(0, self.hours_left) // 24

    @property
    def days_total(self) -> int | None:
        return None if self.hours_total is None else self.hours_total // 24

    @property
    def percent_left(self) -> float | None:
        """% còn lại = MIN(theo lịch, theo giờ bơm) — lõi hết hạn khi chạm 1 trong 2."""
        values = [
            v
            for v in (
                _pct(self.hours_left, self.hours_total),
                _pct(self.pump_hours_left, self.pump_hours_total),
            )
            if v is not None
        ]
        return min(values) if values else None

    @property
    def needs_replacement(self) -> bool | None:
        days = self.days_left
        pump = self.pump_hours_left
        if days is None and pump is None:
            return None
        return (days is not None and days < CORE_WARN_DAYS) or (
            pump is not None and pump < CORE_WARN_PUMP_HOURS
        )


@dataclass(slots=True)
class KarofiDevice:
    """Một máy lọc nước trên tài khoản Karofi 365."""

    device_id: int
    serial: str
    model: str | None
    device_type: str | None
    alias: str | None
    image: str | None
    online: bool
    firmware: str | None = None
    hardware: str | None = None
    mcu_firmware: str | None = None
    house: str | None = None
    room: str | None = None
    properties: dict[str, Any] = field(default_factory=dict)
    cores: list[FilterCore] = field(default_factory=list)

    @property
    def name(self) -> str:
        return self.alias or f"Karofi {self.model or self.serial}"

    def prop(self, code: str) -> Any:
        value = self.properties.get(code)
        return None if value == "" else value

    @property
    def tds(self) -> int | None:
        return _as_int(self.prop("iro_tds"))

    @property
    def water_quality(self) -> str | None:
        tds = self.tds
        if tds is None:
            return None
        if tds < TDS_GOOD_BELOW:
            return "good"
        if tds < TDS_CHECK_BELOW:
            return "check_source"
        return "unsafe"

    @property
    def rssi(self) -> int | None:
        return _as_int(self.prop("rssi"))

    @property
    def water_inlet(self) -> bool | None:
        """iro_nuocIn: 1 = Có nước, 0 = Mất nước."""
        return _flag(self.prop("iro_nuocIn"))

    @property
    def pump_running(self) -> bool | None:
        """iro_bom: 1 = BOM, 0 = TAT."""
        return _flag(self.prop("iro_bom"))

    @property
    def tank_full(self) -> bool | None:
        """iro_ketn: 0 = Đầy bình, 1 = Chưa đầy (ngược chiều!)."""
        flag = _flag(self.prop("iro_ketn"))
        return None if flag is None else not flag

    @property
    def flushing(self) -> bool | None:
        """iro_vx (van xả): 1 = Đang xả, 0 = Đang dừng."""
        return _flag(self.prop("iro_vx"))

    @property
    def error_codes(self) -> list[int] | None:
        raw = self.prop("iro_errs")
        if raw is None:
            return None
        codes = [_as_int(v) for v in _as_list(raw)]
        return sorted({c for c in codes if c})

    @property
    def errors(self) -> list[str] | None:
        codes = self.error_codes
        if codes is None:
            return None
        return [ERROR_CODES.get(c, ERROR_UNKNOWN) for c in codes]

    @property
    def status(self) -> str | None:
        """Lỗi đầu tiên (theo mã nhỏ nhất), 'normal' nếu không lỗi, None nếu chưa biết."""
        errors = self.errors
        if errors is None:
            return None
        return errors[0] if errors else ERROR_NONE


def _core_names(device: dict[str, Any]) -> dict[int, str]:
    params = ((device.get("models") or {}).get("params")) or []
    names: dict[int, str] = {}
    for item in params:
        pos = _as_int(item.get("position")) if isinstance(item, dict) else None
        if pos:
            names[pos] = str(item.get("name") or "").strip()
    return names


def parse_cores(device: dict[str, Any], props: dict[str, Any]) -> list[FilterCore]:
    hsd = _as_list(props.get("iro_hsd"))
    left = _as_list(props.get("iro_lTime"))
    rtt = _as_list(props.get("iro_rtt"))
    rtr = _as_list(props.get("iro_rtr"))
    count = max(len(hsd), len(left), len(rtt), len(rtr))
    names = _core_names(device)
    return [
        FilterCore(
            position=i + 1,
            name=names.get(i + 1) or f"Lõi {i + 1}",
            hours_left=_pick(left, i),
            hours_total=_pick(hsd, i),
            pump_hours_left=_pick(rtr, i),
            pump_hours_total=_pick(rtt, i),
        )
        for i in range(count)
    ]


def parse_device(
    device: dict[str, Any], house: str | None = None, room: str | None = None
) -> KarofiDevice:
    """Dựng KarofiDevice từ 1 phần tử `devices` (house list) hoặc `data` của device/detail."""
    props = property_values(device)
    models = device.get("models") or {}
    dtype = device.get("deviceType") or device.get("Devices_Type") or {}
    room_obj = device.get("room") or {}
    return KarofiDevice(
        device_id=int(device["id"]),
        serial=str(device.get("seriNumber") or device.get("serialNumber") or ""),
        model=models.get("displayName") or models.get("name"),
        device_type=dtype.get("name"),
        alias=(device.get("aliaName") or "").strip() or None,
        image=models.get("image"),
        # status 1 = online (house list & detail); thiết bị mất kết nối → 0
        online=_as_int(device.get("status")) == 1,
        firmware=_str_or_none(device.get("firmwareVersion")),
        hardware=_str_or_none(device.get("hardwareVersion")),
        mcu_firmware=_str_or_none(device.get("mcuFirmVer")),
        house=house,
        room=room or room_obj.get("name"),
        properties=props,
        cores=parse_cores(device, props),
    )


def _str_or_none(value: Any) -> str | None:
    return None if value in (None, "") else str(value)


def iter_house_devices(payload: dict[str, Any]):
    """Duyệt `data.data[].rooms[].devices[]` của house/houseInformation.

    Trả (house_name, room_name, device_json). Bỏ qua thiết bị không có serial.
    """
    for house in ((payload or {}).get("data") or {}).get("data") or []:
        for room in house.get("rooms") or []:
            for dev in room.get("devices") or []:
                if dev.get("seriNumber") and dev.get("id") is not None:
                    yield house.get("name"), room.get("name"), dev
