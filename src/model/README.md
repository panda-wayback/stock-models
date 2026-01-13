# Backtrader 回测框架使用指南

这是一个便捷的 Backtrader 回测框架，提供了简单易用的接口来编写和测试交易策略。

## 核心组件

### 1. BacktestFramework - 回测框架类

提供统一的回测接口，简化回测流程。

```python
from model.backtest_framework import BacktestFramework

# 创建框架
framework = BacktestFramework(
    initial_cash=100000.0,  # 初始资金
    commission=0.00002,      # 手续费率
    printlog=True           # 是否打印日志
)

# 运行回测
result = framework.run_backtest(
    symbol='000651',
    start_date='2024-01-01',
    end_date='2024-12-31',
    frequency='d',  # 'd'=日线, '5'=5分钟, '15'=15分钟, '30'=30分钟, '60'=60分钟
    strategy_class=YourStrategy,
    strategy_params={'param1': value1, 'param2': value2}
)
```

### 2. BaseStrategy - 策略基类

所有策略都应该继承自 `BaseStrategy`，它提供了便捷的数据访问接口。

## 策略编写指南

### 基本结构

```python
from model.backtest_framework import BaseStrategy

class MyStrategy(BaseStrategy):
    params = (
        ('param1', 10),
        ('param2', 20),
    )

    def __init__(self):
        super().__init__()
        # 初始化指标等

    def next(self):
        # 策略主逻辑（每分钟/每天触发）
        pass
```

### 访问历史数据

```python
def next(self):
    # 获取最近30个周期的历史数据
    history = self.get_history_data(lookback=30)
    prices = history['close']      # 收盘价列表
    volumes = history['volume']    # 成交量列表
    highs = history['high']        # 最高价列表
    lows = history['low']          # 最低价列表
    datetimes = history['datetime'] # 时间列表
    
    # 或者直接获取价格列表
    prices = self.get_history_prices(lookback=30)
    volumes = self.get_history_volumes(lookback=30)
```

### 计算和存储自定义指标

```python
def next(self):
    history = self.get_history_data(lookback=20)
    prices = history['close']
    
    # 计算指标
    avg_price = sum(prices[-10:]) / 10
    
    # 存储指标
    self.add_indicator('avg_price', avg_price)
    
    # 获取指标
    avg_price = self.get_indicator('avg_price', 0)  # 0是默认值
```

### 使用技术指标工具

```python
from model.indicators import calculate_rsi, calculate_macd, calculate_bollinger_bands

def next(self):
    history = self.get_history_data(lookback=50)
    prices = history['close']
    
    # 计算RSI
    rsi_list = calculate_rsi(prices, period=14)
    if rsi_list:
        current_rsi = rsi_list[-1]
    
    # 计算MACD
    macd_data = calculate_macd(prices, fast=12, slow=26, signal=9)
    if macd_data['macd']:
        macd_value = macd_data['macd'][-1]
        signal_value = macd_data['signal'][-1]
    
    # 计算布林带
    bb_data = calculate_bollinger_bands(prices, period=20, num_std=2.0)
    if bb_data['upper']:
        upper = bb_data['upper'][-1]
        middle = bb_data['middle'][-1]
        lower = bb_data['lower'][-1]
```

### 交易操作

```python
def next(self):
    # 获取当前数据
    current_price = self.get_current_price()
    current_volume = self.get_current_volume()
    current_time = self.get_current_datetime()
    
    # 检查持仓
    if self.has_position():
        position_size = self.get_position_size()
        # 卖出逻辑
        if some_condition:
            self.sell_all()  # 全仓卖出
            # 或
            self.sell(size=100)  # 卖出指定数量
    else:
        # 买入逻辑
        if some_condition:
            self.buy_all()  # 全仓买入
            # 或
            self.buy(size=100)  # 买入指定数量
    
    # 获取资金信息
    cash = self.get_available_cash()
    total_value = self.get_total_value()
```

### 日志记录

```python
def next(self):
    # 打印日志
    self.log('这是一条日志信息')
    self.log(f'当前价格: {self.get_current_price():.2f}')
    
    # 强制打印（即使 printlog=False）
    self.log('重要信息', doprint=True)
```

## 可用指标函数

`model.indicators` 模块提供了以下技术指标：

- `calculate_sma(prices, period)` - 简单移动平均线
- `calculate_ema(prices, period)` - 指数移动平均线
- `calculate_rsi(prices, period=14)` - 相对强弱指标
- `calculate_macd(prices, fast=12, slow=26, signal=9)` - MACD指标
- `calculate_bollinger_bands(prices, period=20, num_std=2.0)` - 布林带
- `calculate_volatility(prices, period=20)` - 波动率
- `calculate_atr(highs, lows, closes, period=14)` - 平均真实波幅

## 示例策略

- `example_strategy.py` - 基础策略示例
- `minute_strategy_example.py` - 分钟级策略示例
- `advanced_strategy_example.py` - 高级策略示例（使用多个指标）

## 注意事项

1. **T+1 限制**：A股市场当天买入不能当天卖出，框架会自动处理
2. **数据频率**：分钟级数据量大，建议先用较短时间范围测试
3. **指标计算**：确保有足够的历史数据再计算指标
4. **订单管理**：如果已有订单（`self.order`），不要重复下单

## 完整示例

```python
from model.backtest_framework import BacktestFramework, BaseStrategy
from model.indicators import calculate_rsi

class MyStrategy(BaseStrategy):
    params = (('rsi_period', 14),)
    
    def __init__(self):
        super().__init__()
    
    def next(self):
        if self.order:
            return
        
        # 获取历史数据
        history = self.get_history_data(lookback=30)
        prices = history['close']
        
        # 计算RSI
        rsi_list = calculate_rsi(prices, self.params.rsi_period)
        if not rsi_list:
            return
        
        current_rsi = rsi_list[-1]
        current_price = self.get_current_price()
        
        # 策略逻辑
        if self.has_position():
            if current_rsi > 70:  # 超买
                self.sell_all()
        else:
            if current_rsi < 30:  # 超卖
                self.buy_all()

# 运行回测
framework = BacktestFramework(initial_cash=100000.0)
result = framework.run_backtest(
    symbol='000651',
    start_date='2024-01-01',
    end_date='2024-12-31',
    frequency='d',
    strategy_class=MyStrategy
)
```
