# Karofi 365 cho Home Assistant

<!-- readme-axi type=ha -->

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/docs/faq/custom_repositories/)
[![Validate](https://github.com/ngoviet/karofi_ha/actions/workflows/validate.yml/badge.svg)](https://github.com/ngoviet/karofi_ha/actions/workflows/validate.yml)
[![Test](https://github.com/ngoviet/karofi_ha/actions/workflows/test.yml/badge.svg)](https://github.com/ngoviet/karofi_ha/actions/workflows/test.yml)
[![License: MIT](https://img.shields.io/github/license/ngoviet/karofi_ha)](LICENSE)

[English](README.md) · **Tiếng Việt**

Đọc máy lọc nước **Karofi** (có Wi-Fi, quản lý bằng app **Karofi 365**) vào Home Assistant qua
cloud `365api.karofi.com`: TDS và chất lượng nước, trạng thái máy và cảnh báo, thời gian còn
lại của từng lõi lọc. Giao thức được reverse-engineer từ app Karofi 365 v2.2.98 — chi tiết ở
[docs/api-notes.md](docs/api-notes.md).

[![Mở Home Assistant của bạn và mở một kho trong Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=ngoviet&repository=karofi_ha&category=integration)

> 🇻🇳 Dự án do một người Việt tự xây dựng và duy trì — nếu nó giúp ích cho bạn, hãy
> [ủng hộ dự án](#ủng-hộ-dự-án).

## Tính năng

- **Phase 1 — chỉ đọc.** Không điều khiển, không reset lõi.
- **Nước** — TDS (ppm) và mức chất lượng nước theo đúng ngưỡng của app.
- **Trạng thái và cảnh báo** — trạng thái máy theo mã lỗi, cảnh báo chung, rò rỉ nước, nước
  đầu vào, bơm, bình chứa đầy và van xả.
- **Lõi lọc** — số ngày còn lại, phần trăm và cảnh báo "cần thay" cho từng lõi, theo đúng
  ngưỡng cảnh báo của app.
- **Chẩn đoán** — kết nối và tín hiệu Wi-Fi.
- **Không thư viện ngoài**, cài bằng giao diện (config flow), đăng nhập lại, tuỳ chọn (chu kỳ
  cập nhật), diagnostics, giao diện Anh & Việt.

## Thiết bị hỗ trợ

Đã kiểm tra trên **KAQ-U98** (loại `Aiotec_41`). Các máy khác dùng bộ property `iro_*` cũng
chạy; dòng K365 cũ (`mlt_*`) chưa hỗ trợ. Cần **Home Assistant 2026.9** trở lên.

## Cài đặt

1. HACS → *Custom repositories* → thêm repo này (loại *Integration*) → cài **Karofi 365**,
   hoặc chép `custom_components/karofi_ha` vào `/config/custom_components/`.
2. Khởi động lại Home Assistant.

## Cấu hình

*Cài đặt → Thiết bị & Dịch vụ → Thêm tích hợp → Karofi 365* → nhập số điện thoại + mật khẩu
app Karofi 365.

Tuỳ chọn: chu kỳ cập nhật (mặc định 60 s, 30–900 s).

## Thực thể

Mỗi máy lọc có:

| Entity | Nguồn | Ghi chú |
|---|---|---|
| TDS (ppm) | `iro_tds` | |
| Chất lượng nước | TDS | Tốt (< 50) · Kiểm tra lại nguồn nước (< 100) · Kém an toàn — đúng ngưỡng của app |
| Trạng thái | `iro_errs` | Hoạt động ổn định / Bơm chạy quá 5 tiếng / Nước cấp yếu / Cạn bình chứa / Không có nước đầu vào / Rò rỉ / TDS cao. Attribute `error_codes` |
| Cảnh báo (problem) | `iro_errs` | Bật khi có bất kỳ lỗi nào |
| Rò rỉ nước (moisture) | lỗi 5 | |
| Có nước đầu vào | `iro_nuocIn` | |
| Bơm (running) | `iro_bom` | |
| Bình chứa đầy · Van xả | `iro_ketn` · `iro_vx` | `unknown` nếu máy không báo (KAQ-U98 không báo) |
| Lõi N còn lại (ngày) | `iro_lTime / 24` | Attribute: tên lõi, tổng ngày, giờ bơm còn/tổng |
| Lõi N % | min(% theo lịch, % theo giờ bơm) | |
| Lõi N cần thay (problem) | còn < 15 ngày **hoặc** < 50 giờ bơm | Đúng ngưỡng cảnh báo của app |
| Kết nối · Tín hiệu Wi-Fi | `status`, `rssi` | Chẩn đoán |

## Xử lý sự cố

- **Chỉ qua cloud** — cần Internet tới `365api.karofi.com`; không có điều khiển local.
- **Trạng thái, Cảnh báo và Rò rỉ là `unknown`** — `iro_errs` rỗng hoặc thiếu = máy chưa báo,
  nên các entity này là `unknown` (không phải "Hoạt động ổn định"/tắt). Mảng rỗng thật (`[]`)
  hoặc toàn `"0"` vẫn là bình thường.
- **Bình chứa đầy / Van xả là `unknown`** — máy không báo hai giá trị này (KAQ-U98 không báo).
- Khi báo lỗi, đính kèm **diagnostics** của integration (*Thiết bị & Dịch vụ → Karofi 365 → ⋮ →
  Tải xuống chẩn đoán*).

## Phát triển

```bash
pip install -r requirements_test.txt
pytest
```

Deploy thẳng lên HA qua SSH: chép `.env.example` → `.env`, điền `HA_HOST`/`HA_USER`/`HA_PASS`,
rồi `python tools/deploy.py` và restart HA.

<!-- support:start -->
## Ủng hộ dự án

<p align="center">
  <img src="https://raw.githubusercontent.com/ngoviet/.github/main/assets/support/banner.svg" width="720" alt="Built and maintained by one person in Việt Nam">
</p>

<p align="center">
  <a href="https://buymeacoffee.com/ngoviet"><img src="https://raw.githubusercontent.com/ngoviet/.github/main/assets/support/btn-coffee.svg" height="56" alt="Buy me a coffee"></a>
  &nbsp;
  <a href="https://github.com/sponsors/ngoviet"><img src="https://raw.githubusercontent.com/ngoviet/.github/main/assets/support/btn-sponsors.svg" height="56" alt="GitHub Sponsors"></a>
</p>

<p align="center">
  <img src="https://raw.githubusercontent.com/ngoviet/.github/main/assets/support/vietqr-card.svg" width="300" alt="VietQR — MB Bank — NGO DUC VIET — 911051212">
  &nbsp;
  <img src="https://raw.githubusercontent.com/ngoviet/.github/main/assets/support/crypto-card.svg" width="300" alt="Crypto — BNB Smart Chain (BEP20) — 0xcbf0402b232cb24b4d998f09a4884f87b5f74750">
</p>

<p align="center"><b>Ví tiền mã hoá, chỉ gửi qua mạng BNB Smart Chain (BEP20):</b><br><code>0xcbf0402b232cb24b4d998f09a4884f87b5f74750</code></p>

<p align="center"><sub>🇻🇳 VietQR: quét bằng app ngân hàng bất kỳ, nội dung <code>Ung ho karofi_ha</code>. Cảm ơn bạn đã giúp dự án tiếp tục phát triển!</sub></p>
<!-- support:end -->

## Giấy phép

[MIT](LICENSE) © Ngô Đức Việt. Không liên kết với Karofi.
