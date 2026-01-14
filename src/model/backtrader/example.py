"""
Backtrader 框架使用示例
"""
from model.backtrader.core.engine import BacktestEngine
from model.backtrader.strategy.hydro_cost_dynamics import HCDStrategy


def example_hcd():
    """HCD (Hydro-Cost Dynamics) 策略示例"""
    print("=" * 60)
    print("HCD 资金能流策略回测示例")
    print("=" * 60)
    
    # 设置触发频率
    trigger_frequency = "d"  # 触发频率：d=日线, 5=5分钟, 15=15分钟, 60=60分钟
    
    # 创建回测引擎（传入 trigger_frequency 参数）
    engine = BacktestEngine(
        initial_cash=100000.0,
        commission=0.0002,      # 手续费 0.02% 万分之二
        stamp_tax=0.001,     # 印花税 0.1% 千分之一
        min_commission=1.0,
        printlog=True,
        trigger_frequency=trigger_frequency  # 触发频率：控制 backtrader 的主数据源
    )
    
    # 添加所有数据源（所有频率的数据都会被添加）
    # 但只有 trigger_frequency 指定的频率会作为主数据源触发 next()
    engine.add_stock_data(
        symbol="000651",
        start_date="2025-01-01",
        end_date="2025-12-31"
        # 默认添加：5分钟、15分钟、30分钟、60分钟、日线
        # 主数据源由 trigger_frequency 决定
    )
    
    # 添加策略
    engine.add_strategy(
        HCDStrategy,
        trigger_frequency=trigger_frequency,  # 触发频率（传递给策略）
        printlog=True                         # 打印交易日志
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
    # example_rsi()
    
    # 运行 HCD 策略示例
    example_hcd()
