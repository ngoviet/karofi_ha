# Karofi 365 — ghi chú API (reverse engineering)

> Nguồn: app **Karofi 365 v2.2.98** (`com.karofi.k365.iotp.mobile`, versionCode 298), APK kéo
> từ điện thoại của chính chủ (S25 Ultra) bằng `adb pull`. App viết bằng **Flutter**
> (Dart 2.19.6) → logic nằm trong `libapp.so`, decompile bằng
> [blutter](https://github.com/worawit/blutter). Mọi điểm dưới đây đã **đối chiếu trên tài
> khoản thật 2026-10-13** (máy KAQ-U98) — trừ chỗ ghi rõ "chưa xác minh".
>
> Workspace RE (không commit): `D:\code\karofi_re` — `apk/`, `out/blutter/asm/…`,
> `scripts/probe.py` (thăm dò API), `scripts/live_check.py` (chạy code integration trên cloud thật).

## 1. Endpoint

`assets/flutter_assets/assets/cfg/app_config_prod.json`:

| Khoá | Giá trị | Dùng cho |
|---|---|---|
| `apiEndpoint` | `https://365api.karofi.com/api/` | REST — **integration chỉ dùng cái này** |
| `apiEndpointGraphqlA` / `socketEndpointA` | `https://srt-iam-api.karofi.com/graphql` / `wss://…` | Subscription realtime `onUpdateDevice` |
| `apiEndpointGraphQL` / `socketEndpoint` | `srt-rtc-api.karofi.com` | Khai báo nhưng app không gắn vào client nào |
| `amplifyEndpoint` + `amplifyAPIKey` | AppSync ap-southeast-1 | Không thấy dùng cho máy lọc |

## 2. Đăng nhập

```
POST app/user/signin
User-Agent: Mozilla/5.0      Accept-Language: vi
{"email": "", "phone": "09xxxxxxxx", "password": "<plaintext>", "country": "VI"}
→ 200 {"code":200,"data":{"userId","token","refreshToken","currentRole"}}
```

Hai bẫy đã gặp thật:

1. **`country` phải là `"VI"`**, không phải `"VN"`. `AppStringExtension.toCountryCode`
   đổi `"VN"` → `"VI"`. Gửi `"VN"` → server coi là nước ngoài, đòi đăng nhập bằng email:
   `500 ValidationError: "phone" must be []`.
2. Với VN, SĐT nằm ở **`phone`**, `email` để rỗng (`LoginBloc.login` rẽ nhánh theo
   `isIsoVNCode`). Ngược lại → `"phone" is not allowed to be empty`.

Sai tài khoản/mật khẩu: **HTTP 200** `{"code":400,"message":"Account not registered"}`.

Token là JWT (`userId`, `orgId`, `country`) sống **365 ngày**. Header: `Authorization: Bearer <token>`.
Hết hạn/sai → **HTTP 401** `{"error":{"code":401,"message":"Chưa xác thực"}}`.
Refresh: `POST app/user/refreshToken {"refreshToken": …}` → `{token, refreshToken}` (integration
không dùng — đăng nhập lại đơn giản hơn và token sống 1 năm).

## 3. Thiết bị

| Gọi | Ghi chú |
|---|---|
| `GET app/house/houseInformation?page=1&size=50` | `data.data[] → rooms[] → devices[]`, **đã kèm `properties`** nhưng mảng ở dạng **chuỗi phẩy** `"8640,8640,…"` và **thiếu** `iro_ketn`/`iro_vx`/`iro_rsft` |
| `GET app/device/detail/{serial}` | Đủ property, mảng là **JSON array**; thêm `hardwareVersion`, `mcuFirmVer`, `room`, `deviceType.supplier` (= **Makipos**). Gọi bằng **id số → 500** |
| `PUT app/device/reset-core` | `{serial_number, command_type, data}` — reset lõi. **Chưa dùng** (Phase 1 chỉ đọc) |
| `POST app/device/mlt/report` | Biểu đồ thống kê (`dataChart`, `timeChart`) — chưa dùng |

Danh sách đầy đủ ~120 endpoint (REST method + path) trích từ `data/src/services/*.dart` nằm trong
workspace RE.

## 4. Property máy lọc `Aiotec_41` (KAQ-U98)

Bảng `Devices_Type.properties[].ranges` server trả kèm, cộng logic trong
`HydrogenWaterPurifierBloc`:

| code | Ý nghĩa | Giá trị |
|---|---|---|
| `iro_tds` | TDS nước sau lọc (ppm) | `"3"`. App: < 50 tốt · < 100 kiểm tra nguồn · ≥ 100 kém an toàn |
| `iro_errs` | Danh sách lỗi | `["1"]`. 1 bơm chạy > 5 giờ · 2 nước cấp yếu · 3 cạn bình chứa · 4 không có nước vào · 5 rò rỉ · 100 TDS cao |
| `iro_nuocIn` | Nước đầu vào | 1 có nước · 0 mất nước |
| `iro_bom` | Bơm | 1 chạy · 0 tắt |
| `iro_ketn` | Bình chứa | **0 = đầy**, 1 = chưa đầy (ngược chiều). KAQ-U98 trả `""` |
| `iro_vx` | Van xả | 1 đang xả · 0 dừng. KAQ-U98 trả `""` |
| `iro_hsd` | Tuổi thọ lõi theo lịch (**giờ**), mỗi phần tử 1 lõi | `8640` = 360 ngày, RO `25920` = 1080 ngày |
| `iro_lTime` | **Giờ còn lại** theo lịch | `[0,0,0,15144,0]` |
| `iro_rtt` | Tổng **giờ chạy bơm** cho phép của lõi | `[1200,…,3600,…]` |
| `iro_rtr` | Giờ chạy bơm **còn lại** | `[1026,…,3426,…]` |
| `iro_rsft` | Lệnh reset lõi (ghi) | `""` |
| `rssi` | Wi-Fi dBm | `"-46"` |
| `F_OTA_STATUS` | Trạng thái OTA | `"SUCCESS"` |

Tên lõi theo vị trí: `models.params[{name, position}]` (KAQ-U98: SMAX PRO V1/V2/V3, RO PURIFIM, HP 6.0).

**Cách xác định đơn vị lõi** — `_getCoreInfoOnline(lTime, names, rtr, rtt, listHSD: hsd)` gọi
`_mapCoreFilterInfo` với `rtr[i]`, `lTime[i]`, `hsd[i]`; trong đó `lTime/24` và `hsd/24` (ngày),
cảnh báo "Thay lõi" khi `rtr < 50` **hoặc** `lTime/24 < 15`. Số đo khớp: RO còn 631/1080 ngày
→ máy đã chạy ~449 ngày; 4 lõi 360 ngày đã hết hạn nên `lTime = 0`; mọi lõi cùng dùng 174 giờ bơm
(chưa lõi nào được reset). ⚠️ Chưa đối chiếu với màn hình app (S25 ngắt kết nối giữa chừng).

## 5. Realtime (chưa dùng trong integration)

WebSocket `wss://srt-iam-api.karofi.com/graphql`, subprotocol **`graphql-ws`** (Apollo cũ):

```json
{"type":"connection_init","payload":{"authorization":"Bearer <token>","secret":"<hằng số trong app>"}}
{"id":"1","type":"start","payload":{"query":"subscription onUpdateDevice($serial_number: String!) { onUpdateDevice(serial_number: $serial_number) { id serial_number status properties { code value } } }","variables":{"serial_number":"<serial>"}}}
```

Đã nhận `connection_ack`; 90 s không có push khi máy đứng yên. Có thể thêm ở Phase 2 để
bơm/nước vào cập nhật tức thì.
