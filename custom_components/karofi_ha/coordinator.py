"""DataUpdateCoordinator cho Karofi 365."""
from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import (
    TimestampDataUpdateCoordinator,
    UpdateFailed,
)

from .api import KarofiApi, KarofiApiError, KarofiAuthError
from .const import DISCOVERY_EVERY, DOMAIN
from .models import KarofiDevice, iter_house_devices, parse_device

_LOGGER = logging.getLogger(__name__)


class KarofiCoordinator(TimestampDataUpdateCoordinator[dict[str, KarofiDevice]]):
    """Mỗi lần poll: `device/detail/{serial}` cho từng máy (đủ property).

    Danh sách nhà/phòng/máy (`houseInformation`) chỉ lấy lần đầu và mỗi
    DISCOVERY_EVERY lần — nó hiếm đổi. Dữ liệu là {serial: KarofiDevice}.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        api: KarofiApi,
        entry: ConfigEntry,
        update_interval: int,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(seconds=update_interval),
        )
        self.api = api
        self._tick = 0
        # serial → (device json từ house list, tên nhà, tên phòng)
        self._known: dict[str, tuple[dict, str | None, str | None]] = {}
        self.failed_updates = 0

    async def _discover(self) -> None:
        payload = await self.api.get_houses()
        self._known = {
            dev["seriNumber"]: (dev, house, room)
            for house, room, dev in iter_house_devices(payload)
        }
        _LOGGER.debug("karofi: tìm thấy %d thiết bị: %s", len(self._known), list(self._known))

    async def _async_update_data(self) -> dict[str, KarofiDevice]:
        try:
            if self._tick % DISCOVERY_EVERY == 0 or not self._known:
                await self._discover()
            self._tick += 1
            devices: dict[str, KarofiDevice] = {}
            last_error: KarofiApiError | None = None
            fresh = 0
            for serial, (_summary, house, room) in self._known.items():
                try:
                    detail = await self.api.get_device_detail(serial)
                except KarofiAuthError:
                    raise
                except KarofiApiError as err:
                    # 1 máy lỗi không làm hỏng cả account: giữ số liệu lần trước
                    # của máy đó (nếu có); máy chưa có số liệu cũ thì bỏ qua lần
                    # này và tự xuất hiện lại khi API hết lỗi. Máy khác vẫn cập nhật.
                    _LOGGER.debug("karofi: detail %s lỗi: %s", serial, err)
                    last_error = err
                    if self.data and serial in self.data:
                        devices[serial] = self.data[serial]
                    continue
                devices[serial] = parse_device(detail, house, room)
                fresh += 1
            if last_error is not None and fresh == 0:
                # Không máy nào có số liệu mới
                raise last_error
        except KarofiAuthError as err:
            self.failed_updates += 1
            raise ConfigEntryAuthFailed(str(err)) from err
        except KarofiApiError as err:
            self.failed_updates += 1
            raise UpdateFailed(str(err)) from err
        self.failed_updates = 0
        return devices
