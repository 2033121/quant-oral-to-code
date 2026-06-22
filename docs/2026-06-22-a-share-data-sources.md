# A 股数据获取路线研究

更新日期：2026-06-22

## 目标

为 `quant-oral-to-code` skill 提供一套现实可用的 A 股数据获取路线，满足以下场景：

- 用户没有你的本地量化数据栈
- 用户是量化小白，只能接受尽量少配置的方案
- skill 需要在“继续生成回测代码”和“先去准备数据再回来”之间做出明确分流

## 推荐分层

### 第一层：默认优先接入，适合新手

- `AKShare`
  - 适合：A 股历史行情、ETF、指数、资金流等快速拉取
  - 特点：Python 生态成熟，文档全，免注册起步快
  - 风险：依赖公开网站接口，偶发失效要能降级
  - 来源：[GitHub](https://github.com/akfamily/akshare) / [文档](https://akshare.akfamily.xyz/)

- `efinance`
  - 适合：股票/ETF/资金流/龙虎榜等东财系数据
  - 特点：接口直观，适合快速出历史行情样例
  - 风险：依赖公开网站接口，可能限流
  - 来源：[GitHub](https://github.com/Micro-sheep/efinance) / [文档](https://efinance.readthedocs.io)

- `AData`
  - 适合：A 股交易相关数据、概念、指数、北向等
  - 特点：强调多数据源融合、支持代理
  - 风险：研究生态没有 AKShare 那么通用，但做数据落地很实用
  - 来源：[GitHub](https://github.com/1nchaos/adata) / [文档](https://adata.30006124.xyz/)

- `baostock`
  - 适合：日周月线和一部分基础财务、指数成分补充
  - 特点：匿名登录，接口简单
  - 风险：仓库很老，不适合作为唯一主源，更适合兜底或补充
  - 来源：[GitHub](https://github.com/shimencaiji/baostock) / [官网](https://www.baostock.com/)

### 第二层：用户愿意注册后再升级

- `TuShare Pro`
  - 适合：更全的行情与财务研究数据
  - 特点：生态成熟，很多量化用户熟悉
  - 风险：通常需要注册与 token，部分能力依赖 Pro 规则
  - 来源：[GitHub](https://github.com/waditu/tushare) / [官网](https://tushare.pro/)

- `JQData SDK`
  - 适合：研究级行情、平台化数据与后续研究接线
  - 特点：官方 SDK、数据覆盖强、适合长期研究
  - 风险：需要账号认证或试用/购买流程，不适合零门槛默认入口
  - 来源：[GitHub](https://github.com/JoinQuant/jqdatasdk) / [文档](https://www.joinquant.com/help/api/doc?name=JQDatadoc)

### 第三层：轻量快照或兜底

- `easyquotation`
  - 适合：实时全市场快照、轻量行情探测
  - 不适合：默认承担研究级历史回测主源
  - 来源：[GitHub](https://github.com/shidenggui/easyquotation)

- `Ashare`
  - 适合：极简单文件方式取日线/分钟线
  - 不适合：作为长期维护的唯一研究主源
  - 来源：[GitHub](https://github.com/mpquant/Ashare)

## skill 的建议分流逻辑

1. 有本地研究级数据栈：直接走 `full_research_mode`
2. 没有本地数据，但用户愿意零配置起步：优先生成 `AKShare / efinance / AData` 取数脚本
3. 用户明确愿意注册账号：允许改走 `TuShare Pro / JQData SDK`
4. 只需要实时快照或补几根 bar：允许走 `easyquotation / Ashare`
5. 上述都不满足：进入 `DATA_REQUIRED` 截断，只交付：
   - `strategy_spec.json`
   - `translation_trace.json`
   - `data_contract.json`
   - `data/provider_setup.md`
   - `data/fetch_data.py` 或明确的手工导出说明

## 代码样例

### 1. AKShare：拉 A 股日线历史

```python
import akshare as ak
import pandas as pd


def fetch_with_akshare(symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
    df = ak.stock_zh_a_hist(
        symbol=symbol,
        period="daily",
        start_date=start_date.replace("-", ""),
        end_date=end_date.replace("-", ""),
        adjust="qfq",
    )
    df = df.rename(
        columns={
            "日期": "trade_date",
            "开盘": "open",
            "收盘": "close",
            "最高": "high",
            "最低": "low",
            "成交量": "vol",
            "成交额": "amount",
            "涨跌幅": "pct_chg",
            "换手率": "turnover",
        }
    )
    keep = [c for c in ["trade_date", "open", "high", "low", "close", "vol", "amount", "pct_chg", "turnover"] if c in df.columns]
    return df[keep].copy()
```

### 2. efinance：拉 A 股历史行情

```python
import efinance as ef
import pandas as pd


def fetch_with_efinance(symbol: str) -> pd.DataFrame:
    df = ef.stock.get_quote_history(symbol)
    df = df.rename(
        columns={
            "日期": "trade_date",
            "开盘": "open",
            "收盘": "close",
            "最高": "high",
            "最低": "low",
            "成交量": "vol",
            "成交额": "amount",
            "涨跌幅": "pct_chg",
            "换手率": "turnover",
        }
    )
    keep = [c for c in ["trade_date", "open", "high", "low", "close", "vol", "amount", "pct_chg", "turnover"] if c in df.columns]
    return df[keep].copy()
```

### 3. baostock：匿名登录拉日线

```python
import baostock as bs
import pandas as pd


def fetch_with_baostock(symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
    lg = bs.login(user_id="anonymous", password="123456")
    if lg.error_code != "0":
        raise RuntimeError(f"baostock login failed: {lg.error_msg}")

    rs = bs.query_history_k_data_plus(
        symbol,
        "date,open,high,low,close,volume,amount,turn,pctChg",
        start_date=start_date,
        end_date=end_date,
        frequency="d",
        adjustflag="2",
    )

    rows = []
    while rs.error_code == "0" and rs.next():
        rows.append(rs.get_row_data())
    bs.logout()

    df = pd.DataFrame(rows, columns=rs.fields)
    return df.rename(columns={"date": "trade_date", "volume": "vol"}).copy()
```

### 4. TuShare Pro：用户提供 token 后取日线

```python
import tushare as ts
import pandas as pd


def fetch_with_tushare(token: str, ts_code: str, start_date: str, end_date: str) -> pd.DataFrame:
    ts.set_token(token)
    pro = ts.pro_api()
    df = pro.daily(
        ts_code=ts_code,
        start_date=start_date.replace("-", ""),
        end_date=end_date.replace("-", ""),
    )
    return df.rename(
        columns={
            "trade_date": "trade_date",
            "open": "open",
            "high": "high",
            "low": "low",
            "close": "close",
            "vol": "vol",
            "amount": "amount",
            "pct_chg": "pct_chg",
        }
    ).copy()
```

### 5. JQData SDK：用户账号认证后取价格

```python
import jqdatasdk as jq
import pandas as pd


def fetch_with_jqdata(username: str, password: str, jq_code: str, start_date: str, end_date: str) -> pd.DataFrame:
    jq.auth(username, password)
    df = jq.get_price(
        jq_code,
        start_date=start_date,
        end_date=end_date,
        frequency="daily",
        fields=["open", "close", "high", "low", "volume", "money"],
    )
    df = df.reset_index().rename(
        columns={
            "index": "trade_date",
            "volume": "vol",
            "money": "amount",
        }
    )
    return df.copy()
```

## 当自动取数失败时，skill 应该怎么做

### 可继续自动化的失败

- 缺少包：告诉用户安装命令，并生成 `fetch_data.py`
- 缺 token / 账号：切到 `TuShare Pro` 或 `JQData SDK` 引导页，并保留 `fetch_data.py`
- 公开源限流：建议切换 `AKShare -> efinance -> AData -> baostock`

### 必须截断的情况

- 用户没有任何行情数据，也不愿安装或注册
- 关键字段缺失且无法自动映射
- 只拿到实时快照，却想做长期历史回测
- 数据复权口径、时间排序、样本区间不明确

此时只能输出：

- `DATA_REQUIRED`
- 当前缺的字段/数据类型
- 推荐的数据源路线
- 对应获取代码或手工导出说明

## 非 GitHub 自动取数路线

如果 GitHub 开源抓数路线不稳定，后备方法按优先级建议为：

1. 用户已有券商、通达信、同花顺、东方财富客户端：
   - 直接导出 CSV/Excel
   - skill 负责列映射、清洗，并统一导入 DuckDB
2. 用户愿意注册数据平台：
   - `TuShare Pro`
   - `JQData SDK`
3. 用户已有本地数据库：
   - 让 skill 读取现有 `DuckDB / SQLite / Parquet`，再统一归并到标准 DuckDB
4. 仍然无法提供数据：
   - 停在 `strategy_spec + data_contract + fetch_plan`

## 结论

对这个 skill 来说，最稳的默认路线不是“先假设用户有数据”，而是：

- 默认先准备 `AKShare / efinance / AData` 取数模板
- 明确支持 `TuShare Pro / JQData SDK` 升级路线
- 允许 `easyquotation / Ashare` 做快照补位
- 允许用户导入券商或客户端导出的 `CSV/Excel`，但导入后必须统一规范化落盘为 `DuckDB`
- `DuckDB` 作为唯一标准存储：
  - 适合 A 股历史行情这类分析型读多写少场景
  - 单文件交付，对量化新手最省心
  - 比 `SQLite` 更适合列式分析与批量回测
  - 比只存 `Parquet` 更容易做统一入口、表管理和元数据约束
- 生成器默认约束：
  - `fetch_data.py` 写入 `data/normalized/market.duckdb`
  - `run_backtest.py` 只读取 `data/normalized/market.duckdb`
  - `data_contract.json` 中 `storage_format` 固定为 `duckdb`
- `CSV/JSON/Parquet/SQLite` 只作为原始输入、交换格式或调试快照，不作为默认回测读取源
- 任何真实数据不可得时，必须进入 `DATA_REQUIRED` 截断，而不是产出伪回测结果
