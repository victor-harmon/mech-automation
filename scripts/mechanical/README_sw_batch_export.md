# 📦 sw_batch_export.py - Batch Export SolidWorks Files

Xuất hàng loạt file `.SLDPRT`, `.SLDASM`, `.SLDDRW` sang nhiều định dạng.

---

## 🎯 Tính năng
- Duyệt đệ quy thư mục nguồn
- Xuất nhiều định dạng cùng lúc
- Giữ cấu trúc thư mục gốc
- Log chi tiết thành công/thất bại

---

## 📋 Định dạng hỗ trợ

| Format | Extension | Mô tả |
|--------|-----------|-------|
| STEP | `.step` | AP242 - trao đổi mô hình 3D |
| STL | `.stl` | In 3D - mesh tam giác |
| PDF | `.pdf` | Xem 3D nhúng trong PDF |
| DXF | `.dxf` | 2D CAD - laser/cnc cutting |
| glTF | `.gltf` | Web 3D - viewer nhẹ |
| 3D PDF | `.pdf` | PDF tương tác 3D |
| IGES | `.igs` | Trao đổi CAD cũ |
| Parasolid | `.x_t` | Kernel hình học |
| JPEG/PNG | `.jpg/.png` | Render hình ảnh |

---

## 🚀 Cách dùng

```bash
# Cơ bản
python sw_batch_export.py "C:\Projects" "C:\Exports"

# Chỉ định format
python sw_batch_export.py "C:\Projects" "C:\Exports" --formats step,stl,pdf,dxf,gltf

# Chỉ file phần (.SLDPRT)
python sw_batch_export.py "C:\Projects" "C:\Exports" --extensions SLDPRT

# Hiện UI SolidWorks
python sw_batch_export.py "C:\Projects" "C:\Exports" --visible
```

---

## ⚙️ Tham số

| Tham số | Mặc định | Mô tả |
|---------|----------|-------|
| `source` | (bắt buộc) | Thư mục chứa file SolidWorks |
| `output` | (bắt buộc) | Thư mục xuất ra |
| `--formats` | `step,stl,pdf,dxf` | Danh sách format cách nhau bằng dấu phẩy |
| `--extensions` | `SLDPRT,SLDASM` | Phần mở rộng file tìm kiếm |
| `--visible` | `False` | Hiện cửa sổ SolidWorks |

---

## 📂 Cấu trúc output

```
Exports/
├── ProjectA/
│   ├── Part1/
│   │   ├── Part1.step
│   │   ├── Part1.stl
│   │   └── Part1.dxf
│   └── SubAssy/
│       └── SubAssy.step
└── ProjectB/
    └── ...
```

---

## ⚠️ Lưu ý
- SolidWorks tự mở/đóng từng file → **không thao tác chuột** khi chạy
- File assembly lớn (>100 parts) có thể mất vài phút
- STL resolution: Fine (có thể chỉnh trong code)
- PDF xuất drawing view nếu là `.SLDDRW`

---

## 🐛 Lỗi thường gặp
| Lỗi | Giải pháp |
|-----|-----------|
| `OpenDoc6 failed` | File bị corrupt / đang mở bởi user khác |
| `SaveAs3 failed` | Format không hỗ trợ / đường dẫn quá dài |
| `COM Error` | Chạy `python -m pywin32_postinstall` as Admin |

---

*Phiên bản: 1.0 | Cập nhật: 2026-08-13*