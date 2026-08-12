#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
grid_risk.py - 城市网格化风险计算

将城市包围盒划分为 NxN 网格，每个网格点独立拉取 ERA5 温湿度，
计算该点的热指数/WBGT/热浪指标与风险等级，实现"同一城市不同区域
风险不同"的空间粒度。

数据源: Open-Meteo Archive API (ERA5), 免费无 key
"""
import json
import math
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

# 复用 compute_indices 的指标计算
sys.path.insert(0, __import__("os").path.dirname(__file__))
from compute_indices import (  # noqa: E402
    detect_coldwave,
    detect_heatwave,
    heat_index,
    risk_matrix,
    wbgt_outdoor,
    wind_chill,
)

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
TIMEOUT = 30


def city_bounds(lat, lon, span_km=40.0):
    """由中心点与跨度(km)生成城市包围盒经纬度范围。
    40km 覆盖大多数地级市城区范围。
    """
    d_lat = span_km / 111.0
    d_lon = span_km / (111.0 * max(0.1, math.cos(math.radians(lat))))
    return {
        "lat_min": lat - d_lat, "lat_max": lat + d_lat,
        "lon_min": lon - d_lon, "lon_max": lon + d_lon,
    }


def make_grid(lat, lon, n=4, span_km=40.0):
    """生成 n×n 网格点坐标。"""
    b = city_bounds(lat, lon, span_km)
    pts = []
    for i in range(n):
        lat_i = b["lat_min"] + (b["lat_max"] - b["lat_min"]) * (i + 0.5) / n
        for j in range(n):
            lon_j = b["lon_min"] + (b["lon_max"] - b["lon_min"]) * (j + 0.5) / n
            pts.append({"lat": round(lat_i, 4), "lon": round(lon_j, 4)})
    return pts


def fetch_point(lat, lon, start, end):
    """单网格点数据（温湿度+风速）。Archive 优先, 404 时降级 Forecast。"""
    from datetime import datetime, timedelta
    params = {
        "latitude": lat, "longitude": lon,
        "start_date": start, "end_date": end,
        "hourly": "temperature_2m,relative_humidity_2m,wind_speed_10m",
        "timezone": "auto",
    }
    last_err = None
    for attempt in range(3):
        try:
            resp = requests.get(ARCHIVE_URL, params=params, timeout=TIMEOUT)
            if resp.status_code == 200:
                d = resp.json()
                return _parse_resp(d)
            if resp.status_code == 400 or resp.status_code == 404:
                break  # Archive 没有该日期, 降级 Forecast
            last_err = f"HTTP {resp.status_code}"
        except requests.RequestException as exc:
            last_err = str(exc)
        if attempt < 2:
            import time as _t
            _t.sleep(1.5 * (attempt + 1))

    # 降级: Forecast API (用 past_days 覆盖历史, forecast_days 覆盖未来)
    try:
        today = datetime.now().date()
        start_dt = datetime.fromisoformat(start).date()
        end_dt = datetime.fromisoformat(end).date()
        past = max(1, (today - start_dt).days + 1)
        future = max(1, (end_dt - today).days + 1)
        fc_params = {
            "latitude": lat, "longitude": lon,
            "past_days": min(past, 92),
            "forecast_days": min(future, 16),
            "hourly": "temperature_2m,relative_humidity_2m,wind_speed_10m",
            "timezone": "auto",
        }
        resp = requests.get(FORECAST_URL, params=fc_params, timeout=TIMEOUT)
        if resp.status_code == 200:
            return _parse_resp(resp.json())
        last_err = f"Forecast HTTP {resp.status_code}"
    except Exception as exc:
        last_err = str(exc)
    raise RuntimeError(f"网格点取数失败: {last_err}")


def _parse_resp(d):
    """解析 Open-Meteo 响应。"""
    return {
        "time": d["hourly"]["time"],
        "temperature_2m": d["hourly"]["temperature_2m"],
        "relative_humidity_2m": d["hourly"]["relative_humidity_2m"],
        "wind_speed_10m": d["hourly"].get("wind_speed_10m"),
    }


def point_risk(era5, aqi_label, vulnerability):
    """单个网格点的风险指标（复用 compute_indices 逻辑的轻量版）。

    空间差异设计: 热浪/寒潮事件标记由逐点温度决定(不同点可能不同),
    热指数强度直接进入风险评分 -> 同一城市不同区域风险不同。
    """
    t = era5.get("time", [])
    tmax_vals = era5.get("temperature_2m", [])
    rh_vals = era5.get("relative_humidity_2m", [])
    wind_vals = era5.get("wind_speed_10m", [])

    # 日聚合
    daily = {}
    for tt, v in zip(t, tmax_vals):
        if v is not None:
            daily.setdefault(tt[:10], []).append(v)
    daily_tmax = {d: max(v) for d, v in daily.items()}
    daily_tmin = {d: min(v) for d, v in daily.items()}
    rh_daily = {}
    for tt, v in zip(t, rh_vals):
        if v is not None:
            rh_daily.setdefault(tt[:10], []).append(v)

    # 逐小时热指数/WBGT
    hi_list, wbgt_list = [], []
    for tt, tv, rv in zip(t, tmax_vals, rh_vals):
        if tv is None or rv is None:
            continue
        hi = heat_index(tv, rv)
        if hi is not None:
            hi_list.append(hi)
        wb = wbgt_outdoor(tv, rv)
        if wb is not None:
            wbgt_list.append(wb)
    hi_max = max(hi_list) if hi_list else None
    wbgt_max = max(wbgt_list) if wbgt_list else None

    # 风寒
    wc_list = []
    for tt, tv, wv in zip(t, tmax_vals, wind_vals):
        if tv is None or wv is None:
            continue
        wc = wind_chill(tv, wv)
        if wc is not None:
            wc_list.append(wc)
    wc_min = min(wc_list) if wc_list else None

    heatwave = detect_heatwave(daily_tmax)
    coldwave = detect_coldwave(daily_tmin)

    tmax_abs = max(daily_tmax.values()) if daily_tmax else None
    rh_mean = statistics.mean([v for v in rh_vals if v is not None]) if rh_vals else None

    score, level, hazard, actions = risk_matrix(
        heatwave, coldwave, hi_max, aqi_label, vulnerability, wc_min, wbgt_max,
        rh_mean is not None and rh_mean < 40.0)

    # === 空间差异强化: 热指数连续强度修正 ===
    # 全市 AQI 相同 + 热浪事件全网格相同 -> 风险趋同;
    # 用逐点热指数/WBGT 的连续强度重新分层, 保留科学含义:
    #   HI>=54.4: +0.8 / 41.1-54.4: +0.3~0.8 连续 / 32.2-41.1: +0.1~0.3
    #   (依据: NOAA 热指数分级 + PNAS 湿球极限)
    spatial_bonus = 0.0
    if hi_max is not None and hi_max >= 32.2:
        if hi_max >= 54.4:
            spatial_bonus = 0.8
        elif hi_max >= 41.1:
            spatial_bonus = 0.3 + (hi_max - 41.1) / (54.4 - 41.1) * 0.5
        else:
            spatial_bonus = 0.1 + (hi_max - 32.2) / (41.1 - 32.2) * 0.2
    if wbgt_max is not None and wbgt_max >= 30.0:
        spatial_bonus = max(spatial_bonus, (wbgt_max - 30.0) / 5.0 * 0.4)
    score = min(5.0, score + spatial_bonus)

    # 重新定级
    if score >= 4.0:
        level = "极高风险"
    elif score >= 3.0:
        level = "高风险"
    elif score >= 2.0:
        level = "中风险"
    elif score >= 1.0:
        level = "低风险"
    else:
        level = "极低风险"

    return {
        "temperature_max_c": round(tmax_abs, 1) if tmax_abs else None,
        "humidity_mean_pct": round(rh_mean, 1) if rh_mean is not None else None,
        "heat_index_max_c": round(hi_max, 1) if hi_max is not None else None,
        "wbgt_max_c": round(wbgt_max, 1) if wbgt_max is not None else None,
        "heatwave_active": heatwave["active"],
        "coldwave_active": coldwave["active"],
        "risk_score": round(score, 1),
        "risk_level": level,
        "primary_hazard": hazard,
    }


def compute_grid(lat, lon, start, end, n=4, vulnerability=50.0, aqi_label="良",
                 span_km=30.0, max_workers=4):
    """计算城市 n×n 网格各点风险。返回 (points_with_risk, 成功点数)。"""
    pts = make_grid(lat, lon, n, span_km)
    results = []
    ok = 0
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futs = {ex.submit(fetch_point, p["lat"], p["lon"], start, end): p
                for p in pts}
        for fut in as_completed(futs):
            p = futs[fut]
            try:
                data = fut.result()
                risk = point_risk(data, aqi_label, vulnerability)
                risk.update({"lat": p["lat"], "lon": p["lon"]})
                results.append(risk)
                ok += 1
            except Exception as exc:
                results.append({"lat": p["lat"], "lon": p["lon"],
                                "risk_level": "数据失败", "error": str(exc)[:120]})
            time.sleep(0.05)
    results.sort(key=lambda x: (x["lat"], x["lon"]))
    return results, ok


if __name__ == "__main__":
    # 测试: 兰州 4x4 网格
    out, ok = compute_grid(36.06, 103.83, "2026-08-01", "2026-08-07",
                           n=4, vulnerability=50.0)
    print(f"网格点: {len(out)} (成功 {ok})")
    for r in out:
        print(f"  ({r['lat']:.3f},{r['lon']:.3f}) Tmax={r.get('temperature_max_c')} "
              f"HI={r.get('heat_index_max_c')} risk={r.get('risk_score')} "
              f"{r.get('risk_level')} | {r.get('primary_hazard', r.get('error', ''))}")
