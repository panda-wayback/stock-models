# Backtrader 量化交易框架

基于 Backtrader 的中国A股量化交易框架，提供核心处理、策略库和触发机制。

## 快速开始

### 1. 基本使用

```python
from model.backtrader.core.engine import BacktestEngine
from model.backtrader.strategy.sma_cross_strategy import SMACrossStrategy

# 创建回测引擎
engine = BacktestEngine(
    initial_cash=100000.0,
    commission=0.0003,      # 手续费 0.03%
    stamp_tax=0.001,        # 印花税 0.1%
    printlog=True
)

# 添加数据
engine.add_data(
    symbol="000651",
    start_date="2024-01-01",
    end_date="2024-12-31",
    frequency="d"
)

# 添加策略
engine.add_strategy(
    SMACrossStrategy,
    fast_period=5,
    slow_period=20
)

# 运行回测
result = engine.run()
print(f"总收益率: {result['total_return']:.2f}%")
```

### 2. 简化导入（推荐）

```python
# 使用框架提供的统一接口
from model.backtrader import BacktestEngine, BaseStrategy
from model.backtrader.strategy.sma_cross_strategy import SMACrossStrategy

# 使用方式同上
```

## 核心功能

### 1. 核心处理

- **印花税**：卖出时自动收取 0.1%
- **手续费**：买入和卖出都收取（默认 0.03%）
- **T+1 限制**：自动处理，当天买入不能当天卖出
- **最小手续费**：单笔交易手续费不足 5 元时，按 5 元收取

### 2. 策略库

- `BaseStrategy`：策略基类，提供便捷的数据访问和交易接口
- 示例策略：`SMACrossStrategy`、`RSIStrategy`

### 3. 触发机制

- **信号触发**：交叉信号、阈值信号、自定义信号
- **定时触发**：每日触发、每周触发、交易时间触发

## 目录结构

```
backtrader/
├── core/              # 核心处理模块
│   ├── broker.py      # Broker 配置
│   ├── comm_info.py  # 手续费和印花税
│   ├── engine.py      # 回测引擎
│   └── data_adapter.py # 数据适配器
├── strategy/          # 策略库
│   ├── base.py        # 策略基类
│   ├── sma_cross_strategy.py
│   └── rsi_strategy.py
└── trigger/          # 触发机制
    ├── signal_trigger.py
    └── time_trigger.py
```

## 详细文档

- [最佳实践文档](../../docs/量化/Backtrader框架最佳实践.md)
- [架构设计文档](../../docs/量化/Backtrader框架架构.md)

## 示例

运行示例：

```bash
python -m model.backtrader.example
```

## 注意事项

1. **T+1 限制**：框架自动处理，无需手动检查
2. **数据格式**：使用项目的数据获取接口，自动转换为 Backtrader 格式
3. **订单管理**：确保在 `next()` 中检查 `self.order` 状态，避免重复下单
4. **性能优化**：使用 Backtrader 内置指标，避免在 `next()` 中进行复杂计算
