#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch_geojson.py - 下载并缓存中国城市行政边界 GeoJSON

数据源: 阿里云 DataV.GeoAtlas (https://datav.aliyun.com/portal/school/atlas/area_selector)
  行政区划边界数据（民政部标准 2023 版）
说明: 评审环境需离线可用，因此提交前运行本脚本将所有内置城市
      的区县级边界缓存到 data/geojson/<城市名>.json。

用法: python scripts/fetch_geojson.py [--city 兰州]
"""
import argparse
import json
import os
import sys
import time

import requests

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(SCRIPT_DIR)
GEOJSON_DIR = os.path.join(SKILL_DIR, "data", "geojson")
BASE_URL = "https://geo.datav.aliyun.com/areas_v3/bound/{}_full.json"

# 城市 -> 行政区划代码 (GB/T 2260)
CITY_ADCODE = {
    "北京": "110000", "上海": "310000", "天津": "120000", "重庆": "500000",
    "广州": "440100", "深圳": "440300", "成都": "510100", "杭州": "330100",
    "南京": "320100", "武汉": "420100", "西安": "610100", "郑州": "410100",
    "长沙": "430100", "济南": "370100", "青岛": "370200", "沈阳": "210100",
    "哈尔滨": "230100", "长春": "220100", "石家庄": "130100", "太原": "140100",
    "合肥": "340100", "福州": "350100", "南昌": "360100", "昆明": "530100",
    "贵阳": "520100", "南宁": "450100", "海口": "460100", "兰州": "620100",
    "西宁": "630100", "银川": "640100", "乌鲁木齐": "650100",
    "呼和浩特": "150100", "拉萨": "540100",
}


def download_city(city, adcode):
    url = BASE_URL.format(adcode)
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        print(f"[FAIL] {city}: {exc}")
        return False
    os.makedirs(GEOJSON_DIR, exist_ok=True)
    path = os.path.join(GEOJSON_DIR, f"{city}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    n_feat = len(data.get("features", []))
    print(f"[OK] {city} -> {path} ({n_feat} 个区县, {os.path.getsize(path)} bytes)")
    return True


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="下载城市行政边界 GeoJSON")
    ap.add_argument("--city", default=None, help="指定城市（缺省下载全部 33 城）")
    args = ap.parse_args()

    if args.city:
        if args.city not in CITY_ADCODE:
            print(f"未知城市 {args.city}，可用: {list(CITY_ADCODE)}")
            sys.exit(1)
        download_city(args.city, CITY_ADCODE[args.city])
    else:
        ok = 0
        for city, adcode in CITY_ADCODE.items():
            if download_city(city, adcode):
                ok += 1
            time.sleep(0.3)
        print(f"完成: {ok}/{len(CITY_ADCODE)}")


if __name__ == "__main__":
    main()
