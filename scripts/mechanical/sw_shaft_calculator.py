#!/usr/bin/env python3
"""
Shaft Calculator - Thiết kế & kiểm tra trục
Theo ASME B106.1M, ISO 1154, DIN 743
Tính: ứng suất tĩnh, mỏi, độ lệch, tốc độ critical, khóa/chốt
"""

import math
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

class LoadType(Enum):
    PURE_TORSION = "torsion"           # Chỉ xoắn
    PURE_BENDING = "bending"           # Chỉ uốn
    COMBINED = "combined"              # Kết hợp xoắn + uốn
    REVERSED_BENDING = "reversed"      # Uốn luân phiên (xoay)

class MaterialGrade(Enum):
    # Thép carbon
    C45 = ("C45", 600, 350, 210000, 0.3)
    C45_HEAT = ("C45_heat", 900, 600, 210000, 0.3)
    # Thép hợp kim
    _42CRMO4 = ("42CrMo4", 1100, 900, 210000, 0.3)
    _42CRMO4_HEAT = ("42CrMo4_heat", 1400, 1200, 210000, 0.3)
    # Thép cementation
    _16MNVCR5_CARB = ("16MnCr5_carb", 1600, 1200, 210000, 0.3)
    # Gang xám
    GGG40 = ("GGG40", 400, 250, 170000, 0.28)
    GGG60 = ("GGG60", 600, 370, 170000, 0.28)

    def __init__(self, name: str, sut: float, sy: float, E: float, nu: float):
        self.mat_name = name
        self.sut = sut      # MPa
        self.sy = sy        # MPa
        self.E = E          # MPa
        self.nu = nu        # Poisson ratio

@dataclass
class ShaftGeometry:
    diameter: float         # d (mm) - đường kính trục
    length: float           # L (mm) - chiều dài
    # Khoản nới (optional)
    fillet_radius: float = 1.0      # r (mm) - bán kính bo góc
    keyway_width: float = 0.0       # b (mm) - độ rộng khóa
    keyway_depth: float = 0.0       # h (mm) - độ sâu khóa
    hole_diameter: float = 0.0      # d_h (mm) - lỗ trục

@dataclass
class ShaftLoad:
    torque_nm: float = 0.0          # Momen xoắn (Nm)
    bending_nm: float = 0.0         # Momen uốn (Nm)
    axial_n: float = 0.0            # Lực trục (N)
    speed_rpm: float = 0.0          # Tốc độ (rpm)
    load_type: LoadType = LoadType.COMBINED

@dataclass
class ShaftResult:
    # Static strength
    tau_torsion: float              # Ứng suất xoắn (MPa)
    sigma_bending: float            # Ứng suất uốn (MPa)
    sigma_axial: float              # Ứng suất trục (MPa)
    sigma_vm_static: float          # Von Mises tĩnh (MPa)
    safety_static: float            # An toàn tĩnh
    
    # Fatigue (ASME Elliptic / Soderberg / Goodman)
    sigma_a: float                  # Ứng suất luân phiên (MPa)
    sigma_m: float                  # Ứng suất trung bình (MPa)
    se: float                       # Giữa mỏi endurance limit (MPa)
    safety_fatigue: float           # An toàn mỏi
    
    # Deflection & Critical speed
    max_deflection: float           # Độ lệch tối đa (mm)
    max_slope: float                # Góc nghiêng tối đa (rad)
    critical_speed_rpm: float       # Tốc độ critical (rpm)
    safety_critical: float          # An toàn tốc độ
    
    # Stress concentration
    Kt_bending: float               # Hệ số tập trung ứng suất uốn
    Kt_torsion: float               # Hệ số tập trung ứng suất xoắn
    Kf_bending: float               # Hệ số mỏi uốn
    Kf_torsion: float               # Hệ số mỏi xoắn

class ShaftCalculator:
    def __init__(self, geometry: ShaftGeometry, load: ShaftLoad, 
                 material: MaterialGrade, surface_finish: str = "machined",
                 temperature: float = 20, reliability: float = 0.999):
        self.geo = geometry
        self.load = load
        self.mat = material
        self.surface = surface_finish
        self.temp = temperature
        self.reliability = reliability
    
    def calculate(self) -> ShaftResult:
        d = self.geo.diameter
        r = self.geo.fillet_radius
        b = self.geo.keyway_width
        h = self.geo.keyway_depth
        dh = self.geo.hole_diameter
        
        T = self.load.torque_nm * 1000      # N.mm
        M = self.load.bending_nm * 1000     # N.mm
        F = self.load.axial_n               # N
        n = self.load.speed_rpm
        
        # Mômen quán tiết diện
        if dh > 0:
            I = math.pi / 64 * (d**4 - dh**4)
            J = math.pi / 32 * (d**4 - dh**4)
            A = math.pi / 4 * (d**2 - dh**2)
            Z = math.pi / 32 * (d**4 - dh**4) / (d/2)
            Zp = math.pi / 16 * (d**4 - dh**4) / d
        else:
            I = math.pi / 64 * d**4
            J = math.pi / 32 * d**4
            A = math.pi / 4 * d**2
            Z = math.pi / 32 * d**3
            Zp = math.pi / 16 * d**3
        
        # --- 1. Ứng suất tĩnh ---
        tau = T / Zp if Zp > 0 else 0
        sigma_b = M / Z if Z > 0 else 0
        sigma_a = F / A if A > 0 else 0
        
        # Von Mises static
        sigma_vm = math.sqrt((sigma_b + sigma_a)**2 + 3 * tau**2)
        safety_static = self.mat.sy / sigma_vm if sigma_vm > 0 else 999
        
        # --- 2. Hệ số tập trung ứng suất (Kt) ---
        Kt_b, Kt_t = self._stress_concentration_factors(d, r, b, h, dh)
        
        # --- 3. Hệ số mỏi (Kf) ---
        q = self._notch_sensitivity(d, r)  # Neuber
        Kf_b = 1 + q * (Kt_b - 1)
        Kf_t = 1 + q * (Kt_t - 1)
        
        # --- 4. Ứng suất thay đổi (alternating) & trung bình (mean) ---
        # Bending: fully reversed nếu trục xoay
        sigma_b_a = Kf_b * sigma_b if self.load.load_type in [LoadType.COMBINED, LoadType.REVERSED_BENDING] else 0
        sigma_b_m = 0  # Uốn luân phiên -> mean = 0
        
        # Torsion: steady
        tau_m = Kf_t * tau
        tau_a = 0
        
        # Axial: steady
        sigma_ax_m = sigma_a
        sigma_ax_a = 0
        
        # Von Mises alternating & mean
        sigma_a_vm = math.sqrt(sigma_b_a**2 + 3 * tau_a**2 + sigma_ax_a**2)
        sigma_m_vm = math.sqrt((sigma_b_m + sigma_ax_m)**2 + 3 * tau_m**2)
        
        # --- 5. Giới hạn chịu mỏi (Endurance limit) ---
        se_prime = 0.5 * self.mat.sut if self.mat.sut < 1400 else 700  # MPa
        
        # Hệ số điều chỉnh (Marin)
        ka = self._surface_factor()      # Bề mặt
        kb = self._size_factor(d)        # Kích thước
        kc = 1.0                         # Tải trọng (bending=1)
        kd = self._temperature_factor()  # Nhiệt độ
        ke = self._reliability_factor()  # Độ tin cậy
        
        se = se_prime * ka * kb * kc * kd * ke
        
        # --- 6. An toàn mỏi (Soderberg / Goodman / Gerber) ---
        # Soderberg: sigma_a/Se + sigma_m/Sy = 1/n
        # Goodman:  sigma_a/Se + sigma_m/Sut = 1/n
        # Gerber:   sigma_a/Se + (sigma_m/Sut)^2 = 1/n
        
        # Dùng Goodman (phổ biến nhất cho trục)
        if sigma_m_vm > 0 and se > 0:
            n_fatigue = 1 / (sigma_a_vm / se + sigma_m_vm / self.mat.sut)
        elif sigma_a_vm > 0 and se > 0:
            n_fatigue = se / sigma_a_vm
        else:
            n_fatigue = 999
        
        # --- 7. Độ lệch & Tốc độ critical ---
        delta_max, theta_max, n_crit = self._deflection_critical_speed(d, I, n)
        
        safety_critical = n_crit / n if n > 0 and n_crit > 0 else 999
        
        return ShaftResult(
            tau_torsion=tau,
            sigma_bending=sigma_b,
            sigma_axial=sigma_a,
            sigma_vm_static=sigma_vm,
            safety_static=safety_static,
            sigma_a=sigma_a_vm,
            sigma_m=sigma_m_vm,
            se=se,
            safety_fatigue=n_fatigue,
            max_deflection=delta_max,
            max_slope=theta_max,
            critical_speed_rpm=n_crit,
            safety_critical=safety_critical,
            Kt_bending=Kt_b,
            Kt_torsion=Kt_t,
            Kf_bending=Kf_b,
            Kf_torsion=Kf_t
        )
    
    def _stress_concentration_factors(self, d, r, b, h, dh) -> Tuple[float, float]:
        """Kt cho bo góc, khóa, lỗ (Peterson / Shigley approximate)"""
        # Bo góc
        if r > 0:
            D_d = (d + 2*r) / d
            r_d = r / d
            if D_d < 1.2:
                Kt_fillet_b = 1.7 - 0.7 * r_d
                Kt_fillet_t = 1.4 - 0.4 * r_d
            else:
                Kt_fillet_b = 1.0
                Kt_fillet_t = 1.0
        else:
            Kt_fillet_b = 2.5
            Kt_fillet_t = 2.0
        
        # Khóa (keyway)
        if b > 0 and h > 0:
            Kt_key_b = 2.0  # Uốn
            Kt_key_t = 1.8  # Xoắn
        else:
            Kt_key_b = 1.0
            Kt_key_t = 1.0
        
        # Lỗ trục
        if dh > 0:
            ratio = dh / d
            Kt_hole_b = 3.0 * ratio
            Kt_hole_t = 2.0 * ratio
        else:
            Kt_hole_b = 1.0
            Kt_hole_t = 1.0
        
        # Kết hợp (lấy max)
        Kt_b = max(Kt_fillet_b, Kt_key_b, Kt_hole_b)
        Kt_t = max(Kt_fillet_t, Kt_key_t, Kt_hole_t)
        
        return Kt_b, Kt_t
    
    def _notch_sensitivity(self, d, r) -> float:
        """Neuber notch sensitivity q"""
        # sqrt(r) in mm
        sqrt_r = math.sqrt(r) if r > 0 else 0
        # Đường cong Neuber cho thép (approximate)
        if self.mat.sut < 700:
            A = 0.3
        elif self.mat.sut < 1400:
            A = 0.2
        else:
            A = 0.1
        
        q = 1 / (1 + A / sqrt_r) if sqrt_r > 0 else 1.0
        return min(q, 1.0)
    
    def _surface_factor(self) -> float:
        """ka - Hệ số bề mặt"""
        sut = self.mat.sut
        if self.surface == "polished":
            a, b = 1.58, -0.085
        elif self.surface == "ground":
            a, b = 4.51, -0.265
        elif self.surface == "machined":
            a, b = 57.7, -0.718
        elif self.surface == "hot_rolled":
            a, b = 137, -0.853
        elif self.surface == "as_forged":
            a, b = 272, -0.995
        else:
            a, b = 57.7, -0.718
        return a * sut**b
    
    def _size_factor(self, d) -> float:
        """kb - Hệ số kích thước"""
        if d <= 8:
            return 1.0
        elif d <= 250:
            return 1.189 * d**(-0.097)
        else:
            return 0.6
    
    def _temperature_factor(self) -> float:
        """kd - Hệ số nhiệt độ"""
        if self.temp <= 20:
            return 1.0
        elif self.temp <= 200:
            return 1 - 0.001 * (self.temp - 20)
        elif self.temp <= 400:
            return 0.85 - 0.0005 * (self.temp - 200)
        else:
            return 0.7
    
    def _reliability_factor(self) -> float:
        """ke - Hệ số độ tin cậy"""
        rel_map = {
            0.50: 1.000, 0.90: 0.897, 0.95: 0.868,
            0.99: 0.814, 0.999: 0.753, 0.9999: 0.702
        }
        return rel_map.get(self.reliability, 0.814)
    
    def _deflection_critical_speed(self, d, I, n) -> Tuple[float, float, float]:
        """Độ lệch & tốc độ critical (dầm đơn, tải trọng giữa)"""
        L = self.geo.length
        E = self.mat.E
        w = math.pi / 4 * d**2 * 7850 / 1e9  # Trọng lượng riêng (N/mm) - thép 7850 kg/m3
        
        # Tải trọng: trọng lượng + tải ngoài
        F_total = self.load.bending_nm * 1000 / (L/4) if L > 0 else 0  # Approx
        
        # Độ lệch do trọng lượng riêng (dầm đơn, UDL)
        delta_w = 5 * w * L**4 / (384 * E * I) if I > 0 else 0
        
        # Độ lệch do tải trọng giữa
        delta_F = F_total * L**3 / (48 * E * I) if I > 0 else 0
        
        delta_max = delta_w + delta_F
        
        # Góc nghiêng
        theta_max = (w * L**3 / (24 * E * I) + F_total * L**2 / (16 * E * I)) if I > 0 else 0
        
        # Tốc độ critical (dầm đơn, khối lượng phân bố)
        # n_crit = 30/pi * sqrt(g/delta_static)
        if delta_max > 0:
            n_crit = 30 / math.pi * math.sqrt(9810 / delta_max)
        else:
            n_crit = 99999
        
        return delta_max, theta_max, n_crit


def design_shaft(torque_nm: float, bending_nm: float, speed_rpm: float,
                 material: MaterialGrade = MaterialGrade._42CRMO4_HEAT,
                 safety_target: float = 2.0,
                 length: float = 500) -> Dict:
    """Thiết kế sơ bộ đường kính trục tối thiểu"""
    
    # Ước lượng đường kính theo ASME B106.1M
    # d^3 = 16/(pi*Sy) * sqrt((Kf*M)^2 + (Kfs*T)^2) * n
    Kf = 1.5  # Uốn
    Kfs = 1.0 # Xoắn
    
    Sy = material.sy
    M = bending_nm * 1000
    T = torque_nm * 1000
    
    d_est = (16 / (math.pi * Sy) * math.sqrt((Kf*M)**2 + (Kfs*T)**2) * safety_target)**(1/3)
    
    # Làm tròn lên chuẩn (mm)
    std_sizes = [10,12,14,15,16,17,18,19,20,22,24,25,28,30,32,35,38,40,42,45,48,50,
                 55,60,65,70,75,80,85,90,95,100,110,120,130,140,150]
    d = next((s for s in std_sizes if s >= d_est), d_est * 1.1)
    
    # Kiểm tra chi tiết
    geo = ShaftGeometry(diameter=d, length=length, fillet_radius=d*0.05)
    load = ShaftLoad(torque_nm=torque_nm, bending_nm=bending_nm, speed_rpm=speed_rpm)
    calc = ShaftCalculator(geo, load, material)
    result = calc.calculate()
    
    # Nếu chưa an toàn, tăng size
    while result.safety_fatigue < safety_target or result.safety_static < safety_target:
        idx = std_sizes.index(d) if d in std_sizes else 0
        if idx + 1 < len(std_sizes):
            d = std_sizes[idx + 1]
            geo.diameter = d
            calc = ShaftCalculator(geo, load, material)
            result = calc.calculate()
        else:
            break
    
    return {
        "diameter": d,
        "result": result,
        "safe": result.safety_fatigue >= safety_target and result.safety_static >= safety_target
    }

def demo():
    print("=" * 60)
    print("SHAFT CALCULATOR - DEMO")
    print("=" * 60)
    
    # Case 1: Trục truyền động cơ 7.5kW, 1500rpm
    print("\n1. SHAFT DESIGN - 7.5kW, 1500rpm, T=48Nm, M=20Nm")
    design = design_shaft(torque_nm=48, bending_nm=20, speed_rpm=1500,
                          material=MaterialGrade._42CRMO4_HEAT, length=600)
    d = design["diameter"]
    r = design["result"]
    print(f"   Diameter: {d} mm")
    print(f"   Static safety: {r.safety_static:.2f}")
    print(f"   Fatigue safety (Goodman): {r.safety_fatigue:.2f}")
    print(f"   Critical speed: {r.critical_speed_rpm:.0f} rpm")
    print(f"   Speed safety: {r.safety_critical:.2f}")
    print(f"   Max deflection: {r.max_deflection:.3f} mm")
    print(f"   Kt_b={r.Kt_bending:.2f}, Kt_t={r.Kt_torsion:.2f}")
    print(f"   Kf_b={r.Kf_bending:.2f}, Kf_t={r.Kf_torsion:.2f}")
    print(f"   Endurance limit Se: {r.se:.1f} MPa")
    print(f"   Safe: {design['safe']}")
    
    # Case 2: Kiểm tra trục cho trước
    print("\n2. CHECK EXISTING SHAFT - d=40mm, T=120Nm, M=80Nm, 1000rpm")
    geo = ShaftGeometry(diameter=40, length=800, fillet_radius=2.0, 
                        keyway_width=12, keyway_depth=5)
    load = ShaftLoad(torque_nm=120, bending_nm=80, speed_rpm=1000)
    calc = ShaftCalculator(geo, load, MaterialGrade.C45_HEAT)
    r = calc.calculate()
    print(f"   Static: sigma_vm={r.sigma_vm_static:.1f} MPa, n={r.safety_static:.2f}")
    print(f"   Fatigue: sigma_a={r.sigma_a:.1f}, sigma_m={r.sigma_m:.1f}, Se={r.se:.1f}, n={r.safety_fatigue:.2f}")
    print(f"   Critical speed: {r.critical_speed_rpm:.0f} rpm, n={r.safety_critical:.2f}")
    print(f"   Deflection: {r.max_deflection:.3f} mm")
    
    # Case 3: Trục rỗng
    print("\n3. HOLLOW SHAFT - d=60mm, dh=30mm, T=500Nm, M=200Nm")
    geo = ShaftGeometry(diameter=60, length=1000, hole_diameter=30)
    load = ShaftLoad(torque_nm=500, bending_nm=200, speed_rpm=500)
    calc = ShaftCalculator(geo, load, MaterialGrade._42CRMO4)
    r = calc.calculate()
    print(f"   Weight savings: ~{(30/60)**2*100:.0f}% vs solid")
    print(f"   Static safety: {r.safety_static:.2f}")
    print(f"   Fatigue safety: {r.safety_fatigue:.2f}")
    print(f"   Critical speed: {r.critical_speed_rpm:.0f} rpm")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    demo()