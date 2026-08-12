---
name: climate-health-risk-warning
description: >-
  融合 ERA5 再分析温湿度、热浪/寒潮指标、六项大气污染物与人口脆弱性数据，
  为任意中国城市生成社区/城市级气候健康风险预警（综合大屏 + 结构化报告 + Word 报告）。
  覆盖高温热浪、高温高湿、寒潮、持续严寒、风寒、空气污染及复合暴露场景，
  所有指标均基于权威文献与标准（证据链见 data/evidence_base.md）。
---

# 气候健康风险预警 Skill

## 触发条件

当用户请求评估**某个城市的天气/气候健康风险**、**热浪/寒潮健康影响**、
**高温/低温健康预警**、**空气污染健康风险**、**气象与健康**相关分析时，
使用本 Skill 生成科学的、带证据链的健康风险预警报告。

## 核心原则（必须遵守）

1. **一切数值来自代码计算与真实数据源**，禁止模型编造任何温度/湿度/浓度数值
2. 所有指标定义引用 `data/evidence_base.md` 中的文献与标准
3. 输出必须包含：证据链 evidence、不确定性 uncertainty、公平性检查 fairness_check
4. 数据缺失时如实声明，绝不伪造
5. 预警文案只能引用已计算出的数值，禁止虚构数字
6. **实时优先**：大屏的 24h 温度趋势用当天逐小时真实数据，J 型曲线标注当前实时温度，
   温度异常判断对比近 30 天基线

## 工作流

### Step 1: 解析输入

- 城市名（33 个内置城市，见 `data/cities.json`）或经纬度
- 日期范围（默认**今天**，实时预警）
- 可选：脆弱性评分（默认按省级老年人口占比自动计算）

### Step 2: 一键运行

```bash
# 默认今天
python scripts/run_skill.py --city 兰州 --map

# 指定日期
python scripts/run_skill.py --city 上海 --start 2024-07-20 --end 2024-07-26 --map
```

内部流程：
1. `fetch_era5.py` — Open-Meteo ERA5 温湿度/风速（当天/未来自动降级 Forecast）
2. `fetch_aqi.py` — Open-Meteo CAMS 六项污染物（PM2.5/PM10/O3/NO2/SO2/CO）
3. `fetch_realtime.py` — 当天逐小时实时数据 + 近30天基线 + 近15天历史/未来7天预报 + 异常判断
4. `compute_indices.py` — 计算全部指标
5. `grid_risk.py` — 城市 4×4 网格逐点风险计算
6. `build_report.py` — 生成 report.json / report.md / report.docx / risk_map.png
7. `make_dashboard.py` — 生成 dashboard.html 综合大屏

### Step 3: 解读输出

阅读 `report.json`（结构化）、`report.docx`（Word 报告）或 `report.md`（人读）。
- `dashboard.html`：**综合大屏**（深色科技风单文件 HTML，浏览器打开）：
  - 中央：沿行政区边界裁剪色斑图（tab 自动切换：综合风险/温度/湿度/热指数），图例随 tab 切换
  - 左栏：当前实时气温 KPI + 环形仪表 + 今日逐时温度趋势（真实数据）+ J 型曲线（Gasparrini 2015）+ 温度异常判断（vs 近30天 P10/P90/P95）
  - 地图下方：风险趋势（近15天历史实线 + 未来7天预报虚线）
  - 右栏：6 项污染物 + 风险构成 + 行动建议 + 重点人群
- `report.docx`：论文格式 Word 报告（风险图 + 预警文案 + 健康影响文献解读 + 重点人群 + 行动建议 + 不确定性 + 公平性 + 证据链）

核心结构：

```json
{
  "risk_summary": {"risk_score": 2.3, "risk_level": "中风险", "primary_hazard": "高温高湿(危险)"},
  "metrics": {
    "temperature_max_c": 36.0, "heat_index_max_c": 47.1, "wbgt_max_c": 31.5,
    "heatwave": {"active": true, "standard_used": "CMA: 连续3天>=35°C"},
    "coldwave": {"active": false},
    "air_quality": {"aqi_value": 60.7, "aqi_label": "良", "pollutants": {...}}
  },
  "warning_text": "...", "recommended_actions": [...],
  "uncertainty": {...}, "fairness_check": {...}, "evidence": [...]
}
```

### Step 4: 生成回答

- 引用 `warning_text` 作为预警文案
- 引用 `recommended_actions` 作为行动建议
- 引用 `at_risk_groups` 作为重点人群
- 引用 `evidence` 作为数据来源
- 提及 `uncertainty` 中的限制

## 指标定义（全部有文献出处）

| 指标 | 定义 | 依据 |
|---|---|---|
| 高温 | 日最高气温 ≥ 35°C | 中国气象局 |
| 热浪 | 连续 ≥ 3 天 ≥35°C（CMA）或 ≥历史 95 分位（研究标准） | 中国气象局; Xu 2016 Environ Int |
| 热指数 | NOAA Rothfusz 公式；≥41.1°C 危险，≥54.4°C 极度危险 | NOAA/NWS 1990 |
| WBGT | ISO 7243 近似；≥33°C 逼近 PNAS 生存极限 | ISO 7243; Sherwood & Huber 2010 |
| 寒潮 | 24h 降温 ≥8°C 且最低温 ≤4°C | 中国气象局 |
| 严寒 | 日最低温 ≤-15°C 连续 ≥2 天（黄/橙/红分级） | 中国气象局低温预警; Gasparrini 2015 |
| 风寒 | NOAA/NWS 2001 公式 | NOAA |
| AQI | HJ 633-2012 六项污染物 IAQI 最大值 | HJ 633-2012 |
| 污染健康分级 | WHO 2021 AQG 24h 指南值与过渡目标 | WHO 2021 |
| 风险等级 | 热/冷 40% + 空气 30% + 脆弱性 30% 复合矩阵 | Gasparrini 2015; Environ Int 2023 |

## 失败处理

| 场景 | 行为 |
|---|---|
| 未知城市 | 返回 `{error_code: UNKNOWN_CITY, message: 可用城市列表}` |
| API 不可达 | 重试 2 次，仍失败返回 `{error_code: DATA_FETCH_FAILED}` |
| 数据缺失 | 指标为 null 并在 uncertainty 中声明 |
| 网络受限 | 全流程纯 Python + 公开 API，无重依赖 |

## 扩展建议

- 新城市：在 `data/cities.json` 的"城市"对象中添加 `{"纬度": lat, "经度": lon, "省份": province}`
- 脆弱性数据：`data/vulnerability.csv` 按省份更新老年人口占比（注明来源）
- 自定义参数：`compute_indices.py` 中阈值常量为可调参数（CMA 35°C 等）

## 参考

- 证据库: `data/evidence_base.md`（全部文献 DOI 与验证日期）
- 快速开始: `README.md`
- 自测: `python tests/test_skill.py`
