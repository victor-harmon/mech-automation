#!/usr/bin/env python3
"""
Press Fit / Shrink Fit Calculator
Tính toán khít ép, khít nhiệt: ứng suất, lực lắp, mômen xoắn, nhiệt độ
Theo: ISO 286, DIN 7190, Machinery's Handbook
"""

import math
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

class FitType(Enum):
    CLEARANCE = "clearance"       # Khít lỏng
    TRANSITION = "transition"     # Khít quá độ
    INTERFERENCE = "interference" # Khít chặt (press fit)
    SHRINK = "shrink"             # Khít nhiệt (shrink fit)

class MaterialGrade(Enum):
    # (Name, E GPa, ν, α 1e-6/K, Sy MPa, Sut MPa)
    STEEL_45 = ("C45", 210, 0.3, 12.0, 350, 600)
    STEEL_42CRMO4 = ("42CrMo4", 210, 0.3, 12.0, 900, 1100)
    STAINLESS_304 = ("304", 193, 0.3, 17.3, 215, 515)
    CAST_IRON_GG25 = ("GG25", 110, 0.25, 10.5, 250, 250)
    ALUMINUM_7075 = ("7075", 71.7, 0.33, 23.6, 503, 572)
    BRONZE = ("Bronze", 100, 0.34, 18.0, 250, 450)
    TITANIUM = ("Ti-6Al-4V", 113.8, 0.34, 9.0, 880, 950)

    def __init__(self, name: str, E: float, nu: float, alpha: float, sy: float, sut: float):
        self.mat_name = name
        self.E = E * 1000      # MPa
        self.nu = nu
        self.alpha = alpha     # 1e-6/K
        self.sy = sy           # MPa
        self.sut = sut         # MPa

@dataclass
class FitGeometry:
    shaft_dia: float          # d (mm) - đường kính trục
    hub_od: float             # D (mm) - đường kính ngoài毂
    length: float             # L (mm) - chiều dài khít
    hub_id: float = 0.0       # d_h (mm) - đường kính trong毂 (0 = solid)
    surface_roughness_shaft: float = 1.6   # Ra (µm)
    surface_roughness_hub: float = 3.2     # Ra (µm)

@dataclass
class FitTolerance:
    # ISO 286 fundamental deviation
    shaft_upper: float = 0.0      # es (µm)
    shaft_lower: float = 0.0      # ei (µm)
    hub_upper: float = 0.0        # ES (µm)
    hub_lower: float = 0.0        # EI (µm)
    
    @property
    def interference_min(self) -> float:
        """Đảm khít tối thiểu (µm)"""
        return self.shaft_lower - self.hub_upper
    
    @property
    def interference_max(self) -> float:
        """Đảm khít tối đa (µm)"""
        return self.shaft_upper - self.hub_lower
    
    @property
    def interference_mean(self) -> float:
        """Đảm khít trung bình (µm)"""
        return (self.interference_min + self.interference_max) / 2

@dataclass
class FitLoad:
    torque_nm: float = 0.0      # Momen xoắn (Nm)
    axial_force_n: float = 0.0  # Lực trục (N)
    radial_force_n: float = 0.0 # Lực شعاعي (N)
    cycles: float = 0.0         # Số chu kỳ疲劳

@dataclass
class FitResult:
    # Interface pressure
    pressure_mpa: float         # P (MPa) - áp suất tiếp xúc
    pressure_min: float
    pressure_max: float
    
    # Stresses (Lamé equations)
    shaft_stress_radial: float      # σr trục
    shaft_stress_hoop: float        # σθ trục
    shaft_stress_vm: float          # Von Mises trục
    hub_stress_radial: float        # σr 毂
    hub_stress_hoop: float          # σθ 毂
    hub_stress_vm: float            # Von Mises 毂
    
    # Assembly forces
    insertion_force_kn: float       # Lực ép (kN)
    extraction_force_kn: float      # Lực rút (kN)
    
    # Torque & axial capacity
    torque_capacity_nm: float       # Momen truyền (Nm)
    axial_capacity_kn: float        # Lực trục truyền (kN)
    
    # Safety factors
    safety_yield_shaft: float
    safety_yield_hub: float
    safety_fatigue_shaft: float
    safety_fatigue_hub: float
    
    # Shrink fit
    delta_t_heating: float          # ΔT làm nóng毂 (°C)
    delta_t_cooling: float          # ΔT làm lạnh trục (°C)
    
    # Contact
    contact_stiffness: float        # kN/mm
    microslip_load: float           # Lực gây microslip (N)

class PressFitCalculator:
    def __init__(self, shaft_mat: MaterialGrade, hub_mat: MaterialGrade,
                 geometry: FitGeometry, tolerance: FitTolerance,
                 load: FitLoad = None, friction: float = 0.15):
        self.shaft_mat = shaft_mat
        self.hub_mat = hub_mat
        self.geo = geometry
        self.tol = tolerance
        self.load = load or FitLoad()
        self.mu = friction
    
    def calculate(self) -> FitResult:
        d = self.geo.shaft_dia
        D = self.geo.hub_od
        d_h = self.geo.hub_id if self.geo.hub_id > 0 else 0
        L = self.geo.length
        
        # Mean interference (mm)
        delta = self.tol.interference_mean / 1000  # mm
        delta_min = self.tol.interference_min / 1000
        delta_max = self.tol.interference_max / 1000
        
        # Material properties
        Es = self.shaft_mat.E
        vs = self.shaft_mat.nu
        Eh = self.hub_mat.E
        vh = self.hub_mat.nu
        Sys = self.shaft_mat.sy
        Syh = self.hub_mat.sy
        
        # --- 1. Interface Pressure (Lamé) ---
        # P = δ / [d/Es * (C^2+1)/(C^2-1) + v_s + d/Eh * (1+v_h)/(1-d_h^2/D^2) - v_h]
        # C = D/d
        C = D / d
        
        # Shaft term
        term_s = d / Es * (C**2 + 1) / (C**2 - 1) + vs
        
        # Hub term
        if d_h > 0:
            # Hollow hub
            term_h = d / Eh * (1 + vh) / (1 - (d_h/D)**2) - vh
        else:
            # Solid hub
            term_h = d / Eh * (1 + vh) - vh
        
        P = delta / (term_s + term_h)  # MPa
        P_min = delta_min / (term_s + term_h)
        P_max = delta_max / (term_s + term_h)
        
        # --- 2. Stresses at Interface (r = d/2) ---
        # Shaft (solid cylinder under external pressure P)
        # σr = -P
        # σθ = -P * 2 * C^2 / (C^2 - 1)
        shaft_radial = -P
        shaft_hoop = -P * 2 * C**2 / (C**2 - 1)
        shaft_vm = math.sqrt(shaft_hoop**2 - shaft_hoop*shaft_radial + shaft_radial**2)
        
        # Hub (thick cylinder under internal pressure P)
        if d_h > 0:
            # σr = -P * (D^2 - r^2) / (D^2 - d_h^2)
            # σθ = P * (D^2 + r^2) / (D^2 - d_h^2)
            hub_radial = -P
            hub_hoop = P * (D**2 + d**2) / (D**2 - d_h**2)
        else:
            # Solid hub: at r = d/2
            hub_radial = -P
            hub_hoop = P * (1 + (d/D)**2) / (1 - (d/D)**2)
        
        hub_vm = math.sqrt(hub_hoop**2 - hub_hoop*hub_radial + hub_radial**2)
        
        # --- 3. Assembly Forces ---
        # Friction force per unit area = μ * P
        # Total friction = μ * P * π * d * L
        area = math.pi * d * L  # mm2
        F_friction = self.mu * P * area / 1000  # kN
        
        # Additional force for surface roughness deformation
        Rz_s = self.geo.surface_roughness_shaft * 4  # Rz ≈ 4*Ra
        Rz_h = self.geo.surface_roughness_hub * 4
        delta_rough = (Rz_s + Rz_h) / 1000  # mm
        F_rough = math.pi * d * L * delta_rough / (term_s + term_h) / 1000  # kN
        
        insertion_force = F_friction + F_rough
        extraction_force = insertion_force * 1.2  # Typically higher
        
        # --- 4. Torque & Axial Capacity ---
        # T = μ * P * π * d^2 * L / 2
        torque_cap = self.mu * P * math.pi * d**2 * L / 2000  # Nm
        axial_cap = self.mu * P * math.pi * d * L / 1000  # kN
        
        # --- 5. Safety Factors ---
        safety_shaft = Sys / shaft_vm if shaft_vm > 0 else 999
        safety_hub = Syh / hub_vm if hub_vm > 0 else 999
        
        # Fatigue (approximate: alternating stress from torque/axial load)
        # For press fit, mean stress is dominant
        sigma_a_shaft = self._alternating_stress_shaft(P, self.load.torque_nm)
        sigma_a_hub = self._alternating_stress_hub(P, self.load.torque_nm)
        
        Se_s = 0.5 * self.shaft_mat.sut if self.shaft_mat.sut < 1400 else 700
        Se_h = 0.5 * self.hub_mat.sut if self.hub_mat.sut < 1400 else 700
        
        safety_fat_shaft = Se_s / sigma_a_shaft if sigma_a_shaft > 0 else 999
        safety_fat_hub = Se_h / sigma_a_hub if sigma_a_hub > 0 else 999
        
        # --- 6. Shrink Fit Temperature ---
        # δ = α * d * ΔT
        alpha_s = self.shaft_mat.alpha * 1e-6
        alpha_h = self.hub_mat.alpha * 1e-6
        
        # Heating hub: ΔT = δ / (α_h * d)
        delta_T_heat = delta / (alpha_h * d)  # °C
        
        # Cooling shaft: ΔT = δ / (α_s * d)
        delta_T_cool = delta / (alpha_s * d)  # °C
        
        # --- 7. Contact Stiffness ---
        # k = P / δ_contact (per unit area)
        k_contact = P / delta / 1000  # kN/mm per mm2 -> kN/mm/mm2
        
        # --- 8. Microslip ---
        # Load at which microslip initiates
        microslip = self.mu * P * area  # N
        
        return FitResult(
            pressure_mpa=P,
            pressure_min=P_min,
            pressure_max=P_max,
            shaft_stress_radial=shaft_radial,
            shaft_stress_hoop=shaft_hoop,
            shaft_stress_vm=shaft_vm,
            hub_stress_radial=hub_radial,
            hub_stress_hoop=hub_hoop,
            hub_stress_vm=hub_vm,
            insertion_force_kn=insertion_force,
            extraction_force_kn=extraction_force,
            torque_capacity_nm=torque_cap,
            axial_capacity_kn=axial_cap,
            safety_yield_shaft=safety_shaft,
            safety_yield_hub=safety_hub,
            safety_fatigue_shaft=safety_fat_shaft,
            safety_fatigue_hub=safety_fat_hub,
            delta_t_heating=delta_T_heat,
            delta_t_cooling=delta_T_cool,
            contact_stiffness=k_contact,
            microslip_load=microslip
        )
    
    def _alternating_stress_shaft(self, P: float, T: float) -> float:
        """Alternating von Mises stress in shaft from external loads"""
        d = self.geo.shaft_dia
        # Bending from torque
        sigma_b = 16 * T * 1000 / (math.pi * d**3) if T > 0 else 0
        # Shear from torque
        tau = 16 * T * 1000 / (math.pi * d**3) if T > 0 else 0
        # Press fit stresses are mean (steady)
        return math.sqrt(sigma_b**2 + 3 * tau**2)
    
    def _alternating_stress_hub(self, P: float, T: float) -> float:
        return 0  # Simplified

def fit_tolerance_ISO(d: float, shaft_class: str, hub_class: str) -> FitTolerance:
    """ISO 286 standard fits lookup (simplified)"""
    # Standard tolerances in µm for common sizes
    # This is a simplified lookup - real implementation needs full ISO 286 tables
    
    # IT grades (µm) for diameter ranges
    IT_table = {
        6: {1:0.8, 2:1.2, 3:2, 4:3, 5:4, 6:5, 7:8, 8:12, 9:20, 10:30, 11:40},
        10: {1:1, 2:1.5, 3:2.5, 4:4, 5:6, 6:9, 7:15, 8:22, 9:36, 10:58, 11:90},
        18: {1:1.2, 2:2, 3:3, 4:5, 5:8, 6:11, 7:18, 8:27, 9:43, 10:70, 11:110},
        30: {1:1.5, 2:2.5, 3:4, 4:6, 5:9, 6:13, 7:21, 8:33, 9:52, 10:84, 11:130},
        50: {1:1.5, 2:2.5, 3:4, 4:7, 5:11, 6:16, 7:25, 8:39, 9:62, 10:100, 11:160},
        80: {1:2, 2:3, 3:5, 4:8, 5:13, 6:19, 7:30, 8:46, 9:74, 10:120, 11:190},
        120: {1:2.5, 2:4, 3:6, 4:10, 5:15, 6:22, 7:35, 8:54, 9:87, 10:140, 11:220},
    }
    
    # Fundamental deviations (µm) - simplified
    # Shaft: h=0, k=+, m=++, n=+++, p=++++, s=+++++, u=++++++
    # Hub: H=0, J=+, K=++, M=+++, N=++++, P=+++++, U=++++++
    
    shaft_dev = {'h':0, 'k':1, 'm':2, 'n':3, 'p':4, 's':5, 'u':6}
    hub_dev = {'H':0, 'J':1, 'K':2, 'M':3, 'N':4, 'P':5, 'U':6}
    
    # Get IT grade
    d_range = 6
    for limit in sorted(IT_table.keys()):
        if d <= limit:
            d_range = limit
            break
    
    # Parse class (e.g., "h7" -> letter='h', grade=7)
    s_letter = shaft_class[0]
    s_grade = int(shaft_class[1:])
    h_letter = hub_class[0]
    h_grade = int(hub_class[1:])
    
    IT_s = IT_table[d_range].get(s_grade, 10)
    IT_h = IT_table[d_range].get(h_grade, 10)
    
    # Simplified fundamental deviation
    s_dev = shaft_dev.get(s_letter, 0) * IT_s * 0.5
    h_dev = hub_dev.get(h_letter, 0) * IT_h * 0.5
    
    return FitTolerance(
        shaft_upper=s_dev,
        shaft_lower=s_dev - IT_s,
        hub_upper=h_dev + IT_h,
        hub_lower=h_dev
    )

def demo():
    print("=" * 60)
    print("PRESS FIT / SHRINK FIT CALCULATOR - DEMO")
    print("=" * 60)
    
    # Case 1: Press fit trục - bánh răng
    print("\n1. PRESS FIT - Shaft Ø50, Gear hub Ø50/Ø100, L=40mm")
    print("   Fit: s6/H7 (interference fit)")
    
    geo = FitGeometry(shaft_dia=50, hub_od=100, hub_id=0, length=40)
    tol = fit_tolerance_ISO(50, "s6", "H7")
    load = FitLoad(torque_nm=200)
    
    calc = PressFitCalculator(
        MaterialGrade.STEEL_42CRMO4,
        MaterialGrade.STEEL_45,
        geo, tol, load, friction=0.15
    )
    r = calc.calculate()
    
    print(f"   Interference: {tol.interference_mean:.1f} µm ({tol.interference_min:.1f}~{tol.interference_max:.1f})")
    print(f"   Interface pressure: {r.pressure_mpa:.1f} MPa ({r.pressure_min:.1f}~{r.pressure_max:.1f})")
    print(f"   Shaft stresses: σr={r.shaft_stress_radial:.1f}, σθ={r.shaft_stress_hoop:.1f}, VM={r.shaft_stress_vm:.1f} MPa")
    print(f"   Hub stresses: σr={r.hub_stress_radial:.1f}, σθ={r.hub_stress_hoop:.1f}, VM={r.hub_stress_vm:.1f} MPa")
    print(f"   Insertion force: {r.insertion_force_kn:.1f} kN")
    print(f"   Extraction force: {r.extraction_force_kn:.1f} kN")
    print(f"   Torque capacity: {r.torque_capacity_nm:.0f} Nm")
    print(f"   Axial capacity: {r.axial_capacity_kn:.1f} kN")
    print(f"   Safety yield: shaft={r.safety_yield_shaft:.2f}, hub={r.safety_yield_hub:.2f}")
    print(f"   Safety fatigue: shaft={r.safety_fatigue_shaft:.2f}, hub={r.safety_fatigue_hub:.2f}")
    
    # Case 2: Shrink fit nhiệt
    print("\n2. SHRINK FIT - Heating hub")
    print(f"   ΔT heating hub: {r.delta_t_heating:.0f} °C")
    print(f"   ΔT cooling shaft: {r.delta_t_cooling:.0f} °C")
    print(f"   Recommended: Heat hub to {20 + r.delta_t_heating:.0f}°C or cool shaft to {20 - r.delta_t_cooling:.0f}°C")
    
    # Case 3: Kiểm tra truyền mômen
    print("\n3. TORQUE TRANSMISSION CHECK")
    print(f"   Applied torque: {load.torque_nm} Nm")
    print(f"   Capacity: {r.torque_capacity_nm:.0f} Nm")
    print(f"   Safety factor: {r.torque_capacity_nm/load.torque_nm:.2f}")
    print(f"   Microslip load: {r.microslip_load/1000:.1f} kN")
    
    # Case 4: So sánh các fit khác nhau
    print("\n4. COMPARISON OF FITS (Ø50)")
    fits = [("h6", "H7", "Clearance"), ("k6", "H7", "Transition"), ("m6", "H7", "Transition"), 
            ("n6", "H7", "Interference"), ("p6", "H7", "Interference"), ("s6", "H7", "Heavy interference")]
    
    for shaft_cls, hub_cls, fit_type in fits:
        tol = fit_tolerance_ISO(50, shaft_cls, hub_cls)
        calc = PressFitCalculator(MaterialGrade.STEEL_42CRMO4, MaterialGrade.STEEL_45,
                                   geo, tol, FitLoad(), 0.15)
        r = calc.calculate()
        print(f"   {fit_class}: δ={tol.interference_mean:.1f}µm, P={r.pressure_mpa:.1f}MPa, "
              f"T_cap={r.torque_capacity_nm:.0f}Nm, F_ins={r.insertion_force_kn:.1f}kN")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    demo()