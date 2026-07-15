# Issue #7: 概念板块/股东数据接口迁移

- **日期**: 2026-07-15
- **状态**: ✅ 已修复（v0.2.20）

## 问题

数据质量门控显示基本面 [C] 5 处、游资 [B] 2 处、解禁 [C] 3 处数据缺失。排查 3 个独立接口：

- `get_concept_blocks`：返回 `Baidu PAE error: ResultCode=403`
- `get_insider_transactions`：`'dict' object has no attribute 'strip'` 崩溃
- `get_industry_comparison`：本地实测正常（07-15 报告缺失属偶发）

## 根因

### get_concept_blocks：百度 PAE 接口下线

百度 PAE `finance.pae.baidu.com/api/getrelatedblock` 返回 `ResultCode=403`。CLAUDE.md 已记录百度 PAE **资金流**接口（fundsortlist/fundflow）v0.2.7 下线，但 `get_concept_blocks` 用的 `getrelatedblock`（概念板块归属端点）随后也下线，未被迁移。

### get_insider_transactions：mootdx F10 返回类型变更 + 栏目缺失

两个问题叠加：
1. mootdx 0.11.7 `client.F10(name="股东研究")` 返回 **dict**（非 str），代码对 dict 调 `.strip()` 崩溃。
2. 更深层：`F10C` 栏目目录显示通达信 TCP F10 对个股**只返回"最新提示"一个栏目**，根本没有"股东研究"栏目。`name` 不匹配时 F10 回退返回 `{'最新提示': str}`。即 mootdx F10 注定拿不到股东数据。

### get_industry_comparison：非 bug

东财 push2 `clist/get`（`m:90+t:2` 行业板块）本地实测正常返回 100 个行业。07-15 报告缺失是东财连接偶发或 LLM 未调用该工具，代码无需改动。

## 修复

- **get_concept_blocks**：迁移至东财 F10 `CoreConception/PageAjax?code=SZ{code}`，解析 `ssbk`（所属板块：行业/地域/风格/概念，如 CPO概念/算力概念）+ `hxtc`（核心题材要点）。删除失效的 `_BAIDU_PAE_HEADERS`。注：东财 ssbk 不含板块当日涨幅（百度原有），仅返回板块归属。
- **get_insider_transactions**：迁移至东财 datacenter `RPT_F10_EH_HOLDERS`，按 `END_DATE` 降序取最新一期十大股东（HOLDER_NAME/HOLD_NUM/HOLD_NUM_RATIO/HOLD_NUM_CHANGE/IS_HOLDORG）。

## 验证

实跑 300308：
- `get_concept_blocks`：返回 29 个板块（通信/山东板块/光通信模块/算力概念/CPO概念/F5G概念/5G概念...）+ 核心题材要点，不再 403。
- `get_insider_transactions`：返回 2026-03-31 最新一期十大股东（山东中际投资控股 10.93%/不变、香港中央结算 6.97%/+1563万、王伟修 6.28%/个人），不再崩溃。

回归测试 `tests/test_astock_interface_fix.py` 2 例通过；全量 142 passed。

## 接口发现备忘

- 东财 F10 `CoreConception/PageAjax` 返回 `{ssbk: 所属板块列表, hxtc: 核心题材要点}`，是个股概念板块的可靠数据源。
- 东财 datacenter `RPT_F10_EH_HOLDERS` 返回十大股东（需按 END_DATE 排序取最新一期，默认返回最早记录）。
- mootdx 0.11.7 `F10(name=)` 仅当 name 精确匹配 `F10C()` 返回的栏目名时返回 str，否则回退 dict；通达信 TCP F10 对个股只暴露"最新提示"栏目。
