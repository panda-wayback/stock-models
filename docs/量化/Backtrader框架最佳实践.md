# Backtrader 框架最佳实践

## 目录

1. [框架架构](#框架架构)
2. [核心处理](#核心处理)
3. [策略开发](#策略开发)
4. [触发机制](#触发机制)
5. [最佳实践](#最佳实践)
6. [常见问题](#常见问题)

---

## 框架架构

### 模块结构

```
src/model/
├── core/              # 核心处理模块
│   ├── broker.py      # Broker 配置（印花税、手续费、T+1）
│   ├── comm_info.py  # 手续费和印花税计算
│   ├── engine.py      # 回测引擎
│   └── data_adapter.py # 数据适配器
├── strategy/          # 策略库
│   ├── base.py        # 策略基类
│   ├── sma_cross_strategy.py  # 示例策略
│   └── rsi_strategy.py        # 示例策略
└── trigger/          # 触发机制
    ├── signal_trigger.py  # 信号触发
    └── time_trigger.py    # 定时触发
```

### 设计原则

1. **关注点分离**：核心处理、策略、触发机制独立
2. **易于扩展**：通过继承和组合扩展功能
3. **符合A股规则**：自动处理印花税、T+1等限制
4. **统一接口**：提供简洁的 API

---

## 核心处理

### 1. Broker 配置

#### 手续费和印花税

```python
from model.core.engine import BacktestEngine

engine = BacktestEngine(
    initial_cash=100000.0,
    commission=0.0003,      # 手续费 0.03%（买入和卖出都收取）
    stamp_tax=0.001,        # 印花税 0.1%（仅卖出时收取）
    min_commission=5.0,      # 最小手续费 5元
)
```

**费用计算规则**：
- **手续费**：买入和卖出都收取，默认 0.03%（万三）
- **印花税**：仅卖出时收取，默认 0.1%
- **最小手续费**：单笔交易手续费不足 5 元时，按 5 元收取

#### T+1 限制

框架自动处理 T+1 限制：

```python
from model.strategy.base import BaseStrategy

class MyStrategy(BaseStrategy):
    def next(self):
        # 买入
        self.buy()
        
        # 同一天尝试卖出会被拒绝
        self.sell()  # 会被自动拒绝（T+1限制）
```

**T+1 实现原理**：
- 策略基类记录每笔买入的日期
- 卖出前检查是否有当天买入的股票
- 如果有，自动拒绝卖出订单

### 2. 数据适配

#### 从数据源加载

```python
engine = BacktestEngine()
engine.add_data(
    symbol="000651",
    start_date="2024-01-01",
    end_date="2024-12-31",
    frequency="d"  # d=日线, 5=5分钟, 15=15分钟等
)
```

#### 使用 DataFrame

```python
import pandas as pd

df = get_stock_data("000651", "2024-01-01", "2024-12-31", "d")
engine.add_data(df=df, name="000651")
```

---

## 策略开发

### 1. 继承 BaseStrategy

```python
from model.strategy.base import BaseStrategy

class MyStrategy(BaseStrategy):
    params = (
        ('param1', 10),
        ('printlog', False),
    )
    
    def __init__(self):
        super().__init__()
        # 初始化指标等
    
    def next(self):
        # 策略主逻辑
        pass
```

### 2. 数据访问

```python
def next(self):
    # 当前价格
    price = self.get_current_price()
    
    # 历史数据
    history = self.get_history_data(lookback=30)
    prices = history['close']
    volumes = history['volume']
    
    # 或直接获取价格列表
    prices = self.get_history_prices(lookback=30)
```

### 3. 交易操作

```python
def next(self):
    # 买入
    if 买入条件:
        self.buy(size=100)  # 买入100股
    
    # 卖出
    if 卖出条件:
        self.sell(size=100)  # 卖出100股
    
    # 平仓
    if 平仓条件:
        self.close()  # 卖出全部持仓
```

### 4. 订单管理

```python
def next(self):
    # 检查是否有未完成的订单
    if self.order:
        return  # 等待订单完成
    
    # 下单
    self.buy()
```

### 5. 日志记录

```python
def next(self):
    # 普通日志（受 printlog 参数控制）
    self.log('这是一条日志')
    
    # 强制打印（忽略 printlog 参数）
    self.log('重要信息', doprint=True)
```

---

## 触发机制

### 1. 信号触发

#### 交叉信号（金叉/死叉）

```python
from model.trigger.signal_trigger import CrossoverSignal

class MyStrategy(BaseStrategy):
    def __init__(self):
        super().__init__()
        self.fast_ma = bt.indicators.SMA(self.data.close, period=5)
        self.slow_ma = bt.indicators.SMA(self.data.close, period=20)
        
        # 交叉信号
        self.crossover = CrossoverSignal(self.fast_ma, self.slow_ma)
    
    def next(self):
        # 检查金叉
        if self.crossover.check_golden_cross():
            self.buy()
        
        # 检查死叉
        if self.crossover.check_death_cross():
            self.sell()
```

#### 阈值信号

```python
from model.trigger.signal_trigger import ThresholdSignal

class MyStrategy(BaseStrategy):
    def __init__(self):
        super().__init__()
        self.rsi = bt.indicators.RSI(self.data.close, period=14)
        
        # RSI 超卖信号（低于30触发）
        self.oversold = ThresholdSignal(self.rsi, 30, above=False)
    
    def next(self):
        if self.oversold.check():  # 检测上升沿
            self.buy()
```

#### 自定义信号

```python
from model.trigger.signal_trigger import SignalTrigger

class MyStrategy(BaseStrategy):
    def __init__(self):
        super().__init__()
        self.trigger = SignalTrigger()
        
        # 注册自定义信号
        self.trigger.register_signal(
            'buy_signal',
            lambda: self.data.close[0] > self.data.close[-1] * 1.02
        )
    
    def next(self):
        if self.trigger.check_signal('buy_signal'):
            self.buy()
```

### 2. 定时触发

```python
from model.trigger.time_trigger import TimeTrigger
from datetime import time

class MyStrategy(BaseStrategy):
    def __init__(self):
        super().__init__()
        self.time_trigger = TimeTrigger()
        
        # 每天 9:30 触发
        self.time_trigger.add_daily_trigger(
            time(9, 30),
            self.on_market_open,
            "市场开盘"
        )
    
    def on_market_open(self, dt):
        """市场开盘回调"""
        self.log(f'市场开盘: {dt}')
        # 执行开盘逻辑
    
    def next(self):
        # 检查定时触发
        current_dt = self.data.datetime.datetime(0)
        self.time_trigger.check_and_trigger(current_dt)
```

---

## 最佳实践

### 1. 策略设计

#### ✅ 推荐做法

```python
class GoodStrategy(BaseStrategy):
    params = (
        ('fast_period', 5),
        ('slow_period', 20),
        ('printlog', False),
    )
    
    def __init__(self):
        super().__init__()
        # 在 __init__ 中初始化指标（只计算一次）
        self.fast_ma = bt.indicators.SMA(
            self.data.close,
            period=self.params.fast_period
        )
    
    def next(self):
        # 检查订单状态
        if self.order:
            return
        
        # 策略逻辑
        if 买入条件:
            self.buy()
```

#### ❌ 避免做法

```python
class BadStrategy(BaseStrategy):
    def next(self):
        # ❌ 不要在 next() 中重复计算指标
        fast_ma = bt.indicators.SMA(self.data.close, period=5)
        
        # ❌ 不要忽略订单状态
        self.buy()  # 可能重复下单
        
        # ❌ 不要在同一天买入后立即卖出
        self.buy()
        self.sell()  # 违反 T+1
```

### 2. 性能优化

#### 使用 Backtrader 内置指标

```python
# ✅ 推荐：使用内置指标（已优化）
self.sma = bt.indicators.SMA(self.data.close, period=20)
self.rsi = bt.indicators.RSI(self.data.close, period=14)

# ❌ 避免：手动计算（性能差）
def calculate_sma(prices, period):
    return sum(prices[-period:]) / period
```

#### 避免频繁的数据访问

```python
# ✅ 推荐：缓存常用数据
def next(self):
    current_price = self.get_current_price()
    # 多次使用 current_price
    
# ❌ 避免：重复访问
def next(self):
    if self.data.close[0] > 100:
        if self.data.close[0] < 200:  # 重复访问
            pass
```

### 3. 风险管理

#### 仓位管理

```python
def next(self):
    # 计算仓位大小（如总资金的 50%）
    cash = self.broker.getcash()
    price = self.get_current_price()
    size = int(cash * 0.5 / price / 100) * 100  # 按手（100股）买入
    
    if 买入条件:
        self.buy(size=size)
```

#### 止损止盈

```python
def next(self):
    if self.position:
        price = self.get_current_price()
        cost = self.position.price  # 持仓成本
        
        # 止损：亏损超过 5%
        if price < cost * 0.95:
            self.close()
        
        # 止盈：盈利超过 10%
        if price > cost * 1.10:
            self.close()
```

### 4. 代码组织

#### 策略文件结构

```
src/model/strategy/
├── base.py                    # 基类
├── sma_cross_strategy.py      # 双均线策略
├── rsi_strategy.py           # RSI 策略
└── my_custom_strategy.py     # 自定义策略
```

#### 策略命名规范

- 文件名：`小写_下划线.py`（如 `sma_cross_strategy.py`）
- 类名：`大驼峰`（如 `SMACrossStrategy`）
- 参数：`小写_下划线`（如 `fast_period`）

### 5. 测试和调试

#### 使用 printlog 参数

```python
# 开发阶段：开启日志
engine.add_strategy(
    MyStrategy,
    printlog=True  # 查看详细日志
)

# 生产阶段：关闭日志
engine.add_strategy(
    MyStrategy,
    printlog=False  # 提高性能
)
```

#### 小数据集测试

```python
# 先用小数据集测试
engine.add_data(
    symbol="000651",
    start_date="2024-12-01",  # 只用一个月数据
    end_date="2024-12-31",
    frequency="d"
)
```

---

## 常见问题

### Q1: 如何实现更精确的 T+1 限制？

**A**: 当前实现是简化版本。如果需要更精确的 T+1（跟踪每笔买入的日期），可以：

1. 维护持仓成本记录（每笔买入的日期和数量）
2. 卖出时优先卖出最早买入的股票
3. 参考 `T1Broker` 类的实现思路

### Q2: 如何添加更多分析器？

**A**: 使用 `add_analyzer()` 方法：

```python
import backtrader.analyzers as btanalyzers

engine.add_analyzer(btanalyzers.SharpeRatio)
engine.add_analyzer(btanalyzers.DrawDown)

result = engine.run()
sharpe = result['SharpeRatio'].get_analysis()
```

### Q3: 如何处理多只股票？

**A**: 添加多个数据源：

```python
engine.add_data(symbol="000651", ...)
engine.add_data(symbol="600000", ...)

# 在策略中访问多个数据源
def next(self):
    data1 = self.datas[0]  # 第一只股票
    data2 = self.datas[1]  # 第二只股票
```

### Q4: 如何保存回测结果？

**A**: 使用分析器或自定义记录：

```python
# 方法1：使用分析器
engine.add_analyzer(btanalyzers.TradeAnalyzer)
result = engine.run()
trades = result['TradeAnalyzer'].get_analysis()

# 方法2：在策略中记录
class MyStrategy(BaseStrategy):
    def __init__(self):
        super().__init__()
        self.trades = []
    
    def notify_trade(self, trade):
        if trade.isclosed:
            self.trades.append({
                'pnl': trade.pnlcomm,
                'date': self.data.datetime.date(0)
            })
```

### Q5: 如何优化回测速度？

**A**: 
1. 使用较小的数据集测试
2. 关闭日志（`printlog=False`）
3. 避免在 `next()` 中进行复杂计算
4. 使用 Backtrader 内置指标而非手动计算

---

## 总结

本框架提供了：

1. **核心处理**：自动处理印花税、手续费、T+1 限制
2. **策略库**：基于 `BaseStrategy` 的便捷策略开发
3. **触发机制**：信号触发和定时触发
4. **统一接口**：简洁的 API，易于使用

遵循最佳实践，可以高效开发和管理量化交易策略。
