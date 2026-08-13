#!/usr/bin/env python3
"""
Bolt Pattern Calculator
Tính toán các mẫu ổn định: tròn, vuông, hình chữ nhật, flange
Kiểm tra: lực cắt, lực kéo, moment, tương tác
Theo: VDI 2230, Eurocode 3, AISC 360
"""

import math
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

class PatternType(Enum):
    CIRCULAR = "circular"           # Tròn
    RECTANGULAR = "rectangular"     # Vuông/Chữ nhật
    FLANGE = "flange"               # Flange (tròn + lỗ trung tâm)
    LINEAR = "linear"               # Thẳng hàng

class BoltGrade(Enum):
    # Property class: (fu MPa, fy MPa)
    _4_6 = ("4.6", 400, 240)
    _4_8 = ("4.8", 400, 320)
    _5_6 = ("5.6", 500, 300)
    _5_8 = ("5.8", 500, 400)
    _6_8 = ("6.8", 600, 480)
    _8_8 = ("8.8", 800, 640)
    _10_9 = ("10.9", 1000, 900)
    _12_9 = ("12.9", 1200, 1080)
    A2_70 = ("A2-70", 700, 450)     # Inox
    A4_70 = ("A4-70", 700, 450)
    A4_80 = ("A4-80", 800, 600)

    def __init__(self, name: str, fu: float, fy: float):
        self.grade_name = name
        self.fu = fu
        self.fy = fy

@dataclass
class BoltGeometry:
    diameter: float         # d (mm) - M6, M8, M10, M12, M16, M20, M24, M30
    pitch: float = 0.0      # P (mm) - 0 = chuẩn
    grade: BoltGrade = BoltGrade._8_8
    preload_factor: float = 0.7   # Fp = 0.7 * Fy * As (VDI 2230)
    friction_coeff: float = 0.14  # Mu

@dataclass
class PatternGeometry:
    pattern_type: PatternType
    # Circular
    bolt_count: int = 0
    pcd: float = 0.0            # Pitch Circle Diameter (mm)
    # Rectangular
    rows: int = 0
    cols: int = 0
    spacing_x: float = 0.0
    spacing_y: float = 0.0
    # Flange
    flange_od: float = 0.0
    flange_id: float = 0.0
    # Linear
    length: float = 0.0
    count: int = 0

@dataclass
class AppliedLoad:
    fx: float = 0.0       # Lực trục (N)
    fy: float = 0.0       # Lực dọc (N)
    fz: float = 0.0       # Lực ngang (N)
    mx: float = 0.0       # Momen quanh X (N.mm)
    my: float = 0.0       # Momen quanh Y (N.mm)
    mz: float = 0.0       # Momen quanh Z (N.mm)

@dataclass
class BoltForce:
    bolt_id: int
    x: float
    y: float
    fx: float = 0.0
    fy: float = 0.0
    fz: float = 0.0
    f_resultant: float = 0.0
    utilization: float = 0.0

@dataclass
class PatternResult:
    bolts: List[BoltForce]
    max_force: float
    max_utilization: float
    critical_bolt_id: int
    pattern_centroid: Tuple[float, float]
    total_shear_capacity: float
    total_tension_capacity: float

class BoltPatternCalculator:
    def __init__(self, bolt_geo: BoltGeometry, pattern_geo: PatternGeometry):
        self.bolt = bolt_geo
        self.pattern = pattern_geo
        self.bolts_positions = []
    
    def generate_positions(self) -> List[Tuple[float, float]]:
        """Tạo tọa độ các bu lông"""
        pos = []
        
        if self.pattern.pattern_type == PatternType.CIRCULAR:
            n = self.pattern.bolt_count
            r = self.pattern.pcd / 2
            for i in range(n):
                angle = 2 * math.pi * i / n
                x = r * math.cos(angle)
                y = r * math.sin(angle)
                pos.append((x, y))
        
        elif self.pattern.pattern_type == PatternType.RECTANGULAR:
            rows = self.pattern.rows
            cols = self.pattern.cols
            sx = self.pattern.spacing_x
            sy = self.pattern.spacing_y
            for i in range(rows):
                for j in range(cols):
                    x = (j - (cols-1)/2) * sx
                    y = (i - (rows-1)/2) * sy
                    pos.append((x, y))
        
        elif self.pattern.pattern_type == PatternType.FLANGE:
            # Flange: bolts on PCD
            n = self.pattern.bolt_count
            r = self.pattern.pcd / 2
            for i in range(n):
                angle = 2 * math.pi * i / n
                x = r * math.cos(angle)
                y = r * math.sin(angle)
                pos.append((x, y))
        
        elif self.pattern.pattern_type == PatternType.LINEAR:
            n = self.pattern.count
            L = self.pattern.length
            for i in range(n):
                x = (i - (n-1)/2) * L / (n-1) if n > 1 else 0
                y = 0
                pos.append((x, y))
        
        self.bolts_positions = pos
        return pos
    
    def calculate_centroid(self) -> Tuple[float, float]:
        """Tâm trọng của pattern"""
        if not self.bolts_positions:
            self.generate_positions()
        n = len(self.bolts_positions)
        cx = sum(p[0] for p in self.bolts_positions) / n
        cy = sum(p[1] for p in self.bolts_positions) / n
        return (cx, cy)
    
    def bolt_area_properties(self) -> Dict:
        """Tính diện tích bu lông"""
        d = self.bolt.diameter
        # Diện tích khuynh đảo (tensile stress area) - ISO 898
        # As = pi/4 * (d - 0.9382*P)^2
        if self.bolt.pitch > 0:
            P = self.bolt.pitch
        else:
            # Standard pitch
            std_pitch = {6:1, 8:1.25, 10:1.5, 12:1.75, 14:2, 16:2, 18:2.5, 20:2.5, 22:2.5, 24:3, 27:3, 30:3.5}
            P = std_pitch.get(int(d), 1.5)
        
        As = math.pi / 4 * (d - 0.9382 * P)**2
        At = math.pi / 4 * d**2  # Tensile area (nominal)
        return {"As": As, "At": At, "pitch": P}
    
    def bolt_capacities(self) -> Dict:
        """Sức chịu bu lông đơn"""
        props = self.bolt_area_properties()
        As = props["As"]
        fu = self.bolt.grade.fu
        fy = self.bolt.grade.fy
        
        # Shear capacity (VDI 2230 / Eurocode 3)
        # V_Rd = 0.6 * fu * As / gamma_M2
        gamma_M2 = 1.25
        V_rd = 0.6 * fu * As / gamma_M2
        
        # Tension capacity
        # F_t,Rd = 0.9 * fu * As / gamma_M2 (for 8.8, 10.9)
        if self.bolt.grade.grade_name in ["8.8", "10.9", "12.9"]:
            F_t_rd = 0.9 * fu * As / gamma_M2
        else:
            F_t_rd = fu * As / gamma_M2
        
        # Preload
        Fp = self.bolt.preload_factor * fy * As
        
        # Slip resistance (category B)
        mu = self.bolt.friction_coeff
        ks = 1.0  # Slip factor
        Fs = ks * mu * Fp
        
        return {
            "As": As,
            "V_rd": V_rd,
            "F_t_rd": F_t_rd,
            "Fp": Fp,
            "Fs": Fs,
            "fy": fy,
            "fu": fu
        }
    
    def analyze(self, load: AppliedLoad) -> PatternResult:
        """Phân tích pattern dưới tải trọng"""
        if not self.bolts_positions:
            self.generate_positions()
        
        n = len(self.bolts_positions)
        cap = self.bolt_capacities()
        
        # Tâm trọng
        cx, cy = self.calculate_centroid()
        
        # Tọa độ tương đối tâm
        rel_pos = [(x - cx, y - cy) for x, y in self.bolts_positions]
        
        # Khoảng cách bình phương
        r2 = [x**2 + y**2 for x, y in rel_pos]
        sum_r2 = sum(r2)
        
        # Tính lực trên mỗi bu lông (elastic method)
        bolt_forces = []
        
        for i, (rx, ry) in enumerate(rel_pos):
            # Lực do Fx (trục) - chia đều
            fx_axial = load.fx / n if n > 0 else 0
            
            # Lực do Fy, Fz (cắt) - chia đều
            fy_shear = load.fy / n if n > 0 else 0
            fz_shear = load.fz / n if n > 0 else 0
            
            # Lực do Mx (momen quanh X) -> căng/dập
            fx_moment = load.mx * ry / sum_r2 if sum_r2 > 0 else 0
            
            # Lực do My (momen quanh Y) -> căng/dập
            fx_my = -load.my * rx / sum_r2 if sum_r2 > 0 else 0
            
            # Lực do Mz (momen quanh Z) -> cắt
            fy_mz = -load.mz * rx / sum_r2 if sum_r2 > 0 else 0
            fz_mz = load.mz * ry / sum_r2 if sum_r2 > 0 else 0
            
            # Tổng lực
            fx_total = fx_axial + fx_moment + fx_my
            fy_total = fy_shear + fy_mz
            fz_total = fz_shear + fz_mz
            
            f_resultant = math.sqrt(fx_total**2 + fy_total**2 + fz_total**2)
            
            # Utilization
            util_tension = abs(fx_total) / cap["F_t_rd"] if fx_total > 0 else 0
            util_shear = math.sqrt(fy_total**2 + fz_total**2) / cap["V_rd"]
            
            # Interaction (Eurocode 3)
            if util_tension > 0:
                util = util_tension + util_shear / (1 - util_tension) if util_tension < 1 else 999
            else:
                util = util_shear
            
            bolt_forces.append(BoltForce(
                bolt_id=i+1,
                x=self.bolts_positions[i][0],
                y=self.bolts_positions[i][1],
                fx=fx_total,
                fy=fy_total,
                fz=fz_total,
                f_resultant=f_resultant,
                utilization=util
            ))
        
        # Tìm bu lông critical
        critical = max(bolt_forces, key=lambda b: b.utilization)
        
        return PatternResult(
            bolts=bolt_forces,
            max_force=critical.f_resultant,
            max_utilization=critical.utilization,
            critical_bolt_id=critical.bolt_id,
            pattern_centroid=(cx, cy),
            total_shear_capacity=cap["V_rd"] * n,
            total_tension_capacity=cap["F_t_rd"] * n
        )

def design_bolt_pattern(load: AppliedLoad, 
                        pattern_type: PatternType = PatternType.CIRCULAR,
                        bolt_grade: BoltGrade = BoltGrade._8_8,
                        safety_factor: float = 1.5) -> Dict:
    """Thiết kế sơ bộ pattern bu lông"""
    
    # Ước lượng số bu lông cần
    F_total = math.sqrt(load.fx**2 + load.fy**2 + load.fz**2)
    M_total = math.sqrt(load.mx**2 + load.my**2 + load.mz**2)
    
    # Chọn bu lông
    std_diameters = [6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 27, 30]
    
    best_design = None
    
    for d in std_diameters:
        bolt = BoltGeometry(diameter=d, grade=bolt_grade)
        
        # Thử các cấu hình
        if pattern_type == PatternType.CIRCULAR:
            for n in range(4, 13, 2):
                for pcd in range(max(50, d*4), 500, 25):
                    pattern = PatternGeometry(
                        pattern_type=PatternType.CIRCULAR,
                        bolt_count=n,
                        pcd=pcd
                    )
                    calc = BoltPatternCalculator(bolt, pattern)
                    result = calc.analyze(load)
                    
                    if result.max_utilization <= 1.0 / safety_factor:
                        if best_design is None or pcd < best_design["pcd"]:
                            best_design = {
                                "diameter": d,
                                "bolt_count": n,
                                "pcd": pcd,
                                "grade": bolt_grade.grade_name,
                                "result": result
                            }
        
        elif pattern_type == PatternType.RECTANGULAR:
            for rows in [2, 3, 4]:
                for cols in [2, 3, 4, 5]:
                    for sx in [40, 50, 60, 80, 100]:
                        for sy in [40, 50, 60, 80, 100]:
                            pattern = PatternGeometry(
                                pattern_type=PatternType.RECTANGULAR,
                                rows=rows,
                                cols=cols,
                                spacing_x=sx,
                                spacing_y=sy
                            )
                            calc = BoltPatternCalculator(bolt, pattern)
                            result = calc.analyze(load)
                            
                            if result.max_utilization <= 1.0 / safety_factor:
                                area = (cols-1)*sx * (rows-1)*sy
                                if best_design is None or area < best_design.get("area", 999999):
                                    best_design = {
                                        "diameter": d,
                                        "rows": rows,
                                        "cols": cols,
                                        "spacing_x": sx,
                                        "spacing_y": sy,
                                        "grade": bolt_grade.grade_name,
                                        "area": area,
                                        "result": result
                                    }
    
    return best_design

def demo():
    print("=" * 60)
    print("BOLT PATTERN CALCULATOR - DEMO")
    print("=" * 60)
    
    # Case 1: Flange nối trục - Circular pattern
    print("\n1. FLANGE CIRCULAR - 8x M12, PCD=150mm")
    bolt = BoltGeometry(diameter=12, grade=BoltGrade._8_8)
    pattern = PatternGeometry(pattern_type=PatternType.CIRCULAR, bolt_count=8, pcd=150)
    calc = BoltPatternCalculator(bolt, pattern)
    
    load = AppliedLoad(fx=50000, fy=20000, fz=10000, mx=5000000, my=3000000, mz=2000000)
    result = calc.analyze(load)
    
    print(f"   Bolts: {len(result.bolts)}")
    print(f"   Centroid: ({result.pattern_centroid[0]:.1f}, {result.pattern_centroid[1]:.1f})")
    print(f"   Max force: {result.max_force:.0f} N (Bolt {result.critical_bolt_id})")
    print(f"   Max utilization: {result.max_utilization:.2%}")
    print(f"   Total shear cap: {result.total_shear_capacity:.0f} N")
    print(f"   Total tension cap: {result.total_tension_capacity:.0f} N")
    
    # In chi tiết các bu lông
    for b in result.bolts:
        print(f"   Bolt {b.bolt_id}: ({b.x:6.1f}, {b.y:6.1f}) Fx={b.fx:8.0f} Fy={b.fy:8.0f} Fz={b.fz:8.0f} U={b.utilization:.2%}")
    
    # Case 2: Kết nối dầm - Rectangular pattern
    print("\n2. BEAM CONNECTION - Rectangular 4x4, M16, spacing 80x80")
    bolt = BoltGeometry(diameter=16, grade=BoltGrade._10_9)
    pattern = PatternGeometry(pattern_type=PatternType.RECTANGULAR, rows=4, cols=4, spacing_x=80, spacing_y=80)
    calc = BoltPatternCalculator(bolt, pattern)
    
    load = AppliedLoad(fx=80000, fy=40000, mz=10000000)
    result = calc.analyze(load)
    
    print(f"   Bolts: {len(result.bolts)}")
    print(f"   Max utilization: {result.max_utilization:.2%} (Bolt {result.critical_bolt_id})")
    print(f"   Critical bolt force: {result.max_force:.0f} N")
    
    # Case 3: Thiết kế tự động
    print("\n3. AUTO DESIGN - Circular, Fx=30kN, My=2kNm, SF=2.0")
    load = AppliedLoad(fx=30000, my=2000000)
    design = design_bolt_pattern(load, PatternType.CIRCULAR, BoltGrade._8_8, 2.0)
    
    if design:
        print(f"   Diameter: M{design['diameter']}")
        print(f"   Count: {design['bolt_count']}")
        print(f"   PCD: {design['pcd']} mm")
        print(f"   Grade: {design['grade']}")
        print(f"   Max utilization: {design['result'].max_utilization:.2%}")
    else:
        print("   No suitable design found")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    demo()