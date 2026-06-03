"""Shared math and matrix helpers for OrderAnalyzer."""


def flat(matrix):
    """Flatten 2D matrix to 1D list; 用于和 OCTA 元素索引对齐。"""
    return [cell for row in matrix for cell in row]


def clip01(value):
    """Clamp score into [0,1]; 防止数值越界污染聚合分。"""
    return max(0.0, min(1.0, float(value)))


def angle_diff_deg(a, b):
    """Minimal circular angle difference in degrees; 处理 0/360 环绕。"""
    return abs((a - b + 180.0) % 360.0 - 180.0)


def dominant_axis_score(angle_deg):
    """Axis alignment score against 0/90/180/270 directions。"""
    nearest = min(angle_diff_deg(angle_deg, k) for k in (0.0, 90.0, 180.0, 270.0))
    return clip01(1.0 - nearest / 45.0)


def mean(values):
    """Safe mean; empty list returns None 以便上游显式处理缺失分量。"""
    if not values:
        return None
    return sum(values) / len(values)


def variance(values):
    """Population variance for stability metrics; 空输入返回 None。"""
    if not values:
        return None
    m = mean(values)
    return sum((v - m) ** 2 for v in values) / len(values)


def centroid(points):
    """Compute centroid of (x,y) points; 用于 group 间相位与布局比较。"""
    if not points:
        return None
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return (mean(xs), mean(ys))


def spacing_to_xy(row, col, spacing):
    """Map grid index to planar coordinates using configured spacing。"""
    row_spacing, col_spacing = spacing
    return (col * col_spacing, row * row_spacing)
