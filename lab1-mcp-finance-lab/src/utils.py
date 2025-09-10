import math

def is_finite(x: float) -> bool:
    return isinstance(x, (int, float)) and math.isfinite(x)

def round2(x: float) -> float:
    return float(f"{x:.2f}")
