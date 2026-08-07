#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_skill.py - 气候健康风险预警 Skill 自测

覆盖:
  1. 公式正确性 (NOAA 热指数官方验证点 / IAQI 插值)
  2. 热浪/寒潮/严寒判定逻辑
  3. AQI 六项污染物计算
  4. 完整端到端流程 (真实 API, 可跳过)
  5. 失败路径 (未知城市 / 无效坐标)

用法: python tests/test_skill.py [--skip-network]
"""
import argparse
import json
import os
import subprocess
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, os.path.join(SCRIPT_DIR, "..", "scripts"))

import compute_indices as ci  # noqa: E402

PASS = 0
FAIL = 0


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  [PASS] {name}")
    else:
        FAIL += 1
        print(f"  [FAIL] {name} {detail}")


def test_heat_index_formula():
    print("[1] 热指数公式 (NOAA 官方验证点)")
    # 官方表: 90°F(32.2°C)/60% -> 100°F(37.8°C); 100°F(37.8°C)/70% -> 129°F(53.9°C)
    hi = ci.heat_index(32.2, 60)
    check("90°F/60% -> ~100°F(37.8°C)", hi is not None and abs(hi - 37.8) < 1.0,
          f"got {hi}")
    hi2 = ci.heat_index(26.7, 40)
    check("80°F 以下不适用返回 None", hi2 is None, f"got {hi2}")


def test_iaqi():
    print("[2] AQI IAQI 插值 (HJ 633-2012)")
    # PM2.5: 35 -> IAQI 50; 75 -> 100 (线性插值边界)
    v = ci._iaqi(35.0, ci.AQI_POLLUTANT_BREAKPOINTS["pm2_5"])
    check("PM2.5=35 -> IAQI 50", v == 50.0, f"got {v}")
    v = ci._iaqi(75.0, ci.AQI_POLLUTANT_BREAKPOINTS["pm2_5"])
    check("PM2.5=75 -> IAQI 100", v == 100.0, f"got {v}")


def test_heatwave_coldwave_logic():
    print("[3] 热浪/寒潮判定逻辑")
    # 构造连续 3 天 36°C
    dmax = {"2024-07-20": 36.0, "2024-07-21": 36.0, "2024-07-22": 36.0,
            "2024-07-23": 30.0}
    hw = ci.detect_heatwave(dmax)
    check("连续3天>=35°C 判定热浪(CMA)", hw["cma_standard_active"], str(hw))

    # 构造严寒: 连续 2 天 -20°C
    dmin = {"2024-01-10": -20.0, "2024-01-11": -22.0, "2024-01-12": -18.0}
    cw = ci.detect_coldwave(dmin)
    check("连续2天<=-15°C 判定严寒", cw["severe_cold_active"], str(cw))
    check("严寒等级为橙色(-20°C)", cw["severe_cold_level"] == "橙色严寒", str(cw))


def test_aqi_compute():
    print("[4] AQI 六项污染物计算")
    fake_aqi = {
        "time": [f"2024-07-20T{i:02d}:00" for i in range(24)],
        "pm2_5": [50.0] * 24, "pm10": [80.0] * 24, "ozone": [120.0] * 24,
        "nitrogen_dioxide": [40.0] * 24, "sulphur_dioxide": [30.0] * 24,
        "carbon_monoxide": [600.0] * 24,
    }
    air = ci.compute_aqi(["2024-07-20"], fake_aqi)
    check("AQI 值计算成功", air["aqi_value"] is not None, str(air["aqi_value"]))
    check("O3 MDA8 计算", air["o3_mda8_max"] == 120.0, str(air["o3_mda8_max"]))
    check("CO 单位换算 (600μg/m³ -> 0.6mg/m³)",
          air["pollutants"]["carbon_monoxide"]["mean"] == 0.6,
          str(air["pollutants"]["carbon_monoxide"]["mean"]))


def test_end_to_end(city, start, end, args):
    print(f"[5] 端到端 ({city} {start}~{end})")
    r = subprocess.run([sys.executable, "-X", "utf8",
                        os.path.join(SCRIPT_DIR, "..", "scripts", "run_skill.py"),
                        "--city", city, "--start", start, "--end", end,
                        "--map"],
                       capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0:
        check(f"{city} 流程退出码 0", False, r.stderr[:200])
        return
    try:
        out = json.loads(r.stdout)
        check(f"{city} 流程成功", out.get("success") is True, r.stdout[:200])
        report_path = out["report"]
        with open(report_path, encoding="utf-8") as f:
            report = json.load(f)
        m = report["metrics"]
        check("报告含风险等级", report["risk_summary"]["risk_level"] in
              ("极高风险", "高风险", "中风险", "低风险", "极低风险"))
        check("报告含预警文案", len(report["warning_text"]) > 20)
        check("报告含证据链", len(report["evidence"]) >= 10)
        check("报告含行动建议", len(report["recommended_actions"]) >= 1)
        check("报告含不确定性", len(report["uncertainty"]["sources"]) >= 1)
        check("报告含公平性检查", report["fairness_check"]["status"] != "")
        check("AQI 分级有效", m["air_quality"]["aqi_label"] in
              ("优", "良", "轻度污染", "中度污染", "重度污染", "严重污染"))
        map_path = os.path.join(os.path.dirname(report_path), "dashboard.html")
        check("大屏 HTML 生成", os.path.exists(map_path))
        if os.path.exists(map_path):
            with open(map_path, encoding="utf-8") as f:
                html = f.read()
            check("大屏含色斑tab", "tabpane" in html)
            check("大屏含KPI", "kpi-val" in html)
            check("大屏含folium地图", "leaflet" in html)
            check("大屏含J型曲线", "Gasparrini" in html)
            check("大屏含行动建议", "行动建议" in html)
            check("大屏含区县标注", "text-shadow" in html)
            check("大屏含逐时温度或趋势", "今日逐时" in html or "24h" in html)
            check("大屏含J型曲线", "Gasparrini" in html)
    except (json.JSONDecodeError, KeyError, OSError) as exc:
        check(f"{city} 输出解析", False, str(exc))


def test_failure_paths():
    print("[6] 失败路径")
    r = subprocess.run([sys.executable, "-X", "utf8",
                        os.path.join(SCRIPT_DIR, "..", "scripts", "run_skill.py"),
                        "--city", "不存在的城市X", "--start", "2024-07-20",
                        "--end", "2024-07-26"],
                       capture_output=True, text=True, encoding="utf-8")
    try:
        out = json.loads(r.stdout)
        check("未知城市返回结构化错误", out.get("error_code") == "UNKNOWN_CITY",
              r.stdout[:200])
    except json.JSONDecodeError:
        check("未知城市返回结构化错误", False, "非 JSON 输出")

    r2 = subprocess.run([sys.executable, "-X", "utf8",
                         os.path.join(SCRIPT_DIR, "..", "scripts", "fetch_era5.py"),
                         "--latitude", "999", "--longitude", "999",
                         "--start-date", "2024-07-20", "--end-date", "2024-07-26"],
                        capture_output=True, text=True, encoding="utf-8")
    try:
        out2 = json.loads(r2.stdout)
        check("无效坐标返回 DATA_FETCH_FAILED",
              out2.get("error_code") == "DATA_FETCH_FAILED" and not out2["success"])
    except json.JSONDecodeError:
        check("无效坐标返回 DATA_FETCH_FAILED", False, "非 JSON 输出")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-network", action="store_true", help="跳过真实 API 测试")
    args = ap.parse_args()

    test_heat_index_formula()
    test_iaqi()
    test_heatwave_coldwave_logic()
    test_aqi_compute()

    if not args.skip_network:
        test_end_to_end("上海", "2024-07-20", "2024-07-26", args)
        test_end_to_end("哈尔滨", "2024-01-15", "2024-01-25", args)
    else:
        print("[5] 跳过端到端（--skip-network）")

    test_failure_paths()

    print(f"\n===== 结果: {PASS} 通过 / {FAIL} 失败 =====")
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
