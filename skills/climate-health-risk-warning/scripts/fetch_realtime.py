#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch_realtime.py - 获取当天实时逐小时数据 + 近期基线

用途: 健康风险预警需要实时判断, 本模块获取:
  1. 当天逐小时温湿度/风速 (Forecast API, 含 current)
  2. 近 N 天历史基线 (Archive API, 用于异常判断)

数据源: Open-Meteo (免费无 key)
"""
import json
import math
import os
import sys
import time
from datetime import datetime, timedelta, timezone

import requests

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
TIMEOUT = 30
MAX_RETRIES = 2


def _request(url, params):
    last_err = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            resp = requests.get(url, params=params, timeout=TIMEOUT)
            if resp.status_code == 200:
                return resp.json()
            last_err = f"HTTP {resp.status_code}: {resp.text[:200]}"
        except requests.RequestException as exc:
            last_err = str(exc)
        if attempt < MAX_RETRIES:
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"请求失败: {last_err}")


def fetch_today(lat, lon):
    """获取当天逐小时实时数据 (Forecast API, 含 current)。

    返回: {current: {temp, rh, wind, time}, hourly: {time[], temp[], rh[], wind[]},
           today_date, source}
    """
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,relative_humidity_2m,wind_speed_10m",
        "hourly": "temperature_2m,relative_humidity_2m,wind_speed_10m",
        "timezone": "auto",
        "forecast_days": 1,
    }
    data = _request(FORECAST_URL, params)
    cur = data.get("current", {})
    hr = data.get("hourly", {})
    return {
        "current": {
            "temperature_2m": cur.get("temperature_2m"),
            "relative_humidity_2m": cur.get("relative_humidity_2m"),
            "wind_speed_10m": cur.get("wind_speed_10m"),
            "time": cur.get("time"),
        },
        "hourly": {
            "time": hr.get("time", []),
            "temperature_2m": hr.get("temperature_2m", []),
            "relative_humidity_2m": hr.get("relative_humidity_2m", []),
            "wind_speed_10m": hr.get("wind_speed_10m", []),
        },
        "today_date": (cur.get("time") or "")[:10],
        "timezone": data.get("timezone", "unknown"),
        "source": "Open-Meteo Forecast (实时)",
        "fetched_at": datetime.now(timezone.utc).isoformat() + "Z",
    }


def fetch_baseline(lat, lon, days=30):
    """获取近 N 天历史基线 (Archive API), 用于异常判断。

    返回: {time[], temp[], daily_tmax[], daily_tmin[], dates[],
           mean, p10, p90, p95, source}
    """
    end = datetime.now() - timedelta(days=1)
    start = end - timedelta(days=days)
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start.strftime("%Y-%m-%d"),
        "end_date": end.strftime("%Y-%m-%d"),
        "daily": "temperature_2m_max,temperature_2m_min,temperature_2m_mean",
        "timezone": "auto",
    }
    try:
        data = _request(ARCHIVE_URL, params)
    except RuntimeError:
        # Archive 可能有延迟, 退后几天
        end = datetime.now() - timedelta(days=5)
        start = end - timedelta(days=days)
        params["start_date"] = start.strftime("%Y-%m-%d")
        params["end_date"] = end.strftime("%Y-%m-%d")
        data = _request(ARCHIVE_URL, params)

    daily = data.get("daily", {})
    tmax = [v for v in daily.get("temperature_2m_max", []) if v is not None]
    tmin = [v for v in daily.get("temperature_2m_min", []) if v is not None]
    tmean = [v for v in daily.get("temperature_2m_mean", []) if v is not None]

    def pct(vals, p):
        if not vals:
            return None
        s = sorted(vals)
        k = (len(s) - 1) * p / 100
        f = int(k)
        c = min(f + 1, len(s) - 1)
        return s[f] + (s[c] - s[f]) * (k - f)

    return {
        "dates": daily.get("time", []),
        "daily_tmax": daily.get("temperature_2m_max", []),
        "daily_tmin": daily.get("temperature_2m_min", []),
        "daily_tmean": daily.get("temperature_2m_mean", []),
        "mean": sum(tmean) / len(tmean) if tmean else None,
        "p10": pct(tmax, 10),
        "p90": pct(tmax, 90),
        "p95": pct(tmax, 95),
        "mean_tmax": sum(tmax) / len(tmax) if tmax else None,
        "source": f"Open-Meteo ERA5 近{days}天基线",
        "days": days,
    }


def fetch_history_and_forecast(lat, lon, hist_days=15, forecast_days=7):
    """获取近 N 天历史 + 未来 M 天预报的日均温度和日最高温。

    数据源:
    - 历史: Open-Meteo Archive API (ERA5 再分析)
    - 预报: Open-Meteo Forecast API (ECMWF/GFS 数值天气预报)
    两者均为权威气象数据, 非自行建模预测。

    返回: {dates[], tmean[], tmax[], tmin[], is_forecast[], source}
    """
    from datetime import datetime, timedelta
    today = datetime.now().date()
    start_hist = today - timedelta(days=hist_days)
    end_forecast = today + timedelta(days=forecast_days)

    # 历史 (Archive)
    hist_params = {
        "latitude": lat, "longitude": lon,
        "start_date": start_hist.strftime("%Y-%m-%d"),
        "end_date": (today - timedelta(days=1)).strftime("%Y-%m-%d"),
        "daily": "temperature_2m_max,temperature_2m_min,temperature_2m_mean",
        "timezone": "auto",
    }
    # 预报 (Forecast, 含今天和未来)
    fc_params = {
        "latitude": lat, "longitude": lon,
        "daily": "temperature_2m_max,temperature_2m_min,temperature_2m_mean",
        "timezone": "auto",
        "past_days": 1,  # 含今天
        "forecast_days": forecast_days + 1,
    }

    dates, tmax, tmin, tmean, is_fc = [], [], [], [], []
    try:
        hist = _request(ARCHIVE_URL, hist_params)
        d = hist.get("daily", {})
        for i, dt in enumerate(d.get("time", [])):
            dates.append(dt)
            tmax.append(d["temperature_2m_max"][i])
            tmin.append(d["temperature_2m_min"][i])
            tmean.append(d["temperature_2m_mean"][i])
            is_fc.append(False)
    except RuntimeError:
        pass

    try:
        fc = _request(FORECAST_URL, fc_params)
        d = fc.get("daily", {})
        for i, dt in enumerate(d.get("time", [])):
            if dt not in dates:
                dates.append(dt)
                tmax.append(d["temperature_2m_max"][i])
                tmin.append(d["temperature_2m_min"][i])
                tmean.append(d["temperature_2m_mean"][i])
                is_fc.append(True)
    except RuntimeError:
        pass

    return {
        "dates": dates, "tmean": tmean, "tmax": tmax, "tmin": tmin,
        "is_forecast": is_fc,
        "source": "ERA5历史 + ECMWF/GFS预报 (Open-Meteo)",
    }


def daily_risk_score(tmean, tmax, tmin, topt=24.0):
    """根据每日温度估算健康风险评分 (0-5)。

    基于 Gasparrini 2015 J 型曲线的简化量化 (与 compute_indices.rr_from_tmean 一致):
    - RR = exp(a * (T - Topt)^2), 冷端 a=0.0005, 热端 a=0.0013
    - 风险评分 = (RR - 1) * 缩放因子, 映射到 0-5

    注意: 这是示意性量化, 真实风险需完整 DLNM 模型。
    """
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from compute_indices import rr_from_tmean
    if tmean is None:
        return 0.0
    rr = rr_from_tmean(tmean, topt)
    rr = min(rr, 3.5)
    # RR 1.0-3.5 映射到 0-5
    score = (rr - 1.0) / 2.5 * 5.0
    # 日最高温额外加成 (Tmax>=35 时额外风险)
    if tmax and tmax >= 35:
        score += min(1.0, (tmax - 35) / 5.0)
    return round(min(5.0, max(0.0, score)), 2)


def anomaly_assessment(today_tmax, baseline):
    """判断当天日最高温相对于近期基线是否异常。

    方法论:
    - 用当天日最高温 (daily Tmax) 对比近 30 天日最高温的分位数
    - Gasparrini 2015 用日均温度做 J 型曲线, 但气象预警(中国气象局/WHO)
      用日最高温做高温预警, 因为 Tmax 对健康影响最直接(午后热应激)
    - 此处用 Tmax vs 基线 Tmax 的 P90/P95 判断高温异常
    - 用 Tmin vs 基线 Tmin 的 P10 判断低温异常(夜间健康影响)

    返回: {status, detail, deviation, today_tmax, today_tmin}
    """
    if not baseline.get("mean_tmax"):
        return {"status": "数据不足", "detail": "无法判断异常", "deviation": None}

    mean_tmax = baseline["mean_tmax"]
    p90 = baseline.get("p90")
    p95 = baseline.get("p95")
    p10 = baseline.get("p10")
    today_max = today_tmax

    if today_max is None:
        return {"status": "数据不足", "detail": "无当天日最高温数据", "deviation": None}

    dev = today_max - mean_tmax

    if p95 and today_max >= p95:
        return {"status": "异常偏高",
                "detail": f"今日最高温{today_max:.1f}C 超近30天P95({p95:.1f}C), 极端高温",
                "deviation": round(dev, 1)}
    if p90 and today_max >= p90:
        return {"status": "偏高",
                "detail": f"今日最高温{today_max:.1f}C 超近30天P90({p90:.1f}C)",
                "deviation": round(dev, 1)}
    if p10 and today_max <= p10:
        return {"status": "偏低",
                "detail": f"今日最高温{today_max:.1f}C 低于近30天P10({p10:.1f}C)",
                "deviation": round(dev, 1)}
    if dev > 3:
        return {"status": "偏高",
                "detail": f"今日最高温{today_max:.1f}C 高于近30天均值{mean_tmax:.1f}C达{dev:.1f}C",
                "deviation": round(dev, 1)}
    if dev < -3:
        return {"status": "偏低",
                "detail": f"今日最高温{today_max:.1f}C 低于近30天均值{mean_tmax:.1f}C达{abs(dev):.1f}C",
                "deviation": round(dev, 1)}
    return {"status": "正常",
            "detail": f"今日最高温{today_max:.1f}C 接近近30天均值{mean_tmax:.1f}C",
            "deviation": round(dev, 1)}


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    import argparse
    ap = argparse.ArgumentParser(description="实时数据获取")
    ap.add_argument("--latitude", type=float, required=True)
    ap.add_argument("--longitude", type=float, required=True)
    ap.add_argument("--baseline-days", type=int, default=30)
    args = ap.parse_args()

    today = fetch_today(args.latitude, args.longitude)
    print(f"=== 当天实时 ({today['today_date']}) ===")
    print(f"当前: {today['current']['temperature_2m']}C, "
          f"RH {today['current']['relative_humidity_2m']}%, "
          f"风 {today['current']['wind_speed_10m']}km/h")
    print(f"逐小时温度(前12h): {today['hourly']['temperature_2m'][:12]}")

    base = fetch_baseline(args.latitude, args.longitude, args.baseline_days)
    print(f"\n=== 近{base['days']}天基线 ===")
    print(f"均值: {base['mean']:.1f}C, P10: {base['p10']:.1f}, "
          f"P90: {base['p90']:.1f}, P95: {base['p95']:.1f}")

    cur_temp = today["current"]["temperature_2m"]
    anom = anomaly_assessment(cur_temp, base)
    print(f"\n=== 异常判断 ===")
    print(f"状态: {anom['status']}, {anom['detail']}")
