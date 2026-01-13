"""
简化版回测示例
演示如何使用自动添加数据源功能
"""
from model.backtrader.core.engine import BacktestEngine
from model.backtrader.strategy.rsi_strategy import RSIStrategy


def example_simple():
    """简化版回测示例 - 只需指定股票和日期"""
    print("=" * 60)
    print("简化版回测示例")
    print("=" * 60)
    
    # 创建回测引擎
    engine = BacktestEngine(
        initial_cash=100000.0,
        commission=0.0001,
        stamp_tax=0.001,
        min_commission=0.5,
        printlog=True
    )
    
    # 只需一行代码，自动添加所有数据源！
    engine.add_stock_data(
        symbol="000651",
        start_date="2025-01-01",
        end_date="2025-12-31"
    )
    # 默认会自动添加：
    # - 5分钟线（主数据源，用于精确触发判断）
    # - 15分钟线
    # - 30分钟线
    # - 60分钟线
    # - 日线（用于计算长期指标）
    
    # 添加策略
    engine.add_strategy(
        RSIStrategy,
        rsi_period=14,
        rsi_low=40,
        rsi_high=60,
        buy_ratio=1.0,
        sell_ratio=1.0,
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


def example_custom_frequencies():
    """自定义数据频率示例"""
    print("=" * 60)
    print("自定义数据频率示例")
    print("=" * 60)
    
    engine = BacktestEngine(printlog=True)
    
    # 只添加日线和周线，主数据源为日线
    engine.add_stock_data(
        symbol="000651",
        start_date="2025-01-01",
        end_date="2025-12-31",
        frequencies=["d", "w"],  # 只添加日线和周线
        main_frequency="d"        # 主数据源：日线
    )
    
    # 添加策略
    engine.add_strategy(RSIStrategy)
    
    # 运行回测
    result = engine.run()
    return result


if __name__ == "__main__":
    # 运行简化版示例
    example_simple()
    
    # 取消注释以运行自定义频率示例
    # example_custom_frequencies()
