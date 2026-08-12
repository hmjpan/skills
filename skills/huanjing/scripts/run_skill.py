#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run_skill.py - 气候健康风险预警 Skill 一键入口

用法:
  python run_skill.py --city 上海 --start 2024-07-20 --end 2024-07-26 [--out-dir ./output] [--map]

流程: 取数(ERA5+AQI) → 计算指标 → 生成报告(JSON+MD+地图)
数据源: Open-Meteo (ERA5 再分析 + CAMS 空气质量), 免费无 key
证据: 所有指标定义见 data/evidence_base.md, 输出含 evidence 证据链
"""
import argparse
import csv
import json
import os
import subprocess
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(SCRIPT_DIR)
DATA_DIR = os.path.join(SKILL_DIR, "data")


def load_cities():
    path = os.path.join(DATA_DIR, "cities.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)["城市"]


def load_vulnerability():
    """返回 {province: elderly_pct}。"""
    path = os.path.join(DATA_DIR, "vulnerability.csv")
    result = {}
    with open(path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                result[row["province"]] = float(row["elderly_share_pct_65plus"])
            except (KeyError, ValueError):
                continue
    return result


def vulnerability_score(city_info, vuln_data):
    """脆弱性评分 0-100: 以省级老年人口占比归一化到 50-100 区间。
    全国均值 13.5% -> 50分; 每 +1 个百分点 -> +5分; 上限 100。
    """
    province = city_info.get("province", "")
    share = vuln_data.get(province)
    if share is None:
        share = vuln_data.get("全国", 13.5)
    score = 50 + (share - 13.5) * 5.0
    return round(max(50.0, min(100.0, score)), 1)


def run_python(args_list):
    r = subprocess.run([sys.executable, "-X", "utf8"] + args_list,
                       capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0:
        sys.stderr.write(r.stderr)
        sys.exit(r.returncode)
    return r.stdout


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="气候健康风险预警 Skill")
    ap.add_argument("--city", required=True, help="城市名，如 上海/北京/哈尔滨")
    ap.add_argument("--start", default=None, help="起始日期 YYYY-MM-DD (默认今天)")
    ap.add_argument("--end", default=None, help="结束日期 YYYY-MM-DD (默认今天)")
    ap.add_argument("--out-dir", default=None)
    ap.add_argument("--map", action="store_true", help="生成大屏")
    ap.add_argument("--vuln", type=float, default=None,
                    help="手动指定脆弱性评分 0-100")
    args = ap.parse_args()

    # 默认日期: 今天
    from datetime import datetime
    today_str = datetime.now().strftime("%Y-%m-%d")
    if args.start is None:
        args.start = today_str
    if args.end is None:
        args.end = today_str

    # 1. 解析城市
    cities = load_cities()
    if args.city not in cities:
        print(json.dumps({
            "success": False,
            "error_code": "UNKNOWN_CITY",
            "message": f"未收录城市 '{args.city}'。可用城市: {', '.join(list(cities)[:10])} 等 {len(cities)} 个。"
                       "也可直接使用 fetch_era5.py 传入 --latitude/--longitude。",
        }, ensure_ascii=False, indent=2))
        sys.exit(1)
    city_info = cities[args.city]

    # 2. 脆弱性评分
    if args.vuln is not None:
        vuln = args.vuln
    else:
        vuln = vulnerability_score(city_info, load_vulnerability())

    # 3. 取数
    tmp_dir = os.path.join(SKILL_DIR, "output", "tmp")
    os.makedirs(tmp_dir, exist_ok=True)
    era5_path = os.path.join(tmp_dir, f"era5_{args.city}_{args.start}_{args.end}.json")
    aqi_path = os.path.join(tmp_dir, f"aqi_{args.city}_{args.start}_{args.end}.json")
    fetch_era5 = os.path.join(SCRIPT_DIR, "fetch_era5.py")
    fetch_aqi = os.path.join(SCRIPT_DIR, "fetch_aqi.py")

    run_python([fetch_era5, "--latitude", str(city_info["latitude"]),
                "--longitude", str(city_info["longitude"]),
                "--start-date", args.start, "--end-date", args.end,
                "--out", era5_path])
    run_python([fetch_aqi, "--latitude", str(city_info["latitude"]),
                "--longitude", str(city_info["longitude"]),
                "--start-date", args.start, "--end-date", args.end,
                "--out", aqi_path])

    # 4. 计算指标
    compute = os.path.join(SCRIPT_DIR, "compute_indices.py")
    indices_out = run_python([compute, era5_path, aqi_path, str(vuln)])
    indices_path = os.path.join(tmp_dir, f"indices_{args.city}_{args.start}_{args.end}.json")
    with open(indices_path, "w", encoding="utf-8") as f:
        f.write(indices_out)

    # 5. 生成报告
    out_dir = args.out_dir or os.path.join(SKILL_DIR, "output",
                                           f"{args.city}_{args.start}_{args.end}")
    build = os.path.join(SCRIPT_DIR, "build_report.py")
    build_args = [build, indices_path, "--city", args.city,
                  "--lat", str(city_info["latitude"]), "--lon", str(city_info["longitude"]),
                  "--period", f"{args.start}~{args.end}", "--out-dir", out_dir]
    if args.map:
        build_args.append("--map")
    run_python(build_args)

    # 6. 汇总输出
    print(json.dumps({
        "success": True,
        "city": args.city,
        "period": f"{args.start}~{args.end}",
        "vulnerability_score": vuln,
        "output_dir": out_dir,
        "report": os.path.join(out_dir, "report.json"),
        "markdown": os.path.join(out_dir, "report.md"),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
