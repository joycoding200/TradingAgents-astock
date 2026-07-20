# v0.3.0 实施计划

基于**投资研究员** + **多智能体系统架构师** + **软件架构师** 三位 Agent 联合审查输出。

---

## 一、满分路径总览

当前评分：**80/100（B+）**

```
Phase 1: 5xP0 提示词优化（2-3h，零代码风险）  ->  90/100
Phase 2: 4xP1 低风险代码（3-4h）              ->  94/100
Phase 3: 2xP1 State+图拓扑变更（4-6h）        ->  97/100
Phase 4: 3xP2/P1 图拓扑扩展（4-6h）           -> 100/100
```

---

## 二、投资研究员：五项维度改进建议

### 维度一：数据完整性（18/20 -> 20/20）

| 建议 | 类型 | 优先级 |
|------|------|--------|
| 1.1 政策必采降级：policy_analyst.py 将宏观/监管/地方政策从必采改为尽力采集 | 提示词 | P0 |
| 1.2 政策新闻聚合工具：a_stock.py 新增 get_policy_news()，定向抓取政策源 | 代码 | P1 |
| 1.3 数据约束执行链：state 新增 failed_domains，下游强制执行 | 代码+提示词 | P1 |

### 维度二：分析深度（16/20 -> 20/20）

| 建议 | 类型 | 优先级 |
|------|------|--------|
| 2.1 跨报告交叉引用：7个分析师 prompt 加交叉验证（不能引用并行分支不存在的内容） | 提示词 | P0 |
| 2.2 多周期趋势对比：fundamentals/market analyst 要求对比 YoY/QoQ 趋势 | 提示词 | P0 |
| 2.3 行业对比定量化：计算目标公司与行业中位数的偏离度百分比 | 提示词 | P1 |

### 维度三：逻辑严密性（15/20 -> 20/20）

| 建议 | 类型 | 优先级 |
|------|------|--------|
| 3.1 矛盾检测模块：分析师报告生成后、质量门控前新增轻量矛盾检测节点 | 代码 | P1 |
| 3.2 数据约束强制执行：将约束从建议改为辩论规则（配套1.3） | 提示词 | P1 |
| 3.3 复审输出结构化：quality_gate LLM 复审输出 JSON 格式 | 代码 | P2 |

### 维度四：可操作性（16/20 -> 20/20）

| 建议 | 类型 | 优先级 |
|------|------|--------|
| 4.1 投资启示章节：每个分析师报告末尾增加投资启示章节 | 提示词 | P0 |
| 4.2 交易框架结构化：trader.py 要求入场条件/仓位/止损/持有期/出场结构化 | 提示词 | P1 |
| 4.3 概率情景分析：PM 前增加场景分析节点（乐观/基准/悲观+概率） | 代码+提示词 | P1 |

### 维度五：风险覆盖（15/20 -> 20/20）

| 建议 | 类型 | 优先级 |
|------|------|--------|
| 5.1 A股报告注入风险辩论：3个risk debater 更积极使用 policy/hot_money/lockup | 提示词 | P0 |
| 5.2 尾端风险分析：conservative_debator 要求思考极端但可能发生的风险 | 提示词 | P1 |
| 5.3 风险相关性矩阵：风险辩论后新增节点评估风险间相关性 | 代码 | P2 |

---

## 三、多智能体系统架构师：架构影响分析

### 7 个关键陷阱警告

| # | 陷阱 | 影响改动 |
|---|------|---------|
| 1 | **并行分支不能交叉引用报告**：7个分析师并行，生成报告时其他6个report还是空字符串 | P0-2.1 |
| 2 | **新增节点6文件注册**：矛盾检测/情景分析/风险矩阵虽非传统分析师，仍需注册6个文件 | P1-3.1, P1-4.3, P2-5.3 |
| 3 | **State字段必须.get()读取**：TypedDict反序列化旧检查点时不存在的字段直接索引会抛异常 | P1-1.3 |
| 4 | **东财端点铁律**：新增工具若涉及东财必须走_em_get() | P1-1.2 |
| 5 | **Prompt改动验证**：改prompt必须用真实A股案例验证（铁律#9） | 所有P0 |
| 6 | **MiniMax thinking mode兼容**：P2-3.3结构化输出需try/except兜底降级 | P2-3.3 |
| 7 | **下游prompt补充覆盖**：新增state字段后8个agent必须手工补state.get() | P1-1.3 |

### 新增节点在 Graph 中的位置

```
Phase 1 (研究)              Phase 1.5 (校验)     Phase 2 (辩论与决策)
7 Analyst 并行             Contradiction        Bull/Bear -> RM -> Trader
(独立messages)       ->    Detector [3.1]  ->   -> Scenario Analyzer [4.3]
                           -> Quality Gate       -> Risk Debate (3方)
                              (含failed          -> Risk Correlation [5.3]
                               domains [1.3])    -> Portfolio Manager
```

### 新增节点注册清单（每个必须 6 文件）

| 文件 | P1-3.1 矛盾检测 | P1-4.3 情景分析 | P2-5.3 风险矩阵 |
|------|:---:|:---:|:---:|
| 节点 body | contradiction_detector.py | scenario_analyzer.py | risk_correlation.py |
| agent_states.py | +contradiction_analysis | +scenario_analysis | +risk_correlation_matrix |
| agents/__init__.py | 注册 | 注册 | 注册 |
| setup.py | add_node+add_edge | add_node+add_edge | add_node+add_edge |
| propagation.py | 初始值"" | 初始值"" | 初始值"" |
| trading_graph.py | _log_state序列化 | _log_state序列化 | _log_state序列化 |

---

## 四、软件架构师：逐项实现方案

### P0-1.1：政策必采降级

**文件**：`tradingagents/agents/analysts/policy_analyst.py` 第 41-47 行

将「必采清单 — 以下数据点必须出现在报告中，无法获取时标注 [数据缺失: xxx]」替换为「尽力采集清单 — 政策因时效性强、来源分散，以下数据点应尽力获取，确实无法获取时注明[未找到]」

### P0-2.1：跨报告交叉验证（7 个 analyst 文件）

每个文件在必采清单后、get_language_instruction() 前插入：
```
在报告末尾的投资启示章节，指出本报告结论与哪些其他分析维度存在潜在矛盾或相互印证关系。
```
注意：不能写参考其他分析师的报告（并行运行时不存在）。

### P0-2.2：多周期趋势对比

fundamentals_analyst.py：要求对比当前季度与过去4个季度、估值与3年历史分位数
market_analyst.py：要求对比20/60/250日均线位置、5/20日均量倍数、5/20/60日累计涨跌幅

### P0-4.1：投资启示章节（7 个 analyst 文件）

报告末尾附加投资启示章节（2-3句话），说明核心结论对投资决策的意义。

### P0-5.1：A股报告注入风险辩论（3 个 debater 文件）

aggressive_debator.py：政策扶持=最强看多论据，主力流入=强化momentum
conservative_debator.py：政策收紧=强化风险，游资撤退=降温信号，大额解禁=核心做空
neutral_debator.py：全面引用三个特化报告来平衡两方偏执

### P1-1.2：政策新闻聚合工具

新建 `tradingagents/agents/utils/policy_tools.py`，@tool 定义 get_policy_news
注册链 7 文件：a_stock.py(实现) -> interface.py -> policy_tools.py -> agent_utils.py -> policy_analyst.py -> trading_graph.py -> quality_ledger.py

### P1-1.3+3.2：数据约束执行链

agent_states.py 加 failed_domains: list[str]
propagation.py 初始化为 []
quality_gate.py 从 tool_execution_ledger 提取失败领域写入
下游 8 个 agent prompt 加强制执行语句

### P1-2.3：行业对比定量化

fundamentals_analyst.py 追加要求：计算 PE/营收增速/行业排名与行业中位数的偏离度百分比

### P1-3.1：矛盾检测模块

新建 contradiction_detector.py，读取所有 *_report 字段用轻量 LLM 扫描矛盾点
Graph 位置：所有 Analyst -> Contradiction Detector -> Quality Gate

### P1-4.2：交易框架结构化

schemas.py 的 TraderProposal 增加 entry_conditions/holding_period/exit_conditions 字段
render 函数同步增加渲染

### P1-4.3：概率情景分析节点

新建 scenario_analyzer.py，读取 trader_plan + 报告摘要，输出乐观/基准/熊市三种情景+概率
Graph 位置：Trader -> Scenario Analyzer -> Aggressive Analyst

### P1-5.2：尾端风险分析

conservative_debator.py 追加极端风险思考要求：政策黑天鹅/流动性危机/业绩暴雷/质押爆仓

### P2-3.3：复审输出结构化

schemas.py 新增 AnalystReview + QualityGateReview Pydantic 模型
quality_gate.py 解析 LLM 输出的 JSON 块，写入 structured_quality_review

### P2-5.3：风险相关性矩阵

新建 risk_correlation.py，分析 8 类风险两两相关性
Graph 位置：Neutral Analyst -> Risk Correlation -> PM（需修改 conditional_logic 路由）

---

## 五、新增 AgentState 字段总表

| 字段 | 类型 | 默认值 | 改动 | 说明 |
|------|------|--------|------|------|
| failed_domains | list[str] | [] | P1-1.3 | 数据获取失败的领域列表 |
| contradiction_analysis | str | "" | P1-3.1 | 跨报告矛盾检测结果 |
| scenario_analysis | str | "" | P1-4.3 | 三种概率情景分析 |
| structured_quality_review | dict | {} | P2-3.3 | 质量门控结构化评审 JSON |
| risk_correlation_matrix | str | "" | P2-5.3 | 风险相关性矩阵 |

所有新增字段必须：propagation.py 初始化 + 下游用 .get() 读取 + _log_state() 序列化

---

## 六、测试策略

回归测试：`pytest tests/ -v`（期望 197 passed + 44 subtests 不减少）

新增测试文件：
- tests/test_policy_news.py（P1-1.2）
- tests/test_contradiction_detector.py（P1-3.1）
- tests/test_scenario_analyzer.py（P1-4.3）
- tests/test_quality_gate_structured.py（P2-3.3）
- tests/test_risk_correlation.py（P2-5.3）

集成验证：import 链检查 + 新增工具调用测试 + 真实A股案例验证

---

## 七、实施顺序（依赖关系图）

```
Phase 1 (P0全部, 可并行, 2-3h)
  P0-1.1 / P0-2.1 / P0-2.2 / P0-4.1 / P0-5.1
      -> 90/100

Phase 2 (可并行, 3-4h)
  P1-1.2 / P1-2.3 / P1-4.2 / P1-5.2
      -> 94/100

Phase 3 (需串行, 4-6h)
  P1-1.3+3.2 (state变更) -> P1-3.1 (矛盾检测)
      -> 97/100

Phase 4 (可选, 可并行, 4-6h)
  P1-4.3 / P2-5.3 / P2-3.3
      -> 100/100

---

## 八、政策数据缺失背景（来源：原 PLAN_v0.3.0.md）

政策分析师有 3 项数据因接口缺失被标注为 `[数据缺失]`：

| 缺失项 | 要求来源 | 现状 | 可选数据源 |
|--------|---------|------|-----------|
| 宏观政策（降准/降息/LPR/MLF） | 分析师 prompt 要求 | 仅靠 get_news 搜索，命中率低 | 中国人民银行官网、东方财富宏观数据 |
| 监管政策（证监会 IPO/再融资/减持新规） | 分析师 prompt 要求 | 仅靠 get_news 搜索，命中率低 | 证监会官网公告、东方财富监管动态 |
| 地方政策（省/市产业扶持） | 分析师 prompt 要求 | 仅靠 get_news 搜索，命中率低 | 地方政府官网、产业基金公告 |

### 方案对比

| 选项 | 成本 | 收益 | 推荐 |
|------|------|------|------|
| A：保持现状，3 项从必采改为尽力采集 | 零改动 | 减少噪音 | **短期（P0-1.1）** |
| B：新增 3 个独立数据工具（央行/证监会/地方政策 API） | 高（维护 3 个不稳定源） | 数据完整 | 不推荐 |
| C：新增一个聚合政策新闻工具，定向抓取政策类网站 | 中（1 个新工具） | 覆盖大部分政策需求 | **中期（P1-1.2）** |

---

## 九、待评估项（来源：原 PLAN_v0.3.0.md）

| 项目 | 优先级 | 说明 |
|------|--------|------|
| 东财 F10 接口继续监控 | P0 | 见 issues/007，同源端点下线追踪 |
| 数据质量回归自动化 | P1 | 见 issues/008，每次数据层变更后自动运行回归测试 |
| Streamlit 升级兼容性 | P2 | Streamlit 迭代快，定期验证 |
| 快速分析模式优化 | P2 | 当前快速分析仍跑完整风控链，可评估裁剪 |
| 多模型 prompt 差异收敛 | P2 | 不同模型对同一 prompt 行为差异大，需系统性测试 |
```
