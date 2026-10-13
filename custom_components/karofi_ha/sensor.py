"""Sensor cho máy lọc Karofi: TDS, chất lượng nước, trạng thái lỗi, lõi lọc."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    CONCENTRATION_PARTS_PER_MILLION,
    PERCENTAGE,
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    EntityCategory,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import KarofiConfigEntry
from .const import ERROR_OPTIONS, QUALITY_OPTIONS
from .coordinator import KarofiCoordinator
from .entity import KarofiEntity
from .models import FilterCore, KarofiDevice


@dataclass(frozen=True, kw_only=True)
class KarofiSensorDescription(SensorEntityDescription):
    value_fn: Callable[[KarofiDevice], Any]
    attrs_fn: Callable[[KarofiDevice], dict[str, Any]] | None = None


SENSORS: tuple[KarofiSensorDescription, ...] = (
    KarofiSensorDescription(
        key="tds",
        translation_key="tds",
        native_unit_of_measurement=CONCENTRATION_PARTS_PER_MILLION,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.tds,
    ),
    KarofiSensorDescription(
        key="water_quality",
        translation_key="water_quality",
        device_class=SensorDeviceClass.ENUM,
        options=QUALITY_OPTIONS,
        value_fn=lambda d: d.water_quality,
    ),
    KarofiSensorDescription(
        key="status",
        translation_key="status",
        device_class=SensorDeviceClass.ENUM,
        options=ERROR_OPTIONS,
        value_fn=lambda d: d.status,
        attrs_fn=lambda d: {"error_codes": d.error_codes, "errors": d.errors},
    ),
    KarofiSensorDescription(
        key="rssi",
        translation_key="rssi",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.rssi,
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
        entities: list[SensorEntity] = []
        for serial, dev in (coordinator.data or {}).items():
            if serial in added:
                continue
            added.add(serial)
            entities += [KarofiSensor(coordinator, serial, desc) for desc in SENSORS]
            for core in dev.cores:
                entities += [
                    KarofiCoreDaysSensor(coordinator, serial, core.position),
                    KarofiCorePercentSensor(coordinator, serial, core.position),
                ]
        if entities:
            async_add_entities(entities)

    _add_new()
    entry.async_on_unload(coordinator.async_add_listener(_add_new))


class KarofiSensor(KarofiEntity, SensorEntity):
    entity_description: KarofiSensorDescription

    def __init__(
        self, coordinator: KarofiCoordinator, serial: str, desc: KarofiSensorDescription
    ) -> None:
        super().__init__(coordinator, serial, desc.key)
        self.entity_description = desc

    @property
    def native_value(self) -> Any:
        dev = self.device
        return None if dev is None else self.entity_description.value_fn(dev)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        dev = self.device
        fn = self.entity_description.attrs_fn
        return None if dev is None or fn is None else fn(dev)


class _CoreSensor(KarofiEntity, SensorEntity):
    _kind = ""

    def __init__(self, coordinator: KarofiCoordinator, serial: str, position: int) -> None:
        super().__init__(coordinator, serial, f"core_{position}_{self._kind}")
        self._position = position
        self._attr_translation_key = f"core_{self._kind}"
        self._attr_translation_placeholders = {"position": str(position)}

    @property
    def core(self) -> FilterCore | None:
        dev = self.device
        if dev is None:
            return None
        return next((c for c in dev.cores if c.position == self._position), None)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        core = self.core
        if core is None:
            return None
        return {
            "position": core.position,
            "core_name": core.name,
            "days_left": core.days_left,
            "days_total": core.days_total,
            "pump_hours_left": core.pump_hours_left,
            "pump_hours_total": core.pump_hours_total,
            "needs_replacement": core.needs_replacement,
        }


class KarofiCoreDaysSensor(_CoreSensor):
    """Số ngày còn lại theo lịch (iro_lTime / 24)."""

    _kind = "days_left"
    _attr_device_class = SensorDeviceClass.DURATION
    _attr_native_unit_of_measurement = UnitOfTime.DAYS
    _attr_suggested_display_precision = 0

    @property
    def native_value(self) -> int | None:
        core = self.core
        return None if core is None else core.days_left


class KarofiCorePercentSensor(_CoreSensor):
    """% tuổi thọ còn lại = MIN(theo lịch, theo giờ bơm)."""

    _kind = "percent_left"
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 0

    @property
    def native_value(self) -> float | None:
        core = self.core
        return None if core is None else core.percent_left
