#!/usr/bin/env python3
"""
Tolerance Stack-up Calculator
Phân tích chuỗi công差: Worst-case, RSS, Monte Carlo
Theo: ASME Y14.5, ISO 1101, ISO 286
"""

import math
import random
import statistics
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from collections import namedtuple

class DistributionType(Enum):
    NORMAL = "normal"           # Phân bố chuẩn
    UNIFORM = "uniform"         # Phân bố đều
    TRIANGULAR = "triangular"   # Phân bố tam giác
    BETA = "beta"               # Phân bố Beta (cho QC)

class SensitivityType(Enum):
    LINEAR = "linear"           # Tuyến tính
    ROOT_SUM_SQUARE = "rss"     # Căn bổng bình phương
    WORST_CASE = "worst_case"   # Tối thiểu/tối đa

@dataclass
class Dimension:
    name: str
    nominal: float              # Kích thước định danh (mm)
    tolerance: float            # ± tolerance (mm) hoặc (upper, lower)
    distribution: DistributionType = DistributionType.NORMAL
    upper: float = 0.0          # Upper limit (nếu asymmetric)
    lower: float = 0.0          # Lower limit
    cpk: float = 1.33           # Process capability
    shift: float = 0.0          # Mean shift (mm)
    correlation: float = 0.0    # Correlation with previous (-1 to 1)

@dataclass
class StackResult:
    nominal: float
    # Worst case
    wc_min: float
    wc_max: float
    wc_range: float
    # RSS (Root Sum Square)
    rss_sigma: float
    rss_3sigma_min: float
    rss_3sigma_max: float
    rss_6sigma_min: float
    rss_6sigma_max: float
    # Monte Carlo
    mc_mean: float
    mc_std: float
    mc_min: float
    mc_max: float
    mc_3sigma_min: float
    mc_3sigma_max: float
    mc_percentiles: Dict[str, float]
    # Yield
    yield_3sigma: float
    yield_6sigma: float
    dpm_3sigma: float
    dpm_6sigma: float

@dataclass
class SensitivityResult:
    dimension: str
    contribution_wc: float      # % contribution to worst case
    contribution_rss: float     # % contribution to RSS variance
    sensitivity: float          # dY/dXi

class ToleranceStackCalculator:
    def __init__(self):
        self.dimensions = []
        self.target_nominal = 0.0
        self.target_upper = 0.0
        self.target_lower = 0.0
    
    def add_dimension(self, dim: Dimension):
        self.dimensions.append(dim)
    
    def set_target(self, nominal: float, upper: float, lower: float):
        self.target_nominal = nominal
        self.target_upper = upper
        self.target_lower = lower
    
    def worst_case(self) -> Tuple[float, float]:
        """Worst-case stack: sum of all tolerances"""
        total_nominal = sum(d.nominal for d in self.dimensions)
        total_tol = sum(d.tolerance for d in self.dimensions)
        return total_nominal - total_tol, total_nominal + total_tol
    
    def rss_analysis(self) -> Dict:
        """RSS (Root Sum Square) - assume normal distribution"""
        total_nominal = sum(d.nominal for d in self.dimensions)
        
        # RSS: sigma_total = sqrt(sum(sigma_i^2))
        # tolerance = 3*sigma (for 3-sigma quality)
        sigma_total = math.sqrt(sum((d.tolerance / 3)**2 for d in self.dimensions))
        
        return {
            "nominal": total_nominal,
            "sigma": sigma_total,
            "3sigma_min": total_nominal - 3 * sigma_total,
            "3sigma_max": total_nominal + 3 * sigma_total,
            "6sigma_min": total_nominal - 6 * sigma_total,
            "6sigma_max": total_nominal + 6 * sigma_total,
        }
    
    def monte_carlo(self, n_samples: int = 100000) -> Dict:
        """Monte Carlo simulation"""
        results = []
        
        for _ in range(n_samples):
            total = 0.0
            for d in self.dimensions:
                if d.distribution == DistributionType.NORMAL:
                    # sigma = tolerance / 3 (for 3-sigma spec)
                    sigma = d.tolerance / 3
                    val = random.normalvariate(d.nominal + d.shift, sigma)
                elif d.distribution == DistributionType.UNIFORM:
                    # Uniform: tolerance = half-width
                    val = random.uniform(d.nominal - d.tolerance, d.nominal + d.tolerance)
                elif d.distribution == DistributionType.TRIANGULAR:
                    # Triangular: mode at nominal
                    val = random.triangular(d.nominal - d.tolerance, d.nominal + d.tolerance, d.nominal)
                else:
                    val = d.nominal
                total += val
            results.append(total)
        
        mean = statistics.mean(results)
        std = statistics.stdev(results) if len(results) > 1 else 0
        
        percentiles = {
            "0.1%": statistics.quantiles(results, n=1000)[0],
            "1%": statistics.quantiles(results, n=100)[0],
            "5%": statistics.quantiles(results, n=20)[0],
            "50%": statistics.median(results),
            "95%": statistics.quantiles(results, n=20)[18],
            "99%": statistics.quantiles(results, n=100)[98],
            "99.9%": statistics.quantiles(results, n=1000)[998],
        }
        
        return {
            "mean": mean,
            "std": std,
            "min": min(results),
            "max": max(results),
            "3sigma_min": mean - 3 * std,
            "3sigma_max": mean + 3 * std,
            "percentiles": percentiles,
        }
    
    def sensitivity_analysis(self) -> List[SensitivityResult]:
        """Phân tích độ nhạy: contribution của từng dimension"""
        # Worst case contribution
        wc_total = sum(d.tolerance for d in self.dimensions)
        
        # RSS variance contribution
        rss_var_total = sum((d.tolerance / 3)**2 for d in self.dimensions)
        
        sensitivities = []
        for d in self.dimensions:
            wc_contrib = (d.tolerance / wc_total * 100) if wc_total > 0 else 0
            rss_contrib = ((d.tolerance / 3)**2 / rss_var_total * 100) if rss_var_total > 0 else 0
            # Sensitivity = dY/dXi = 1 cho linear stack
            sensitivities.append(SensitivityResult(
                dimension=d.name,
                contribution_wc=wc_contrib,
                contribution_rss=rss_contrib,
                sensitivity=1.0
            ))
        
        return sorted(sensitivities, key=lambda x: x.contribution_wc, reverse=True)
    
    def yield_analysis(self, mc_results: Dict) -> Dict:
        """Tính yield & DPM"""
        if self.target_upper == 0 and self.target_lower == 0:
            return {"yield_3sigma": 0, "yield_6sigma": 0, "dpm_3sigma": 0, "dpm_6sigma": 0}
        
        mean = mc_results["mean"]
        std = mc_results["std"]
        
        if std == 0:
            return {"yield_3sigma": 100, "yield_6sigma": 100, "dpm_3sigma": 0, "dpm_6sigma": 0}
        
        # Z-scores
        z_upper_3s = (self.target_upper - mean) / std
        z_lower_3s = (mean - self.target_lower) / std
        z_upper_6s = (self.target_upper - mean) / std * 2  # 6-sigma limit
        z_lower_6s = (mean - self.target_lower) / std * 2
        
        # Standard normal CDF
        def phi(z):
            return 0.5 * (1 + math.erf(z / math.sqrt(2)))
        
        yield_3s = (phi(z_upper_3s) - (1 - phi(z_lower_3s))) * 100
        yield_6s = (phi(z_upper_6s) - (1 - phi(z_lower_6s))) * 100
        
        dpm_3s = (1 - yield_3s / 100) * 1_000_000
        dpm_6s = (1 - yield_6s / 100) * 1_000_000
        
        return {
            "yield_3sigma": max(0, min(100, yield_3s)),
            "yield_6sigma": max(0, min(100, yield_6s)),
            "dpm_3sigma": max(0, dpm_3s),
            "dpm_6sigma": max(0, dpm_6s),
        }
    
    def full_analysis(self, mc_samples: int = 100000) -> StackResult:
        """Phân tích đầy đủ"""
        wc_min, wc_max = self.worst_case()
        rss = self.rss_analysis()
        mc = self.monte_carlo(mc_samples)
        sens = self.sensitivity_analysis()
        yield_anal = self.yield_analysis(mc)
        
        return StackResult(
            nominal=sum(d.nominal for d in self.dimensions),
            wc_min=wc_min,
            wc_max=wc_max,
            wc_range=wc_max - wc_min,
            rss_sigma=rss["sigma"],
            rss_3sigma_min=rss["3sigma_min"],
            rss_3sigma_max=rss["3sigma_max"],
            rss_6sigma_min=rss["6sigma_min"],
            rss_6sigma_max=rss["6sigma_max"],
            mc_mean=mc["mean"],
            mc_std=mc["std"],
            mc_min=mc["min"],
            mc_max=mc["max"],
            mc_3sigma_min=mc["3sigma_min"],
            mc_3sigma_max=mc["3sigma_max"],
            mc_percentiles=mc["percentiles"],
            yield_3sigma=yield_anal["yield_3sigma"],
            yield_6sigma=yield_anal["yield_6sigma"],
            dpm_3sigma=yield_anal["dpm_3sigma"],
            dpm_6sigma=yield_anal["dpm_6sigma"],
        )

def fit_tolerance(distribution: str, samples: List[float]) -> Dict:
    """Fit tolerance distribution from measurement data"""
    mean = statistics.mean(samples)
    std = statistics.stdev(samples) if len(samples) > 1 else 0
    
    if distribution == "normal":
        # 99.73% within ±3σ
        tol_3sigma = 3 * std
        tol_6sigma = 6 * std
    elif distribution == "uniform":
        # min, max
        tol_3sigma = (max(samples) - min(samples)) / 2
        tol_6sigma = tol_3sigma
    else:
        tol_3sigma = 3 * std
        tol_6sigma = 6 * std
    
    # Process capability
    # Cpk = min((USL-mean)/(3σ), (mean-LSL)/(3σ))
    
    return {
        "mean": mean,
        "std": std,
        "tolerance_3sigma": tol_3sigma,
        "tolerance_6sigma": tol_6sigma,
        "min": min(samples),
        "max": max(samples),
        "range": max(samples) - min(samples),
    }

def demo():
    print("=" * 60)
    print("TOLERANCE STACK-UP CALCULATOR - DEMO")
    print("=" * 60)
    
    # Case 1: Đơn giản - 4 bộ phận lắp ráp
    print("\n1. ASSEMBLY STACK - 4 parts")
    calc = ToleranceStackCalculator()
    
    # Base: 100 ± 0.05
    calc.add_dimension(Dimension("Base", 100.0, 0.05))
    # Block A: 25 ± 0.03
    calc.add_dimension(Dimension("Block_A", 25.0, 0.03))
    # Block B: 30 ± 0.04
    calc.add_dimension(Dimension("Block_B", 30.0, 0.04))
    # Cover: 15 ± 0.02
    calc.add_dimension(Dimension("Cover", 15.0, 0.02))
    
    # Target: gap = 170 ± 0.2
    calc.set_target(170.0, 170.2, 169.8)
    
    result = calc.full_analysis()
    
    print(f"   Nominal stack: {result.nominal:.3f} mm")
    print(f"\n   WORST CASE:")
    print(f"   Range: {result.wc_min:.3f} to {result.wc_max:.3f} (span: {result.wc_range:.3f})")
    
    print(f"\n   RSS (3-sigma):")
    print(f"   Sigma: {result.rss_sigma:.4f} mm")
    print(f"   3σ range: {result.rss_3sigma_min:.3f} to {result.rss_3sigma_max:.3f}")
    print(f"   6σ range: {result.rss_6sigma_min:.3f} to {result.rss_6sigma_max:.3f}")
    
    print(f"\n   MONTE CARLO (100k samples):")
    print(f"   Mean: {result.mc_mean:.3f}, Std: {result.mc_std:.4f}")
    print(f"   3σ range: {result.mc_3sigma_min:.3f} to {result.mc_3sigma_max:.3f}")
    print(f"   Percentiles: P0.1={result.mc_percentiles['0.1%']:.3f}, P99.9={result.mc_percentiles['99.9%']:.3f}")
    
    print(f"\n   YIELD ANALYSIS:")
    print(f"   3-sigma yield: {result.yield_3sigma:.2f}% (DPM: {result.dpm_3sigma:.0f})")
    print(f"   6-sigma yield: {result.yield_6sigma:.2f}% (DPM: {result.dpm_6sigma:.0f})")
    
    # Sensitivity
    print(f"\n   SENSITIVITY:")
    for s in calc.sensitivity_analysis():
        print(f"   {s.dimension}: WC={s.contribution_wc:.1f}%, RSS={s.contribution_rss:.1f}%")
    
    # Case 2: Asymmetric tolerances
    print("\n2. ASYMMETRIC TOLERANCES - Shaft/Hole fit")
    calc2 = ToleranceStackCalculator()
    
    # Hole: Ø50 H7 (+0.025/+0)
    calc2.add_dimension(Dimension("Hole", 50.0, 0.0125, upper=0.025, lower=0.0))
    # Shaft: Ø50 g6 (-0.004/-0.012)
    calc2.add_dimension(Dimension("Shaft", 50.0, 0.004, upper=-0.004, lower=-0.012))
    
    result2 = calc2.full_analysis()
    print(f"   Clearance nominal: {result2.nominal:.3f} mm")
    print(f"   Worst case clearance: {result2.wc_min:.4f} to {result2.wc_max:.4f} mm")
    print(f"   RSS 3σ clearance: {result2.rss_3sigma_min:.4f} to {result2.rss_3sigma_max:.4f} mm")
    
    # Case 3: Fit from measurement data
    print("\n3. FIT FROM MEASUREMENT DATA")
    # Giả lập dữ liệu đo 50 mẫu
    hole_samples = [50.012 + random.normalvariate(0, 0.004) for _ in range(100)]
    shaft_samples = [49.992 + random.normalvariate(0, 0.002) for _ in range(100)]
    
    hole_fit = fit_tolerance("normal", hole_samples)
    shaft_fit = fit_tolerance("normal", shaft_samples)
    
    print(f"   Hole: mean={hole_fit['mean']:.4f}, std={hole_fit['std']:.4f}, tol_3σ={hole_fit['tolerance_3sigma']:.4f}")
    print(f"   Shaft: mean={shaft_fit['mean']:.4f}, std={shaft_fit['std']:.4f}, tol_3σ={shaft_fit['tolerance_3sigma']:.4f}")
    
    # Tính clearance từ fit
    clearance_mean = hole_fit['mean'] - shaft_fit['mean']
    clearance_std = math.sqrt(hole_fit['std']**2 + shaft_fit['std']**2)
    print(f"   Clearance: mean={clearance_mean:.4f}, std={clearance_std:.4f}")
    print(f"   3σ clearance: {clearance_mean - 3*clearance_std:.4f} to {clearance_mean + 3*clearance_std:.4f}")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    demo()