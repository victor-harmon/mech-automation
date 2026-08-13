# 📐 sw_drawing_template.py - Drawing Template Generator

Tạo template bản vẽ kỹ thuật chuẩn (`.drwdot`) cho SolidWorks.

---

## 🎯 Tính năng
- Tạo template ISO / ASME / JIS
- Khổ giấy A0-A4 (ISO) & A-E (ANSI)
- Title block có linked properties
- BOM table template
- GD&T symbols reference
- Revision table
- Custom properties mapping

---

## 📋 Chuẩn hỗ trợ

| Chuẩn | Projection | Units | Title Block | BOM Standard |
|-------|------------|-------|-------------|--------------|
| ISO | Third Angle | MMGS | ISO 7200 | ISO 7200 |
| ASME | First Angle | IPS | ASME Y14.34 | ASME Y14.34 |
| JIS | Third Angle | MMGS | JIS B 0001 | JIS B 0001 |

---

## 📐 Khổ giấy

| ISO | Kích thước (mm) | ANSI | Kích thước (inch) |
|-----|-----------------|------|-------------------|
| A0 | 1189 × 841 | E | 44 × 34 |
| A1 | 841 × 594 | D | 34 × 22 |
| A2 | 594 × 420 | C | 22 × 17 |
| A3 | 420 × 297 | B | 17 × 11 |
| A4 | 297 × 210 | A | 11 × 8.5 |

---

## 🚀 Cách dùng

```bash
# Tạo ISO A3, A4
python sw_drawing_template.py --standard ISO --sizes A3,A4 --output "C:\Templates"

# Tạo tất cả chuẩn, tất cả khổ
python sw_drawing_template.py --standard ISO,ASME,JIS --sizes A4,A3,A2,A1,A0,A,B,C,D,E --output "C:\Templates"

# Hiện UI
python sw_drawing_template.py --standard ISO --sizes A3 --output "C:\Templates" --visible
```

---

## ⚙️ Tham số

| Tham số | Mặc định | Mô tả |
|---------|----------|-------|
| `--standard` | `ISO,ASME` | ISO,ASME,JIS (cách nhau dấu phẩy) |
| `--sizes` | `A4,A3,A2,A1,A0` | Khổ giấy |
| `--output` | `C:/Templates` | Thư mục xuất |
| `--visible` | `False` | Hiện SolidWorks |

---

## 📦 Output

```
Templates/
├── ISO_A4.drwdot
├── ISO_A3.drwdot
├── ISO_A2.drwdot
├── ASME_A.drwdot
├── ASME_B.drwdot
└── JIS_A3.drwdot
```

---

## 🔧 Template bao gồm

1. **Title Block** - Linked properties: Project, Drawing No, Rev, Scale, Weight, Material, Drawn/Checked/Approved by, Date
2. **Standard Views** - Front, Top, Right, Isometric placeholders
3. **BOM Table** - Indented, top-level only
4. **GD&T Symbols** - 20+ ký hiệu tham chiếu (off-sheet)
5. **Revision Table** - 5 rows × 4 cols (Rev, Desc, Date, Approved)
6. **Custom Properties** - SW_STANDARD, SW_PROJECTION, SW_UNITS, SW_DECIMAL_PLACES

---

## 📝 Cách sử dụng template

1. Mở SolidWorks → `File` → `New` → Chọn template `.drwdot`
2. Kéo model vào → Views tự động tạo
3. Properties tự động fill từ model (Mass, Material, Scale...)
4. Điền Project, Drawing No, Rev, Finish, Drawn/Checked/Approved

---

## ⚠️ Lưu ý
- Template chỉ tạo khung, cần model mới có views/BOM thực
- GD&T symbols là note tham chiếu (không link dim)
- Revision table cần điền tay hoặc macro

---

*Phiên bản: 1.0 | Cập nhật: 2026-08-13*