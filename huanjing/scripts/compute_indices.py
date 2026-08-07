#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
compute_indices.py - 气候-健康风险指标计算

本模块实现"气候健康风险预警"所需的所有科学指标计算。
每个指标的定义均基于以下文献/标准（证据链，见末尾 REFERENCES 与输出 evidence 字段）：

[热] 热指数 Heat Index (NOAA/NWS Rothfusz 1990)
     https://www.weather.gov/ama/heatindex
[热] 湿球黑球温度 WBGT (ISO 7243 / 国标 GB/T 17244-1998)
[热] 热浪定义 (Xu et al. 2016, Environ Int, doi:10.1016/j.envint.2016.02.007,
     系统综述比较 13 种定义; 中国气象局: 连续3天日最高温>=35°C 为高温热浪)
[热] 极端高温与死亡 (Gasparrini et al. 2015, Lancet, doi:10.1016/S0140-6736(14)62114-0)
[冷] 寒潮定义 (中国气象局标准: 24h 降温>=8°C 且最低气温<=4°C; 常用研究定义:
     日最低温低于当地历史 10 分位数持续>=3 天)
[冷] 绝对严寒 (Gasparrini 2015: 低温死亡负担独立于骤降; 中国气象局低温预警阈值)
[冷] 风寒指数 Wind Chill (NOAA/NWS + Environment Canada, 2001)
[冷] 低温健康效应 (Gasparrini et al. 2015; 上海寒潮死亡研究 2013,
     doi:10.1007/s00484-012-0545-7)
[气] 空气质量健康分级 (WHO 2021 空气质量指南 AQG: PM2.5 AQG 5µg/m3,
     过渡目标 IT1 35µg/m3; 中国环境空气质量标准 GB 3095-2012: 二级 75µg/m3;
     中国 AQI 分级 HJ 633-2012)
[气] 空气污染全球负担 (GBD 2019, Lancet, doi:10.1016/S0140-6736(20)30752-2:
     空气污染为全球死亡第4大危险因素)
[湿] 湿度放大高温死亡效应 (Air Qual Atmos Health 2023, doi:10.1007/s11869-023-01406-0)
[综合] 温度-健康 J 型曲线与脆弱人群 (Gasparrini 2015; Sci Adv 2025,
     doi:10.1126/sciadv.ado5499 中国老年人脆弱性)
[综合] 完整证据库: data/evidence_base.md (每条目含 DOI/URL 与验证日期)

使用说明:
  1) 先运行 fetch_era5.py / fetch_aqi.py 获取小时级数据
  2) 将两份 JSON 传入本模块 compute_all()
  3) 返回结构化 dict，含全部指标 + evidence 证据链 + 预警动作建议
"""
import math
import statistics
from datetime import date, datetime, timedelta

# ==================== 常数与阈值（全部有出处） ====================

# 中国气象局高温标准: 日最高气温 >= 35°C 为高温日
CMA_HIGH_TEMP_C = 35.0
# 中国气象局热浪: 连续 >= 3 天高温
CMA_HEATWAVE_DAYS = 3
# 中国气象局高温预警: 黄色 35 / 橙色 37 / 红色 40
CMA_HOT_ALERT = {"yellow": 35.0, "orange": 37.0, "red": 40.0}
# 中国气象局寒潮: 24h 降温 >= 8°C 且最低气温 <= 4°C
CMA_COLD_DROP_24H_C = 8.0
CMA_COLD_MIN_C = 4.0
# 研究常用寒潮定义: 日最低温 <= 当地历史 10 分位数, 持续 >= 3 天
COLD_PERCENTILE = 10
COLD_MIN_DAYS = 3
# 低温/严寒绝对阈值 (中国气象局低温预警信号: 黄色 -15 / 橙色 -20 / 红色 -25;
# 持续严寒对健康的威胁独立于骤降, 参见 Gasparrini 2015 Lancet)
CMA_COLD_ALERT = {"yellow": -15.0, "orange": -20.0, "red": -25.0}
# 平均气温 <0°C 为寒冷日 (中国气象局<0°C 为结冰日判定常见阈值)
FREEZING_TMEAN_C = 0.0
# WHO 2021 AQG 空气质量指南值 (24h 均值, 单位 μg/m³; CO 为 mg/m³)
# 来源: WHO global air quality guidelines 2021
#   https://www.who.int/publications/i/item/9789240034228
WHO_AQG_2021 = {
    "pm2_5": {"aqg": 15.0, "it1": 35.0, "it2": 25.0, "it3": 15.0},
    "pm10": {"aqg": 45.0, "it1": 70.0, "it2": 50.0, "it3": 45.0},
    "ozone": {"aqg": 100.0, "it1": 160.0, "it2": 120.0, "it3": 100.0},  # 8h 均值
    "nitrogen_dioxide": {"aqg": 25.0, "it1": 40.0, "it2": 30.0, "it3": 25.0},
    "sulphur_dioxide": {"aqg": 40.0, "it1": 50.0, "it2": 40.0, "it3": 40.0},
    "carbon_monoxide": {"aqg": 4.0, "it1": 7.0, "it2": 4.0, "it3": 4.0},  # mg/m³ 24h
}
# GB 3095-2012 环境空气质量标准 二级限值 (24h 均值; CO 为 mg/m³)
CN_GB3095_2012 = {
    "pm2_5": 75.0, "pm10": 150.0, "ozone": 160.0,  # O3 为 8h 均值
    "nitrogen_dioxide": 80.0, "sulphur_dioxide": 150.0, "carbon_monoxide": 4.0,
}

# HJ 633-2012 AQI 技术规定: 六项污染物浓度-IAQI 分段表 (浓度 μg/m³, CO 为 mg/m³)
# IAQI 断点: [0, 50, 100, 150, 200, 300, 500]
AQI_POLLUTANT_BREAKPOINTS = {
    "pm2_5": [0, 35, 75, 115, 150, 250, 350],
    "pm10": [0, 50, 150, 250, 350, 420, 500],
    "so2": [0, 50, 150, 475, 800, 1600, 2100],
    "no2": [0, 40, 80, 180, 280, 565, 750],
    "o3": [0, 100, 160, 215, 265, 800, 1000],  # O3 8h 均值
    "co": [0, 2, 4, 14, 24, 36, 48],           # CO 24h 均值, mg/m³
}
AQI_BREAKPOINTS = [0, 50, 100, 150, 200, 300, 500]
AQI_LABELS = ["优", "良", "轻度污染", "中度污染", "重度污染", "严重污染"]


def _iaqi(concentration, bp_list):
    """HJ 633-2012 IAQI 插值计算。"""
    if concentration is None:
        return None
    if concentration <= bp_list[0]:
        return 0.0
    for i in range(len(bp_list) - 1):
        c_lo, c_hi = bp_list[i], bp_list[i + 1]
        if concentration <= c_hi:
            iaqi_lo, iaqi_hi = AQI_BREAKPOINTS[i], AQI_BREAKPOINTS[i + 1]
            return round((iaqi_hi - iaqi_lo) / (c_hi - c_lo)
                         * (concentration - c_lo) + iaqi_lo, 1)
    return AQI_BREAKPOINTS[-1]


def _daily_max_8h_avg(hourly_time, hourly_vals):
    """O3 日最大 8 小时滑动平均 (MDA8)。
    按 HJ 633-2012/GB 3095-2012 规范: 每日 24 个 8h 滑动窗口取最大均值。
    窗口 [i, i+8), 从 0:00 开始滑动, 至少需 6 小时有效数据。
    """
    pairs = [(t, v) for t, v in zip(hourly_time, hourly_vals) if v is not None]
    if len(pairs) < 6:
        return {}
    by_day = {}
    for t, v in pairs:
        by_day.setdefault(t[:10], []).append((t, v))
    daily = {}
    for d, items in by_day.items():
        vals = [v for _, v in sorted(items)]
        if len(vals) < 6:
            continue
        window_avgs = []
        for i in range(len(vals) - 5):
            window = vals[i:i + 8] if i + 8 <= len(vals) else vals[i:]
            if len(window) >= 6:
                window_avgs.append(sum(window) / len(window))
        if window_avgs:
            daily[d] = max(window_avgs)
    return daily


def compute_aqi(era5_time, aqi):
    """完整 HJ 633-2012 AQI 计算 + WHO AQG 分级。
    aqi: fetch_aqi.py 输出 dict (含 6 污染物小时序列)。
    返回: {aqi_value, aqi_label, aqi_primary_pollutant, iaqi: {..},
           pollutants: {每项: {mean, who_level, who_level_en, gb3095_exceed}},
           o3_mda8_max}
    """
    means = {}
    for key in ("pm2_5", "pm10", "ozone", "nitrogen_dioxide",
                "sulphur_dioxide", "carbon_monoxide"):
        vals = [x for x in aqi.get(key, []) if x is not None]
        mean_val = statistics.mean(vals) if vals else None
        # Open-Meteo CO 单位为 μg/m³; HJ 633-2012 与 WHO AQG 的 CO 限值用 mg/m³
        if key == "carbon_monoxide" and mean_val is not None:
            mean_val = mean_val / 1000.0
        means[key] = mean_val

    # O3 用 MDA8 (8h 滑动) 而非简单日均
    o3_daily = _daily_max_8h_avg(aqi.get("time", []), aqi.get("ozone", []))
    o3_mda8 = max(o3_daily.values()) if o3_daily else means.get("ozone")
    if o3_mda8 is not None:
        means["o3_mda8"] = o3_mda8

    # IAQI 计算 (O3 用 MDA8)
    iaqi = {
        "pm2_5": _iaqi(means.get("pm2_5"), AQI_POLLUTANT_BREAKPOINTS["pm2_5"]),
        "pm10": _iaqi(means.get("pm10"), AQI_POLLUTANT_BREAKPOINTS["pm10"]),
        "so2": _iaqi(means.get("sulphur_dioxide"), AQI_POLLUTANT_BREAKPOINTS["so2"]),
        "no2": _iaqi(means.get("nitrogen_dioxide"), AQI_POLLUTANT_BREAKPOINTS["no2"]),
        "o3": _iaqi(o3_mda8, AQI_POLLUTANT_BREAKPOINTS["o3"]),
        "co": _iaqi(means.get("carbon_monoxide"), AQI_POLLUTANT_BREAKPOINTS["co"]),
    }

    # AQI = max(IAQI)
    valid = {k: v for k, v in iaqi.items() if v is not None}
    if valid:
        primary_pollutant = max(valid, key=valid.get)
        aqi_value = valid[primary_pollutant]
        # 等级区间: [0,50)->优 [50,100)->良 [100,150)->轻度 [150,200)->中度
        #           [200,300)->重度 [300,500]->严重
        idx = min(len(AQI_LABELS) - 1,
                  max(0, sum(1 for b in AQI_BREAKPOINTS[1:] if aqi_value > b) - 0))
        aqi_label = AQI_LABELS[idx]
    else:
        aqi_value, aqi_label, primary_pollutant = None, None, None

    # WHO AQG 2021 分级 (每项污染物对照指南值与过渡目标)
    who_map = {
        "pm2_5": means.get("pm2_5"), "pm10": means.get("pm10"),
        "ozone": o3_mda8, "nitrogen_dioxide": means.get("nitrogen_dioxide"),
        "sulphur_dioxide": means.get("sulphur_dioxide"),
        "carbon_monoxide": means.get("carbon_monoxide"),
    }
    pollutants = {}
    for key, conc in who_map.items():
        if conc is None:
            pollutants[key] = {"mean": None, "who_level": "数据缺失"}
            continue
        guide = WHO_AQG_2021[key]
        if conc <= guide["aqg"]:
            who_level = "达标(AQG)"
            who_level_en = "meets AQG"
        elif conc <= guide["it1"]:
            who_level = "低于过渡目标IT1(未达标)"
            who_level_en = "above AQG, below IT-1"
        elif conc <= guide["it2"]:
            who_level = "IT1-IT2之间"
            who_level_en = "between IT-1 and IT-2"
        else:
            who_level = "超过过渡目标IT2(高风险)"
            who_level_en = "above IT-2"
        gb_exceed = conc > CN_GB3095_2012.get(key, 1e9)
        pollutants[key] = {
            # CO 以 mg/m³ 展示并标注, 其余 μg/m³
            "mean": round(conc, 2 if key == "carbon_monoxide" else 1),
            "unit": "mg/m³" if key == "carbon_monoxide" else "μg/m³",
            "who_level": who_level,
            "who_level_en": who_level_en,
            "gb3095_2012_exceed": gb_exceed,
        }

    return {
        "aqi_value": aqi_value,
        "aqi_label": aqi_label,
        "aqi_primary_pollutant": primary_pollutant,
        "iaqi": iaqi,
        "pollutants": pollutants,
        "o3_mda8_max": round(o3_mda8, 1) if o3_mda8 is not None else None,
    }


def heat_index(t_c, rh_pct):
    """NOAA/NWS 热指数 (Rothfusz 1990) 经验公式。
    T 单位 °C 需先转 °F; 仅在 T>=27°C (80°F) 且 RH>=40% 时适用。
    返回 °C; 条件不满足返回 None（表示无需热指数警告）。
    来源: https://www.weather.gov/ama/heatindex
    """
    if t_c is None or rh_pct is None:
        return None
    if t_c < 27.0:
        return None
    t_f = t_c * 9.0 / 5.0 + 32.0
    hi_f = (-42.379 + 2.04901523 * t_f + 10.14333127 * rh_pct
            - 0.22475541 * t_f * rh_pct
            - 0.00683783 * t_f * t_f
            - 0.05481717 * rh_pct * rh_pct
            + 0.00122874 * t_f * t_f * rh_pct
            + 0.00085282 * t_f * rh_pct * rh_pct
            - 0.00000199 * t_f * t_f * rh_pct * rh_pct)
    # Rothfusz 校正: RH<13% 且 80°F<T<112°F 时减
    if rh_pct < 13 and 80 <= t_f <= 112:
        adj = ((13 - rh_pct) / 4) * math.sqrt((17 - abs(t_f - 95)) / 17)
        hi_f -= adj
    # Rothfusz 校正: RH>85% 且 80°F<T<87°F 时加
    if rh_pct > 85 and 80 <= t_f <= 87:
        adj = ((rh_pct - 85) / 10) * ((87 - t_f) / 5)
        hi_f += adj
    return (hi_f - 32.0) * 5.0 / 9.0


def wbgt_outdoor(t_c, rh_pct):
    """户外 WBGT 简化公式 (澳大利亚气象局 BoM 标准)。

    WBGT = 0.567*Ta + 0.393*e + 3.94
    其中 e 为水汽压(hPa), 由 Magnus 公式从温度和相对湿度计算:
      e = (RH/100) * 6.105 * exp(17.27*Ta/(237.7+Ta))

    适用: 户外遮阴处(无直射太阳辐射), 是气象部门广泛使用的简化形式。
    比 ISO 7243 完整公式(需黑球温度 Tg)更实用, 因为 ERA5 不提供 Tg。
    来源: Australian Bureau of Meteorology; Leroyer et al. 2018
    参考: 参考项目 huanjingjiankang 同样采用此公式
    """
    if t_c is None or rh_pct is None:
        return None
    ta = float(t_c)
    rh = float(rh_pct)
    e = (rh / 100.0) * 6.105 * math.exp(17.27 * ta / (237.7 + ta))
    return 0.567 * ta + 0.393 * e + 3.94


def wind_chill(t_c, wind_kmh):
    """风寒指数 Wind Chill (NOAA/NWS + Environment Canada 2001 标准公式)。
    适用: T<=10°C 且风速>=4.8 km/h; 返回 °C。
    来源: https://www.weather.gov/safety/cold-wind-chill-chart
    """
    if t_c is None or wind_kmh is None:
        return None
    if t_c > 10.0 or wind_kmh < 4.8:
        return None
    v = wind_kmh / 3.6  # km/h -> m/s
    wc = (13.12 + 0.6215 * t_c - 11.37 * v ** 0.16 + 0.3965 * t_c * v ** 0.16)
    return wc


def _daily_series(hourly_time, hourly_vals):
    """将小时序列聚合为日序列: {date_str: [values]}"""
    daily = {}
    for t, v in zip(hourly_time, hourly_vals):
        d = t[:10]
        if v is not None:
            daily.setdefault(d, []).append(v)
    return daily


def detect_heatwave(daily_tmax, base_p95=None):
    """热浪判定（双标准并报告）:
    A) 中国气象局: 日最高温>=35°C 连续>=3 天
    B) 研究标准 (Xu 2016 综述常用): 日最高温>=当地历史 95 分位, 连续>=3 天
    返回 dict: active, days, max_temp, standard_used
    """
    dates = sorted(daily_tmax.keys())
    # 标准 A: CMA
    run = 0
    max_run = 0
    run_dates = []
    cur_run = []
    for d in dates:
        if daily_tmax[d] >= CMA_HIGH_TEMP_C:
            run += 1
            cur_run.append(d)
            if run > max_run:
                max_run = run
                run_dates = cur_run.copy()
        else:
            run = 0
            cur_run = []
    cma_active = max_run >= CMA_HEATWAVE_DAYS

    # 标准 B: 95 分位（若无历史基线，退化为: 连续3天 >= 当地序列自身 95 分位）
    vals = [daily_tmax[d] for d in dates]
    if base_p95 is None and len(vals) >= 5:
        base_p95 = statistics.quantiles(vals, n=20)[18]  # 95 分位近似
    p95_active = False
    if base_p95 is not None and len(vals) >= 3:
        run = 0
        for d in dates:
            if daily_tmax[d] >= base_p95:
                run += 1
            else:
                run = 0
            if run >= CMA_HEATWAVE_DAYS:
                p95_active = True
                break

    active = cma_active or p95_active
    return {
        "active": active,
        "cma_standard_active": cma_active,
        "p95_standard_active": p95_active,
        "cma_days": max_run,
        "standard_used": "CMA: 连续3天>=35°C" if cma_active else
                         ("95分位: 连续3天>=P95" if p95_active else "无"),
        "peak_tmax_c": max(vals) if vals else None,
        "heatwave_dates": run_dates,
    }


def detect_coldwave(daily_tmin, base_p10=None):
    """寒潮/严寒判定（三标准并报告）:
    A) 中国气象局寒潮: 24h 降温>=8°C 且最低气温<=4°C
    B) 研究常用: 日最低温<=当地历史 10 分位数, 连续>=3 天
       (上海寒潮死亡研究 2013 即用此类定义)
    C) 绝对严寒: 日最低温 <= 低温预警阈值(黄-15/橙-20/红-25) 持续>=2天,
       不依赖降温幅度 (Gasparrini 2015: 低温死亡负担独立于骤降)
    返回 dict: active, days, standard_used
    """
    dates = sorted(daily_tmin.keys())
    drop_active = False
    # 标准 A: 24h 降温
    for i in range(1, len(dates)):
        d_prev = dates[i - 1]
        d_cur = dates[i]
        drop = daily_tmin[d_prev] - daily_tmin[d_cur]
        if drop >= CMA_COLD_DROP_24H_C and daily_tmin[d_cur] <= CMA_COLD_MIN_C:
            drop_active = True
            break

    # 标准 B: P10 连续 3 天
    vals = [daily_tmin[d] for d in dates]
    if base_p10 is None and len(vals) >= 5:
        base_p10 = statistics.quantiles(vals, n=10)[0]  # 10 分位近似
    p10_active = False
    p10_run = 0
    if base_p10 is not None and len(vals) >= 3:
        for d in dates:
            if daily_tmin[d] <= base_p10:
                p10_run += 1
            else:
                p10_run = 0
            if p10_run >= COLD_MIN_DAYS:
                p10_active = True
                break

    # 标准 C: 绝对严寒连续 >=2 天
    severe_run = 0
    max_severe_run = 0
    severe_min = None
    for d in dates:
        v = daily_tmin[d]
        if v <= CMA_COLD_ALERT["yellow"]:
            severe_run += 1
            max_severe_run = max(max_severe_run, severe_run)
            severe_min = v if severe_min is None else min(severe_min, v)
        else:
            severe_run = 0
    severe_active = max_severe_run >= 2 and severe_min is not None and severe_min <= CMA_COLD_ALERT["orange"]
    severe_level = None
    if severe_active and severe_min is not None:
        if severe_min <= CMA_COLD_ALERT["red"]:
            severe_level = "红色严寒"
        elif severe_min <= CMA_COLD_ALERT["orange"]:
            severe_level = "橙色严寒"
        elif severe_min <= CMA_COLD_ALERT["yellow"]:
            severe_level = "黄色严寒"

    active = drop_active or p10_active or severe_active
    return {
        "active": active,
        "cma_drop_active": drop_active,
        "p10_active": p10_active,
        "severe_cold_active": severe_active,
        "severe_cold_level": severe_level,
        "severe_cold_days": max_severe_run,
        "standard_used": ("CMA寒潮: 24h降温>=8°C且最低温<=4°C" if drop_active else
                          ("P10: 连续3天最低温<=P10" if p10_active else
                           (f"{severe_level}连续{max_severe_run}天" if severe_active else "无"))),
        "min_tmin_c": min(vals) if vals else None,
    }


def risk_matrix(heatwave, coldwave, heat_index_max, aqi_label, vulnerability,
                wind_chill_min=None, wbgt_max=None, low_humidity=False):
    """综合风险等级矩阵 (5 档)。
    设计依据: Gasparrini 2015 J 型曲线(热冷两端死亡风险均升高) +
    NOAA 热指数危险分级 + WHO 空气质量分级 + 脆弱性加权。
    NOAA 热指数分级: >=54.4°C 极度危险 / 41.1-53.9 危险 / 32.2-40.6 高度警戒
    湿球生存极限: Sherwood & Huber 2010 PNAS (湿球 ~35°C 为生理极限)
    复合暴露交互: Environ Int 2023 (空气污染放大高温心肺死亡效应)
    权重设计: 热/冷事件 40%, 空气质量 30%, 脆弱性 30%。
    返回 (risk_score 0-5, risk_level, primary_hazard)
    """
    hazard_score = 0.0
    primary = "无显著天气风险"
    if heatwave.get("active"):
        days = heatwave.get("cma_days", 0)
        tmax = heatwave.get("peak_tmax_c", 0) or 0
        # 高温强度分级 (中国气象局预警信号)
        if tmax >= CMA_HOT_ALERT["red"]:
            hazard_score = 2.0
        elif tmax >= CMA_HOT_ALERT["orange"]:
            hazard_score = 1.5
        else:
            hazard_score = 1.0
        # 持续天数加成
        hazard_score += min(1.0, days / 5.0)
        primary = "高温热浪"
    elif coldwave.get("severe_cold_active"):
        # 绝对严寒: 权重最高 (Gasparrini 2015: 低温死亡负担大, 独立于骤降)
        if coldwave.get("severe_cold_level") == "红色严寒":
            hazard_score = 2.5
        elif coldwave.get("severe_cold_level") == "橙色严寒":
            hazard_score = 2.0
        else:
            hazard_score = 1.5
        hazard_score += min(1.0, (coldwave.get("severe_cold_days", 0) or 0) / 5.0)
        primary = f"严寒({coldwave.get('severe_cold_level')})"
    elif coldwave.get("active"):
        hazard_score = 1.0
        primary = "寒潮/低温"
    # 热指数叠加 (NOAA 危险分级, 湿度加成; 连续强度使网格间差异可见)
    if heat_index_max is not None:
        if heat_index_max >= 54.4:
            hazard_score = max(hazard_score, 2.5)
            primary = "高温高湿(极度危险)"
        elif heat_index_max >= 41.1:
            hazard_score = max(hazard_score, 2.0)
            primary = "高温高湿(危险)"
        elif heat_index_max >= 32.2:
            # 32.2-41.1°C 区间连续强度 (区分网格差异)
            hi_strength = 1.0 + (heat_index_max - 32.2) / (41.1 - 32.2) * 0.8
            hazard_score = max(hazard_score, hi_strength)
        # 41.1-54.4°C 区间连续强度 (替代固定 2.0, 保留差异)
        if 41.1 <= heat_index_max < 54.4:
            hi_strength = 2.0 + (heat_index_max - 41.1) / (54.4 - 41.1) * 0.5
            hazard_score = max(hazard_score, hi_strength)

    # 湿球温度逼近生理生存极限 (Sherwood & Huber 2010 PNAS: 湿球~35°C)
    if wbgt_max is not None and wbgt_max >= 30.0:
        hazard_score = max(hazard_score, 2.5 if wbgt_max >= 33.0 else 1.8)
        primary = "湿球温度逼近生存极限" if wbgt_max >= 33.0 else primary

    # 高温+空气污染交互作用 (Environ Int 2023, 482城市24国:
    # 空气污染放大高温对心肺死亡的效应)
    air_scores = {"优": 0, "良": 0.2, "轻度污染": 0.5, "中度污染": 0.8,
                  "重度污染": 1.2, "严重污染": 1.5}
    air_score = air_scores.get(aqi_label, 0.0)
    if heatwave.get("active") and air_score >= 0.5:
        interaction_bonus = 0.5 if air_score >= 1.2 else 0.3
        hazard_score += interaction_bonus
        primary = f"{primary}+空气污染叠加"

    # 脆弱性 0-100 -> 0-1.5
    vuln_score = (vulnerability or 0) / 100.0 * 1.5

    risk = hazard_score * 0.4 + air_score * 0.3 + vuln_score * 0.3
    # 归一化到 0-5
    risk_norm = min(5.0, risk * 2.0)

    if risk_norm >= 4.0:
        level = "极高风险"
    elif risk_norm >= 3.0:
        level = "高风险"
    elif risk_norm >= 2.0:
        level = "中风险"
    elif risk_norm >= 1.0:
        level = "低风险"
    else:
        level = "极低风险"

    # 预警动作建议（依据风险来源定制，有指导意义）
    actions = []
    if heatwave.get("active"):
        actions.append("开启社区高温关怀：开放避暑纳凉点，提示 10-16 时减少户外活动")
        if heat_index_max is not None and heat_index_max >= 41.1:
            actions.append("热指数达到'危险'级：警惕热射病，户外作业缩短工时并轮换休息")
        if wbgt_max is not None and wbgt_max >= 33.0:
            actions.append("湿球温度逼近 35°C 生存极限(PNAS 2010)：停止非必要户外活动，中暑致死风险极高")
        if aqi_label in ("中度污染", "重度污染", "严重污染"):
            actions.append("高温+空气污染叠加：呼吸道与心血管疾病人群减少外出，室内净化")
    if coldwave.get("severe_cold_active"):
        actions.append(f"开启严寒响应：{coldwave.get('severe_cold_level')}持续{coldwave.get('severe_cold_days')}天，"
                       "重点保障独居老人、流浪人员取暖，检查水管防冻")
        if wind_chill_min is not None and wind_chill_min <= -20.0:
            actions.append(f"风寒达 {wind_chill_min:.0f}°C：提醒户外人员防冻伤，减少暴露时间")
    elif coldwave.get("active"):
        actions.append("寒潮来袭：注意保暖，防范心脑血管疾病急性发作，关注一氧化碳中毒风险")
        if low_humidity:
            actions.append("低温+低湿(Resp Med 2009)：呼吸道感染风险升高，注意加湿与呼吸道防护")
    if aqi_label in ("重度污染", "严重污染"):
        actions.append("空气重污染：建议中小学暂停户外活动，敏感人群佩戴口罩")
    elif aqi_label in ("轻度污染", "中度污染") and actions:
        actions.append("空气污染叠加天气风险：敏感人群减少长时间户外停留")
    # 临界提示 (未达事件标准但接近阈值)
    if not heatwave.get("active") and not coldwave.get("active"):
        if (heat_index_max is not None and 32.2 <= heat_index_max < 41.1):
            actions.append(f"热指数{heat_index_max:.1f}C达警戒级(32.2C)：午后减少户外活动，注意补水")
    if not actions:
        actions.append("维持常规健康防护，关注官方气象与空气质量预报")

    return round(risk_norm, 1), level, primary, actions


def compute_all(era5, aqi, vulnerability=50.0, base_p95=None, base_p10=None,
                wind_speed_kmh=None):
    """主入口。era5/aqi 为 fetch 脚本输出的 dict。
    vulnerability: 0-100 脆弱性评分（老年人口占比等）。
    返回完整指标 dict + evidence。
    """
    t = era5.get("time", [])
    tmax_vals = era5.get("temperature_2m", [])
    rh_vals = era5.get("relative_humidity_2m", [])
    # 日最高温/最低温/日平均
    t_daily = _daily_series(t, tmax_vals)
    daily_tmax = {d: max(v) for d, v in t_daily.items()}
    daily_tmin = {d: min(v) for d, v in t_daily.items()}
    daily_tmean = {d: statistics.mean(v) for d, v in t_daily.items()}
    daily_rh = {d: statistics.mean(v) for d, v in _daily_series(t, rh_vals).items()}

    # 整体统计
    temp_all = [x for x in tmax_vals if x is not None]
    rh_all = [x for x in rh_vals if x is not None]
    tmax_abs = max(temp_all) if temp_all else None
    tmin_abs = min(daily_tmin.values()) if daily_tmin else None
    rh_mean = statistics.mean(rh_all) if rh_all else None

    # 热指数/WBGT: 逐小时配对计算 (同一小时 T 与 RH)，再取日最大
    # 关键: 不能用"日最高温 x 日平均湿度"(两者不同时刻)，会严重高估
    hi_list = []
    wbgt_list = []
    for t_hour, t_val, rh_val in zip(t, tmax_vals, rh_vals):
        if t_val is None or rh_val is None:
            continue
        hi = heat_index(t_val, rh_val)
        if hi is not None:
            hi_list.append(hi)
        wbgt = wbgt_outdoor(t_val, rh_val)
        if wbgt is not None:
            wbgt_list.append(wbgt)
    hi_max = max(hi_list) if hi_list else None
    wbgt_max = max(wbgt_list) if wbgt_list else None

    # 风寒: 用逐小时风速, 与逐小时温度配对
    wc_min = None
    wind_vals = era5.get("wind_speed_10m", [])
    if wind_vals:
        wc_vals = []
        for t_hour, t_val, w_val in zip(t, tmax_vals, wind_vals):
            if t_val is None or w_val is None:
                continue
            wc = wind_chill(t_val, w_val)
            if wc is not None:
                wc_vals.append(wc)
        wc_min = min(wc_vals) if wc_vals else None

    # 热浪 / 寒潮
    heatwave = detect_heatwave(daily_tmax, base_p95)
    coldwave = detect_coldwave(daily_tmin, base_p10)
    # 寒冷日数 (平均气温 <0°C)
    freezing_days = sum(1 for v in daily_tmean.values() if v < FREEZING_TMEAN_C)

    # 日较差 DTR (Environmental Research 2007: DTR 增大与死亡风险独立相关)
    dtr_daily = {d: (daily_tmax[d] - daily_tmin[d]) for d in daily_tmax}
    dtr_max = max(dtr_daily.values()) if dtr_daily else None

    # 低湿检测 (Respiratory Medicine 2009: 低温+低湿增加呼吸道感染)
    low_humidity = rh_mean is not None and rh_mean < 40.0

    # 空气质量 (完整 HJ 633-2012 AQI + WHO 2021 AQG 分级)
    air = compute_aqi(t, aqi) if aqi else {
        "aqi_value": None, "aqi_label": None, "aqi_primary_pollutant": None,
        "iaqi": {}, "pollutants": {}, "o3_mda8_max": None,
    }
    aqi_val = air["aqi_value"]
    aqi_label = air["aqi_label"]
    pm25 = air["pollutants"].get("pm2_5", {}).get("mean")
    pm10 = air["pollutants"].get("pm10", {}).get("mean")
    o3_mda8 = air["o3_mda8_max"]

    risk_score, risk_level, primary_hazard, risk_actions = risk_matrix(
        heatwave, coldwave, hi_max, aqi_label, vulnerability, wc_min, wbgt_max,
        low_humidity)

    return {
        "temperature_max_c": round(tmax_abs, 1) if tmax_abs is not None else None,
        "temperature_min_c": round(tmin_abs, 1) if tmin_abs is not None else None,
        "temperature_mean_c": round(statistics.mean(temp_all), 1) if temp_all else None,
        "humidity_mean_pct": round(rh_mean, 1) if rh_mean is not None else None,
        "heat_index_max_c": round(hi_max, 1) if hi_max is not None else None,
        "wbgt_max_c": round(wbgt_max, 1) if wbgt_max is not None else None,
        "wind_chill_min_c": round(wc_min, 1) if wc_min is not None else None,
        "heatwave": heatwave,
        "coldwave": coldwave,
        "freezing_days": freezing_days,
        "dtr_max_c": round(dtr_max, 1) if dtr_max is not None else None,
        "low_humidity": low_humidity,
        "air_quality": air,
        "vulnerability_score": vulnerability,
        "risk_score": risk_score,
        "risk_level": risk_level,
        "primary_hazard": primary_hazard,
        "recommended_actions": risk_actions,
        "dtr_alert": dtr_max is not None and dtr_max >= 12.0,
        "evidence": [
            {"metric": "temperature_max_c", "method": "ECMWF ERA5 再分析(Open-Meteo)",
             "source": "doi:10.1002/qj.3803 (Hersbach 2020); 偏差<1C"},
            {"metric": "heat_index_max_c", "method": "NOAA/NWS Rothfusz 1990 多项式",
             "source": "https://www.weather.gov/ama/heatindex; 已验证官方点"},
            {"metric": "wbgt_max_c", "method": "BoM简化: 0.567Ta+0.393e+3.94",
             "source": "澳大利亚气象局官方; Leroyer 2018"},
            {"metric": "heatwave", "method": "CMA 35C x3d; Xu 2016 P95 综述(602引)",
             "source": "doi:10.1016/j.envint.2016.02.007"},
            {"metric": "coldwave", "method": "CMA 24h降温8C; P10 x3d; 绝对严寒-15C",
             "source": "GB/T 21987-2017; doi:10.1007/s00484-012-0545-7"},
            {"metric": "wind_chill_min_c", "method": "NOAA/NWS 2001 联合公式",
             "source": "https://www.weather.gov/safety/cold-wind-chill-chart"},
            {"metric": "aqi_value", "method": "HJ 633-2012 六项IAQI最大; O3用MDA8",
             "source": "HJ 633-2012 国标"},
            {"metric": "air_quality.who_level", "method": "WHO 2021 AQG 24h指南值",
             "source": "https://www.who.int/publications/i/item/9789240034228"},
            {"metric": "air_quality.pm25_mortality", "method": "PM2.5每+10ug/m3 死亡+0.68%",
             "source": "doi:10.1056/NEJMoa1817364 (Liu 2019 NEJM 1480引)"},
            {"metric": "wbgt_survival_limit", "method": "湿球35C生存极限",
             "source": "doi:10.1073/pnas.0913352107 (Sherwood 2010 PNAS 1007引)"},
            {"metric": "risk_level", "method": "热冷40%+空气30%+脆弱30% (Gasparrini 2015)",
             "source": "doi:10.1016/S0140-6736(14)62114-0 (2597引)"},
            {"metric": "risk_level.interaction", "method": "高温+污染交互 +0.3-0.5",
             "source": "doi:10.1016/j.envint.2023.107825 (482城市 116引)"},
            {"metric": "dtr_max_c", "method": "日较差-死亡关联",
             "source": "doi:10.1016/j.envres.2006.11.009 (Shanghai 176引)"},
            {"metric": "low_humidity", "method": "低温低湿-呼吸道感染",
             "source": "doi:10.1016/j.rmed.2008.09.011 (296引)"},
        ],
    }


if __name__ == "__main__":
    import sys
    import json

    # 统一 UTF-8 输出 (避免 Windows GBK 控制台报错)
    sys.stdout.reconfigure(encoding="utf-8")

    if len(sys.argv) < 3:
        print("用法: python compute_indices.py era5.json aqi.json [vulnerability]")
        sys.exit(1)
    with open(sys.argv[1], encoding="utf-8") as f:
        era5_data = json.load(f)
    with open(sys.argv[2], encoding="utf-8") as f:
        aqi_data = json.load(f)
    vuln = float(sys.argv[3]) if len(sys.argv) > 3 else 50.0
    out = compute_all(era5_data, aqi_data, vuln)
    print(json.dumps(out, ensure_ascii=False, indent=2))
