#!/usr/bin/env python3
"""
Beam Deflection Calculator
Tính độ lệch, ứng suất, phản lực cho các loại dầm cơ bản
"""

import math
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

class BeamType(Enum):
    SIMPLY_SUPPORTED = "simply_supported"      # Dầm đơn
    CANTILEVER = "cantilever"                  # Dầm console
    FIXED_FIXED = "fixed_fixed"                # Dầm cố định 2 đầu
    FIXED_PINNED = "fixed_pinned"              # Dầm cố định - gọn
    CONTINUOUS_2_SPAN = "continuous_2_span"    # Dầm liên tục 2 nhịp

class LoadType(Enum):
    POINT_LOAD_CENTER = "point_center"         # Tải trọng tập trung giữa camp
    POINT_LOAD_ANY = "point_any"               # Tải trọng tập trung vị trí bất kỳ
    UDL = "udl"                                # Tải trọng phân bố đều
    TRIANGULAR = "triangular"                  # Tải trọng tam giác
    MOMENT = "moment"                          # Momen tác dụng

@dataclass
class BeamProperties:
    length: float          # L (mm)
    E: float               # Module Young (MPa = N/mm2)
    I: float               # Moment quán tiết diện (mm4)
    A: float = 0           # Diện tích tiết diện (mm2) - cho ứng suất trục
    type: BeamType = BeamType.SIMPLY_SUPPORTED  # Loại dầm

@dataclass
class LoadCase:
    load_type: LoadType
    magnitude: float       # P (N) hoặc w (N/mm) hoặc M (N.mm)
    position: float = 0    # Vị trí từ đầu trái (mm) - cho point load any
    a: float = 0           # Tham số bổ sung (cho tam giác, etc.)

@dataclass
class BeamResult:
    max_deflection: float      # Độ lệch tối đa (mm)
    max_stress: float          # Ứng suất tối đa (MPa)
    reactions: Dict[str, float] # Phản lực tại các điểm op
    deflection_eq: str         # Công thức độ lệch
    stress_eq: str             # Công thức ứng suất

class BeamCalculator:
    def __init__(self, beam: BeamProperties):
        self.beam = beam
    
    def calculate(self, loads: List[LoadCase]) -> BeamResult:
        """Tính toán cho nhiều trường hợp tải trọng (siêu vị)"""
        total_deflection = 0
        total_stress = 0
        total_reactions = {}
        
        for load in loads:
            result = self._single_load(load)
            total_deflection += result.max_deflection
            total_stress = max(total_stress, result.max_stress)
            for k, v in result.reactions.items():
                total_reactions[k] = total_reactions.get(k, 0) + v
        
        return BeamResult(
            max_deflection=total_deflection,
            max_stress=total_stress,
            reactions=total_reactions,
            deflection_eq="Superposition of individual load cases",
            stress_eq="Max of individual load cases"
        )
    
    def _single_load(self, load: LoadCase) -> BeamResult:
        L = self.beam.length
        E = self.beam.E
        I = self.beam.I
        P = load.magnitude
        a = load.position
        b = L - a if a > 0 else 0
        
        bt = self.beam  # alias
        
        if bt.type == BeamType.SIMPLY_SUPPORTED:
            return self._simply_supported(load, L, E, I, a, b)
        elif bt.type == BeamType.CANTILEVER:
            return self._cantilever(load, L, E, I, a)
        elif bt.type == BeamType.FIXED_FIXED:
            return self._fixed_fixed(load, L, E, I, a, b)
        elif bt.type == BeamType.FIXED_PINNED:
            return self._fixed_pinned(load, L, E, I, a, b)
        else:
            raise ValueError(f"Beam type {bt.type} not implemented yet")
    
    def _simply_supported(self, load: LoadCase, L, E, I, a, b) -> BeamResult:
        P = load.magnitude
        
        if load.load_type == LoadType.POINT_LOAD_CENTER:
            # Tải trọng giữa camp
            delta_max = P * L**3 / (48 * E * I)
            M_max = P * L / 4
            c = self.beam.A / 2 if self.beam.A else 0  # Khoách trục trung hòa approx
            stress_max = M_max * c / I if c else 0
            reactions = {"R_A": P/2, "R_B": P/2}
            return BeamResult(delta_max, stress_max, reactions,
                            "PL^3/48EI", "PL/4 * c/I")
        
        elif load.load_type == LoadType.POINT_LOAD_ANY:
            # Tải trọng vị trí bất kỳ
            delta_max = P * a**2 * b**2 / (3 * E * I * L)  # Tại vị trí tải
            M_max = P * a * b / L
            reactions = {"R_A": P * b / L, "R_B": P * a / L}
            return BeamResult(delta_max, 0, reactions,
                            "Pa^2b^2/3EIL", "Pab/L * c/I")
        
        elif load.load_type == LoadType.UDL:
            w = load.magnitude  # N/mm
            delta_max = 5 * w * L**4 / (384 * E * I)
            M_max = w * L**2 / 8
            reactions = {"R_A": w * L / 2, "R_B": w * L / 2}
            return BeamResult(delta_max, 0, reactions,
                            "5wL^4/384EI", "wL^2/8 * c/I")
        
        elif load.load_type == LoadType.TRIANGULAR:
            w0 = load.magnitude  # N/mm tại đỉnh
            delta_max = w0 * L**4 / (120 * E * I)  # Tải tăng dần từ 0
            M_max = w0 * L**2 / 30 * math.sqrt(3)
            reactions = {"R_A": w0 * L / 3, "R_B": w0 * L / 6}
            return BeamResult(delta_max, 0, reactions,
                            "w0L^4/120EI", "w0L^2/30*sqrt(3) * c/I")
        
        return BeamResult(0, 0, {}, "", "")
    
    def _cantilever(self, load: LoadCase, L, E, I, a) -> BeamResult:
        P = load.magnitude
        
        if load.load_type == LoadType.POINT_LOAD_CENTER:
            # Tải trọng tại đầu tự do
            delta_max = P * L**3 / (3 * E * I)
            M_max = P * L
            reactions = {"R_fixed": P, "M_fixed": P * L}
            return BeamResult(delta_max, 0, reactions,
                            "PL^3/3EI", "PL * c/I")
        
        elif load.load_type == LoadType.UDL:
            w = load.magnitude
            delta_max = w * L**4 / (8 * E * I)
            M_max = w * L**2 / 2
            reactions = {"R_fixed": w * L, "M_fixed": w * L**2 / 2}
            return BeamResult(delta_max, 0, reactions,
                            "wL^4/8EI", "wL^2/2 * c/I")
        
        return BeamResult(0, 0, {}, "", "")
    
    def _fixed_fixed(self, load: LoadCase, L, E, I, a, b) -> BeamResult:
        P = load.magnitude
        
        if load.load_type == LoadType.POINT_LOAD_CENTER:
            delta_max = P * L**3 / (192 * E * I)
            M_max = P * L / 8
            reactions = {"R_A": P/2, "R_B": P/2, "M_A": P*L/8, "M_B": P*L/8}
            return BeamResult(delta_max, 0, reactions,
                            "PL^3/192EI", "PL/8 * c/I")
        
        elif load.load_type == LoadType.UDL:
            w = load.magnitude
            delta_max = w * L**4 / (384 * E * I)
            M_max = w * L**2 / 12
            reactions = {"R_A": w*L/2, "R_B": w*L/2, "M_A": w*L**2/12, "M_B": w*L**2/12}
            return BeamResult(delta_max, 0, reactions,
                            "wL^4/384EI", "wL^2/12 * c/I")
        
        return BeamResult(0, 0, {}, "", "")
    
    def _fixed_pinned(self, load: LoadCase, L, E, I, a, b) -> BeamResult:
        P = load.magnitude
        
        if load.load_type == LoadType.POINT_LOAD_CENTER:
            delta_max = P * L**3 / (108 * E * I)  # Approximate
            M_max = P * L / 8
            reactions = {"R_A": 3*P/8, "R_B": 5*P/8, "M_A": P*L/8}
            return BeamResult(delta_max, 0, reactions,
                            "PL^3/108EI (approx)", "PL/8 * c/I")
        
        elif load.load_type == LoadType.UDL:
            w = load.magnitude
            delta_max = w * L**4 / (185 * E * I)  # Approximate
            M_max = w * L**2 / 8
            reactions = {"R_A": 3*w*L/8, "R_B": 5*w*L/8, "M_A": w*L**2/8}
            return BeamResult(delta_max, 0, reactions,
                            "wL^4/185EI (approx)", "wL^2/8 * c/I")
        
        return BeamResult(0, 0, {}, "", "")

def calculate_beam_section(b: float, h: float) -> Dict:
    """Tính I, A cho tiết diện chữ nhật"""
    I = b * h**3 / 12
    A = b * h
    c = h / 2
    return {"I": I, "A": A, "c": c}

def demo():
    print("=" * 60)
    print("BEAM DEFLECTION CALCULATOR - DEMO")
    print("=" * 60)
    
    # Dầm thép: L=6000mm, E=200000 MPa, tiết diện 200x400
    section = calculate_beam_section(200, 400)
    beam = BeamProperties(
        length=6000,
        E=200000,
        I=section["I"],
        A=section["A"],
        type=BeamType.SIMPLY_SUPPORTED
    )
    
    calc = BeamCalculator(beam)
    
    # Case 1: Tải trọng giữa camp 10kN
    loads = [LoadCase(LoadType.POINT_LOAD_CENTER, 10000)]
    result = calc.calculate(loads)
    print(f"\n1. Dầm đơn, tải giữa 10kN:")
    print(f"   Delta_max = {result.max_deflection:.2f} mm")
    print(f"   Reactions = {result.reactions}")
    
    # Case 2: Tải phân bố đều 5 N/mm
    loads = [LoadCase(LoadType.UDL, 5)]
    result = calc.calculate(loads)
    print(f"\n2. Dầm đơn, UDL 5 N/mm:")
    print(f"   Delta_max = {result.max_deflection:.2f} mm")
    print(f"   Reactions = {result.reactions}")
    
    # Case 3: Kết hợp (siêu vị)
    loads = [
        LoadCase(LoadType.POINT_LOAD_CENTER, 10000),
        LoadCase(LoadType.UDL, 5)
    ]
    result = calc.calculate(loads)
    print(f"\n3. Kết hợp Point + UDL:")
    print(f"   Delta_max = {result.max_deflection:.2f} mm")
    print(f"   Reactions = {result.reactions}")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    demo()