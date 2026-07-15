"""回归测试：关键财务数据缺失的 3 个 bug 修复。

覆盖：
- bug1: get_fundamentals 从 mootdx 拼音字段正确提取并推算 EPS/ROE
- bug2: _get_financial_report_sina 从 report_list 正确解析三表
- bug3: _ths_eps_forecast 用 io.StringIO 兼容 pandas 3.0 read_html
"""
import pandas as pd


def _fake_mootdx_finance_row():
    return pd.DataFrame([{
        "zongguben": 1_250_000_000.0,
        "liutongguben": 1_250_000_000.0,
        "zhuyingshouru": 539_000_000_000.0,
        "jinglirun": 272_000_000_000.0,
        "yingyelirun": 375_000_000_000.0,
        "meigujingzichan": 216.0,
        "jingyingxianjinliu": 269_000_000_000.0,
        "zongzichan": 3_199_000_000_000.0,
        "jingzichan": 2_700_000_000_000.0,
    }])


class _FakeMootdxClient:
    def finance(self, symbol):
        return _fake_mootdx_finance_row()


class _FakeResp:
    """模拟 requests.Response：json() 与 text。"""

    def __init__(self, payload=None, text=""):
        self._payload = payload
        self.text = text
        self.encoding = "gbk"

    def json(self):
        return self._payload


def test_get_fundamentals_derives_eps_roe_from_pinyin_fields(monkeypatch):
    """bug1: mootdx 字段为拼音缩写，应提取净利润/营收并推算 EPS/ROE。"""
    from tradingagents.dataflows import a_stock

    monkeypatch.setattr(a_stock, "_get_mootdx_client", lambda: _FakeMootdxClient())
    monkeypatch.setattr(a_stock, "_tencent_quote", lambda codes: {})
    monkeypatch.setattr(a_stock, "_ths_eps_forecast", lambda code: pd.DataFrame())

    out = a_stock.get_fundamentals("600519", "2026-07-14")

    assert "Net Profit (净利润): 272000000000.0" in out
    assert "Revenue (主营收入): 539000000000.0" in out
    assert "EPS (derived): 217.6000" in out        # 272e9 / 1.25e9
    assert "ROE (%) (derived): 10.07" in out        # 272e9 / 2.7e12 * 100
    assert "Book Value Per Share (每股净资产): 216.0" in out


def test_get_financial_report_sina_parses_report_list(monkeypatch):
    """bug2: 新浪数据在 result.data.report_list[日期]['data']，应解析为 DataFrame。"""
    from tradingagents.dataflows import a_stock

    fake_json = {
        "result": {
            "data": {
                "report_list": {
                    "20260331": {"data": [
                        {"item_title": "营业收入", "item_value": "53909252220.51"},
                        {"item_title": "营业成本", "item_value": "10000000000.00"},
                    ]},
                    "20251231": {"data": [
                        {"item_title": "营业收入", "item_value": "50000000000.00"},
                    ]},
                }
            }
        }
    }
    monkeypatch.setattr(a_stock._requests, "get", lambda *a, **k: _FakeResp(fake_json))

    df = a_stock._get_financial_report_sina("600519", "利润表", "quarterly", None)

    assert not df.empty
    assert "报告日" in df.columns
    assert "营业收入" in df.columns
    assert len(df) == 2
    # 降序：最新报告期在前
    assert df.iloc[0]["报告日"] == pd.Timestamp("2026-03-31")
    assert df.iloc[0]["营业收入"] == "53909252220.51"


def test_get_financial_report_sina_annual_filter(monkeypatch):
    """bug2: annual 频率应只保留 12 月末年报。"""
    from tradingagents.dataflows import a_stock

    fake_json = {
        "result": {
            "data": {
                "report_list": {
                    "20260331": {"data": [{"item_title": "营业收入", "item_value": "1"}]},
                    "20251231": {"data": [{"item_title": "营业收入", "item_value": "2"}]},
                    "20250930": {"data": [{"item_title": "营业收入", "item_value": "3"}]},
                }
            }
        }
    }
    monkeypatch.setattr(a_stock._requests, "get", lambda *a, **k: _FakeResp(fake_json))

    df = a_stock._get_financial_report_sina("600519", "利润表", "annual", None)
    assert len(df) == 1
    assert df.iloc[0]["报告日"] == pd.Timestamp("2025-12-31")


def test_get_financial_report_sina_empty_report_list(monkeypatch):
    """bug2: report_list 为空时应返回空 DataFrame（不抛异常）。"""
    from tradingagents.dataflows import a_stock

    monkeypatch.setattr(
        a_stock._requests, "get", lambda *a, **k: _FakeResp({"result": {"data": {}}})
    )
    df = a_stock._get_financial_report_sina("600519", "利润表", "quarterly", None)
    assert df.empty


def test_ths_eps_forecast_stringio_compat(monkeypatch):
    """bug3: pandas 3.0 read_html 不再接受裸 HTML 字符串，应用 io.StringIO 包装。"""
    from tradingagents.dataflows import a_stock

    html = (
        "<html><body><table>"
        "<tr><th>年度</th><th>机构数</th><th>最小</th><th>均值</th><th>最大</th></tr>"
        "<tr><td>2026</td><td>46</td><td>66.27</td><td>68.83</td><td>77.85</td></tr>"
        "</table></body></html>"
    )
    monkeypatch.setattr(a_stock._requests, "get", lambda *a, **k: _FakeResp(text=html))

    df = a_stock._ths_eps_forecast("600519")
    assert not df.empty
