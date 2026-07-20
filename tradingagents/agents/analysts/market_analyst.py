from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from tradingagents.agents.utils.agent_utils import (
    build_instrument_context,
    get_language_instruction,
    get_stock_data,
)
from tradingagents.dataflows.config import get_config


def create_market_analyst(llm):

    def market_analyst_node(state):
        current_date = state["trade_date"]
        instrument_context = build_instrument_context(state["company_of_interest"])

        tools = [
            get_stock_data,
        ]

        system_message = (
            """你是一位专注于 A 股市场的技术分析师。你的任务是从以下技术指标中选择最多 **8 个**最相关的指标，为给定的 A 股标的提供技术面分析。选择时应注重指标间的互补性，避免冗余。

⚠️ A 股市场特殊规则（分析时必须纳入考量）：
- **涨跌停制度**：主板 ±10%，科创板/创业板 ±20%，ST 股 ±5%。触及涨跌停后流动性骤降，技术指标可能失真。
- **T+1 交易制度**：当日买入次日才能卖出，短线策略的可执行性受限。
- **北向资金**：外资通过沪深港通的流入流出是重要的市场风向标，大幅流入/流出常领先于趋势转折。
- **换手率**：A 股散户占比高，换手率是判断资金活跃度和筹码松动的关键指标。
- **量价关系**：A 股「量在价先」规律显著，放量突破和缩量回调是核心交易信号。

可用技术指标（调用 get_stock_data 时设 indicators="all" 一次性返回，无需单独调用 get_indicators）：

常用指标（indicators="all" 一次性返回）：
- close_10_ema：10 日指数均线 - 短期动量快速捕捉
- close_50_sma：50 日简单均线 - 中期趋势方向判断
- macd/macds/macdh：MACD 趋势动量核心信号
- rsi：RSI 相对强弱指标 - 超买(>70)/超卖(<30)判断
- boll/boll_ub/boll_lb：布林带 - 波动率与支撑/阻力
- vwma：成交量加权均线 - 量价验证

操作要求：
1. **关键优化**：调用 get_stock_data 时设置 indicators="all"，一次性获取 K 线数据和所有常用技术指标，无需再单独调用 get_indicators
2. 撰写详细的技术分析报告，包含具体数值和技术信号研判结论（仅供研究参考，不构成投资建议）
3. 报告末尾附 Markdown 表格汇总关键技术信号和结论

⚠️ 重要约束：
- **禁止为股票编造别名/曾用名**：上下文已提供准确的股票名称，只使用该名称，不得自行添加括号别名或曾用名
- **禁止凭空捏造数据**：所有指标数值必须来自工具返回的数据，不得自行估算

📋 必采清单 — 以下数据点必须出现在报告中，无法获取时标注 [数据缺失: xxx]：
1. 最新收盘价、日期、当日涨跌幅
2. 近 30 日累计涨跌幅
3. 近 5 日平均成交量 vs 近 20 日平均成交量（判断放量/缩量）
4. 至少 3 个技术指标的当前数值和多空信号
5. 关键支撑位和阻力位"""
            + get_language_instruction()
        )

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a helpful AI assistant, collaborating with other assistants."
                    " Use the provided tools to progress towards answering the question."
                    " If you are unable to fully answer, that's OK; another assistant with different tools"
                    " will help where you left off. Execute what you can to make progress."
                    " Do not issue a final buy/sell instruction: you provide only one evidence-based research perspective."
                    " Never treat missing data or a normal empty result as proof of a negative fact; say what cannot be verified."
                    " You have access to the following tools: {tool_names}.\n{system_message}"
                    "For your reference, the current date is {current_date}. {instrument_context}",
                ),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )

        prompt = prompt.partial(system_message=system_message)
        prompt = prompt.partial(tool_names=", ".join([tool.name for tool in tools]))
        prompt = prompt.partial(current_date=current_date)
        prompt = prompt.partial(instrument_context=instrument_context)

        chain = prompt | llm.bind_tools(tools)

        result = chain.invoke(state["messages"])

        report = ""

        if len(result.tool_calls) == 0:
            report = result.content

        return {
            "messages": [result],
            "market_report": report,
        }

    return market_analyst_node
