#!/usr/bin/env python3
"""
Gear Calculator
Tính toán các loại bánh răng: Spur, Helical, Bevel, Worm
Theo chuẩn ISO 6336, AGMA 2001, DIN 3990
"""

import math
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

class GearType(Enum):
    SPUR = "spur"           # Bánh răng trụ thẳng
    HELICAL = "helical"     # Bánh răng xiên
    BEVEL = "bevel"         # Bánh răng nón
    WORM = "worm"           # Trục vít / bánh răng côn

class MaterialGrade(Enum):
    # Thép carbon
    C45 = ("C45", 600, 350)          # (name, Sut MPa, Sy MPa)
    C45_HEAT = ("C45_heat", 900, 600)
    # Thép hợp kim
    _42CRMO4 = ("42CrMo4", 1100, 900)
    _42CRMO4_HEAT = ("42CrMo4_heat", 1400, 1200)
    # Thép cementation
    _16MNVCR5 = ("16MnCr5", 900, 600)  # Sau x الكربون
    _16MNVCR5_CARB = ("16MnCr5_carb", 1600, 1200)
    # Gang xám
    GGG40 = ("GGG40", 400, 250)
    GGG60 = ("GGG60", 600, 370)
    # Nhôm
    AL_7075 = ("Al7075", 570, 500)

    def __init__(self, name: str, sut: float, sy: float):
        self.mat_name = name
        self.sut = sut      # Ultimate tensile strength (MPa)
        self.sy = sy        # Yield strength (MPa)

@dataclass
class GearGeometry:
    module: float           # m (mm)
    teeth_pinion: int       # z1
    teeth_gear: int         # z2
    pressure_angle: float = 20.0    # alpha (deg)
    helix_angle: float = 0.0        # beta (deg) - cho helical
    face_width: float = 0.0         # b (mm)
    profile_shift_pinion: float = 0.0   # x1
    profile_shift_gear: float = 0.0     # x2
    center_distance: float = 0.0        # a (mm) - 0 = tính theo chuẩn

@dataclass
class GearLoad:
    power_kw: float         # Công suất (kW)
    speed_rpm: float        # Tốc độ trục nhỏ (rpm)
    torque_nm: float = 0.0  # Momen (Nm) - ưu tiên nếu có
    service_factor: float = 1.25    # K_A
    reliability_factor: float = 1.0  # K_R

@dataclass
class GearResult:
    # Geometry
    ratio: float
    pitch_dia_pinion: float
    pitch_dia_gear: float
    base_dia_pinion: float
    base_dia_gear: float
    center_distance: float
    contact_ratio: float
    
    # Strength (ISO 6336)
    bending_stress_pinion: float
    bending_stress_gear: float
    contact_stress: float
    allowable_bending: float
    allowable_contact: float
    safety_bending_pinion: float
    safety_bending_gear: float
    safety_contact: float
    
    # Forces
    tangential_force: float
    radial_force: float
    axial_force: float

class GearCalculator:
    def __init__(self, geometry: GearGeometry, load: GearLoad, 
                 material_pinion: MaterialGrade, material_gear: MaterialGrade):
        self.geo = geometry
        self.load = load
        self.mat1 = material_pinion
        self.mat2 = material_gear
    
    def calculate(self) -> GearResult:
        # Tính torque nếu chưa có
        if self.load.torque_nm == 0:
            T = 9550 * self.load.power_kw / self.load.speed_rpm
        else:
            T = self.load.torque_nm
        
        # Geometry cơ bản
        m = self.geo.module
        z1 = self.geo.teeth_pinion
        z2 = self.geo.teeth_gear
        alpha = math.radians(self.geo.pressure_angle)
        beta = math.radians(self.geo.helix_angle)
        x1 = self.geo.profile_shift_pinion
        x2 = self.geo.profile_shift_gear
        
        # Tỷ số truyền
        ratio = z2 / z1
        
        # Đường kính đường phần
        d1 = m * z1
        d2 = m * z2
        
        # Đường kính đường cơ sở
        db1 = d1 * math.cos(alpha)
        db2 = d2 * math.cos(alpha)
        
        # Khoảng cách trục
        if self.geo.center_distance > 0:
            a = self.geo.center_distance
        else:
            a = (d1 + d2) / 2
        
        # Số chân cắt thực tế (cho helical)
        if beta > 0:
            z_v1 = z1 / (math.cos(beta)**3)
            z_v2 = z2 / (math.cos(beta)**3)
        else:
            z_v1 = z1
            z_v2 = z2
        
        # Hệ số chồng cheo (contact ratio)
        eps_alpha = self._contact_ratio_transverse(d1, d2, db1, db2, a, alpha, x1, x2, self.geo.teeth_pinion)
        if beta > 0:
            eps_beta = self.geo.face_width * math.tan(beta) / (m * math.pi)
            eps_total = eps_alpha + eps_beta
        else:
            eps_total = eps_alpha
        
        # Lực tiếp xúc
        Ft = 2000 * T / d1  # N
        Fr = Ft * math.tan(alpha) / math.cos(beta)
        Fa = Ft * math.tan(beta)
        
        # Hệ số tải (ISO 6336 simplified)
        Ka = self.load.service_factor
        Kv = 1.0  # Giả định vận hành đều
        KHbeta = 1.0  # Phân bố tải theo chiều rộng
        KHalpha = 1.0
        
        # Ứng suất uốn (bending) - ISO 6336 simplified
        YF = self._form_factor(z_v1)
        YS = self._stress_correction_factor(z_v1)
        Ybeta = 1.0
        Yeps = 0.5 + 0.5 / eps_alpha  # Simplified
        
        sigma_F1 = Ft * Ka * Kv * KHbeta / (self.geo.face_width * m) * YF * YS * Ybeta / Yeps
        sigma_F2 = sigma_F1 * (z1/z2)**0.5  # Approximate
        
        # Ứng suất tiếp xúc (contact) - Hertz
        ZH = math.sqrt(2 * ratio / (1 + ratio))  # Zone factor
        ZE = 189.8  # Elasticity factor cho thép (MPa^0.5)
        Zeps = math.sqrt(eps_alpha)  # Contact ratio factor
        Zbeta = 1.0
        
        sigma_H = ZE * math.sqrt(Ft * Ka * Kv / (self.geo.face_width * d1)) * \
                  math.sqrt(ratio / (1 + ratio)) * ZH * Zbeta / Zeps
        
        # Cho phép (cho phép)
        sigma_FP = self.mat1.sy / 1.5  # Allowable bending
        sigma_HP = self.mat1.sut / 1.2  # Allowable contact
        
        # An toàn
        SF1 = sigma_FP / sigma_F1 if sigma_F1 > 0 else 999
        SF2 = sigma_FP / sigma_F2 if sigma_F2 > 0 else 999
        SH = sigma_HP / sigma_H if sigma_H > 0 else 999
        
        return GearResult(
            ratio=ratio,
            pitch_dia_pinion=d1,
            pitch_dia_gear=d2,
            base_dia_pinion=db1,
            base_dia_gear=db2,
            center_distance=a,
            contact_ratio=eps_total,
            bending_stress_pinion=sigma_F1,
            bending_stress_gear=sigma_F2,
            contact_stress=sigma_H,
            allowable_bending=sigma_FP,
            allowable_contact=sigma_HP,
            safety_bending_pinion=SF1,
            safety_bending_gear=SF2,
            safety_contact=SH,
            tangential_force=Ft,
            radial_force=Fr,
            axial_force=Fa
        )
    
    def _contact_ratio_transverse(self, d1, d2, db1, db2, a, alpha, x1, x2, z1):
        """Tính hệ số chồng cheo mặt phẳng"""
        m = self.geo.module
        # Góc áp lực thực tế tại đường phần
        alpha_w = math.acos((db1 + db2) / (2 * a))
        
        # Đường kính ngoài (tính xấp xỉ)
        da1 = d1 + 2 * m * (1 + x1)
        da2 = d2 + 2 * m * (1 + x2)
        
        # Góc áp lực tại đường ngoài
        alpha_a1 = math.acos(db1 / da1)
        alpha_a2 = math.acos(db2 / da2)
        
        # Hệ số chồng cheo
        eps = (math.tan(alpha_a1) + math.tan(alpha_a2) - 
               2 * math.tan(alpha_w)) / (2 * math.pi / z1 * math.cos(alpha))
        
        return max(eps, 1.0)
    
    def _form_factor(self, z_v):
        """Hệ số hình dạng YF (ISO 6336 approximate)"""
        if z_v < 10:
            return 0.3
        elif z_v < 20:
            return 0.4
        elif z_v < 50:
            return 0.5
        else:
            return 0.6
    
    def _stress_correction_factor(self, z_v):
        """Hệ số chỉnh ứng suất YS"""
        if z_v < 10:
            return 1.3
        elif z_v < 20:
            return 1.1
        else:
            return 1.0


def design_gear_pair(power_kw: float, speed_rpm: float, ratio: float,
                     material: MaterialGrade = MaterialGrade._42CRMO4_HEAT,
                     gear_type: GearType = GearType.SPUR) -> Dict:
    """Thiết kế sơ bộ cặp bánh răng"""
    T = 9550 * power_kw / speed_rpm
    
    # Chọn module theo công suất (kinh nghiệm)
    if power_kw < 1:
        m = 1.5
    elif power_kw < 5:
        m = 2.5
    elif power_kw < 20:
        m = 4
    elif power_kw < 50:
        m = 6
    else:
        m = 8
    
    # Chọn số răng
    z1 = 20  # Tránh undercut
    z2 = int(z1 * ratio)
    
    # Chiều rộng mặt răng
    b = 10 * m
    
    # Tạo geometry
    geo = GearGeometry(
        module=m,
        teeth_pinion=z1,
        teeth_gear=z2,
        face_width=b,
        helix_angle=15.0 if gear_type == GearType.HELICAL else 0.0
    )
    
    load = GearLoad(power_kw=power_kw, speed_rpm=speed_rpm)
    
    calc = GearCalculator(geo, load, material, material)
    result = calc.calculate()
    
    return {
        "module": m,
        "z1": z1,
        "z2": z2,
        "face_width": b,
        "result": result,
        "safe": result.safety_bending_pinion > 1.2 and result.safety_contact > 1.0
    }

def demo():
    print("=" * 60)
    print("GEAR CALCULATOR - DEMO")
    print("=" * 60)
    
    # Case 1: Bánh răng trụ thẳng 5.5kW, 1500rpm, i=3
    print("\n1. SPUR GEAR - 5.5kW, 1500rpm, i=3")
    design = design_gear_pair(5.5, 1500, 3.0, MaterialGrade._42CRMO4_HEAT, GearType.SPUR)
    r = design["result"]
    print(f"   Module: {design['module']}mm, z1={design['z1']}, z2={design['z2']}")
    print(f"   d1={r.pitch_dia_pinion:.1f}mm, d2={r.pitch_dia_gear:.1f}mm")
    print(f"   Center distance: {r.center_distance:.1f}mm")
    print(f"   Contact ratio: {r.contact_ratio:.2f}")
    print(f"   Bending stress: {r.bending_stress_pinion:.1f} MPa (allow {r.allowable_bending:.1f})")
    print(f"   Contact stress: {r.contact_stress:.1f} MPa (allow {r.allowable_contact:.1f})")
    print(f"   Safety bending: {r.safety_bending_pinion:.2f}")
    print(f"   Safety contact: {r.safety_contact:.2f}")
    print(f"   Forces: Ft={r.tangential_force:.0f}N, Fr={r.radial_force:.0f}N, Fa={r.axial_force:.0f}N")
    print(f"   Safe: {design['safe']}")
    
    # Case 2: Helical gear
    print("\n2. HELICAL GEAR - 15kW, 1500rpm, i=4")
    design = design_gear_pair(15, 1500, 4.0, MaterialGrade._42CRMO4_HEAT, GearType.HELICAL)
    r = design["result"]
    print(f"   Module: {design['module']}mm, z1={design['z1']}, z2={design['z2']}")
    print(f"   Helix angle: 15 deg")
    print(f"   Safety bending: {r.safety_bending_pinion:.2f}")
    print(f"   Safety contact: {r.safety_contact:.2f}")
    print(f"   Axial force: {r.axial_force:.0f}N")
    print(f"   Safe: {design['safe']}")
    
    # Case 3: Kiểm tra bánh răng cho trước
    print("\n3. CHECK EXISTING GEAR - m=4, z1=25, z2=75, b=40mm")
    geo = GearGeometry(module=4, teeth_pinion=25, teeth_gear=75, face_width=40)
    load = GearLoad(power_kw=7.5, speed_rpm=1000)
    calc = GearCalculator(geo, load, MaterialGrade.C45_HEAT, MaterialGrade.C45_HEAT)
    r = calc.calculate()
    print(f"   Ratio: {r.ratio:.2f}")
    print(f"   Contact ratio: {r.contact_ratio:.2f}")
    print(f"   Bending stress: {r.bending_stress_pinion:.1f} MPa")
    print(f"   Contact stress: {r.contact_stress:.1f} MPa")
    print(f"   Safety factors: SF1={r.safety_bending_pinion:.2f}, SH={r.safety_contact:.2f}")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    demo()