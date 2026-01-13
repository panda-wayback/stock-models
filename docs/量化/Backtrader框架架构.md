# Backtrader 框架架构设计

## 一、整体架构

### 1.1 三层架构

```
┌─────────────────────────────────────────┐
│           策略层 (Strategy)              │
│  - 量化模型实现                          │
│  - 交易逻辑                              │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│           触发层 (Trigger)                │
│  - 信号触发 (SignalTrigger)              │
│  - 定时触发 (TimeTrigger)                │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│           核心层 (Core)                   │
│  - Broker 配置 (印花税、手续费、T+1)     │
│  - 回测引擎 (BacktestEngine)              │
│  - 数据适配 (DataAdapter)                │
└─────────────────────────────────────────┘
```

### 1.2 模块职责

| 模块 | 职责 | 关键类 |
|------|------|--------|
| **core** | 核心处理 | `BacktestEngine`, `ChinaStockCommInfo` |
| **strategy** | 策略实现 | `BaseStrategy` |
| **trigger** | 触发机制 | `SignalTrigger`, `TimeTrigger` |

---

## 二、核心处理层

### 2.1 Broker 配置

#### 费用计算

```python
# 手续费计算
commission = value * commission_rate
if commission < min_commission:
    commission = min_commission

# 印花税计算（仅卖出）
if is_sell:
    stamp_tax = value * stamp_tax_rate
else:
    stamp_tax = 0

# 总费用
total_cost = commission + stamp_tax
```

#### T+1 限制实现

**方案1：策略层检查（当前实现）**
- 在 `BaseStrategy` 中记录买入日期
- 卖出前检查是否有当天买入
- 优点：实现简单
- 缺点：不够精确（无法跟踪每笔买入的数量）

**方案2：Broker 层检查（推荐用于生产）**
- 在 `Broker` 中维护持仓成本记录
- 跟踪每笔买入的日期和数量
- 卖出时优先卖出最早买入的股票
- 优点：精确，符合实际交易规则
- 缺点：实现复杂

### 2.2 回测引擎

#### 设计模式：建造者模式

```python
engine = BacktestEngine(...)  # 创建引擎
engine.add_data(...)          # 添加数据
engine.add_strategy(...)      # 添加策略
engine.add_analyzer(...)      # 添加分析器
result = engine.run()          # 运行回测
```

**优点**：
- 链式调用，代码简洁
- 灵活配置，易于扩展

### 2.3 数据适配器

#### 数据流

```
BaoStock API
    ↓
DataHandler (缓存)
    ↓
DataFrame (项目格式)
    ↓
DataAdapter (转换)
    ↓
Backtrader PandasData
```

---

## 三、策略层

### 3.1 策略基类设计

#### 职责分离

```python
class BaseStrategy:
    # 1. 数据访问
    - get_current_price()
    - get_history_data()
    
    # 2. 交易操作
    - buy()
    - sell()
    - close()
    
    # 3. 订单管理
    - notify_order()
    - notify_trade()
    
    # 4. 日志记录
    - log()
    
    # 5. T+1 检查
    - can_sell_today()
```

### 3.2 策略开发模式

#### 模板方法模式

```python
class BaseStrategy:
    def next(self):
        # 模板方法：定义算法骨架
        raise NotImplementedError

class MyStrategy(BaseStrategy):
    def next(self):
        # 具体实现：填充算法细节
        pass
```

---

## 四、触发机制

### 4.1 信号触发

#### 设计模式：观察者模式

```python
# 注册信号
trigger.register_signal('buy', condition_func)

# 检查信号
if trigger.check_signal('buy'):  # 检测上升沿
    execute_buy()
```

#### 信号类型

1. **交叉信号** (`CrossoverSignal`)
   - 金叉/死叉检测
   - 适用于均线交叉策略

2. **阈值信号** (`ThresholdSignal`)
   - 超买/超卖检测
   - 适用于 RSI、MACD 等指标

3. **自定义信号** (`SignalTrigger`)
   - 灵活的条件函数
   - 适用于复杂策略

### 4.2 定时触发

#### 应用场景

1. **每日触发**
   - 开盘/收盘操作
   - 定时调仓

2. **每周触发**
   - 周度复盘
   - 定期检查

3. **交易时间触发**
   - 盘中操作
   - 时段策略

---

## 五、最佳实践

### 5.1 策略设计原则

#### SOLID 原则

1. **单一职责**：每个策略类只负责一种策略逻辑
2. **开闭原则**：通过继承扩展，而非修改基类
3. **里氏替换**：所有策略都可以替换 `BaseStrategy`
4. **接口隔离**：策略只需要实现 `next()` 方法
5. **依赖倒置**：策略依赖抽象的 `BaseStrategy`

#### 代码组织

```
strategy/
├── base.py              # 基类（稳定）
├── sma_cross.py         # 双均线策略
├── rsi.py              # RSI 策略
└── custom/             # 自定义策略
    ├── strategy1.py
    └── strategy2.py
```

### 5.2 性能优化

#### 1. 指标计算

```python
# ✅ 推荐：在 __init__ 中计算（只计算一次）
def __init__(self):
    self.sma = bt.indicators.SMA(self.data.close, period=20)

# ❌ 避免：在 next() 中重复计算
def next(self):
    sma = bt.indicators.SMA(self.data.close, period=20)  # 每次调用都计算
```

#### 2. 数据访问

```python
# ✅ 推荐：缓存常用数据
def next(self):
    price = self.get_current_price()
    if price > 100 and price < 200:
        pass

# ❌ 避免：重复访问
def next(self):
    if self.data.close[0] > 100:
        if self.data.close[0] < 200:  # 重复访问
            pass
```

#### 3. 订单管理

```python
# ✅ 推荐：检查订单状态
def next(self):
    if self.order:
        return  # 等待订单完成
    self.buy()

# ❌ 避免：忽略订单状态
def next(self):
    self.buy()  # 可能重复下单
```

### 5.3 测试策略

#### 单元测试

```python
# 测试策略逻辑
def test_strategy():
    strategy = MyStrategy()
    # 模拟数据
    # 验证交易信号
    assert strategy.should_buy() == True
```

#### 回测验证

```python
# 小数据集快速测试
engine.add_data(
    symbol="000651",
    start_date="2024-12-01",  # 只用一个月
    end_date="2024-12-31",
    frequency="d"
)
```

---

## 六、扩展性设计

### 6.1 添加新策略

```python
# 1. 继承 BaseStrategy
class NewStrategy(BaseStrategy):
    def next(self):
        # 实现策略逻辑
        pass

# 2. 使用
engine.add_strategy(NewStrategy, param1=value1)
```

### 6.2 添加新触发机制

```python
# 1. 实现触发器
class CustomTrigger:
    def check(self):
        # 实现检查逻辑
        pass

# 2. 在策略中使用
class MyStrategy(BaseStrategy):
    def __init__(self):
        super().__init__()
        self.trigger = CustomTrigger()
    
    def next(self):
        if self.trigger.check():
            self.buy()
```

### 6.3 添加新分析器

```python
# 1. 使用 Backtrader 分析器
import backtrader.analyzers as btanalyzers

engine.add_analyzer(btanalyzers.SharpeRatio)
engine.add_analyzer(btanalyzers.DrawDown)

# 2. 获取结果
result = engine.run()
sharpe = result['SharpeRatio'].get_analysis()
```

---

## 七、总结

### 7.1 设计优势

1. **模块化**：核心、策略、触发分离，易于维护
2. **可扩展**：通过继承和组合扩展功能
3. **符合规则**：自动处理 A 股交易规则
4. **易于使用**：提供简洁的 API

### 7.2 适用场景

- ✅ 单股票策略回测
- ✅ 多股票策略回测
- ✅ 分钟级/日线级策略
- ✅ 技术指标策略
- ✅ 量化模型验证

### 7.3 未来改进

1. **更精确的 T+1**：实现持仓成本记录
2. **更多分析器**：集成更多性能指标
3. **可视化**：增强图表功能
4. **参数优化**：集成参数优化工具
5. **实盘对接**：支持实盘交易接口

---

## 八、参考资源

- [Backtrader 官方文档](https://www.backtrader.com/)
- [最佳实践文档](./Backtrader框架最佳实践.md)
- [使用示例](../src/model/example.py)
