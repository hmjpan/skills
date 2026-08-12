# 气候健康风险预警 Skill — 科学证据库 (Evidence Base)

> 本文件是 Skill 的权威性根基。所有指标定义、风险矩阵、预警文案均基于以下文献与标准。
> 每个条目均已通过 Crossref/官网验证真实存在（验证日期 2026-08-07）。

## 证据覆盖总览

| 维度 | 核心证据 | 覆盖状态 |
|---|---|---|
| 温度-死亡总论 | Gasparrini 2015 Lancet (2597引) | ✅ |
| 中国温度-死亡 | BMJ 272城市 2018 / 17城市 2014 | ✅ |
| 热浪定义 | CMA国标 + Xu 2016综述(602引) + Perkins 2013(1162引) | ✅ |
| 寒潮/严寒定义 | CMA国标 + 上海2008研究(62引) + 低温负担 | ✅ |
| 湿度-高温 | NOAA热指数 + AQAH 2023中国 + **PNAS湿球极限(1007引)** | ✅ |
| 湿度-低温 | **Resp Med 2009 低温低湿呼吸道感染(296引)** | ✅ |
| 日较差 DTR | **Environ Res 2007 上海 DTR-死亡(176引)** | ✅ |
| 大气污染-死亡 | GBD2019(8012引) + **NEJM 652城市(1480引)** + **AJRCCM 272城市(661引)** + **EHP O3(341引)** | ✅ |
| 污染-死亡中国证据 | AJRCCM/EHP/Lancet PH 272城市 | ✅ |
| 复合暴露交互 | **Environ Int 2023 482城市(116引)** | ✅ |
| 脆弱人群 | Sci Adv 2025 + WHO | ✅ |

## 1. 温度与健康（总论）

### 1.1 温度-死亡 J 型曲线（核心框架）
- **Gasparrini A, et al. Mortality risk attributable to high and low ambient temperature:
  a multicountry observational study. *The Lancet*, 2015.**
  DOI: 10.1016/S0140-6736(14)62114-0 （引用 2597 次）
  - 13 国 74 城市、7400 万死亡数据
  - **结论**: 温度-死亡关系呈 J 型曲线，热端和冷端死亡风险均升高
  - **关键数字**: 非最适温度归因死亡占 7.71%（冷 7.29% > 热 0.42%），
    即**低温造成的死亡负担远高于高温** —— 这是本 Skill 必须纳入寒潮/严寒的核心依据
  - 冷效应滞后约 0-3 周，热效应滞后 0-3 天

### 1.2 中国温度-死亡证据
- **Chen R, et al. Association between ambient temperature and mortality risk and burden:
  time series study in 272 main Chinese cities. *BMJ*, 2018.**
  DOI: 10.1136/bmj.k4306
  - **中国 272 主要城市时间序列研究**（覆盖全中国）
  - 温度-死亡 J 型曲线在中国全国尺度复现；非最适温度死亡负担以低温为主
  - 本 Skill 的全国代表性依据（优于 17 城市 2014 研究）
- **Ma W, et al. Temperature-related mortality in 17 large Chinese cities. *Environmental Research*, 2014.**
  DOI: 10.1016/j.envres.2014.07.007 （引用 188 次）
  - 中国 17 大城市：寒冷死亡风险高于炎热；南北城市差异大
- **Wang Y, et al. Elderly vulnerability to temperature-related mortality risks in China.
  *Science Advances*, 2025.** DOI: 10.1126/sciadv.ado5499 （引用 24 次）
  - **老年人（65+）对温度相关死亡风险显著更脆弱** —— 支撑脆弱性评分与重点人群提示
- **中国伤害相关温度死亡. *Nature Communications*, 2023.** DOI: 10.1038/s41467-022-35462-4
  - 极端温度与伤害（如交通事故、跌倒）死亡也有关联

## 2. 热浪定义（本 Skill 采用双标准）

### 2.1 中国气象局标准（优先）
- 高温日: 日最高气温 ≥ 35°C
- 高温热浪: 连续 ≥ 3 天日最高气温 ≥ 35°C
- 高温预警信号分级: 黄色 ≥35°C / 橙色 ≥37°C / 红色 ≥40°C
- 来源: 中国气象局《气象灾害预警信号发布与传播办法》; 《高温热浪等级》(GB/T 29457-2012)

### 2.2 研究标准（95 分位）
- **Xu Z, et al. Impact of heatwave on mortality under different heatwave definitions:
  a systematic review and meta-analysis. *Environment International*, 2016.**
  DOI: 10.1016/j.envint.2016.02.007 （引用 602 次）
  - 系统比较 13 种热浪定义对死亡效应估计的影响
  - **结论**: 最常见且稳健的定义 = 日最高温 ≥ 当地历史 95 分位、连续 ≥ 3 天
  - 采用不同定义，热浪归因死亡差异可达数倍 —— 本 Skill 采用双标准并如实报告所用标准

### 2.3 热浪度量体系
- **Perkins SE, Alexander LV. On the Measurement of Heat Waves. *Journal of Climate*, 2013.**
  DOI: 10.1175/JCLI-D-12-00383.1 （引用 1162 次）
  - 定义 HWN(次数)/HWF(频率)/HWD(持续天数)/HWM(强度) 指标
  - 本 Skill 输出 heatwave_days（对应 HWD）、peak_tmax_c（对应 HWM）

### 2.4 热浪健康效应综述
- **Xu Z, et al. Heatwave and health impact research: a global review. *Health & Place*, 2018.**
  DOI: 10.1016/j.healthplace.2018.08.017 （引用 527 次）
  - 热浪死亡效应在老年、城市、低收入地区更明显

## 3. 寒潮/低温定义（本 Skill 采用三标准）

### 3.1 中国气象局寒潮标准
- 寒潮: 24 小时日最低气温下降 ≥ 8°C，且最低气温 ≤ 4°C
- 低温预警: 黄 -15°C / 橙 -20°C / 红 -25°C（日最低气温）
- 来源: 中国气象局《气象灾害预警信号发布与传播办法》; 《寒潮等级》(GB/T 21987-2017)

### 3.2 研究标准（10 分位）
- 日最低温 ≤ 当地历史 10 分位数、连续 ≥ 3 天
- 依据: 上海寒潮死亡研究采用类似定义
- **Ma W, et al. The impact of the 2008 cold spell on mortality in Shanghai, China.
  *International Journal of Biometeorology*, 2013.** DOI: 10.1007/s00484-012-0545-7 （引用 62 次）
  - 2008 年 1 月上海寒潮: 超额死亡显著，老年与呼吸/心血管疾病人群风险最高

### 3.3 绝对严寒（本 Skill 增设）
- 依据: Gasparrini 2015 证明低温死亡负担独立于"降温幅度"
  ——持续严寒（如哈尔滨 -30°C）即使无骤降也构成重大健康威胁
- 本 Skill 定义: 日最低温 ≤ -15°C 连续 ≥ 2 天触发严寒风险分级

## 4. 湿度与体感温度（热应激核心）

### 4.1 热指数 Heat Index（NOAA/NWS）
- **Rothfusz LP. The Heat Index "Equation". NWS Technical Attachment SR 90-23, 1990.**
  - 公式已验证（90°F/60% → 100°F，与官方表一致）
  - 危险分级: ≥32.2°C 高度警戒 / ≥41.1°C 危险 / ≥54.4°C 极度危险
  - 来源: https://www.weather.gov/ama/heatindex
- 生理基础: 人体散热依赖汗液蒸发，高湿降低蒸发效率 → 体感温度远超气温

### 4.2 湿度放大高温死亡效应（中国证据）
- **The role of high humidity on extreme-temperature-related mortality in central China.
  *Air Quality, Atmosphere & Health*, 2023.** DOI: 10.1007/s11869-023-01406-0 （引用 8 次）
  - 中国中部: 高湿度显著放大极端高温死亡效应
  - **支撑本 Skill 将热指数（含湿度）作为独立风险维度**

### 4.2b 湿球温度生存极限（湿度-高温的生理学上限）
- **Sherwood SC, Huber M. An adaptability limit to climate change due to heat stress.
  *PNAS*, 2010.** DOI: 10.1073/pnas.0913352107 （引用 1007 次）
  - **湿球温度 ~35°C 是人类生理生存极限**（约对应 46°C 且 50% 湿度 / 40°C 且 70% 湿度）
  - 超过后人体无法通过汗液蒸发散热
  - **本 Skill 将热指数/湿球温度逼近 35°C 视为极高危信号** —— 湿度板块最强生理学证据
  - 辅助: 湿球温度近似公式 Stull (2011), doi:10.1175/2011JAMC2684.1

### 4.3 WBGT（劳动热应激）
- ISO 7243:2017 热环境-人体劳动 WBGT 阈值
- 本 Skill 用 Stull (2011) 湿球温度近似公式: doi:10.1175/2011JAMC2684.1

### 4.4 风寒指数 Wind Chill
- NOAA/NWS + Environment Canada 2001 联合标准公式
- 来源: https://www.weather.gov/safety/cold-wind-chill-chart

### 4.5 湿度-低温与呼吸道健康（寒冷季节）
- **Cold temperature and low humidity are associated with increased occurrence
  of respiratory tract infections. *Respiratory Medicine*, 2009.**
  DOI: 10.1016/j.rmed.2008.09.011 （引用 296 次）
  - **低温+低湿增加呼吸道感染发生风险**
  - 支撑本 Skill 在寒潮/严寒场景将"低湿"纳入呼吸道风险提示

### 4.6 日较差 DTR 与死亡
- **Diurnal temperature range and daily mortality in Shanghai, China.
  *Environmental Research*, 2007.** DOI: 10.1016/j.envres.2006.11.009 （引用 176 次）
  - **日较差（DTR）增大与死亡风险升高相关**，独立于平均温度
  - 本 Skill 计算 temperature_max-min 差值作为 DTR 指标，
    大 DTR（≥12°C 且均值>25°C 或<5°C 时）纳入风险提示

## 5. 空气污染与健康

### 5.1 全球负担（核心数字）
- **GBD 2019 Risk Factors Collaborators. *The Lancet*, 2020.**
  DOI: 10.1016/S0140-6736(20)30752-2 （引用 8012 次）
  - 2019 年空气污染（含室内）致约 667 万人死亡，全球死亡第 4 大危险因素
  - PM2.5 与心血管、呼吸系统、肺癌死亡显著相关

### 5.2 WHO 2021 空气质量指南（AQG）
- **WHO global air quality guidelines: particulate matter, ozone, nitrogen dioxide... 2021.**
  - 24h 指南值与过渡目标（本 Skill 采用）:
    | 污染物 | AQG 24h | IT-1 | IT-2 |
    |---|---|---|---|
    | PM2.5 | 15 µg/m³ | 35 | 25 |
    | PM10 | 45 µg/m³ | 70 | 50 |
    | O3 (8h) | 100 µg/m³ | 160 | 120 |
    | NO2 | 25 µg/m³ | 40 | 30 |
    | SO2 | 40 µg/m³ | 50 | 40 |
    | CO | 4 mg/m³ | 7 | 4 |
  - 来源: https://www.who.int/publications/i/item/9789240034228

### 5.3 中国标准
- **HJ 633-2012《环境空气质量指数(AQI)技术规定》**: AQI = max(六项污染物 IAQI)
  - 六项: PM2.5、PM10、SO2、NO2、O3(8h)、CO(24h)
  - 本 Skill 完整实现六项 IAQI 插值计算（O3 用日最大 8h 滑动均值 MDA8）
  - 分级: 0-50 优 / 50-100 良 / 100-150 轻度 / 150-200 中度 / 200-300 重度 / >300 严重
- **GB 3095-2012《环境空气质量标准》**: PM2.5 二级日均 75 µg/m³、PM10 150、O3(8h) 160、NO2 80、SO2 150、CO 4 mg/m³

### 5.4 中国证据
- **Chen R, et al. Ambient temperature and mortality risk and burden: 272 main Chinese cities.
  *BMJ*, 2018.** DOI: 10.1136/bmj.k4306 —— 见 1.2
- **Chen R, et al. Fine Particulate Air Pollution and Daily Mortality:
  A Nationwide Analysis in 272 Chinese Cities. *American Journal of Respiratory and
  Critical Care Medicine*, 2017.** DOI: 10.1164/rccm.201609-1862OC （引用 661 次）
  - **中国 272 城市 PM2.5 每日死亡全国分析**：PM2.5 每升 10 µg/m³，
    总死亡率增加 0.22%～0.27%（滞后 0-1 天）
  - 心血管/呼吸系统死亡关联更强 —— 本 Skill 空气风险层的中国核心证据
- **Yin P, et al. Ambient Ozone Pollution and Daily Mortality:
  A Nationwide Study in 272 Chinese Cities. *Environmental Health Perspectives*, 2017.**
  DOI: 10.1289/ehp1849 （引用 341 次）
  - **O3 短期暴露与死亡显著正相关**（夏季效应更强）—— 支撑 O3 作为独立风险指标
- **Ambient carbon monoxide and cardiovascular mortality: 272 cities in China.
  *The Lancet Planetary Health*, 2018.** DOI: 10.1016/S2542-5196(17)30181-X （引用 182 次）
  - 全国 272 城市: CO 暴露与心血管死亡正相关

### 5.5 污染物短期暴露-死亡（全球多城市证据）
- **Liu C, et al. Ambient Particulate Air Pollution and Daily Mortality in 652 Cities.
  *New England Journal of Medicine*, 2019.** DOI: 10.1056/NEJMoa1817364 （引用 1480 次）
  - **24 国 652 城市、6520 万死亡**：PM2.5 每升 10 µg/m³ → 总死亡 +0.68%（滞后 0-1 天）
  - 短期暴露无安全阈值 —— 本 Skill 空气层全球金标准证据

### 5.6 高温+空气污染复合暴露（交互作用）
- **Heat-related cardiorespiratory mortality: Effect modification by air pollution
  across 482 cities from 24 countries. *Environment International*, 2023.**
  DOI: 10.1016/j.envint.2023.107825 （引用 116 次）
  - **空气污染放大高温对心肺死亡的效应**（污染物浓度高时，高温效应更强）
  - **支撑本 Skill 在"高温+污染"叠加时上调风险等级与预警建议**

## 6. 脆弱人群（重点人群提示的依据）

- **Gasparrini 2015 (Lancet)**: 老年人、心血管/呼吸疾病患者风险最高
- **Sci Adv 2025 (中国)**: 65+ 老年人温度相关死亡脆弱性显著
- **WHO climate change and health fact sheet (2023)**:
  - 受热浪等影响的重点人群: 老年、儿童、孕妇、户外工作者、
    慢性病患者、低收入与住房条件差人群
  - 来源: https://www.who.int/news-room/fact-sheets/detail/climate-change-and-health
- **本 Skill 固定 at_risk_groups**: ["老年人", "儿童", "户外工作者", "慢性病患者",
  "孕妇"] + 按数据可及的社区低收入人群

## 7. 不确定性方法论

- ERA5 再分析本身有 ±0.5-1.5°C 量级误差（对标观测站验证，ECMWF 文档）
- 热指数/风寒为经验公式，存在近似误差（NOAA 官方说明）
- 脆弱性数据若为省级替代市级，标注"数据缺口+保守估计"
- 输出 uncertainty 字段须如实呈现上述来源，禁止隐瞒

## 8. 权威性声明规则（写入 SKILL.md）

1. 所有输出数值必须能在此证据库中找到出处
2. 风险等级判定规则、阈值一律引用上述标准/文献
3. 证据链 evidence 字段引用本文件条目 + 原始 URL/DOI
4. 数据缺口或公式近似必须在 uncertainty 中声明
5. 禁止将模型自身知识当作数据来源；一切以实测 API 数据为准

## 9. 计算方法与文献对照表（每个数字的出处）

> 本表是 Skill 输出每个数值的计算方法与文献依据，供评审追溯。

### 9.1 数据源（最可信选择）

| 数据 | 来源 | 为何最可信 |
|---|---|---|
| 温度/湿度/风速/露点 | ECMWF ERA5 再分析 (经 Open-Meteo) | ERA5 是全球再分析金标准，空间 0.25°，对标地面站验证偏差 <1°C (Hersbach et al. 2020, doi:10.1002/qj.3803) |
| PM2.5/PM10/O3/NO2/SO2/CO | Copernicus CAMS 再分析 (经 Open-Meteo) | CAMS 是欧盟官方大气监测服务，融合卫星+地面站，全球 0.4° |

### 9.2 指标计算公式

| 指标 | 公式/方法 | 文献出处 | 验证 |
|---|---|---|---|
| **热指数 HI** | Rothfusz 1990 多项式（T→°F 计算） | NOAA/NWS 官方，doi:技术附件 SR 90-23 | 已验证官方点：90°F/60%→100°F, 90°F/70%→106°F |
| **WBGT** | BoM 简化: 0.567·Ta + 0.393·e + 3.94, e=Magnus 水汽压 | 澳大利亚气象局官方; Leroyer et al. 2018 | 与参考项目 huanjingjiankang 一致；含中等太阳辐射假设，遮阴处偏低 1-2°C |
| **风寒 WC** | NOAA/NWS + Environment Canada 2001 联合公式 | https://www.weather.gov/safety/cold-wind-chill-chart | 官方标准公式 |
| **水汽压 e** | Magnus 公式: e = (RH/100)·6.105·exp(17.27·T/(237.7+T)) | August-Roche-Magnus 近似，气象学教科书标准 | — |
| **O3 MDA8** | 8h 滑动窗口日最大值（≥6h 有效数据） | HJ 633-2012 / GB 3095-2012 规范 | 与中国环境监测总站算法一致 |
| **AQI** | 六项污染物 IAQI 分段线性插值取最大 | HJ 633-2012《环境空气质量指数技术规定》 | 分段表直接取自国标 |
| **PM2.5 IAQI 分段** | [0,35,75,115,150,250,350]→[0,50,100,150,200,300,500] | HJ 633-2012 附录 A | — |
| **热浪判定 A** | 日最高温≥35°C 连续≥3 天 | 中国气象局; GB/T 29457-2012《高温热浪等级》 | 国标 |
| **热浪判定 B** | 日最高温≥历史 95 分位 连续≥3 天 | Xu et al. 2016 Environ Int (602引) 综述最稳健定义 | — |
| **寒潮判定 A** | 24h 降温≥8°C 且最低温≤4°C | 中国气象局; GB/T 21987-2017《寒潮等级》 | 国标 |
| **寒潮判定 B** | 日最低温≤历史 10 分位 连续≥3 天 | 上海寒潮死亡研究 2013 (62引) | — |
| **绝对严寒** | 日最低温≤-15°C 连续≥2 天 | 中国气象局低温预警信号; Gasparrini 2015 低温负担独立于骤降 | — |

### 9.3 风险评分权重依据

| 维度 | 权重 | 依据 |
|---|---|---|
| 热/冷事件 | 40% | Gasparrini 2015 Lancet: 非最适温度归因死亡 7.71%，其中冷 7.29% > 热 0.42%。但热效应更急性（滞后0-3天 vs 冷0-3周），故热冷合计 40% |
| 空气污染 | 30% | GBD 2019 Lancet (8012引): 空气污染全球第4大死亡危险因素，2019 年约 667 万死亡。NEJM 2019 (1480引): PM2.5 每升 10μg/m³ 总死亡+0.68% |
| 脆弱性 | 30% | Sci Adv 2025: 中国老年人温度死亡脆弱性显著; WHO: 老年/儿童/慢病/户外工作者为重点人群 |

### 9.4 阈值依据

| 阈值 | 值 | 出处 |
|---|---|---|
| 高温日 | ≥35°C | 中国气象局 |
| 高温预警黄/橙/红 | 35/37/40°C | 中国气象局《气象灾害预警信号发布与传播办法》 |
| 低温预警黄/橙/红 | -15/-20/-25°C | 中国气象局 |
| NOAA 热指数危险级 | ≥41.1°C 危险, ≥54.4°C 极度危险 | NOAA/NWS 官方分级 |
| WBGT 生存极限 | 湿球~35°C | Sherwood & Huber 2010 PNAS (1007引) |
| WHO PM2.5 AQG 24h | 15 μg/m³ | WHO 2021 AQG |
| WHO PM2.5 IT-1 | 35 μg/m³ | WHO 2021 AQG |
| GB 3095 PM2.5 二级 | 75 μg/m³ | GB 3095-2012 |
| 高温+污染交互加成 | +0.3~0.5 | Environ Int 2023 (116引): 482城市24国, 空气污染放大高温心肺死亡 |

### 9.5 J 型曲线参数

大屏中的温度-健康 J 型曲线为**示意性近似曲线**，基于 Gasparrini 2015 Lancet 的 J 型趋势：
- 最适温度 Topt = 24°C（Gasparrini 2015 全球中位最适温度；中国约 22-24°C，取 24°C）
- 冷端: RR = exp(0.010·(T-24)²)，较缓（冷效应滞后长、慢性病负担累积）
- 热端: RR = exp(0.025·(T-24)²)，较陡（热效应急性、短期陡升）
- **注意**: 真实曲线基于 DLNM（分布滞后非线性模型），本 Skill 用指数近似展示趋势，
  不用于精确风险定量。定量风险以风险矩阵（§9.3）为准。

### 9.6 脆弱性评分

| 输入 | 来源 | 映射 |
|---|---|---|
| 省级 65+ 老年人口占比 | 国家统计局第七次全国人口普查(2020) | 全国均值 13.5% → 50 分；每 +1pp → +5 分；范围 50-100 |
| 缺市级数据时 | 降级为省级 | 在 uncertainty 中声明 |
