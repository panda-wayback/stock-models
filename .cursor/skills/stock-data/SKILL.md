---

## name: stock-data

description: 获取中国A股市场历史K线数据，支持日线、周线、月线和分钟线，自动缓存到本地。使用 baostock 数据源，支持前复权、后复权和不复权。当用户需要获取股票数据、K线数据、历史行情或进行回测数据准备时使用此技能。

# 股市数据获取

## 快速开始

使用 `DataHandler` 获取股票数据，支持自动缓存和增量更新。

```python
from utils.stock_data.data_handler import get_stock_data

# 获取日线数据
df = get_stock_data(
    symbol="000651",        # 股票代码（6位，自动识别市场）
    start_date="2020-01-01",
    end_date="2023-12-31",
    frequency="d"           # d=日线, w=周线, m=月线, 5/15/30/60=分钟线
)
```

## 数据源

项目使用 **BaoStock** 作为数据源：

- 免费、无需注册
- 支持历史K线数据
- 支持日线、周线、月线、分钟线
- 支持前复权、后复权、不复权

## 核心功能

### 1. 获取股票数据

**使用 DataHandler（推荐）**：

- 自动缓存到本地 `local_data/` 目录
- 按天分文件存储，支持增量更新
- 自动识别股票代码所属市场（上海/深圳/北京）

```python
from utils.stock_data.data_handler import get_stock_data

df = get_stock_data(
    symbol="000651",           # 6位代码或完整代码（如 sz.000651）
    start_date="2020-01-01",   # YYYY-MM-DD
    end_date="2023-12-31",     # YYYY-MM-DD
    frequency="d",              # 数据周期
    adjust_flag="2"            # 1=后复权, 2=前复权, 3=不复权（默认2）
)
```

**直接使用 BaoStockHandler**：

- 每次调用都会登录/登出 BaoStock
- 适合一次性数据获取，不缓存

```python
from utils.stock_data.data_source.baostock_handler import BaoStockHandler

handler = BaoStockHandler()
df = handler.get_history_k_data(
    code="sz.000651",          # 完整代码格式
    start_date="2020-01-01",
    end_date="2023-12-31",
    frequency="d",
    adjustflag="2"
)
```

### 2. 股票代码转换

使用 `get_full_code` 将6位代码转换为完整格式：

```python
from utils.stock_utils import get_full_code

code = get_full_code("000651")  # 返回 "sz.000651"
code = get_full_code("600000")  # 返回 "sh.600000"
```

**代码规则**：

- `60/68/90` → 上海 (sh)
- `00/30/20` → 深圳 (sz)
- `43/83/87` → 北京 (bj)

### 3. 转换为 Backtrader 格式

```python
from utils.stock_data.bt_adapter import load_data_to_bt

data = load_data_to_bt(
    symbol="000651",
    start_date="2020-01-01",
    end_date="2023-12-31",
    frequency="d"
)

# 用于 Backtrader
cerebro = bt.Cerebro()
cerebro.adddata(data)
```

## 数据周期


| 参数值  | 说明    | 适用场景    |
| ---- | ----- | ------- |
| `d`  | 日线    | 长期策略、回测 |
| `w`  | 周线    | 中长期分析   |
| `m`  | 月线    | 长期趋势分析  |
| `5`  | 5分钟线  | 日内交易    |
| `15` | 15分钟线 | 短期交易    |
| `30` | 30分钟线 | 短期交易    |
| `60` | 60分钟线 | 日内/短期交易 |


## 返回数据字段

**日线/周线/月线包含**：

- `date`: 日期（索引）
- `code`: 股票代码
- `open`, `high`, `low`, `close`: OHLC价格
- `preclose`: 前收盘价
- `volume`: 成交量
- `amount`: 成交额
- `pctChg`: 涨跌幅
- `turn`: 换手率
- `peTTM`, `pbMRQ`, `psTTM`, `pcfNcfTTM`: 财务指标
- `isST`: 是否ST股票

**分钟线包含**：

- `time`: 时间（索引）
- `date`: 日期
- `code`: 股票代码
- `open`, `high`, `low`, `close`: OHLC价格
- `volume`: 成交量
- `amount`: 成交额

## 使用示例

### 示例1：获取单只股票日线数据

```python
from utils.stock_data.data_handler import get_stock_data

df = get_stock_data("000651", "2020-01-01", "2023-12-31", "d")
print(df.head())
```

### 示例2：获取分钟线数据

```python
df = get_stock_data("000651", "2023-12-01", "2023-12-01", "60")
print(df.head())
```

### 示例3：批量获取多只股票

```python
symbols = ["000651", "600000", "000001"]
dfs = {}
for symbol in symbols:
    dfs[symbol] = get_stock_data(symbol, "2023-01-01", "2023-12-31", "d")
```

### 示例4：使用后复权数据

```python
from utils.stock_data.data_handler import DataHandler

handler = DataHandler()
df = handler.get_stock_data(
    symbol="000651",
    start_date="2020-01-01",
    end_date="2023-12-31",
    frequency="d",
    adjust_flag="1"  # 后复权
)
```

## 注意事项

1. **数据缓存**：`DataHandler` 会自动缓存数据到 `local_data/` 目录，避免重复下载
2. **交易日**：数据仅包含交易日，周末和节假日无数据
3. **网络连接**：首次获取数据需要网络连接，后续可从缓存读取
4. **数据格式**：返回的 DataFrame 以日期/时间为索引，已转换为数值类型
5. **BaoStock 限制**：免费数据可能有延迟，分钟线数据历史长度有限

## 错误处理

如果获取数据失败，检查：

- 股票代码是否正确
- 日期范围是否合理
- 网络连接是否正常
- BaoStock 服务是否可用

```python
try:
    df = get_stock_data("000651", "2020-01-01", "2023-12-31", "d")
    if df.empty:
        print("未获取到数据，请检查代码和日期范围")
except Exception as e:
    print(f"获取数据失败: {e}")
```

