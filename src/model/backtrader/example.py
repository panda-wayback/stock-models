"""
Backtrader 框架使用示例
"""
from model.backtrader.core.engine import BacktestEngine
from model.backtrader.strategy.sma_cross_strategy import SMACrossStrategy
from model.backtrader.strategy.rsi_strategy import RSIStrategy


def example_sma_cross():
    """双均线交叉策略示例"""
    print("=" * 60)
    print("双均线交叉策略回测示例")
    print("=" * 60)
    
    # 创建回测引擎
    engine = BacktestEngine(
        initial_cash=100000.0,
        commission=0.0002,      # 手续费 0.02% 万分之二
        stamp_tax=0.001,        # 印花税 0.1% 千分之一
        min_commission=1.0,
        printlog=True
    )
    
    # 添加数据（方式1：单个数据源）
    # engine.add_data(
    #     symbol="000651",
    #     start_date="2024-01-01",
    #     end_date="2025-12-31",
    #     frequency="d"  # 日线
    # )
    
    # 添加数据（方式2：自动添加所有数据源，推荐）
    engine.add_stock_data(
        symbol="000651",
        start_date="2024-01-01",
        end_date="2025-12-31"
        # 默认添加：5分钟、15分钟、30分钟、60分钟、日线
        # 主数据源：5分钟（用于精确触发判断）
    )
    
    # 添加策略
    engine.add_strategy(
        SMACrossStrategy,
        fast_period=5,
        slow_period=20,
        buy_ratio=1.0,      # 使用100%现金买入
        sell_ratio=1.0,     # 卖出100%持仓
        printlog=True
    )
    
    # 运行回测
    result = engine.run()
    
    # 显示结果
    print("\n回测完成！")
    print(f"初始资金: {result['initial_cash']:,.2f}")
    print(f"最终资金: {result['final_value']:,.2f}")
    print(f"总收益率: {result['total_return']:.2f}%")
    
    return result


def example_rsi():
    """RSI 策略示例"""
    print("=" * 60)
    print("RSI 策略回测示例")
    print("=" * 60)
    
    # 创建回测引擎
    engine = BacktestEngine(
        initial_cash=100000.0,
        commission=0.0001, # 万分之1
        stamp_tax=0.001, # 千分之一
        min_commission=0.5,
        printlog=True
    )
    
    # 添加数据（自动添加所有数据源）
    engine.add_stock_data(
        symbol="000651",
        start_date="2025-01-01",
        end_date="2025-12-31"
        # 默认添加：5分钟、15分钟、30分钟、60分钟、日线
        # 主数据源：5分钟（用于精确触发判断）
    )
    
    # 添加策略
    engine.add_strategy(
        RSIStrategy,
        rsi_low=30,         # RSI 超卖阈值
        rsi_high=70,        # RSI 超买阈值
        buy_ratio=1.0,      # 使用100%现金买入
        sell_ratio=1.0,     # 卖出100%持仓
        printlog=True
    )
    
    # 运行回测
    result = engine.run()
    
    # 显示结果
    print("\n回测完成！")
    print(f"初始资金: {result['initial_cash']:,.2f}")
    print(f"最终资金: {result['final_value']:,.2f}")
    print(f"总收益率: {result['total_return']:.2f}%")
    
    return result


if __name__ == "__main__":
    # 运行示例
    # example_sma_cross()
    
    # 取消注释以运行 RSI 策略示例
    example_rsi()
