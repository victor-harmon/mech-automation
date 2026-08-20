# 🔧 SolidWorks Automation Toolkit - Bộ công cụ tự động hóa SolidWorks

Bộ 12 script Python hỗ trợ thiết kế cơ khí (COM automation + calculators).

---

## 📦 Danh sách công cụ

| Script | Mục đích |
|--------|----------|
| `sw_batch_export.py` | Xuất batch nhiều định dạng: STEP, STL, PDF, DXF, glTF, IGES, Parasolid |
| `sw_bom_extractor.py` | Trích xuất BOM + ước lượng chi phí: Excel/CSV |
| `sw_drawing_template.py` | Tạo template drawing chuẩn: `.drwdot` |
| `sw_part_library.py` | Tạo thư viện chi tiết tiêu chuẩn: `.SLDPRT` + `.step` |
| `sw_sheetmetal_export.py` | Xuất flat pattern + nesting: DXF/DWG/PDF + report JSON |
| `sw_beam_calculator.py` | Kết cấu dầm: biến dạng, ứng suất uốn/cắt, MAWP |
| `sw_gear_calculator.py` | Bánh răng: spur/helical/bevel/worm (ISO 6336, AGMA 2001) |
| `sw_shaft_calculator.py` | Trục: xoắn, uốn, mỏi, tốc độ tới hạn, khóa (ASME B106.1M, DIN 743) |
| `sw_tolerance_stack.py` | Xếp chồng dung sai: worst-case, RSS, Monte Carlo (ASME Y14.5, ISO 1101) |
| `sw_spring_design.py` | Lò xo nén/kéo/xoắn (EN 13906, DIN 2088/2089, ISO 7046) |
| `sw_press_fit.py` | Lắp chặt: lực lắp, ứng suất trụ/vòng, khe hở (DIN 18095) |
| `sw_bolt_pattern.py` | Bố trí bulông: lực, momen, shear, prying, an toàn (FEA-style) |

Các file `README_<name>.md` có hướng dẫn chi tiết từng tool.

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
python sw_bom_extractor.py "C:\Projects\Assembly.SLDASM" "C:\Exports\BOM.csv" --material-csv materials.csv

# 3. Tạo template drawing ISO A3, A4
python sw_drawing_template.py --standard ISO --sizes A3,A4 --output "C:\Templates"

# 4. Generate thư viện fastener M6-M20, bearing, profile
python sw_part_library.py "C:\PartsLibrary" --standard ISO --categories fasteners,bearings,profiles --fastener-sizes M6,M8,M10,M12,M16,M20

# 5. Xuất flat pattern sheet metal + nesting 1500x3000
python sw_sheetmetal_export.py "C:\SheetMetalParts" "C:\Exports" --nesting-sheet 1500x3000 --formats dxf,pdf
```

Tính toán (không cần SolidWorks):

```bash
python sw_beam_calculator.py --help
python sw_gear_calculator.py --help
python sw_shaft_calculator.py --help
python sw_tolerance_stack.py --help
python sw_spring_design.py --help
python sw_press_fit.py --help
python sw_bolt_pattern.py --help
```

---

## Cập nhật: 2026-08-20 | 12 tools, duy trì bởi Johnny (Mechanical Engineer)