"""
多数据源回测示例
演示如何使用日线、分时、周线等多种数据源
"""
from model.backtrader.core.engine import BacktestEngine
from model.backtrader.strategy.multi_data_strategy import SimpleMultiDataStrategy


def example_multi_data():
    """多数据源策略示例"""
    print("=" * 60)
    print("多数据源策略回测示例")
    print("=" * 60)
    
    # 创建回测引擎
    engine = BacktestEngine(
        initial_cash=100000.0,
        commission=0.0001,      # 手续费 0.01%
        stamp_tax=0.001,        # 印花税 0.1%
        min_commission=0.5,
        printlog=True
    )
    
    # 自动添加所有数据源（推荐方式）
    engine.add_stock_data(
        symbol="000651",
        start_date="2025-01-01",
        end_date="2025-12-31"
    )
    # 默认自动添加：5分钟、15分钟、30分钟、60分钟、日线
    # 主数据源：5分钟（用于精确触发判断）
    
    # 或者手动添加（如果需要自定义）
    # engine.add_data(symbol="000651", ..., frequency="60", is_main=True)
    # engine.add_data(symbol="000651", ..., frequency="d", name="000651_d")
    
    # 添加策略
    engine.add_strategy(
        SimpleMultiDataStrategy,
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
    example_multi_data()
