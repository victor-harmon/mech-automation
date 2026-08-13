# 🔧 sw_sheetmetal_export.py - Sheet Metal Flat Pattern & Nesting

Xuất flat pattern tấm kim loại và tạo layout nesting tự động.

---

## 🎯 Tính năng
- Nhận diện sheet metal part tự động
- Xuất flat pattern: DXF, DWG, PDF (có bend table, bend notes)
- Trích xuất thông số: Thickness, Bend radius, K-factor, Bends
- **Nesting layout** tự động (shelf packing algorithm)
- Xuất nesting DXF + report JSON

---

## 📋 Thông số trích xuất

| Tham số | Đơn vị | Mô tả |
|---------|--------|-------|
| Thickness | mm | Độ dày tấm |
| Bend Radius | mm | Bán kính uốn mặc định |
| K-Factor | - | Hệ số uốn |
| Bend Allowance Type | - | K_FACTOR / BEND_TABLE... |
| Bends | danh sách | Angle, Radius, Length, Direction |
| Flat Pattern Area | m² | Diện tích flat pattern |
| BBox Width/Height | mm | Kích thước bao |

---

## 🚀 Cách dùng

```bash
# Cơ bản
python sw_sheetmetal_export.py "C:\SheetMetalParts" "C:\Exports"

# Tùy chỉnh sheet nesting
python sw_sheetmetal_export.py "C:\SheetMetalParts" "C:\Exports" --nesting-sheet 1500x3000

# Chỉ DXF
python sw_sheetmetal_export.py "C:\SheetMetalParts" "C:\Exports" --formats dxf

# Hiện UI
python sw_sheetmetal_export.py "C:\SheetMetalParts" "C:\Exports" --visible
```

---

## ⚙️ Tham số

| Tham số | Mặc định | Mô tả |
|---------|----------|-------|
| `source` | (bắt buộc) | Thư mục chứa file .SLDPRT sheet metal |
| `output` | (bắt buộc) | Thư mục xuất |
| `--nesting-sheet` | `1500x3000` | Kích thước tấm nguyên liệu WxH (mm) |
| `--formats` | `dxf,pdf` | dxf,dwg,pdf |
| `--visible` | `False` | Hiện SolidWorks |

---

## 📂 Output structure

```
Exports/
├── Bracket1/
│   ├── Bracket1.dxf
│   ├── Bracket1.pdf
│   └── Bracket1_bends.csv
├── Cover2/
│   ├── Cover2.dxf
│   ├── Cover2.pdf
│   └── Cover2_bends.csv
├── nesting_layout.dxf
└── nesting_report.json
```

---

## 📋 Bends CSV

| Cột | Mô tả |
|-----|-------|
| Bend # | STT đường uốn |
| Angle (deg) | Góc uốn (độ) |
| Radius (mm) | Bán kính uốn |
| Length (mm) | Chiều dài đường uốn |
| Direction | Up / Down |

---

## 📦 Nesting Report JSON

```json
{
  "placements": [
    {"part_name": "Bracket1", "x": 10, "y": 10, "rotation": 0, "width": 200, "height": 150},
    {"part_name": "Cover2", "x": 220, "y": 10, "rotation": 0, "width": 300, "height": 200}
  ],
  "sheet_width": 1500,
  "sheet_height": 3000,
  "utilization_percent": 45.2,
  "parts_placed": 2,
  "total_parts": 2
}
```

---

## 🔧 Nesting Algorithm
- **Shelf Packing** (đơn giản, nhanh)
- Sắp xếp phần theo diện tích giảm dần
- Xoay 0°/90° (có thể mở rộng)
- Spacing mặc định 10mm

> ⚠️ Nesting này cơ bản. Production cần: TrueShape nesting, remnant tracking, grain direction, collision avoidance → dùng phần mềm chuyên dụng (SigmaNEST, Lantek, TruNest).

---

## ⚠️ Lưu ý
- Chỉ hoạt động với part có **Sheet Metal feature** (Base Flange)
- Flat pattern phải có thể flatten (không self-intersect)
- PDF xuất drawing view + bend table + bend notes
- DWG cần SolidWorks license có DXF/DWG translator

---

*Phiên bản: 1.0 | Cập nhật: 2026-08-13*