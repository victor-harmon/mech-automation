# 📊 sw_bom_extractor.py - BOM Extractor & Cost Estimator

Trích xuất Bill of Materials từ Assembly và ước lượng chi phí vật liệu + gia công.

---

## 🎯 Tính năng
- Đọc BOM từ Assembly (.SLDASM)
- Làm giàu dữ liệu: Mass, Volume, Material, Quantity
- Ước tính chi phí: Material + Manufacturing
- Xuất Excel/CSV chuẩn cho báo giá

---

## 📋 Output columns

| Cột | Mô tả |
|-----|-------|
| `Item_No` | STT |
| `Part_No` | Mã phụ tùng |
| `Description` | Mô tả |
| `Quantity` | Số lượng |
| `Material` | Vật liệu |
| `Mass_kg` | Khối lượng (kg) |
| `Volume_cm3` | Thể tích (cm³) |
| `Material_Cost_USD` | Chi phí vật liệu |
| `Mfg_Cost_USD` | Chi phí gia công |
| `Unit_Cost_USD` | Chi phí/ cái |
| `Total_Cost_USD` | Tổng chi phí (Qty × Unit) |
| `Process` | Quy trình gia công |
| `Vendor` | Nhà cung cấp |
| `Lead_Time` | Lead time (ngày) |

---

## 🚀 Cách dùng

```bash
# Cơ bản
python sw_bom_extractor.py "C:\Projects\MainAssembly.SLDASM" "C:\Exports\BOM.csv"

# Với file vật liệu tùy chỉnh
python sw_bom_extractor.py "C:\Projects\MainAssembly.SLDASM" "C:\Exports\BOM.csv" --material-csv materials.csv

# Chỉ định quy trình gia công
python sw_bom_extractor.py "C:\Projects\MainAssembly.SLDASM" "C:\Exports\BOM.csv" --process Laser_Cutting
```

---

## ⚙️ File materials.csv (tùy chọn)

```csv
Material,Cost_USD_per_kg
A36,0.80
S235JR,0.85
S355JR,0.95
1045,1.20
4140,1.80
Stainless_304,3.50
Stainless_316,4.20
6061-T6,3.20
7075-T6,5.50
ABS,2.50
POM,3.80
PEEK,85.00
```

Nếu không cung cấp → dùng giá mặc định trong script ($2/kg).

---

## 🔧 Quy trình gia công hỗ trợ

| Process | Factor (USD/kg) | Ứng dụng |
|---------|-----------------|----------|
| `CNC_Milling` | 15.0 | Gia công frais |
| `CNC_Turning` | 12.0 | Gia công tiện |
| `Laser_Cutting` | 8.0 | Cắt laser tấm |
| `Waterjet` | 10.0 | Cắt nước áp lực cao |
| `Sheet_Metal_Bending` | 5.0 | Dập tấm |
| `Welding` | 20.0 | Hàn |
| `Injection_Molding` | 3.0 | Đúc nhựa (lượng lớn) |
| `Die_Casting` | 4.0 | Đúc áp lực |
| `Forging` | 8.0 | Rèn |
| `3D_Print_FDM` | 25.0 | In 3D FDM |
| `3D_Print_SLA` | 40.0 | In 3D SLA |
| `3D_Print_SLS` | 60.0 | In 3D SLS |

---

## 📝 Công thức chi phí

```
Material_Cost = Mass_kg × Material_Cost_per_kg
Mfg_Cost = Mass_kg × Manufacturing_Factor
Unit_Cost = Material_Cost + Mfg_Cost
Total_Cost = Unit_Cost × Quantity
```

---

## ⚠️ Lưu ý
- Assembly phải có BOM table hoặc custom properties (Material, Mass)
- Mass/Volume lấy từ `Evaluate` → `Mass Properties` trong SW
- Material name khớp với `materials.csv` (case-insensitive)
- Chi phí chỉ ước lượng tham khảo, không thay thế báo giá thực

---

*Phiên bản: 1.0 | Cập nhật: 2026-08-13*