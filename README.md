# Karofi 365 cho Home Assistant

Đọc máy lọc nước **Karofi** (có Wi-Fi, quản lý bằng app **Karofi 365**) vào Home Assistant qua
cloud `365api.karofi.com`. Giao thức được reverse-engineer từ app Karofi 365 v2.2.98 —
chi tiết ở [docs/api-notes.md](docs/api-notes.md).

> **Phase 1 — chỉ đọc.** Không điều khiển, không reset lõi.
> Đã kiểm tra trên **KAQ-U98** (loại `Aiotec_41`). Các máy khác dùng bộ property `iro_*`
> cũng chạy; dòng K365 cũ (`mlt_*`) chưa hỗ trợ.

## Cài đặt

1. HACS → *Custom repositories* → thêm repo này (loại *Integration*) → cài **Karofi 365**,
   hoặc chép `custom_components/karofi_ha` vào `/config/custom_components/`.
2. Khởi động lại Home Assistant.
3. *Cài đặt → Thiết bị & Dịch vụ → Thêm tích hợp → Karofi 365* → nhập số điện thoại + mật khẩu
   app Karofi 365.

Tuỳ chọn: chu kỳ cập nhật (mặc định 60 s, 30–900 s).

## Entity (mỗi máy lọc)

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

> `iro_errs` rỗng hoặc thiếu = máy chưa báo → Trạng thái, Cảnh báo và Rò rỉ là `unknown`
> (không phải "Hoạt động ổn định"/tắt). Mảng rỗng thật (`[]`) hoặc toàn `"0"` vẫn là bình thường.

## Phát triển

```bash
pip install -r requirements_test.txt
pytest
```

Deploy thẳng lên HA qua SSH: chép `.env.example` → `.env`, điền `HA_HOST`/`HA_USER`/`HA_PASS`,
rồi `python tools/deploy.py` và restart HA.

---

<!-- support:start -->
## Support the project

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
</p>

<p align="center"><sub>🇻🇳 VietQR: quét bằng app ngân hàng bất kỳ, nội dung <code>Ung ho karofi_ha</code>. Cảm ơn bạn! · Thank you for keeping this project alive.</sub></p>
<!-- support:end -->
