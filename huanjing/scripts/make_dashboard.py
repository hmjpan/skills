#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""make_dashboard.py - 气候健康风险预警大屏 (HTML, 深色科技风)

借鉴气象部门大屏风格: CSS Grid 三栏布局, 中央为沿行政区边界裁剪的
色斑图(tab切换: 综合风险/温度/湿度/污染), 左栏KPI+仪表+趋势,
右栏污染详情+风险构成+行动建议, 底部风险分布条带。

输入: report.json + grid points + era5/aqi 原始数据 + geojson
输出: dashboard.html (单文件)
"""
import html as _html
import json
import math
import os
import sys
from string import Template

import numpy as np

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
import compute_indices as ci  # noqa: E402

BG = "#0a1420"
PANEL = "rgba(14,30,46,.82)"
BORDER = "#1e4976"
ACCENT = "#2fb7ff"
ACCENT2 = "#37e2c8"
TEXT = "#e8f2fb"
SUB = "#8fb3d1"

LEVEL_COLORS = {1: "#1a9850", 2: "#fee08b", 3: "#f46d43",
                4: "#d73027", 5: "#7f0000"}
LEVEL_NAMES = {1: "低", 2: "中", 3: "较高", 4: "高", 5: "极高"}


def _level(score):
    if score >= 4:
        return 5
    if score >= 3:
        return 4
    if score >= 2:
        return 3
    if score >= 1:
        return 2
    return 1


def _kpi(label, value, unit, color=ACCENT, sub=""):
    return (f'<div class="kpi"><div class="kpi-label">{label}</div>'
            f'<div class="kpi-val" style="color:{color}">{value}'
            f'<span class="kpi-unit">{unit}</span></div>'
            f'<div class="kpi-sub">{sub}</div></div>')


def _gauge_svg(pct, color, label_text=""):
    r = 30
    c = 2 * math.pi * r
    off = c * (1 - max(0, min(100, pct)) / 100)
    return (f'<svg width="78" height="78" viewBox="0 0 78 78">'
            f'<circle cx="39" cy="39" r="{r}" fill="none" stroke="#17334d" stroke-width="8"/>'
            f'<circle cx="39" cy="39" r="{r}" fill="none" stroke="{color}" stroke-width="8" '
            f'stroke-linecap="round" stroke-dasharray="{c:.1f}" stroke-dashoffset="{off:.1f}" '
            f'transform="rotate(-90 39 39)" style="filter:drop-shadow(0 0 4px {color})"/>'
            f'<text x="39" y="44" text-anchor="middle" fill="{color}" font-size="17" '
            f'font-weight="700">{pct:.0f}</text></svg>')


def _bar(label, pct, color, val=""):
    return (f'<div class="barrow"><div class="bar-label">{label}</div>'
            f'<div class="bar-track"><div class="bar-fill" style="width:{min(pct,100):.0f}%;'
            f'background:{color};box-shadow:0 0 6px {color}"></div></div>'
            f'<div class="bar-val">{val}</div></div>')


def _temp_color(t):
    for th, c in [(40, "#7f0000"), (37, "#d73027"), (35, "#f46d43"),
                  (32, "#fdae61"), (28, "#fee08b")]:
        if t >= th:
            return c
    return "#74c7e3"


def _sparkline_realtime(hourly_temps, hourly_times=None):
    """24h 温度趋势 SVG (用当天逐小时真实数据, 非拟合)。

    hourly_temps: 24 个逐小时温度值
    hourly_times: 对应时间标签 (如 ["00:00", "01:00", ...])
    """
    temps = list(hourly_temps[:24])
    if not temps or all(v is None for v in temps):
        return '<div style="color:#8fb3d1;font-size:11px">暂无逐小时数据</div>'
    # 填充 None
    for i in range(len(temps)):
        if temps[i] is None:
            temps[i] = temps[i - 1] if i > 0 and temps[i - 1] else 20.0
    n = len(temps)
    W, H = 268, 96
    pad = 8
    xs = [pad + i / max(n - 1, 1) * (W - 2 * pad) for i in range(n)]
    ymin = min(temps) - 0.5
    ymax = max(temps) + 0.5
    ys = [H - pad - (t - ymin) / (ymax - ymin + 0.01) * (H - 2 * pad) for t in temps]
    segs = ""
    for i in range(n - 1):
        c = _temp_color(temps[i])
        segs += (f'<line x1="{xs[i]:.1f}" y1="{ys[i]:.1f}" x2="{xs[i+1]:.1f}" '
                 f'y2="{ys[i+1]:.1f}" stroke="{c}" stroke-width="2.5" stroke-linecap="round"/>')
    hi = int(np.argmax(temps))
    lo = int(np.argmin(temps))
    ticks = ""
    for h in [0, 6, 12, 18, 23]:
        if h < n:
            x = xs[h]
            ticks += f'<text x="{x:.0f}" y="{H-1}" fill="{SUB}" font-size="8" text-anchor="middle">{h:02d}</text>'
    # 标注当前时刻 (最后一个有效点)
    cur_idx = len(temps) - 1
    return (f'<svg width="{W}" height="{H}" viewBox="0 0 {W} {H}">{segs}{ticks}'
            f'<circle cx="{xs[hi]:.1f}" cy="{ys[hi]:.1f}" r="3" fill="#ff4d4f"/>'
            f'<text x="{xs[hi]:.1f}" y="{ys[hi]-6:.1f}" fill="#ff8a65" font-size="10" '
            f'font-weight="700" text-anchor="middle">{temps[hi]:.0f}</text>'
            f'<circle cx="{xs[lo]:.1f}" cy="{ys[lo]:.1f}" r="3" fill="#74c7e3"/>'
            f'<text x="{xs[lo]:.1f}" y="{ys[lo]+12:.1f}" fill="#9fd6ef" font-size="10" '
            f'font-weight="700" text-anchor="middle">{temps[lo]:.0f}</text>'
            f'<circle cx="{xs[cur_idx]:.1f}" cy="{ys[cur_idx]:.1f}" r="4" fill="#fff" '
            f'stroke="#2fb7ff" stroke-width="2"/></svg>')


def _anomaly_panel(anomaly, baseline):
    """温度异常判断面板 HTML。"""
    status = anomaly.get("status", "数据不足")
    detail = anomaly.get("detail", "")
    dev = anomaly.get("deviation")
    color_map = {"异常偏高": "#ff4d4f", "偏高": "#ff8a65", "偏低": "#74c7e3",
                 "异常偏低": "#3498db", "正常": "#37e2c8", "数据不足": SUB}
    col = color_map.get(status, SUB)
    mean = baseline.get("mean")
    p10 = baseline.get("p10")
    p90 = baseline.get("p90")
    dev_str = f" (偏离{dev:+.1f}C)" if dev is not None else ""
    return (f'<div class="panel"><div class="panel-title">温度异常判断 '
            f'<span style="color:{SUB};font-size:9px">(今日Tmax vs 近30天)</span></div>'
            f'<div style="font-size:20px;font-weight:800;color:{col};margin:4px 0">{status}'
            + (f" (偏离{dev:+.1f}C)" if dev is not None else "") + '</div>'
            f'<div style="font-size:11px;color:{SUB};margin-bottom:6px">{detail}</div>'
            f'{_bar("近30天Tmax均值", 50, SUB, f"{mean:.1f}C" if mean else "-")}'
            f'{_bar("P10(低温端)", 10, "#74c7e3", f"{p10:.1f}C" if p10 else "-")}'
            f'{_bar("P90(高温端)", 90, "#ff8a65", f"{p90:.1f}C" if p90 else "-")}'
            f'</div>')


def _sparkline(tmax, tmin):
    """[已弃用] 24h 温度趋势 SVG (拟合), 保留兼容。"""
    hrs = np.arange(24)
    diurnal = (tmax + tmin) / 2 + (tmax - tmin) / 2 * np.sin((hrs - 9) / 24 * 2 * np.pi + np.pi / 2)
    W, H = 268, 96
    pad = 8
    xs = pad + hrs / 23 * (W - 2 * pad)
    ymin, ymax = diurnal.min() - 0.5, diurnal.max() + 0.5
    ys = H - pad - (diurnal - ymin) / (ymax - ymin) * (H - 2 * pad)
    segs = ""
    for i in range(23):
        c = _temp_color(diurnal[i])
        segs += (f'<line x1="{xs[i]:.1f}" y1="{ys[i]:.1f}" x2="{xs[i+1]:.1f}" '
                 f'y2="{ys[i+1]:.1f}" stroke="{c}" stroke-width="2.5" stroke-linecap="round"/>')
    hi = int(diurnal.argmax())
    lo = int(diurnal.argmin())
    return (f'<svg width="{W}" height="{H}" viewBox="0 0 {W} {H}">{segs}'
            f'<circle cx="{xs[hi]:.1f}" cy="{ys[hi]:.1f}" r="3" fill="#ff4d4f"/>'
            f'<text x="{xs[hi]:.1f}" y="{ys[hi]-6:.1f}" fill="#ff8a65" font-size="10" '
            f'font-weight="700" text-anchor="middle">{diurnal[hi]:.0f}</text>'
            f'<circle cx="{xs[lo]:.1f}" cy="{ys[lo]:.1f}" r="3" fill="#74c7e3"/>'
            f'<text x="{xs[lo]:.1f}" y="{ys[lo]+12:.1f}" fill="#9fd6ef" font-size="10" '
            f'font-weight="700" text-anchor="middle">{diurnal[lo]:.0f}</text></svg>')


def _risk_trend_svg_wide(dates, tmean_list, risk_scores, is_forecast):
    """宽版风险趋势折线图 SVG (放在地图下方, 宽扁清晰)。"""
    n = len(dates)
    if n < 3:
        return '<div style="color:#8fb3d1;font-size:11px">数据不足</div>'
    W, H = 960, 120
    pad_l, pad_r, pad_t, pad_b = 40, 15, 10, 28
    plot_w = W - pad_l - pad_r
    plot_h = H - pad_t - pad_b
    half_h = plot_h / 2

    valid_t = [v for v in tmean_list if v is not None]
    if not valid_t:
        return '<div style="color:#8fb3d1;font-size:11px">温度数据缺失</div>'
    tmin_val = min(valid_t)
    tmax_val = max(valid_t)
    t_range = tmax_val - tmin_val + 2
    xs = [pad_l + i / (n - 1) * plot_w for i in range(n)]

    t_ys = []
    for v in tmean_list:
        if v is None:
            t_ys.append(None)
        else:
            y = pad_t + half_h - (v - tmin_val + 1) / t_range * (half_h - 6)
            t_ys.append(y)
    r_ys = []
    for v in risk_scores:
        y = pad_t + half_h + (1 - v / 5.0) * (half_h - 6)
        r_ys.append(y)

    mid_y = pad_t + half_h
    today_idx = 0
    for i, isf in enumerate(is_forecast):
        if isf:
            today_idx = i
            break
    else:
        today_idx = n - 1
    today_x = xs[today_idx]

    t_segs = ""
    for i in range(n - 1):
        if t_ys[i] is None or t_ys[i + 1] is None:
            continue
        dash = 'stroke-dasharray="5,3"' if is_forecast[i] or is_forecast[i + 1] else ""
        t_segs += (f'<line x1="{xs[i]:.1f}" y1="{t_ys[i]:.1f}" x2="{xs[i+1]:.1f}" '
                   f'y2="{t_ys[i+1]:.1f}" stroke="#ff7a45" stroke-width="2.2" {dash}/>'
                   f'<circle cx="{xs[i]:.1f}" cy="{t_ys[i]:.1f}" r="2" fill="#ff7a45"/>')
    r_segs = ""
    for i in range(n - 1):
        if risk_scores[i] is None or risk_scores[i + 1] is None:
            continue
        dash = 'stroke-dasharray="5,3"' if is_forecast[i] or is_forecast[i + 1] else ""
        r = risk_scores[i]
        rcolor = LEVEL_COLORS.get(_level(r), "#666")
        r_segs += (f'<line x1="{xs[i]:.1f}" y1="{r_ys[i]:.1f}" x2="{xs[i+1]:.1f}" '
                   f'y2="{r_ys[i+1]:.1f}" stroke="{rcolor}" stroke-width="2.8" {dash}/>'
                   f'<circle cx="{xs[i]:.1f}" cy="{r_ys[i]:.1f}" r="2" fill="{rcolor}"/>')

    xlabels = ""
    for i in range(0, n, max(1, n // 8)):
        xlabels += f'<text x="{xs[i]:.0f}" y="{H-8}" fill="{SUB}" font-size="8" text-anchor="middle">{dates[i][5:]}</text>'
    ylabels = (f'<text x="5" y="{pad_t+10}" fill="{ACCENT}" font-size="8">温度C</text>'
               f'<text x="5" y="{mid_y+12}" fill="{ACCENT2}" font-size="8">风险0-5</text>')

    # 风险等级色带背景 (下半部分)
    band_y = pad_t + half_h
    band_h = half_h - 4
    bands = ""
    for l, c in [(1, "#1a9850"), (2, "#fee08b"), (3, "#f46d43"), (4, "#d73027"), (5, "#7f0000")]:
        y1 = band_y + (1 - (l - 1) / 5) * band_h
        y2 = band_y + (1 - l / 5) * band_h
        bands += f'<rect x="{pad_l}" y="{y1:.1f}" width="{plot_w}" height="{y2-y1:.1f}" fill="{c}" opacity="0.08"/>'

    return (f'<svg width="100%" height="{H}" viewBox="0 0 {W} {H}" preserveAspectRatio="none">'
            f'<rect x="0" y="0" width="{W}" height="{H}" fill="rgba(10,20,32,.4)" rx="4"/>'
            f'{bands}'
            f'<line x1="{pad_l}" y1="{mid_y:.1f}" x2="{W-pad_r}" y2="{mid_y:.1f}" '
            f'stroke="#1e4976" stroke-width=".5"/>'
            f'{t_segs}{r_segs}'
            f'<line x1="{today_x:.1f}" y1="{pad_t}" x2="{today_x:.1f}" y2="{H-pad_b}" '
            f'stroke="#37e2c8" stroke-width="1" stroke-dasharray="3,3" opacity=".7"/>'
            f'<text x="{today_x+3:.1f}" y="{pad_t+10}" fill="#37e2c8" font-size="8">今天</text>'
            f'{xlabels}{ylabels}</svg>')


def _risk_trend_svg(dates, tmean_list, risk_scores, is_forecast):
    """近15天+未来7天风险趋势折线图 SVG。

    上半: 日均温度折线 + MMT参考线
    下半: 风险评分折线 + 等级色带
    预报段用虚线区分
    """
    n = len(dates)
    if n < 3:
        return '<div style="color:#8fb3d1;font-size:11px">数据不足</div>'
    W, H = 300, 140
    pad_l, pad_r, pad_t, pad_b = 30, 10, 10, 30
    plot_w = W - pad_l - pad_r
    plot_h = H - pad_t - pad_b
    half_h = plot_h / 2

    # 温度范围
    tmin_val = min(v for v in tmean_list if v is not None)
    tmax_val = max(v for v in tmean_list if v is not None)
    t_range = tmax_val - tmin_val + 2
    # 风险范围 0-5
    xs = [pad_l + i / (n - 1) * plot_w for i in range(n)]

    # 温度折线 (上半)
    t_ys = []
    for v in tmean_list:
        if v is None:
            t_ys.append(None)
        else:
            y = pad_t + half_h - (v - tmin_val + 1) / t_range * (half_h - 4)
            t_ys.append(y)
    # 风险折线 (下半)
    r_ys = []
    for v in risk_scores:
        y = pad_t + half_h + (1 - v / 5.0) * (half_h - 4)
        r_ys.append(y)

    # 分隔线
    mid_y = pad_t + half_h
    # MMT 参考线
    mmt = 24.0
    if tmin_val <= mmt <= tmax_val:
        mmt_y = pad_t + half_h - (mmt - tmin_val + 1) / t_range * (half_h - 4)
    else:
        mmt_y = None

    # 温度折线段 (区分历史/预报) - 亮色
    t_segs = ""
    for i in range(n - 1):
        if t_ys[i] is None or t_ys[i + 1] is None:
            continue
        dash = 'stroke-dasharray="4,3"' if is_forecast[i] or is_forecast[i + 1] else ""
        t_segs += (f'<line x1="{xs[i]:.1f}" y1="{t_ys[i]:.1f}" x2="{xs[i+1]:.1f}" '
                   f'y2="{t_ys[i+1]:.1f}" stroke="#ff7a45" stroke-width="2" {dash}/>'
                   f'<circle cx="{xs[i]:.1f}" cy="{t_ys[i]:.1f}" r="1.5" fill="#ff7a45"/>')

    # 风险折线段 - 亮色
    r_segs = ""
    for i in range(n - 1):
        if risk_scores[i] is None or risk_scores[i + 1] is None:
            continue
        dash = 'stroke-dasharray="4,3"' if is_forecast[i] or is_forecast[i + 1] else ""
        r = risk_scores[i]
        rcolor = LEVEL_COLORS.get(_level(r), "#666")
        r_segs += (f'<line x1="{xs[i]:.1f}" y1="{r_ys[i]:.1f}" x2="{xs[i+1]:.1f}" '
                   f'y2="{r_ys[i+1]:.1f}" stroke="{rcolor}" stroke-width="2.5" {dash}/>'
                   f'<circle cx="{xs[i]:.1f}" cy="{r_ys[i]:.1f}" r="1.5" fill="{rcolor}"/>')

    # 今天的位置标记
    today_idx = 0
    for i, isf in enumerate(is_forecast):
        if isf:
            today_idx = i
            break
    else:
        today_idx = n - 1
    today_x = xs[today_idx]

    # X 轴标签 (每5天一个)
    xlabels = ""
    for i in range(0, n, max(1, n // 6)):
        xlabels += f'<text x="{xs[i]:.0f}" y="{H-5}" fill="{SUB}" font-size="7" text-anchor="middle">{dates[i][5:]}</text>'

    # Y 轴标签
    ylabels = (f'<text x="3" y="{pad_t+8}" fill="{SUB}" font-size="7">温</text>'
               f'<text x="3" y="{mid_y+8}" fill="{SUB}" font-size="7">险</text>')

    return (f'<svg width="{W}" height="{H}" viewBox="0 0 {W} {H}">'
            f'<rect x="0" y="0" width="{W}" height="{H}" fill="rgba(10,20,32,.5)" rx="4"/>'
            f'<line x1="{pad_l}" y1="{mid_y:.1f}" x2="{W-pad_r}" y2="{mid_y:.1f}" '
            f'stroke="#1e4976" stroke-width=".5"/>'
            f'{t_segs}{r_segs}'
            f'<line x1="{today_x:.1f}" y1="{pad_t}" x2="{today_x:.1f}" y2="{H-pad_b}" '
            f'stroke="#37e2c8" stroke-width=".8" stroke-dasharray="2,2" opacity=".6"/>'
            f'<text x="{today_x+2:.1f}" y="{pad_t+8}" fill="#37e2c8" font-size="7">今</text>'
            f'{xlabels}{ylabels}</svg>')


def _jcurve_svg(tmean):
    """温度-健康 J 型曲线 SVG (示意性近似, 基于 Gasparrini 2015 Lancet 趋势)。

    方法论依据 (Gasparrini et al. 2015, The Lancet):
    - 使用日均温度 (daily mean temperature), 非日最高或当前时刻温度
    - 最适温度 (minimum mortality temperature, MMT) 各城市不同,
      通常在日均温度的 60-90 百分位, 全球中位数约 22-25C
    - 冷端效应更大且滞后长 (0-3周), 热端效应急性 (0-3天)
    - 本 Skill 用指数近似: RR=exp(a*(T-MMT)^2), 冷端 a=0.010, 热端 a=0.025
      (热端系数更大, 因为热效应虽归因比例小但急性风险陡升)
    - 真实曲线基于 DLNM 模型, 此处为示意性近似
    """
    topt = 24.0  # 全球中位最适温度 (Gasparrini 2015)
    T = np.linspace(-10, 45, 150)
    # 冷端系数小(缓增, 长期), 热端系数大(陡升, 急性)
    RR = np.where(T < topt, np.exp(0.010 * (T - topt) ** 2),
                  np.exp(0.025 * (T - topt) ** 2))
    RR = np.clip(RR, 0, 3.5)
    W, H = 260, 130
    pad = 10
    xs = pad + (T - T.min()) / (T.max() - T.min()) * (W - 2 * pad)
    ys = H - pad - (RR - 0.4) / (3.5 - 0.4) * (H - 2 * pad)
    pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in zip(xs, ys))
    fill_pts = f"{pad},{H-pad} {pts} {W-pad},{H-pad}"
    # 标注当前日均温度
    coef = 0.010 if tmean < topt else 0.025
    rr_now = float(np.exp(coef * (tmean - topt) ** 2))
    rr_now = min(rr_now, 3.5)
    x_now = pad + (tmean - T.min()) / (T.max() - T.min()) * (W - 2 * pad)
    y_now = H - pad - (rr_now - 0.4) / (3.5 - 0.4) * (H - 2 * pad)
    # RR=1 参考线
    y_rr1 = H - pad - (1.0 - 0.4) / (3.5 - 0.4) * (H - 2 * pad)
    return (f'<svg width="{W}" height="{H}" viewBox="0 0 {W} {H}">'
            f'<polygon points="{fill_pts}" fill="rgba(215,48,39,.12)"/>'
            f'<polyline points="{pts}" fill="none" stroke="{ACCENT}" stroke-width="2"/>'
            f'<line x1="{pad}" y1="{y_rr1:.1f}" x2="{W-pad}" y2="{y_rr1:.1f}" '
            f'stroke="{SUB}" stroke-width=".8" stroke-dasharray="3,3"/>'
            f'<text x="{W-50}" y="{y_rr1-3:.1f}" fill="{SUB}" font-size="8">RR=1</text>'
            f'<line x1="{pad + (topt-T.min())/(T.max()-T.min())*(W-2*pad):.1f}" y1="{pad}" '
            f'x2="{pad + (topt-T.min())/(T.max()-T.min())*(W-2*pad):.1f}" y2="{H-pad}" '
            f'stroke="#37e2c8" stroke-width=".6" stroke-dasharray="2,4" opacity=".5"/>'
            f'<circle cx="{x_now:.1f}" cy="{y_now:.1f}" r="5" fill="#d73027" '
            f'stroke="#fff" stroke-width="1.5"/>'
            f'<text x="{x_now+8:.1f}" y="{y_now-5:.1f}" fill="#ff8a65" font-size="9" '
            f'font-weight="700">{tmean:.1f}C RR={rr_now:.2f}</text>'
            f'<text x="5" y="12" fill="{SUB}" font-size="8">RR</text>'
            f'<text x="{W-25}" y="{H-2}" fill="{SUB}" font-size="8">C</text>'
            f'<text x="{pad + (topt-T.min())/(T.max()-T.min())*(W-2*pad)+2:.1f}" y="{H-2}" '
            f'fill="#37e2c8" font-size="7">MMT{topt:.0f}</text></svg>')


def _field_map_html(geojson_path, points, field, stops, city_lat, city_lon, zoom=10,
                    city_name=""):
    """沿行政区边界裁剪的色斑图 (folium)。"""
    import folium
    from shapely.geometry import Point
    from shapely.ops import unary_union
    import geopandas as gpd

    with open(geojson_path, encoding="utf-8") as f:
        gj = json.load(f)
    gdf = gpd.read_file(geojson_path)
    union = unary_union(gdf.geometry.tolist())
    from shapely.prepared import prep
    prep_u = prep(union)

    pts = [p for p in points if p.get("risk_level") != "数据失败"
           and p.get(field) is not None]
    if len(pts) < 4:
        return ""

    lats = np.array([p["lat"] for p in pts])
    lons = np.array([p["lon"] for p in pts])
    vals = np.array([float(p[field]) for p in pts])

    b = gdf.total_bounds
    pad = 0.03
    grid = 60
    glat = np.linspace(b[1] - pad, b[3] + pad, grid)
    glon = np.linspace(b[0] - pad, b[2] + pad, grid)
    LA, LO = np.meshgrid(glat, glon, indexing="ij")
    Z = np.zeros_like(LA)
    W = np.zeros_like(LA)
    for la, lo, v in zip(lats, lons, vals):
        d2 = np.maximum((LA - la) ** 2 + (LO - lo) ** 2, 1e-10)
        w = 1.0 / d2
        Z += w * v
        W += w
    Z /= np.maximum(W, 1e-12)

    def val_to_color(v, stops):
        for i in range(len(stops) - 1):
            if v <= stops[i + 1][0]:
                t = (v - stops[i][0]) / (stops[i + 1][0] - stops[i][0] + 1e-9)
                c1 = [int(stops[i][1][j:j + 2], 16) for j in (1, 3, 5)]
                c2 = [int(stops[i + 1][1][j:j + 2], 16) for j in (1, 3, 5)]
                c = [int(c1[k] + t * (c2[k] - c1[k])) for k in range(3)]
                return f"#{c[0]:02x}{c[1]:02x}{c[2]:02x}"
        return stops[-1][1]

    # 白底瓦片 (高德标准图, 中文标注) + 清晰边界
    # zoom 自适应: 根据边界经纬度跨度计算, 保证整个城市可见
    b = gdf.total_bounds  # minx,miny,maxx,maxy
    lon_span = b[2] - b[0]
    lat_span = b[3] - b[1]
    # 粗略估算 zoom: 城市跨度约 1-2 度 -> zoom 9-10; 跨度越大 zoom 越小
    diag = max(lon_span, lat_span)
    if diag > 2.5:
        zoom = 8
    elif diag > 1.5:
        zoom = 9
    elif diag > 0.8:
        zoom = 10
    elif diag > 0.4:
        zoom = 11
    else:
        zoom = 12
    m = folium.Map(location=[city_lat, city_lon], zoom_start=zoom,
                   tiles="https://webrd04.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x={x}&y={y}&z={z}",
                   attr="高德地图 AMAP", zoom_control=True)
    dlat = glat[1] - glat[0]
    dlon = glon[1] - glon[0]
    for i in range(grid):
        for j in range(grid):
            if prep_u.contains(Point(glon[j], glat[i])):
                col = val_to_color(Z[i, j], stops)
                folium.Rectangle(
                    bounds=[[glat[i] - dlat / 2, glon[j] - dlon / 2],
                            [glat[i] + dlat / 2, glon[j] + dlon / 2]],
                    stroke=False, fill=True, fill_color=col,
                    fill_opacity=0.65).add_to(m)
    folium.GeoJson(gj, style_function=lambda f: dict(
        fillColor="none", color="#1a3a5c", weight=2.5, opacity=1.0),
        name="boundary").add_to(m)
    # 城市中心标注
    folium.Marker([city_lat, city_lon], icon=folium.DivIcon(
        html=f'<div style="font-size:13px;font-weight:800;color:#d73027;'
             f'text-shadow:0 0 4px #fff,0 0 6px #fff,0 0 8px #fff;white-space:nowrap;'
             f'transform:translate(-50%,-50%)">&#9733;{city_name}</div>',
        icon_size=(0, 0))).add_to(m)
    for feat in gj.get("features", []):
        name = feat.get("properties", {}).get("name", "")
        cen = feat.get("properties", {}).get("center")
        if cen and len(cen) >= 2:
            folium.Marker([cen[1], cen[0]], icon=folium.DivIcon(
                html=f'<div style="font-size:11px;font-weight:700;color:#fff;'
                     f'text-shadow:0 0 4px #000,0 0 6px #000;white-space:nowrap;'
                     f'transform:translate(-50%,-50%)">{name}</div>',
                icon_size=(0, 0))).add_to(m)

    # 底部图例 (跟随 tab 切换, 与地图同宽, 紧挨地图)
    return m.get_root().render()


RISK_STOPS = [(0, "#1a9850"), (1, "#fee08b"), (2, "#f46d43"),
              (3, "#d73027"), (4, "#7f0000"), (5, "#7f0000")]
TEMP_STOPS = [(0, "#2c7fb8"), (15, "#74c7e3"), (25, "#fee08b"),
              (32, "#fdae61"), (35, "#f46d43"), (40, "#d73027"), (45, "#7f0000")]
RH_STOPS = [(20, "#f7fbff"), (40, "#c6dbef"), (60, "#6baed6"),
            (80, "#3182bd"), (100, "#08519c")]
PM_STOPS = [(0, "#2fb344"), (15, "#fee08b"), (35, "#fdae61"),
            (75, "#f46d43"), (150, "#d73027")]


def build(points, era5, aqi, report, metrics, geojson_path, city, period, out_html,
          realtime=None):
    """生成 HTML 大屏。

    realtime: 可选, fetch_realtime.fetch_today() + fetch_baseline() + anomaly_assessment() 结果
              包含当天逐小时数据和异常判断, 用于实时 24h 趋势和 J 曲线标注。
    """
    m = metrics
    tmax = m.get("temperature_max_c") or 0
    tmin = m.get("temperature_min_c") or 0
    tmean = m.get("temperature_mean_c") or 0
    rh = m.get("humidity_mean_pct") or 0
    hi = m.get("heat_index_max_c") or 0
    wbgt = m.get("wbgt_max_c") or 0
    score = m.get("risk_score") or 0
    level = _level(score)
    aq = m.get("air_quality", {})
    aqi_val = aq.get("aqi_value") or 0
    aqi_label = aq.get("aqi_label") or "-"
    city_lat = report["location"]["latitude"]
    city_lon = report["location"]["longitude"]

    # 实时数据 (优先用于 24h 趋势和 J 曲线)
    rt_today = (realtime or {}).get("today", {})
    rt_baseline = (realtime or {}).get("baseline", {})
    rt_anomaly = (realtime or {}).get("anomaly", {})
    cur_temp = rt_today.get("current", {}).get("temperature_2m")
    hourly_temps = rt_today.get("hourly", {}).get("temperature_2m", [])
    # J 曲线标注日均温度 (Gasparrini 2015 方法学: 用 daily mean temperature)
    # 优先用当天逐小时均值, 其次用区间均值
    valid_hourly = [t for t in hourly_temps if t is not None]
    if valid_hourly:
        jcurve_temp = sum(valid_hourly) / len(valid_hourly)
    else:
        jcurve_temp = tmean

    map_risk = _field_map_html(geojson_path, points, "risk_score", RISK_STOPS, city_lat, city_lon, city_name=city)
    map_temp = _field_map_html(geojson_path, points, "temperature_max_c", TEMP_STOPS, city_lat, city_lon, city_name=city)
    map_rh = _field_map_html(geojson_path, points, "humidity_mean_pct", RH_STOPS, city_lat, city_lon, city_name=city)
    map_pm = _field_map_html(geojson_path, points, "heat_index_max_c", PM_STOPS, city_lat, city_lon, city_name=city)

    rh_pct = int(rh)
    wbgt_pct = int(np.clip((wbgt - 25) / 10 * 100, 0, 100))
    hw_days = m.get("heatwave", {}).get("cma_days", 0)
    left = (
        f'<div class="panel"><div class="panel-title">气象实况'
        + (f' <span style="color:#37e2c8;font-size:10px">实时 {rt_today.get("today_date","")}</span>'
           if rt_today else '')
        + '</div>'
        + (f'{_kpi("当前气温", f"{cur_temp:.1f}", "C", "#2fb7ff", "实时数据")}' if cur_temp is not None else
           f'{_kpi("最高气温", f"{tmax:.1f}", "C", "#ff7a45", f"均值{tmean:.1f}C 最低{tmin:.1f}C")}')
        + f'<div class="row2"><div class="mini"><div class="mini-t">相对湿度</div>'
        f'{_gauge_svg(rh_pct, ACCENT2)}<div class="mini-s">{rh:.0f}%</div></div>'
        f'<div class="mini"><div class="mini-t">热指数WBGT</div>'
        f'{_gauge_svg(wbgt_pct, "#ff7a45")}<div class="mini-s">{wbgt:.1f}C</div></div></div>'
        f'{_bar("热浪持续", hw_days / 7 * 100, "#ff4d4f", f"{hw_days}天")}'
        f'{_bar("体感闷热", wbgt_pct, "#ffa940", f"{wbgt:.1f}C")}</div>'
    )
    # 24h 温度趋势: 优先用真实逐小时数据
    if hourly_temps and len(hourly_temps) >= 6:
        left += (f'<div class="panel"><div class="panel-title">今日逐时温度 (实时)</div>'
                 f'<div class="spark">{_sparkline_realtime(hourly_temps)}</div></div>')
    else:
        left += (f'<div class="panel"><div class="panel-title">24h温度趋势</div>'
                 f'<div class="spark">{_sparkline(tmax, tmin)}</div></div>')
    # J 型曲线: 标注当天日均温度 (Gasparrini 2015 方法学)
    left += (f'<div class="panel"><div class="panel-title">温度-健康J型曲线</div>'
             f'<div class="spark">{_jcurve_svg(jcurve_temp)}</div>'
             f'<div style="font-size:10px;color:{SUB};margin-top:4px">基于Gasparrini 2015 Lancet'
             + (f' | 标注今日日均{jcurve_temp:.1f}C' if valid_hourly else f' | 标注区间均值{tmean:.1f}C')
             + '</div></div>')
    # 温度异常判断
    if rt_anomaly and rt_baseline:
        left += _anomaly_panel(rt_anomaly, rt_baseline)

    # 风险趋势 (放到地图下方, 宽一些) -> 存到 trend_html 变量
    trend_html = ""
    rt_trend = (realtime or {}).get("trend", {})
    if rt_trend and rt_trend.get("dates"):
        trend_svg = _risk_trend_svg_wide(
            rt_trend["dates"], rt_trend.get("tmean", []),
            rt_trend.get("risk_scores", []), rt_trend.get("is_forecast", []))
        trend_html = (f'<div class="panel trend-panel" style="padding:6px 10px"><div class="panel-title" style="margin-bottom:4px">风险趋势 '
                 f'<span style="color:{SUB};font-size:9px">近15天历史(实线)+未来7天预报(虚线) | 上:温度C 下:风险0-5 | 绿线=今天</span></div>'
                 f'<div class="spark" style="overflow:hidden">{trend_svg}</div></div>')

    aq_col = "#ff4d4f" if aqi_val >= 100 else ("#ffa940" if aqi_val >= 50 else ACCENT2)
    aq_primary = aq.get("aqi_primary_pollutant", "-")
    vuln_score = m.get("vulnerability_score", 50)
    poll_rows = ""
    for k, label in [("pm2_5", "PM2.5"), ("pm10", "PM10"), ("ozone", "O3"),
                     ("nitrogen_dioxide", "NO2"), ("sulphur_dioxide", "SO2"),
                     ("carbon_monoxide", "CO")]:
        p = aq.get("pollutants", {}).get(k, {})
        val = p.get("mean")
        wl = p.get("who_level", "-")
        unit = p.get("unit", "ug/m3")
        if val is not None:
            poll_rows += (f'<div class="prrow"><span class="prname">{label}</span>'
                          f'<span class="prval" style="color:{aq_col}">{val} {unit}</span>'
                          f'<span class="prsub">{wl}</span></div>')
    actions = report.get("recommended_actions", [])
    act_html = "".join(f"<div>- {a}</div>" for a in actions[:4])
    groups = report.get("at_risk_groups", [])
    lvl_name = {1: "极低", 2: "低", 3: "中", 4: "高", 5: "极高"}.get(level, "-")
    right = (
        f'<div class="panel"><div class="panel-title">空气污染</div>'
        f'{_kpi("AQI", f"{aqi_val:.0f}", "", aq_col, f"{aqi_label} 首要:{aq_primary}")}'
        f'<div class="poprisk">{poll_rows}</div></div>'
        f'<div class="panel"><div class="panel-title">风险构成</div>'
        f'{_bar("综合风险", score / 5 * 100, LEVEL_COLORS[level], f"{score:.1f}/5 {lvl_name}")}'
        f'{_bar("高温热效应", min(hi / 54 * 100, 100), "#ff4d4f", f"HI {hi:.1f}C")}'
        f'{_bar("空气污染", min(aqi_val / 200 * 100, 100), "#9467bd", f"AQI {aqi_val:.0f}")}'
        f'{_bar("脆弱性", vuln_score, "#ffa940", f"{vuln_score:.0f}/100")}'
        f'</div>'
        f'<div class="panel"><div class="panel-title">行动建议</div>'
        f'<div style="font-size:12px;color:{TEXT};line-height:1.6">{act_html}</div>'
        f'<div style="font-size:11px;color:{SUB};margin-top:6px">重点人群: {" ".join(groups[:5])}</div></div>'
    )
    # 每个 tab 的图例
    risk_lg = "".join(f'<span class="lg"><i style="background:{LEVEL_COLORS[l]}"></i>L{l} {LEVEL_NAMES[l]}</span>' for l in range(1, 6))
    temp_lg = '<span class="lg"><i style="background:#2c7fb8"></i><24C</span><span class="lg"><i style="background:#74c7e3"></i>24-28</span><span class="lg"><i style="background:#fee08b"></i>28-32</span><span class="lg"><i style="background:#fdae61"></i>32-35</span><span class="lg"><i style="background:#f46d43"></i>35-37</span><span class="lg"><i style="background:#d73027"></i>37-40</span><span class="lg"><i style="background:#7f0000"></i>>40C</span>'
    rh_lg = '<span class="lg"><i style="background:#f7fbff"></i><40%</span><span class="lg"><i style="background:#c6dbef"></i>40-60</span><span class="lg"><i style="background:#6baed6"></i>60-75</span><span class="lg"><i style="background:#3182bd"></i>75-90</span><span class="lg"><i style="background:#08519c"></i>>90%</span>'
    hi_lg = '<span class="lg"><i style="background:#2fb344"></i><32C</span><span class="lg"><i style="background:#fee08b"></i>32-41</span><span class="lg"><i style="background:#fdae61"></i>41-54</span><span class="lg"><i style="background:#d73027"></i>54-75C</span>'
    legends = [risk_lg, temp_lg, rh_lg, hi_lg]

    # ---- 汇总数值 (顶栏 KPI + 副标题) ----
    n_high = sum(1 for p in points if isinstance(p, dict)
                 and _level(p.get("risk_score") or 0) >= 4)
    n_l5 = sum(1 for p in points if isinstance(p, dict)
               and _level(p.get("risk_score") or 0) >= 5)
    n_unit = len(points)
    valid_pts = [p for p in points if isinstance(p, dict) and p.get("risk_score") is not None]
    worst = max(valid_pts, key=lambda p: p.get("risk_score") or 0) if valid_pts else {}
    worst_name = worst.get("unit_name") or worst.get("name") or city
    worst_score = worst.get("risk_score") or 0
    worst_lv = _level(worst_score)
    period_disp = str(period).replace("~", " ~ ")
    start_d = str(period).split("~")[0]
    subline = (f"{worst_name} 风险最高（L{worst_lv} {LEVEL_NAMES[worst_lv]} · {worst_score:.1f}/5）"
               f" · 高/极高 {n_high} 个网格点 · 首要风险 {m.get('primary_hazard','-')}")
    level_count = {l: sum(1 for p in valid_pts if _level(p.get("risk_score") or 0) == l)
                   for l in range(1, 6)}

    html = Template(_SHELL).substitute(
        city=city, date=start_d, period=period_disp, subline=subline,
        n_high=n_high, n_l5=n_l5, n_unit=n_unit, tmax=f"{tmax:.1f}",
        worst_color=LEVEL_COLORS[worst_lv],
        left=left, right=right, trend_html=trend_html,
        map_risk=_html.escape(map_risk, quote=True),
        map_temp=_html.escape(map_temp, quote=True),
        map_rh=_html.escape(map_rh, quote=True),
        map_hi=_html.escape(map_pm, quote=True),
        legend=risk_lg,
        legends_json=json.dumps(legends, ensure_ascii=False),
        level_count_json=json.dumps(level_count),
        BG=BG, PANEL=PANEL, BORDER=BORDER, ACCENT=ACCENT,
        ACCENT2=ACCENT2, SUB=SUB, TEXT=TEXT,
    )
    with open(out_html, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  ✔ 大屏已生成: {out_html}")
    return out_html


def draw_dashboard(geojson_path, points, era5, aqi, report, metrics,
                   city, period, out_pdf, out_png=None, dpi=180):
    """兼容接口: 生成 HTML 大屏。"""
    out_html = out_pdf.replace(".pdf", ".html").replace(".png", ".html")
    build(points, era5, aqi, report, metrics, geojson_path, city, period, out_html)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    import argparse
    ap = argparse.ArgumentParser(description="气候健康风险大屏")
    ap.add_argument("--report", required=True)
    ap.add_argument("--points", required=True)
    ap.add_argument("--era5", required=True)
    ap.add_argument("--aqi", required=True)
    ap.add_argument("--geojson", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    r = json.load(open(args.report, encoding="utf-8"))
    p = json.load(open(args.points, encoding="utf-8"))
    e = json.load(open(args.era5, encoding="utf-8"))
    a = json.load(open(args.aqi, encoding="utf-8"))
    city = r["location"]["city"]
    period = f"{r['period'].get('start','')}~{r['period'].get('end','')}"
    build(p, e, a, r, r["metrics"], args.geojson, city, period, args.out)


_SHELL = """<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>$city 气候健康风险预警大屏</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:$BG;color:$TEXT;font-family:"Microsoft YaHei","SimHei",system-ui;overflow:hidden}
.dash{display:grid;grid-template-rows:64px 1fr 84px;height:100vh;gap:10px;padding:10px}
header{display:flex;align-items:center;justify-content:space-between;
  background:linear-gradient(90deg,rgba(20,50,80,.9),rgba(14,30,46,.9));
  border:1px solid $BORDER;border-radius:10px;padding:0 20px;
  box-shadow:0 0 20px rgba(47,183,255,.15)}
.h-title{font-size:24px;font-weight:800;letter-spacing:1px;
  background:linear-gradient(90deg,#7fd4ff,#37e2c8);-webkit-background-clip:text;
  -webkit-text-fill-color:transparent}
.h-sub{font-size:12.5px;color:$SUB;margin-top:2px}
.h-kpis{display:flex;gap:22px}
.hk{text-align:center}.hk b{font-size:22px}.hk span{display:block;font-size:11px;color:$SUB}
main{display:grid;grid-template-columns:300px 1fr 300px;gap:10px;min-height:0}
.col{display:flex;flex-direction:column;gap:10px;min-height:0;overflow:auto}
.center{display:flex;flex-direction:column;gap:10px;min-height:0}
.panel{background:$PANEL;border:1px solid $BORDER;border-radius:10px;padding:12px 14px;
  box-shadow:inset 0 0 24px rgba(47,183,255,.06)}
.panel-title{font-size:14px;font-weight:700;color:#bfe6ff;margin-bottom:10px;
  border-left:3px solid $ACCENT;padding-left:8px}
.kpi{margin-bottom:8px}.kpi-label{font-size:12px;color:$SUB}
.kpi-val{font-size:34px;font-weight:800;line-height:1.05}
.kpi-unit{font-size:14px;margin-left:2px}.kpi-sub{font-size:11px;color:$SUB}
.row2{display:flex;gap:8px;justify-content:space-between;margin:8px 0}
.mini{flex:1;text-align:center}.mini-t{font-size:11px;color:$SUB;margin-bottom:4px}
.mini-s{font-size:12px;color:$TEXT;margin-top:-6px}
.barrow{display:flex;align-items:center;gap:8px;margin:8px 0}
.bar-label{width:74px;font-size:11.5px;color:$SUB}
.bar-track{flex:1;height:10px;background:#12283c;border-radius:5px;overflow:hidden}
.bar-fill{height:100%;border-radius:5px}
.bar-val{width:56px;text-align:right;font-size:11.5px}
.spark{margin-top:2px}
.poprisk{margin-top:2px}
.prrow{display:flex;align-items:center;gap:6px;margin:6px 0}
.prname{width:64px;font-size:12px;color:$TEXT}
.prval{width:96px;text-align:right;font-size:12px;font-weight:700}
.prsub{flex:1;text-align:right;font-size:10.5px;color:$SUB}
.mapwrap{position:relative;border:1px solid $BORDER;border-radius:10px;overflow:hidden;
  box-shadow:0 0 24px rgba(47,183,255,.12);display:flex;flex-direction:column;flex:1;min-height:0}
.tabs{display:flex;gap:6px;background:rgba(10,20,32,.9);padding:8px 10px;border-bottom:1px solid $BORDER}
.tab{flex:1;text-align:center;padding:8px 0;font-size:13px;font-weight:600;color:$SUB;
  border:1px solid $BORDER;border-radius:8px;cursor:pointer;user-select:none;transition:.15s}
.tab.active{color:#04202f;background:linear-gradient(90deg,#7fd4ff,#37e2c8);
  box-shadow:0 0 12px rgba(55,226,200,.5)}
.tabpane{flex:1;display:none;min-height:0}
.tabpane.active{display:block}
.tabpane iframe{width:100%;height:100%;border:0}
.trend-panel{flex:0 0 auto}
footer{background:$PANEL;border:1px solid $BORDER;border-radius:10px;padding:10px 16px}
.lgs{display:flex;gap:16px;flex-wrap:wrap}
.lg{font-size:11.5px;color:$SUB;display:flex;align-items:center;gap:5px}
.lg i{width:14px;height:14px;border-radius:3px;display:inline-block}
::-webkit-scrollbar{width:6px}::-webkit-scrollbar-thumb{background:#1c3a55;border-radius:3px}
</style></head><body><div class="dash">

<header>
  <div>
    <div class="h-title">&#x1F321; $city 气候健康风险预警</div>
    <div class="h-sub">$subline</div>
  </div>
  <div class="h-kpis">
    <div class="hk"><b style="color:$worst_color">$n_high</b><span>高/极高网格</span></div>
    <div class="hk"><b style="color:#ff4d4f">$n_l5</b><span>极高(L5)</span></div>
    <div class="hk"><b style="color:$ACCENT2">$n_unit</b><span>监测网格</span></div>
    <div class="hk"><b style="color:#ff7a45">$tmax&deg;</b><span>最高气温</span></div>
    <div class="hk"><b style="color:$SUB;font-size:13px">$date<br>$period</b><span>预警时效</span></div>
  </div>
</header>

<main>
  <div class="col">$left</div>

  <div class="center">
    <div class="mapwrap">
      <div class="tabs">
        <div class="tab active" data-t="0">&#x1F5FA; 综合风险</div>
        <div class="tab" data-t="1">&#x1F321; 温度</div>
        <div class="tab" data-t="2">&#x1F4A7; 湿度</div>
        <div class="tab" data-t="3">&#x1F32B; 热指数</div>
      </div>
      <div class="tabpane active"><iframe srcdoc="$map_risk"></iframe></div>
      <div class="tabpane"><iframe srcdoc="$map_temp"></iframe></div>
      <div class="tabpane"><iframe srcdoc="$map_rh"></iframe></div>
      <div class="tabpane"><iframe srcdoc="$map_hi"></iframe></div>
    </div>
    $trend_html
  </div>

  <div class="col">$right</div>
</main>

<footer>
  <div class="lgs" id="legend">$legend</div>
</footer>

</div>
<script>
var LEGENDS = $legends_json;
var LEVEL_COUNT = $level_count_json;
var LV_NAME = {1:"低",2:"中",3:"较高",4:"高",5:"极高"};
var LV_COLOR = {1:"#1a9850",2:"#fee08b",3:"#f46d43",4:"#d73027",5:"#7f0000"};
document.querySelectorAll('.tab').forEach(function(el){
  el.addEventListener('click',function(){
    var i=+el.getAttribute('data-t');
    document.querySelectorAll('.tab').forEach(function(t){t.classList.remove('active')});
    document.querySelectorAll('.tabpane').forEach(function(p){p.classList.remove('active')});
    el.classList.add('active');
    document.querySelectorAll('.tabpane')[i].classList.add('active');
    // 底部图例随 tab 切换; 综合风险 tab 附带各等级网格计数
    var lg = LEGENDS[i];
    if (i === 0) {
      lg = "";
      for (var l = 1; l <= 5; l++) {
        lg += '<span class="lg"><i style="background:'+LV_COLOR[l]+'"></i>L'+l+' '+LV_NAME[l]+'('+ (LEVEL_COUNT[l]||0) +')</span>';
      }
    }
    document.getElementById('legend').innerHTML = lg;
  });
});
</script>
</body></html>"""


if __name__ == "__main__":
    main()
