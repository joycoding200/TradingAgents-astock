# Issue #6: 关键财务数据缺失

- **日期**: 2026-07-15
- **状态**: ✅ 已修复

## 问题

用户在阿里云服务器跑股票分析时，基本面报告里关键财务数据大面积缺失（EPS/ROE/净利润/营收/资产负债表/现金流/利润表/一致预期 EPS），analyst 标注 `[数据缺失: xxx]`。

## 根因

三个独立的代码 bug 叠加，均因各数据源 try/except 静默吞错，只在日志留 warning：

### Bug 1: mootdx 财务字段名错配（`a_stock.py` get_fundamentals）

`get_fundamentals` 的 `field_map` 用英文键名 `eps/bvps/roe/profit/income` 去 mootdx `client.finance()` 返回里取值，但 mootdx 返回的 F10 概况列名是**拼音缩写**（`jinglirun=净利润` / `zhuyingshouru=主营收入` / `meigujingzichan=每股净资产` ...），英文键全部不存在，仅 `liutongguben/zongguben` 命中。导致 EPS/ROE/净利润/营收结构性丢失。mootdx 无 `eps/roe` 直字段。

### Bug 2: 新浪财报三表解析 key 错误（`a_stock.py` _get_financial_report_sina）

代码用 `result.data.<source_type>`（`lrb`/`fzb`/`llb`）取数，但新浪 API 实际结构是 `result.data.report_list = {日期YYYYMMDD: {data: [{item_title, item_value, ...}]}}`，`lrb`/`fzb`/`llb` key 不存在，恒返回空。导致资产负债表/现金流/利润表全部 "No data found"。

### Bug 3: pandas 3.0 read_html 破坏性变更（`a_stock.py` _ths_eps_forecast）

`pd.read_html(r.text)` 在 pandas 3.0 不再接受裸 HTML 字符串，会当文件路径 `open()`，抛 `FileNotFoundError`。导致同花顺 EPS 一致预期崩溃，`get_profit_forecast` 整体失效，`get_fundamentals` 的一致预期段缺失。pandas 2.x 不受影响（2.1+ 起为 DeprecationWarning，3.0 强制）。

## 修复

- **Bug 1**: `field_map` 改用拼音字段，并推算 `EPS = jinglirun/zongguben`、`ROE = jinglirun/jingzichan*100`。
- **Bug 2**: 重写 `_get_financial_report_sina`，从 `report_list[日期]["data"]` 提取 `item_title/item_value`，构造「行=报告期、列=项目名」的 DataFrame，保留 curr_date/annual 过滤。
- **Bug 3**: `pd.read_html(io.StringIO(r.text))`，顶部加 `import io`。兼容 pandas 2.x/3.0。

## 验证

实跑 600519：`get_fundamentals` 含 `EPS (derived): 217.9259` / `ROE (%) (derived): 10.06` / `Net Profit: 272425120000.0` / `Revenue: 539092480000.0`；三表（balance_sheet/cashflow/income_statement）均非空；`get_profit_forecast` 返回 `FY2026 EPS=68.83 (46 analysts)` + Forward PE 18.1x + PEG 3.29。回归测试 `tests/test_astock_fundamentals_fix.py` 5 例全过。

## 关于主力资金

`get_fund_flow`（东财 push2）接口本身可用，实测返回完整实时分钟级 + 20 日历史资金流。本机偶发 `ProxyError` 是代理/网络环境问题，阿里云服务器国内直连稳定，无需改代码。
