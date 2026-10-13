"""Entity gốc: 1 máy lọc = 1 device."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .coordinator import KarofiCoordinator
from .models import KarofiDevice


class KarofiEntity(CoordinatorEntity[KarofiCoordinator]):
    _attr_has_entity_name = True

    def __init__(self, coordinator: KarofiCoordinator, serial: str, key: str) -> None:
        super().__init__(coordinator)
        self._serial = serial
        self._attr_unique_id = f"{serial}_{key}"
        dev = coordinator.data[serial]
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, serial)},
            name=dev.name,
            manufacturer=MANUFACTURER,
            model=dev.model,
            model_id=dev.device_type,
            serial_number=serial,
            sw_version=dev.firmware,
            hw_version=dev.hardware,
            suggested_area=dev.room
            if dev.room and "chưa gán" not in dev.room.lower()
            else None,
        )

    @property
    def device(self) -> KarofiDevice | None:
        return (self.coordinator.data or {}).get(self._serial)

    @property
    def available(self) -> bool:
        dev = self.device
        return super().available and dev is not None and dev.online
