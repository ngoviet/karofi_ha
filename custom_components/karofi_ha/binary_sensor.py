"""Binary sensor cho máy lọc Karofi: kết nối, nước vào, bơm, bình đầy, lỗi, lõi cần thay."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import KarofiConfigEntry
from .coordinator import KarofiCoordinator
from .entity import KarofiEntity
from .models import KarofiDevice


@dataclass(frozen=True, kw_only=True)
class KarofiBinaryDescription(BinarySensorEntityDescription):
    value_fn: Callable[[KarofiDevice], bool | None]


BINARY_SENSORS: tuple[KarofiBinaryDescription, ...] = (
    KarofiBinaryDescription(
        key="water_inlet",
        translation_key="water_inlet",
        value_fn=lambda d: d.water_inlet,
    ),
    KarofiBinaryDescription(
        key="pump",
        translation_key="pump",
        device_class=BinarySensorDeviceClass.RUNNING,
        value_fn=lambda d: d.pump_running,
    ),
    KarofiBinaryDescription(
        key="tank_full",
        translation_key="tank_full",
        value_fn=lambda d: d.tank_full,
    ),
    KarofiBinaryDescription(
        key="flushing",
        translation_key="flushing",
        device_class=BinarySensorDeviceClass.RUNNING,
        value_fn=lambda d: d.flushing,
    ),
    KarofiBinaryDescription(
        key="problem",
        translation_key="problem",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=lambda d: None if d.error_codes is None else bool(d.error_codes),
    ),
    KarofiBinaryDescription(
        key="leak",
        translation_key="leak",
        device_class=BinarySensorDeviceClass.MOISTURE,
        value_fn=lambda d: None if d.error_codes is None else 5 in d.error_codes,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: KarofiConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    added: set[str] = set()

    @callback
    def _add_new() -> None:
        entities: list[BinarySensorEntity] = []
        for serial, dev in (coordinator.data or {}).items():
            if serial in added:
                continue
            added.add(serial)
            entities.append(KarofiOnlineSensor(coordinator, serial))
            entities += [
                KarofiBinarySensor(coordinator, serial, d) for d in BINARY_SENSORS
            ]
            entities += [
                KarofiCoreReplaceSensor(coordinator, serial, core.position)
                for core in dev.cores
            ]
        if entities:
            async_add_entities(entities)

    _add_new()
    entry.async_on_unload(coordinator.async_add_listener(_add_new))


class KarofiBinarySensor(KarofiEntity, BinarySensorEntity):
    entity_description: KarofiBinaryDescription

    def __init__(
        self, coordinator: KarofiCoordinator, serial: str, desc: KarofiBinaryDescription
    ) -> None:
        super().__init__(coordinator, serial, desc.key)
        self.entity_description = desc

    @property
    def is_on(self) -> bool | None:
        dev = self.device
        return None if dev is None else self.entity_description.value_fn(dev)


class KarofiOnlineSensor(KarofiEntity, BinarySensorEntity):
    """Máy có kết nối cloud không (`status` == 1) — vẫn available khi máy offline."""

    _attr_translation_key = "online"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: KarofiCoordinator, serial: str) -> None:
        super().__init__(coordinator, serial, "online")

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success and self.device is not None

    @property
    def is_on(self) -> bool | None:
        dev = self.device
        return None if dev is None else dev.online


class KarofiCoreReplaceSensor(KarofiEntity, BinarySensorEntity):
    """Lõi cần thay: còn < 15 ngày hoặc < 50 giờ bơm (ngưỡng của app)."""

    _attr_translation_key = "core_replace"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(
        self, coordinator: KarofiCoordinator, serial: str, position: int
    ) -> None:
        super().__init__(coordinator, serial, f"core_{position}_replace")
        self._position = position
        self._attr_translation_placeholders = {"position": str(position)}

    @property
    def is_on(self) -> bool | None:
        dev = self.device
        if dev is None:
            return None
        core = next((c for c in dev.cores if c.position == self._position), None)
        return None if core is None else core.needs_replacement
