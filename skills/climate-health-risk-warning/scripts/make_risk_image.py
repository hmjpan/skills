#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""make_risk_image.py - 生成静态风险分布图 (Word 报告嵌入用, 白底)"""
import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import Polygon as MplPolygon
import numpy as np

_CN_FONT = None
for _name in ("SimHei", "Microsoft YaHei", "SimSun", "Noto Sans CJK SC"):
    if any(f.name == _name for f in font_manager.fontManager.ttflist):
        _CN_FONT = _name
        break
plt.rcParams["font.sans-serif"] = [_CN_FONT] if _CN_FONT else ["DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

RISK_COLORS = {
    "极低风险": "#1a9850", "低风险": "#66bd63", "中风险": "#ffd700",
    "高风险": "#ff8c00", "极高风险": "#d73027",
}


def _idw(points, field, grid_lat, grid_lon, power=2.0):
    """反距离加权插值 (独立实现, 无外部依赖)。"""
    src = [p for p in points
           if p.get("risk_level") != "数据失败" and p.get(field) is not None]
    if len(src) < 4:
        return np.full((len(grid_lat), len(grid_lon)), np.nan)
    lats = np.array([p["lat"] for p in src])
    lons = np.array([p["lon"] for p in src])
    vals = np.array([float(p[field]) for p in src])
    glat, glon = np.meshgrid(grid_lat, grid_lon, indexing="ij")
    out = np.full_like(glat, np.nan, dtype=float)
    for i in range(glat.shape[0]):
        for j in range(glat.shape[1]):
            d = np.sqrt((lats - glat[i, j]) ** 2 + (lons - glon[i, j]) ** 2)
            w = 1.0 / (d ** power + 1e-9)
            out[i, j] = np.sum(w * vals) / w.sum()
    return out


def draw_risk_image(geojson_path, points, city, start, end, out_png, dpi=200):
    """白底静态风险图: 行政边界 + IDW插值色斑(同大屏, 非散点)。"""
    with open(geojson_path, encoding="utf-8") as f:
        gj = json.load(f)

    fig, ax = plt.subplots(figsize=(7, 6))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    all_lats = []
    all_lons = []
    rings_all = []

    def _rings(geom):
        t = geom.get("type")
        c = geom.get("coordinates", [])
        if t == "Polygon":
            return c
        if t == "MultiPolygon":
            return [p for mp in c for p in mp]
        return []

    for feat in gj.get("features", []):
        name = feat.get("properties", {}).get("name", "")
        geom = feat.get("geometry", {})
        for ring in _rings(geom):
            if not ring or len(ring) < 3:
                continue
            if isinstance(ring[0], (int, float)):
                xs = [ring[0]]
                ys = [ring[1]]
            else:
                xs = [pt[0] for pt in ring]
                ys = [pt[1] for pt in ring]
            rings_all.append((xs, ys, name))
            all_lats.extend(ys)
            all_lons.extend(xs)

    if all_lats:
        dlat = (max(all_lats) - min(all_lats)) * 0.05 or 0.05
        dlon = (max(all_lons) - min(all_lons)) * 0.05 or 0.05
        xmin, xmax = min(all_lons) - dlon, max(all_lons) + dlon
        ymin, ymax = min(all_lats) - dlat, max(all_lats) + dlat
    else:
        xmin, xmax, ymin, ymax = 0, 1, 0, 1

    # IDW 插值色斑 (同大屏色阶) + 按行政边界裁剪
    from matplotlib.colors import LinearSegmentedColormap
    from matplotlib.cm import ScalarMappable
    from matplotlib.colors import Normalize
    cmap = LinearSegmentedColormap.from_list(
        "risk", ["#1a9850", "#66bd63", "#ffffbf", "#ffd700",
                 "#ff8c00", "#d73027", "#800026"])
    pts = [p for p in points if p.get("risk_level") != "数据失败"
           and p.get("risk_score") is not None]
    if len(pts) >= 4:
        n = 120
        glat = np.linspace(ymin, ymax, n)
        glon = np.linspace(xmin, xmax, n)
        fv = _idw(pts, "risk_score", glat, glon)
        # 边界掩膜: 仅保留行政区并集内的网格
        try:
            import geopandas as gpd
            from shapely.geometry import Point
            from shapely.ops import unary_union
            from shapely.prepared import prep
            gdf = gpd.read_file(geojson_path)
            union = prep(unary_union(gdf.geometry.tolist()))
            for i in range(n):
                for j in range(n):
                    if not union.contains(Point(glon[j], glat[i])):
                        fv[i, j] = np.nan
        except Exception:
            pass  # 掩膜失败则显示全部插值
        if np.any(~np.isnan(fv)):
            ax.contourf(glon, glat, fv, levels=np.linspace(0, 5, 21),
                        cmap=cmap, alpha=0.85, vmin=0, vmax=5, zorder=1)
            ax.contour(glon, glat, fv, levels=[1, 2, 3, 4],
                       colors="#444444", linewidths=0.4, linestyles="--",
                       zorder=2, alpha=0.5)

    # 边界线
    for xs, ys, name in rings_all:
        ax.plot(xs, ys, color="#2c3e50", linewidth=1.1, zorder=3)

    # 区县名标注
    for xs, ys, name in rings_all:
        if name and len(xs) > 3:
            ax.text(sum(xs) / len(xs), sum(ys) / len(ys), name, fontsize=7,
                    ha="center", va="center", color="#333333", zorder=4,
                    bbox=dict(boxstyle="round,pad=0.15", facecolor="white",
                              edgecolor="none", alpha=0.85))

    ax.set_xlim(xmin, xmax)
    ax.set_ylim(ymin, ymax)
    ax.set_xlabel("经度(E)", fontsize=9)
    ax.set_ylabel("纬度(N)", fontsize=9)
    ax.tick_params(labelsize=8)
    ax.set_title(f"{city} 气候健康风险空间分布\n{start} ~ {end}",
                 fontsize=12, fontweight="bold", pad=10)
    for s in ax.spines.values():
        s.set_color("#999999")

    # 色标
    sm = ScalarMappable(cmap=cmap, norm=Normalize(vmin=0, vmax=5))
    sm.set_array(np.linspace(0, 5, 256))
    cbar = fig.colorbar(sm, ax=ax, shrink=0.75, pad=0.03)
    cbar.set_label("风险评分(0=极低,5=极高)", fontsize=8)

    fig.tight_layout()
    os.makedirs(os.path.dirname(os.path.abspath(out_png)), exist_ok=True)
    fig.savefig(out_png, dpi=dpi, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"OK: {out_png}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--geojson", required=True)
    ap.add_argument("--points", required=True)
    ap.add_argument("--city", required=True)
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    pts = json.load(open(args.points, encoding="utf-8"))
    draw_risk_image(args.geojson, pts, args.city, args.start, args.end, args.out)
