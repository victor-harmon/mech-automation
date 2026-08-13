# 📚 sw_part_library.py - Standard Part Library Generator

Generate thư viện bộ phận cơ khí chuẩn (ISO/DIN/JIS) từ định nghĩa tham số.

---

## 🎯 Tính năng
- Tự động tạo file `.SLDPRT` + `.step` cho:
  - **Fasteners**: Bolts, Nuts, Washers, Screws
  - **Bearings**: Deep groove, Angular contact, Tapered roller
  - **Profiles**: Box, H-beam, I-beam, Channel, Angle
- Xuất catalog CSV (`PART_CATALOG.csv`)
- Hỗ trợ 3 chuẩn: ISO, DIN, JIS

---

## 📋 Danh mục & Kích thước

### Fasteners (M3-M30)
| Category | ISO Standards | DIN Standards |
|----------|---------------|---------------|
| Bolts | ISO 4014, 4017, 4762, 7380 | DIN 931, 933, 912, 7991 |
| Nuts | ISO 4032, 4035, 7040, 10511 | DIN 934, 985, 982, 6923 |
| Washers | ISO 7089, 7090, 7091, 7093 | DIN 125, 9021, 433, 6798 |
| Screws | ISO 4762, 7380, 14579, 14580 | DIN 912, 7991, 7984, 7500 |

Sizes: `M3, M4, M5, M6, M8, M10, M12, M14, M16, M18, M20, M22, M24, M27, M30`

### Bearings
| Type | Sizes (sample) |
|------|----------------|
| Deep Groove | 6000-6010, 6200-6210, 6300-6310 |
| Angular Contact | 7200-7208, 7300-7308 |
| Tapered Roller | 30202-30210, 32202-32210 |

### Structural Profiles (Vietnam/Asia common)
| Type | Sizes |
|------|-------|
| Box | 20×20×2 → 300×200×8 |
| H-Beam | 100×100 → 300×300 |
| I-Beam | I100 → I400 |
| Channel | C75×40 → C250×90 |
| Angle | L30×30×3 → L100×100×10 |

---

## 🚀 Cách dùng

```bash
# Mặc định: ISO, fastener M6-M20, bearing, profile
python sw_part_library.py "C:\PartsLibrary"

# Chỉ định chuẩn & category
python sw_part_library.py "C:\PartsLibrary" --standard DIN --categories fasteners,bearings

# Chỉ fastener M8,M10,M12
python sw_part_library.py "C:\PartsLibrary" --fastener-sizes M8,M10,M12 --categories fasteners

# Hiện UI
python sw_part_library.py "C:\PartsLibrary" --visible
```

---

## ⚙️ Tham số

| Tham số | Mặc định | Mô tả |
|---------|----------|-------|
| `output` | (bắt buộc) | Thư mục xuất |
| `--standard` | `ISO` | ISO, DIN, JIS |
| `--categories` | `fasteners,bearings,profiles` | Phân loại |
| `--fastener-sizes` | `M6,M8,M10,M12,M16,M20` | Kích thước fastener |
| `--visible` | `False` | Hiện SolidWorks |

---

## 📂 Output structure

```
PartsLibrary/
├── fasteners/
│   ├── ISO_bolts_M6.SLDPRT
│   ├── ISO_bolts_M6.step
│   ├── ISO_nuts_M8.SLDPRT
│   └── ...
├── bearings/
│   ├── ISO_bearing_deep_groove_6205.SLDPRT
│   └── ...
├── profiles/
│   ├── ISO_profile_box_50x50x3.SLDPRT
│   └── ...
└── PART_CATALOG.csv
```

---

## 📋 PART_CATALOG.csv columns

| Cột | Mô tả |
|-----|-------|
| Part_Number | Tên file (ISO_bolts_M6) |
| Category | fasteners/bearings/profiles |
| Standard | ISO/DIN/JIS |
| Size | M6, 6205, 50x50x3... |
| Description | Mô tả đầy đủ |
| File_SLDPRT | File native |
| File_STEP | File trao đổi |
| Material | Steel (mặc định) |
| Weight_kg | Ước lượng |
| Notes | Ghi chú |

---

## ⚠️ Lưu ý
- Script tạo **geometry cơ bản** (block/cylinder) - cần thêm thread feature, chamfer, fillet thủ công hoặc mở rộng code
- Bearing/profile là placeholder - cần modeling chi tiết theo catalog nhà sản xuất
- Chạy lần đầu mất thời gian (khởi động SW + tạo nhiều file)
- Khuyến nghị: Chạy demo nhỏ trước (`--fastener-sizes M6,M8 --categories fasteners`)

---

*Phiên bản: 1.0 | Cập nhật: 2026-08-13*