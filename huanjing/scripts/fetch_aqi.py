#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch_aqi.py - 获取空气质量数据（Open-Meteo Air Quality API）

数据源: Open-Meteo Air Quality API (https://air-quality-api.open-meteo.com)
  基于 CAMS (Copernicus Atmosphere Monitoring Service) 全球再分析/预报,
  免费、无需 API key。

用法:
  python fetch_aqi.py --latitude 31.23 --longitude 121.47 \
      --start-date 2024-07-20 --end-date 2024-07-26 --out data/aqi_raw.json

输出: JSON {time[], pm2_5[], pm10[], ozone[], nitrogen_dioxide[], european_aqi[],
           source, fetched_at, url}
失败: 结构化错误 JSON + 退出码 1
"""
import argparse
import json
import sys
import time
from datetime import datetime, timezone

import requests

AQI_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
AQI_FORECAST_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
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
    raise RuntimeError(f"请求失败（已重试 {MAX_RETRIES} 次）: {last_err}")


def fetch(lat, lon, start, end):
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start,
        "end_date": end,
        "hourly": "pm2_5,pm10,ozone,nitrogen_dioxide,sulphur_dioxide,carbon_monoxide,european_aqi",
        "timezone": "auto",
    }
    try:
        data = _request(AQI_URL, params)
        if "error" in data and data.get("error"):
            raise RuntimeError(data.get("reason", "AQI API 错误"))
        return data
    except RuntimeError:
        # 降级: 用 past_days + forecast_days
        from datetime import datetime
        today = datetime.now().date()
        start_dt = datetime.fromisoformat(start).date()
        end_dt = datetime.fromisoformat(end).date()
        past = max(1, (today - start_dt).days + 1)
        future = max(1, (end_dt - today).days + 1)
        fc_params = {
            "latitude": lat, "longitude": lon,
            "past_days": min(past, 92),
            "forecast_days": min(future, 16),
            "hourly": "pm2_5,pm10,ozone,nitrogen_dioxide,sulphur_dioxide,carbon_monoxide,european_aqi",
            "timezone": "auto",
        }
        data = _request(AQI_FORECAST_URL, fc_params)
        if "error" in data and data.get("error"):
            raise RuntimeError(data.get("reason", "AQI Forecast 错误"))
        return data


def main():
    # 统一 UTF-8 输出 (避免 Windows GBK 控制台报错)
    sys.stdout.reconfigure(encoding="utf-8")

    ap = argparse.ArgumentParser(description="空气质量取数")
    ap.add_argument("--latitude", type=float, required=True)
    ap.add_argument("--longitude", type=float, required=True)
    ap.add_argument("--start-date", required=True)
    ap.add_argument("--end-date", required=True)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    try:
        data = fetch(args.latitude, args.longitude, args.start_date, args.end_date)
    except RuntimeError as exc:
        print(json.dumps({"success": False, "error_code": "DATA_FETCH_FAILED",
                          "message": str(exc), "stage": "fetch_aqi"},
                         ensure_ascii=False))
        sys.exit(1)

    result = {
        "success": True,
        "source": "Open-Meteo Air Quality API (CAMS)",
        "timezone": data.get("timezone", "unknown"),
        "fetched_at": datetime.now(timezone.utc).isoformat() + "Z",
    }
    if "hourly" in data:
        result["time"] = data["hourly"]["time"]
        result["pm2_5"] = data["hourly"]["pm2_5"]
        result["pm10"] = data["hourly"]["pm10"]
        result["ozone"] = data["hourly"]["ozone"]
        result["nitrogen_dioxide"] = data["hourly"]["nitrogen_dioxide"]
        result["sulphur_dioxide"] = data["hourly"]["sulphur_dioxide"]
        result["carbon_monoxide"] = data["hourly"]["carbon_monoxide"]
        result["european_aqi"] = data["hourly"]["european_aqi"]
    else:
        for k in ("time", "pm2_5", "pm10", "ozone", "nitrogen_dioxide",
                  "sulphur_dioxide", "carbon_monoxide", "european_aqi"):
            result[k] = []

    out = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(out)
        print(f"OK: {args.out} ({len(result['time'])} 小时数据)")
    else:
        print(out)


if __name__ == "__main__":
    main()
