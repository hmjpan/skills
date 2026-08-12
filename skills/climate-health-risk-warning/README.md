# 气候健康风险预警 Skill

> AI4S Future ScienceSkills Hackathon · Climate 赛道 · 任务3
> 融合 ERA5 再分析温湿度、热浪/寒潮指标、六项大气污染物与人口脆弱性数据，
> 生成社区/城市级气候健康风险预警（综合大屏 + 结构化报告 + Word 报告）。

## 功能

输入一个城市（或经纬度）+ 日期范围，自动产出：

| 输出 | 说明 |
|---|---|
| `dashboard.html` | 综合大屏（深色科技风，单文件）：沿行政区边界裁剪的色斑图（tab 切换 综合风险/温度/湿度/热指数）+ 当前实时气温 KPI + 今日逐时温度趋势（真实数据）+ J 型曲线（Gasparrini 2015）+ 温度异常判断（vs 近 30 天基线）+ 风险趋势（近 15 天历史 + 未来 7 天预报）+ 6 项污染物 vs WHO/GB 标准 + 行动建议 |
| `report.json` | 结构化报告：全部指标 + 14 条证据链 + 不确定性 + 公平性检查 + 重点人群详情 |
| `report.docx` | Word 报告（论文格式）：风险图 + 预警文案 + 健康影响文献解读 + 重点人群 + 行动建议 + 不确定性 + 公平性 + 证据链 |
| `report.md` | Markdown 报告 |
| `risk_map.png` | 静态风险分布图（IDW 插值色斑，按行政边界裁剪） |

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 一键运行（默认评估今天，城市为必填）
python scripts/run_skill.py --city 兰州 --map

# 指定日期
python scripts/run_skill.py --city 上海 --start 2024-07-20 --end 2024-07-26 --map

# 输出到 output/兰州_2026-08-08_2026-08-08/
#   dashboard.html / report.json / report.docx / report.md / risk_map.png
```

支持 33 个城市（`data/cities.json`）：北京、上海、天津、重庆、广州、深圳、成都、杭州、南京、武汉、西安、郑州、长沙、济南、青岛、沈阳、哈尔滨、长春、石家庄、太原、合肥、福州、南昌、昆明、贵阳、南宁、海口、兰州、西宁、银川、乌鲁木齐、呼和浩特、拉萨

## 科学依据（证据链）

所有指标定义均来自权威文献与标准，完整对照表见 [`data/evidence_base.md`](data/evidence_base.md)：

| 指标 | 依据 | 引用 |
|---|---|---|
| 热指数 | NOAA/NWS Rothfusz 1990 多项式 | 已验证官方验证点 |
| WBGT | 澳大利亚气象局 BoM 简化公式 | Leroyer 2018 |
| 热浪判定 | 中国气象局 35°C×3天 + P95 双标准 | GB/T 29457-2012; Xu 2016 (602引) |
| 寒潮/严寒判定 | 中国气象局 24h降温8°C + P10 + 绝对严寒 | GB/T 21987-2017; 上海2008研究 |
| 风寒指数 | NOAA/NWS 2001 联合公式 | 官方标准 |
| AQI | HJ 633-2012 六项污染物 IAQI | 国标 |
| 空气健康分级 | WHO 2021 AQG 24h 指南值 | WHO 2021 |
| 温度-健康 J 型曲线 | Gasparrini 2015 Lancet | doi:10.1016/S0140-6736(14)62114-0 (2597引) |
| 风险矩阵 | 热冷40%+空气30%+脆弱30% 复合矩阵 | Gasparrini 2015; Environ Int 2023 |

## 数据源（免费、无需 API key）

| 数据 | 来源 | 说明 |
|---|---|---|
| 温湿度/风速 | Open-Meteo Archive API（ECMWF ERA5 再分析） | 历史；当天/未来自动降级 Forecast |
| 空气质量 | Open-Meteo Air Quality API（Copernicus CAMS） | PM2.5/PM10/O3/NO2/SO2/CO |
| 实时+预报 | Open-Meteo Forecast API（ECMWF/GFS） | 当前气温、逐小时、近15天+未来7天 |
| 人口脆弱性 | 国家统计局第七次全国人口普查（省级 65+ 占比） | `data/vulnerability.csv` |
| 行政边界 | 阿里云 DataV.GeoAtlas（民政部标准） | `data/geojson/` 33 城，离线可用 |

## 测试

```bash
python tests/test_skill.py
```

46 项测试：公式验证（NOAA 热指数官方点）、AQI 六项计算、热浪/寒潮判定、端到端真实 API、大屏 HTML 完整性、失败路径。

## 失败处理

- 未知城市 → 结构化错误 JSON（`error_code: UNKNOWN_CITY`）
- API 不可达 → 重试 2 次后结构化错误（`DATA_FETCH_FAILED`），**绝不编造数据**
- 数据缺失 → 在 `uncertainty` 与 `fairness_check.data_gaps` 中如实声明

## License

MIT
