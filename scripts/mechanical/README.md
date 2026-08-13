# 🔧 SolidWorks Automation Toolkit - Bộ công cụ tự động hóa SolidWorks

Bộ 5 script Python tự động hóa quy trình thiết kế cơ khí trên SolidWorks thông qua COM API.

---

## 📦 Danh sách công cụ

| Script | Mục đích | Output |
|--------|----------|--------|
| `sw_batch_export.py` | Xuất batch nhiều định dạng | STEP, STL, PDF, DXF, glTF, 3D PDF, IGES, Parasolid |
| `sw_bom_extractor.py` | Trích xuất BOM + ước lượng chi phí | Excel/CSV: PartNo, Qty, Material, Mass, Cost, Vendor... |
| `sw_drawing_template.py` | Tạo template drawing chuẩn | `.drwdot` (ISO/ASME/JIS, A0-A4, ANSI A-E) |
| `sw_part_library.py` | Generate thư viện bộ phận chuẩn | `.SLDPRT` + `.step` + `PART_CATALOG.csv` |
| `sw_sheetmetal_export.py` | Xuất flat pattern + nesting | DXF/DWG/PDF + `nesting_layout.dxf` + report JSON |

---

## 🚀 Yêu cầu hệ thống

- **Windows** (SolidWorks chỉ chạy trên Windows)
- **SolidWorks** cài đặt & license hợp lệ (2020+ khuyến nghị)
- **Python 3.8+** với thư viện: `pywin32`, `ezdxf` (cho nesting)
- Quyền Administrator (để COM kết nối SolidWorks)

```bash
pip install pywin32 ezdxf
python -m pywin32_postinstall  # Đăng ký COM
```

---

## ⚡ Chạy nhanh

```bash
# 1. Batch export toàn bộ thư mục
python sw_batch_export.py "C:\Projects" "C:\Exports" --formats step,stl,pdf,dxf,gltf

# 2. Trích BOM từ assembly + ước giá
python sw_bom_extractor.py "C:\Projects\Assembly.SLDASM" "C:\Exports\BOM.csv" --material-csv materials.csv --process CNC_Milling

# 3. Tạo template drawing ISO A3, A4
python sw_drawing_template.py --standard ISO --sizes A3,A4 --output "C:\Templates"

# 4. Generate thư viện fastener M6-M20, bearing, profile
python sw_part_library.py "C:\PartsLibrary" --standard ISO --categories fasteners,bearings,profiles --fastener-sizes M6,M8,M10,M12,M16,M20

# 5. Xuất flat pattern sheet metal + nesting 1500x3000
python sw_sheetmetal_export.py "C:\SheetMetalParts" "C:\Exports" --nesting-sheet 1500x3000 --formats dxf,pdf
```

---

## 📁 Cấu trúc output mẫu

```
Exports/
├── sw_batch_export/
│   ├── Part1/
│   │   ├── Part1.step
│   │   ├── Part1.stl
│   │   └── Part1.dxf
│   └── Assembly1/
│       └── ...
├── sw_bom_extractor/
│   └── BOM.csv
├── sw_drawing_template/
│   ├── ISO_A3.drwdot
│   └── ISO_A4.drwdot
├── sw_part_library/
│   ├── fasteners/
│   │   ├── ISO_bolts_M6.SLDPRT
│   │   └── ISO_bolts_M6.step
│   ├── bearings/
│   ├── profiles/
│   └── PART_CATALOG.csv
└── sw_sheetmetal_export/
    ├── Bracket1/
    │   ├── Bracket1.dxf
    │   ├── Bracket1.pdf
    │   └── Bracket1_bends.csv
    ├── nesting_layout.dxf
    └── nesting_report.json
```

---

## 🔧 Tùy chỉnh

### Material costs (`sw_bom_extractor.py`)
Tạo file `materials.csv`:
```csv
Material,Cost_USD_per_kg
A36,0.80
S355JR,0.95
Stainless_304,3.50
6061-T6,3.20
ABS,2.50
```

Chạy: `--material-csv materials.csv`

### Manufacturing process
Các process hỗ trợ: `CNC_Milling`, `CNC_Turning`, `Laser_Cutting`, `Waterjet`, `Sheet_Metal_Bending`, `Welding`, `Injection_Molding`, `Die_Casting`, `Forging`, `3D_Print_FDM`, `3D_Print_SLA`, `3D_Print_SLS`

---

## ⚠️ Lưu ý quan trọng

1. **SolidWorks phải đang chạy** (hoặc script sẽ tự khởi động)
2. **Không thao tác chuột/phím** khi script đang chạy (COM automation)
3. **File lớn** (>50MB) có thể chậm - chạy từng batch nhỏ
4. **License SolidWorks** - cần seat network hoặc standalone
5. **Backup dữ liệu** trước khi chạy batch trên thư mục gốc

---

## 🐛 Troubleshooting

| Lỗi | Nguyên nhân | Khắc phục |
|-----|-------------|-----------|
| `win32com.client.Dispatch failed` | SolidWorks chưa cài/không đăng ký COM | Repair SolidWorks, chạy `python -m pywin32_postinstall` |
| `Access denied` | Không quyền Admin | Chạy terminal as Administrator |
| `Document not found` | Đường dẫn sai/ file bị khóa | Kiểm tra path, đóng file trong SW |
| `Export format failed` | Phiên bản SW không hỗ trợ format | Cập nhật SW hoặc bỏ format đó |

---

## 📄 License

MIT License - Tự do sử dụng, sửa đổi, phân phối.

---

## 🤝 Đóng góp

1. Fork repo
2. Tạo feature branch
3. Test trên SolidWorks thực tế
4. Submit PR

---

*Cập nhật: 2026-08-13 | Tác giả: Johnny (Mechanical Engineer)*