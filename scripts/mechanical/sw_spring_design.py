#!/usr/bin/env python3
"""
Spring Design Calculator
Thiết kế lò xo: nén, kéo, xoắn
Theo: EN 13906, DIN 2088, DIN 2089, ISO 7046
"""

import math
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

class SpringType(Enum):
    COMPRESSION = "compression"     # Lò xo nén
    EXTENSION = "extension"         # Lò xo kéo
    TORSION = "torsion"             # Lò xo xoắn

class SpringEndType(Enum):
    # Compression
    PLAIN = "plain"                 # Đẳng, không ép
    GROUND = "ground"               # Đẳng, ép
    GROUND_SQUARED = "ground_sq"    # Vuông, ép
    # Extension
    FULL_LOOP = "full_loop"         # Khuyên tròn đầy
    HALF_LOOP = "half_loop"         # Khuyên nửa
    EXTENDED_HOOK = "ext_hook"      # Móc dài
    # Torsion
    STRAIGHT = "straight"           # Thẳng
    HINGED = "hinged"               # Có khớp

class SpringMaterial(Enum):
    # Dây thép lò xo (EN 10270)
    SM_1 = ("SM", 1500, 1800)       # Music wire (Class A)
    SM_2 = ("SM", 1400, 1700)       # Class B
    SM_3 = ("SM", 1300, 1600)       # Class C
    SH_1 = ("SH", 1600, 1900)       # Valve spring wire (Class A)
    SH_2 = ("SH", 1500, 1800)       # Class B
    DH_1 = ("DH", 1700, 2000)       # Cr-Si (Class A)
    DH_2 = ("DH", 1600, 1900)       # Class B
    # Inox
    X10CRNI18_8 = ("X10CrNi18-8", 1200, 1500)  # 1.4310
    X5CRNI18_10 = ("X5CrNi18-10", 1100, 1400)  # 1.4301
    # Thép hợp kim
    _51CRV4 = ("51CrV4", 1500, 1800)  # 1.8159

    def __init__(self, name: str, ts_min: float, ts_max: float):
        self.mat_name = name
        self.ts_min = ts_min      # MPa - tensile strength min
        self.ts_max = ts_max      # MPa - tensile strength max

@dataclass
class SpringGeometry:
    # Common
    wire_dia: float           # d (mm)
    outer_dia: float = 0.0    # De (mm) - đường kính ngoài
    inner_dia: float = 0.0    # Di (mm) - đường kính trong
    mean_dia: float = 0.0     # Dm (mm) - đường kính trung bình
    total_coils: float = 0.0  # Nt - tổng số vòng
    active_coils: float = 0.0 # Na - số vòng hoạt động
    free_length: float = 0.0  # L0 (mm) - chiều dài tự do
    solid_length: float = 0.0 # Ls (mm) - chiều dài ép chặt
    pitch: float = 0.0        # p (mm) - bước sóng
    # Ends
    end_type: SpringEndType = SpringEndType.GROUND_SQUARED
    # Torsion specific
    leg_length1: float = 0.0
    leg_length2: float = 0.0
    leg_angle: float = 0.0    # Góc giữa 2 chân (deg)

@dataclass
class SpringLoad:
    # Operating points
    force_1: float = 0.0      # F1 (N) - tại L1
    length_1: float = 0.0     # L1 (mm)
    force_2: float = 0.0      # F2 (N) - tại L2
    length_2: float = 0.0     # L2 (mm)
    # Or rate + preload
    rate: float = 0.0         # R (N/mm) - độ cứng
    preload: float = 0.0      # F0 (N) - lực lắp đặt
    # Torsion
    torque_1: float = 0.0     # M1 (N.mm)
    angle_1: float = 0.0      # α1 (deg)
    torque_2: float = 0.0     # M2 (N.mm)
    angle_2: float = 0.0      # α2 (deg)
    # Dynamic
    freq_hz: float = 0.0      # Tần số dao động (Hz)
    max_cycles: float = 1e7   # Số chu kỳ thiết kế

@dataclass
class SpringResult:
    # Geometry
    spring_index: float       # C = Dm/d
    mean_dia: float
    inner_dia: float
    outer_dia: float
    solid_length: float
    pitch: float
    
    # Stiffness
    rate: float               # R (N/mm) hoặc (N.mm/deg)
    
    # Stress
    stress_1: float           # τ1 (MPa) - tại F1/α1
    stress_2: float           # τ2 (MPa) - tại F2/α2
    stress_solid: float       # τs (MPa) - tại ép chặt
    stress_correction: float  # Ks hoặc Kw
    
    # Strength
    tensile_strength: float   # Rm (MPa)
    allowable_static: float   # τ_allow static (MPa)
    allowable_fatigue: float  # τ_allow fatigue (MPa)
    safety_static_1: float
    safety_static_2: float
    safety_fatigue: float
    
    # Buckling (compression)
    slenderness_ratio: float
    buckling_safety: float
    
    # Dynamic
    natural_freq: float       # fn (Hz)
    surge_waves: float        # Surge waves count
    
    # Manufacturing
    weight: float             # (g)
    material_volume: float    # (mm3)

class SpringCalculator:
    def __init__(self, spring_type: SpringType, geometry: SpringGeometry, 
                 load: SpringLoad, material: SpringMaterial):
        self.type = spring_type
        self.geo = geometry
        self.load = load
        self.mat = material
    
    def calculate(self) -> SpringResult:
        if self.type == SpringType.COMPRESSION:
            return self._calc_compression()
        elif self.type == SpringType.EXTENSION:
            return self._calc_extension()
        elif self.type == SpringType.TORSION:
            return self._calc_torsion()
        else:
            raise ValueError("Unknown spring type")
    
    def _geometry_setup(self):
        """Tính các thông số hình học cơ bản"""
        d = self.geo.wire_dia
        
        if self.geo.mean_dia > 0:
            Dm = self.geo.mean_dia
        elif self.geo.outer_dia > 0:
            Dm = self.geo.outer_dia - d
        elif self.geo.inner_dia > 0:
            Dm = self.geo.inner_dia + d
        else:
            raise ValueError("Need at least one diameter")
        
        Di = Dm - d
        De = Dm + d
        C = Dm / d
        
        # Active coils
        if self.geo.active_coils > 0:
            Na = self.geo.active_coils
        elif self.geo.total_coils > 0:
            Na = self._total_to_active(self.geo.total_coils)
        else:
            raise ValueError("Need coil count")
        
        # Solid length
        if self.geo.end_type in [SpringEndType.GROUND, SpringEndType.GROUND_SQUARED]:
            Ls = d * (Na + 2)  # Ground ends
        else:
            Ls = d * (Na + 1)
        
        # Pitch
        if self.geo.free_length > 0:
            p = (self.geo.free_length - Ls) / Na + d
        else:
            p = 0
        
        return Dm, Di, De, C, Na, Ls, p
    
    def _total_to_active(self, Nt: float) -> float:
        """Chuyển tổng vòng sang vòng hoạt động"""
        if self.geo.end_type == SpringEndType.PLAIN:
            return Nt
        elif self.geo.end_type in [SpringEndType.GROUND, SpringEndType.GROUND_SQUARED]:
            return Nt - 2
        else:
            return Nt - 1.5
    
    def _calc_compression(self) -> SpringResult:
        d = self.geo.wire_dia
        Dm, Di, De, C, Na, Ls, p = self._geometry_setup()
        
        # Material properties
        G = 79300  # MPa - Shear modulus cho thép
        Rm = self.mat.ts_min  # Tensile strength
        
        # Spring rate
        R = G * d**4 / (8 * Dm**3 * Na)  # N/mm
        
        # Stress correction factor (Wahl)
        Ks = (4*C - 1) / (4*C - 4) + 0.615 / C
        
        # Forces
        F1 = self.load.force_1
        F2 = self.load.force_2
        if F1 == 0 and self.load.rate > 0:
            F1 = self.load.preload
        if F2 == 0 and self.load.length_2 > 0:
            F2 = self.load.rate * (self.geo.free_length - self.load.length_2)
        
        # Stresses
        tau1 = Ks * 8 * F1 * Dm / (math.pi * d**3) if F1 > 0 else 0
        tau2 = Ks * 8 * F2 * Dm / (math.pi * d**3) if F2 > 0 else 0
        
        # Solid stress
        Fs = R * (self.geo.free_length - Ls)
        tau_solid = Ks * 8 * Fs * Dm / (math.pi * d**3)
        
        # Allowable stresses
        tau_allow_static = 0.45 * Rm  # Static shear
        tau_allow_fatigue = self._fatigue_limit_compression(d, Rm)
        
        # Safety factors
        sf1 = tau_allow_static / tau1 if tau1 > 0 else 999
        sf2 = tau_allow_static / tau2 if tau2 > 0 else 999
        sf_fat = tau_allow_fatigue / max(tau1, tau2) if max(tau1, tau2) > 0 else 999
        
        # Buckling
        slenderness = self.geo.free_length / Dm
        buckling_sf = self._buckling_check(slenderness, C)
        
        # Natural frequency
        # m = active mass = density * volume * (active fraction)
        rho = 7850  # kg/m3
        wire_vol = math.pi * d**2 / 4 * (math.pi * Dm * Na)  # mm3
        m_active = rho * wire_vol * 1e-9 * 0.33  # kg (1/3 mass active)
        fn = 0.5 * math.sqrt(R * 1000 / m_active) if m_active > 0 else 0
        
        # Surge waves
        # N_surge = fn / f_operating
        surge = fn / self.load.freq_hz if self.load.freq_hz > 0 else 0
        
        # Weight
        weight = rho * wire_vol * 1e-9 * 1000  # g
        
        return SpringResult(
            spring_index=C,
            mean_dia=Dm,
            inner_dia=Di,
            outer_dia=De,
            solid_length=Ls,
            pitch=p,
            rate=R,
            stress_1=tau1,
            stress_2=tau2,
            stress_solid=tau_solid,
            stress_correction=Ks,
            tensile_strength=Rm,
            allowable_static=tau_allow_static,
            allowable_fatigue=tau_allow_fatigue,
            safety_static_1=sf1,
            safety_static_2=sf2,
            safety_fatigue=sf_fat,
            slenderness_ratio=slenderness,
            buckling_safety=buckling_sf,
            natural_freq=fn,
            surge_waves=surge,
            weight=weight,
            material_volume=wire_vol
        )
    
    def _fatigue_limit_compression(self, d: float, Rm: float) -> float:
        """Giới hạn mỏi lò xo nén (EN 13906-1)"""
        # τ_fat = a * d^b  (approximate)
        # Cho thép lò xo: ~0.35-0.45 * Rm tùy kích thước
        if d <= 1:
            return 0.45 * Rm
        elif d <= 3:
            return 0.40 * Rm
        elif d <= 6:
            return 0.35 * Rm
        else:
            return 0.30 * Rm
    
    def _buckling_check(self, slenderness: float, C: float) -> float:
        """Kiểm tra좌굴 (EN 13906-2)"""
        # Critical slenderness ratio
        if slenderness < 0.8:
            return 999  # Không lo ngại
        elif slenderness < 3.0:
            return 3.0 / slenderness
        else:
            # Cần hướng dẫn/buồng
            return 0.5
    
    def _calc_extension(self) -> SpringResult:
        d = self.geo.wire_dia
        Dm, Di, De, C, Na, Ls, p = self._geometry_setup()
        
        G = 79300
        Rm = self.mat.ts_min
        
        # Rate
        R = G * d**4 / (8 * Dm**3 * Na)
        
        # Stress correction - extension springs have higher stress at hooks
        Ks = (4*C - 1) / (4*C - 4) + 0.615 / C  # Body
        Kw = Ks * 1.25  # Hook stress concentration (approx)
        
        F1 = self.load.force_1
        F2 = self.load.force_2
        
        tau1 = Ks * 8 * F1 * Dm / (math.pi * d**3) if F1 > 0 else 0
        tau2 = Ks * 8 * F2 * Dm / (math.pi * d**3) if F2 > 0 else 0
        
        # Hook stress (critical)
        tau_hook1 = Kw * 8 * F1 * Dm / (math.pi * d**3) if F1 > 0 else 0
        tau_hook2 = Kw * 8 * F2 * Dm / (math.pi * d**3) if F2 > 0 else 0
        
        # Allowable
        tau_allow_static = 0.45 * Rm
        tau_allow_hook = 0.40 * Rm  # Lower for hooks
        tau_allow_fatigue = 0.35 * Rm
        
        sf1 = tau_allow_static / tau1 if tau1 > 0 else 999
        sf2 = tau_allow_static / tau2 if tau2 > 0 else 999
        sf_hook1 = tau_allow_hook / tau_hook1 if tau_hook1 > 0 else 999
        sf_hook2 = tau_allow_hook / tau_hook2 if tau_hook2 > 0 else 999
        sf_fat = tau_allow_fatigue / max(tau1, tau2) if max(tau1, tau2) > 0 else 999
        
        # Natural frequency
        rho = 7850
        wire_vol = math.pi * d**2 / 4 * (math.pi * Dm * Na)
        m_active = rho * wire_vol * 1e-9 * 0.33
        fn = 0.5 * math.sqrt(R * 1000 / m_active) if m_active > 0 else 0
        
        weight = rho * wire_vol * 1e-9 * 1000
        
        return SpringResult(
            spring_index=C,
            mean_dia=Dm,
            inner_dia=Di,
            outer_dia=De,
            solid_length=Ls,
            pitch=p,
            rate=R,
            stress_1=tau1,
            stress_2=tau2,
            stress_solid=tau_hook1,  # Hook stress is critical
            stress_correction=Ks,
            tensile_strength=Rm,
            allowable_static=tau_allow_static,
            allowable_fatigue=tau_allow_fatigue,
            safety_static_1=min(sf1, sf_hook1),
            safety_static_2=min(sf2, sf_hook2),
            safety_fatigue=sf_fat,
            slenderness_ratio=0,
            buckling_safety=0,
            natural_freq=fn,
            surge_waves=0,
            weight=weight,
            material_volume=wire_vol
        )
    
    def _calc_torsion(self) -> SpringResult:
        d = self.geo.wire_dia
        Dm, Di, De, C, Na, Ls, p = self._geometry_setup()
        
        E = 206000  # MPa - Young's modulus
        Rm = self.mat.ts_min
        
        # Torsion spring rate (N.mm/deg)
        R = E * d**4 / (3667 * Dm * Na)  # N.mm/deg
        
        # Stress correction for torsion
        Ki = (4*C**2 - C - 1) / (4*C*(C-1))  # Inner fiber (critical)
        Ko = (4*C**2 + C - 1) / (4*C*(C-1))  # Outer fiber
        
        M1 = self.load.torque_1
        M2 = self.load.torque_2
        
        # Bending stress (torsion springs work in bending)
        sigma1 = Ki * 32 * M1 / (math.pi * d**3) if M1 > 0 else 0
        sigma2 = Ki * 32 * M2 / (math.pi * d**3) if M2 > 0 else 0
        
        # Allowable bending stress
        sigma_allow_static = 0.75 * Rm
        sigma_allow_fatigue = 0.45 * Rm
        
        sf1 = sigma_allow_static / sigma1 if sigma1 > 0 else 999
        sf2 = sigma_allow_static / sigma2 if sigma2 > 0 else 999
        sf_fat = sigma_allow_fatigue / max(sigma1, sigma2) if max(sigma1, sigma2) > 0 else 999
        
        # Deflection angle
        theta1 = M1 / R if R > 0 else 0
        theta2 = M2 / R if R > 0 else 0
        
        weight = 7850 * (math.pi * d**2 / 4 * math.pi * Dm * Na) * 1e-9 * 1000
        
        return SpringResult(
            spring_index=C,
            mean_dia=Dm,
            inner_dia=Di,
            outer_dia=De,
            solid_length=Ls,
            pitch=p,
            rate=R,
            stress_1=sigma1,
            stress_2=sigma2,
            stress_solid=0,
            stress_correction=Ki,
            tensile_strength=Rm,
            allowable_static=sigma_allow_static,
            allowable_fatigue=sigma_allow_fatigue,
            safety_static_1=sf1,
            safety_static_2=sf2,
            safety_fatigue=sf_fat,
            slenderness_ratio=0,
            buckling_safety=0,
            natural_freq=0,
            surge_waves=0,
            weight=weight,
            material_volume=math.pi * d**2 / 4 * math.pi * Dm * Na
        )

def design_compression_spring(F_max: float, L_min: float, L_max: float,
                              D_max: float, material: SpringMaterial = SpringMaterial.SM_1,
                              safety: float = 1.5) -> Dict:
    """Thiết kế sơ bộ lò xo nén"""
    # Ước lượng d từ ứng suất
    Rm = material.ts_min
    tau_allow = 0.45 * Rm / safety
    
    # Giả định C = 8
    C = 8
    Ks = (4*C - 1) / (4*C - 4) + 0.615 / C
    
    # τ = Ks * 8 * F * D / (π * d^3) = Ks * 8 * F * C / (π * d^2)
    # d^2 = Ks * 8 * F * C / (π * τ)
    d_est = math.sqrt(Ks * 8 * F_max * C / (math.pi * tau_allow))
    
    # Chuẩn hóa
    std_wire = [0.5,0.6,0.7,0.8,0.9,1.0,1.2,1.4,1.6,1.8,2.0,2.2,2.5,2.8,3.0,3.5,4.0,4.5,5.0,5.5,6.0,7.0,8.0,9.0,10.0]
    d = next((s for s in std_wire if s >= d_est), d_est)
    
    Dm = C * d
    
    # Rate
    R = (F_max - 0) / (L_max - L_min) if L_max > L_min else 0
    
    # Active coils
    G = 79300
    Na = G * d**4 / (8 * Dm**3 * R) if R > 0 else 0
    
    # Free length
    L0 = L_max
    if Na > 0:
        Ls = d * (Na + 2)
        p = (L0 - Ls) / Na + d
    
    # Verify
    geo = SpringGeometry(wire_dia=d, mean_dia=Dm, active_coils=Na, 
                         free_length=L0, end_type=SpringEndType.GROUND_SQUARED)
    load = SpringLoad(force_1=F_max, length_1=L_min, force_2=0, length_2=L_max)
    calc = SpringCalculator(SpringType.COMPRESSION, geo, load, material)
    result = calc.calculate()
    
    return {
        "wire_dia": d,
        "mean_dia": Dm,
        "outer_dia": Dm + d,
        "inner_dia": Dm - d,
        "active_coils": round(Na, 1),
        "total_coils": round(Na + 2, 1),
        "free_length": L0,
        "solid_length": result.solid_length,
        "rate": result.rate,
        "pitch": result.pitch,
        "stress_max": result.stress_1,
        "safety_static": result.safety_static_1,
        "safety_fatigue": result.safety_fatigue,
        "buckling_safety": result.buckling_safety,
        "natural_freq": result.natural_freq,
        "weight": result.weight,
        "result": result
    }

def demo():
    print("=" * 60)
    print("SPRING DESIGN CALCULATOR - DEMO")
    print("=" * 60)
    
    # Case 1: Lò xo nén
    print("\n1. COMPRESSION SPRING - Design")
    design = design_compression_spring(
        F_max=500, L_min=30, L_max=50, D_max=30,
        material=SpringMaterial.SM_1, safety=1.5
    )
    print(f"   Wire dia: {design['wire_dia']} mm")
    print(f"   Mean dia: {design['mean_dia']:.1f} mm")
    print(f"   Outer dia: {design['outer_dia']:.1f} mm")
    print(f"   Active coils: {design['active_coils']}")
    print(f"   Free length: {design['free_length']} mm")
    print(f"   Solid length: {design['solid_length']:.1f} mm")
    print(f"   Rate: {design['rate']:.1f} N/mm")
    print(f"   Pitch: {design['pitch']:.1f} mm")
    print(f"   Max stress: {design['stress_max']:.0f} MPa")
    print(f"   Safety static: {design['safety_static']:.2f}")
    print(f"   Safety fatigue: {design['safety_fatigue']:.2f}")
    print(f"   Buckling safety: {design['buckling_safety']:.2f}")
    print(f"   Natural freq: {design['natural_freq']:.0f} Hz")
    print(f"   Weight: {design['weight']:.1f} g")
    
    # Case 2: Kiểm tra lò xo nén cho trước
    print("\n2. CHECK EXISTING COMPRESSION SPRING")
    geo = SpringGeometry(wire_dia=4.0, mean_dia=24.0, active_coils=8.5,
                         free_length=60, end_type=SpringEndType.GROUND_SQUARED)
    load = SpringLoad(force_1=200, length_1=45, force_2=400, length_2=30)
    calc = SpringCalculator(SpringType.COMPRESSION, geo, load, SpringMaterial.SH_1)
    r = calc.calculate()
    print(f"   Rate: {r.rate:.1f} N/mm")
    print(f"   Stress at F1: {r.stress_1:.0f} MPa")
    print(f"   Stress at F2: {r.stress_2:.0f} MPa")
    print(f"   Solid stress: {r.stress_solid:.0f} MPa")
    print(f"   Safety static: {r.safety_static_1:.2f} / {r.safety_static_2:.2f}")
    print(f"   Safety fatigue: {r.safety_fatigue:.2f}")
    print(f"   Buckling safety: {r.buckling_safety:.2f}")
    print(f"   Natural freq: {r.natural_freq:.0f} Hz")
    
    # Case 3: Lò xo kéo
    print("\n3. EXTENSION SPRING")
    geo = SpringGeometry(wire_dia=3.0, mean_dia=18.0, active_coils=12,
                         free_length=50, end_type=SpringEndType.FULL_LOOP)
    load = SpringLoad(force_1=100, length_1=65, force_2=200, length_2=80)
    calc = SpringCalculator(SpringType.EXTENSION, geo, load, SpringMaterial.SM_1)
    r = calc.calculate()
    print(f"   Rate: {r.rate:.1f} N/mm")
    print(f"   Body stress: {r.stress_1:.0f} / {r.stress_2:.0f} MPa")
    print(f"   Hook stress (solid): {r.stress_solid:.0f} MPa")
    print(f"   Safety (body): {r.safety_static_1:.2f} / {r.safety_static_2:.2f}")
    print(f"   Safety fatigue: {r.safety_fatigue:.2f}")
    print(f"   Natural freq: {r.natural_freq:.0f} Hz")
    
    # Case 4: Lò xo xoắn
    print("\n4. TORSION SPRING")
    geo = SpringGeometry(wire_dia=2.5, mean_dia=15.0, active_coils=6,
                         free_length=0, end_type=SpringEndType.STRAIGHT)
    load = SpringLoad(torque_1=500, angle_1=45, torque_2=800, angle_2=90)
    calc = SpringCalculator(SpringType.TORSION, geo, load, SpringMaterial.SM_1)
    r = calc.calculate()
    print(f"   Rate: {r.rate:.1f} N.mm/deg")
    print(f"   Stress at M1: {r.stress_1:.0f} MPa")
    print(f"   Stress at M2: {r.stress_2:.0f} MPa")
    print(f"   Safety static: {r.safety_static_1:.2f} / {r.safety_static_2:.2f}")
    print(f"   Safety fatigue: {r.safety_fatigue:.2f}")
    print(f"   Deflection at M1: {500/r.rate:.1f} deg")
    print(f"   Deflection at M2: {800/r.rate:.1f} deg")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    demo()