#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch_era5.py - 获取 ERA5 再分析温湿度数据（Open-Meteo）

数据源:
  - 主: Open-Meteo Archive API (ERA5 再分析, https://archive-api.open-meteo.com)
  - 兜底: Open-Meteo Forecast API past_days (覆盖最近 5 天内的日期)
  - 说明: Open-Meteo 免费、无需 API key、数据可追溯至 ERA5 (ECMWF)

用法:
  python fetch_era5.py --latitude 31.23 --longitude 121.47 \
      --start-date 2024-07-20 --end-date 2024-07-26 --out data/era5_raw.json

输出: JSON {time[], temperature_2m[], relative_humidity_2m[], dewpoint_2m[],
           source, timezone, fetched_at, url}
失败: 结构化错误 JSON + 退出码 1，绝不编造数据
"""
import argparse
import json
import sys
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import requests

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
TIMEOUT = 30
MAX_RETRIES = 2


def _request(url, params):
    """带重试的 GET 请求。"""
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
    """主流程: Archive 优先，近 5 天或 Archive 报错时降级 Forecast。"""
    base_params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start,
        "end_date": end,
        "hourly": "temperature_2m,relative_humidity_2m,dewpoint_2m,wind_speed_10m,wind_direction_10m",
        "timezone": "auto",
    }
    used = "archive"
    try:
        data = _request(ARCHIVE_URL, base_params)
        if "error" in data and data.get("error"):
            raise RuntimeError(data.get("reason", "Archive API 未知错误"))
    except RuntimeError as exc:
        # 日期在 Archive 数据窗口之外（最近约 5 天）→ 降级 Forecast
        try:
            days = max(1, (datetime.fromisoformat(end) - datetime.fromisoformat(start)).days + 1)
            past_days = max(days, 10)
            forecast_params = {
                "latitude": lat,
                "longitude": lon,
                "past_days": past_days,
                "hourly": "temperature_2m,relative_humidity_2m,dewpoint_2m,wind_speed_10m",
                "timezone": "auto",
            }
            data = _request(FORECAST_URL, forecast_params)
            used = "forecast"
        except Exception as exc2:
            raise RuntimeError(
                f"Archive 与 Forecast 均失败: Archive错误: {exc} | Forecast错误: {exc2}"
            )
    return data, used


def main():
    # 统一 UTF-8 输出 (避免 Windows GBK 控制台报错)
    sys.stdout.reconfigure(encoding="utf-8")

    ap = argparse.ArgumentParser(description="ERA5 温湿度取数")
    ap.add_argument("--latitude", type=float, required=True)
    ap.add_argument("--longitude", type=float, required=True)
    ap.add_argument("--start-date", required=True)
    ap.add_argument("--end-date", required=True)
    ap.add_argument("--out", default=None, help="输出 JSON 路径，缺省打印到 stdout")
    args = ap.parse_args()

    try:
        data, used = fetch(args.latitude, args.longitude, args.start_date, args.end_date)
    except RuntimeError as exc:
        err = {"success": False, "error_code": "DATA_FETCH_FAILED",
               "message": str(exc), "stage": "fetch_era5"}
        print(json.dumps(err, ensure_ascii=False))
        sys.exit(1)

    result = {
        "success": True,
        "source": "Open-Meteo ERA5 (archive)" if used == "archive" else "Open-Meteo Forecast (past_days)",
        "api_used": used,
        "timezone": data.get("timezone", "unknown"),
        "fetched_at": datetime.now(timezone.utc).isoformat() + "Z",
        "url": None,
    }
    if used == "archive":
        result["url"] = ARCHIVE_URL + "?" + urlencode({**{"latitude": args.latitude,
                                                          "longitude": args.longitude,
                                                          "start_date": args.start_date,
                                                          "end_date": args.end_date,
                                                          "hourly": "temperature_2m,relative_humidity_2m,dewpoint_2m"}})
    if "hourly" in data:
        result["time"] = data["hourly"]["time"]
        result["temperature_2m"] = data["hourly"]["temperature_2m"]
        result["relative_humidity_2m"] = data["hourly"]["relative_humidity_2m"]
        result["dewpoint_2m"] = data["hourly"].get("dewpoint_2m")
        result["wind_speed_10m"] = data["hourly"].get("wind_speed_10m")
    else:
        result["time"] = []
        result["temperature_2m"] = []
        result["relative_humidity_2m"] = []
        result["wind_speed_10m"] = []

    out = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(out)
        print(f"OK: {args.out} ({len(result['time'])} 小时数据, source={result['source']})")
    else:
        print(out)


if __name__ == "__main__":
    main()
