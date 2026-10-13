"""Hằng số cho Karofi 365.

Mọi giá trị dưới đây lấy từ decompile app Karofi 365 v2.2.98 (Flutter, Dart 2.19.6,
blutter) và đã đối chiếu trên tài khoản thật 2026-10-13 — xem docs/api-notes.md.
"""

from __future__ import annotations

DOMAIN = "karofi_ha"
MANUFACTURER = "Karofi"

# assets/flutter_assets/assets/cfg/app_config_prod.json → "apiEndpoint"
API_BASE = "https://365api.karofi.com/api/"
# Header app gửi kèm mọi request (token_security_interceptor.dart)
USER_AGENT = "Mozilla/5.0"
ACCEPT_LANGUAGE = "vi"
# AppStringExtension.toCountryCode("VN") == "VI" — server từ chối "VN" ("phone" must be [])
COUNTRY_VN = "VI"

CONF_PHONE = "phone"
CONF_PASSWORD = "password"
CONF_SCAN_INTERVAL = "scan_interval"

DEFAULT_SCAN_INTERVAL = 60
MIN_SCAN_INTERVAL = 30
MAX_SCAN_INTERVAL = 900
# Danh sách nhà/thiết bị đổi rất hiếm → quét lại mỗi N lần poll (60 s × 30 = 30 phút)
DISCOVERY_EVERY = 30

REQUEST_TIMEOUT = 30

# Ngưỡng app dùng (HydrogenWaterPurifierBloc._mapTitleWithPureIndex): TDS < 50 tốt,
# < 100 "kiểm tra lại nguồn nước", còn lại "kém an toàn".
TDS_GOOD_BELOW = 50
TDS_CHECK_BELOW = 100

# Ngưỡng cảnh báo thay lõi (_mapCoreFilterInfo): còn < 15 ngày HOẶC < 50 giờ bơm.
CORE_WARN_DAYS = 15
CORE_WARN_PUMP_HOURS = 50

# Mã lỗi `iro_errs` → key enum (dịch trong strings.json). Nguồn: bảng `ranges` của
# Devices_Type từ server + _getNotifyMessageFromError (mã 3 chỉ có trong app).
ERROR_CODES: dict[int, str] = {
    1: "pump_overrun",  # Bơm hoạt động quá 5 tiếng
    2: "inlet_weak",  # Nước cấp đầu vào yếu
    3: "tank_empty",  # Cạn nước bình chứa
    4: "no_water_inlet",  # Không có nước đầu vào
    5: "leak",  # Máy bị rò rỉ nước
    100: "high_tds",  # TDS cao
}
ERROR_NONE = "normal"
ERROR_UNKNOWN = "unknown_error"
ERROR_OPTIONS = [ERROR_NONE, *ERROR_CODES.values(), ERROR_UNKNOWN]

QUALITY_OPTIONS = ["good", "check_source", "unsafe"]
