"""
双均线交叉策略示例
"""
import backtrader as bt
from model.backtrader.strategy.base import BaseStrategy
from model.backtrader.trigger.signal_trigger import CrossoverSignal


class SMACrossStrategy(BaseStrategy):
    """
    双均线交叉策略
    
    策略逻辑：
    - 短期均线上穿长期均线（金叉）→ 买入
    - 短期均线下穿长期均线（死叉）→ 卖出
    """
    
    params = (
        ('fast_period', 5),   # 短期均线周期
        ('slow_period', 20),  # 长期均线周期
        ('buy_ratio', 1.0),   # 买入时使用的现金比例（0.0-1.0）
        ('sell_ratio', 1.0),  # 卖出时使用的持仓比例（0.0-1.0）
        ('printlog', False),
    )
    
    def __init__(self):
        super().__init__()
        
        # 计算均线
        self.fast_ma = bt.indicators.SMA(
            self.data.close,
            period=self.params.fast_period
        )
        self.slow_ma = bt.indicators.SMA(
            self.data.close,
            period=self.params.slow_period
        )
        
        # 交叉信号
        self.crossover = CrossoverSignal(self.fast_ma, self.slow_ma)
    
    def next(self):
        """策略主逻辑"""
        # 如果有未完成的订单，跳过
        if self.order:
            return
        
        # 检查金叉（买入信号）
        if self.crossover.check_golden_cross():
            if not self.position:
                # 计算买入数量（使用指定比例的现金）
                size = self.calculate_position_size(cash_ratio=self.params.buy_ratio)
                if size > 0:
                    self.log(f'金叉信号，买入 {size} 股（使用 {self.params.buy_ratio*100:.0f}% 现金）')
                    self.buy(size=size)
                # 或使用便捷方法
                # self.buy_with_ratio(cash_ratio=self.params.buy_ratio)
        
        # 检查死叉（卖出信号）
        elif self.crossover.check_death_cross():
            if self.position:
                # 计算卖出数量（卖出指定比例的持仓）
                size = self.calculate_position_size(position_ratio=self.params.sell_ratio)
                if size > 0:
                    self.log(f'死叉信号，卖出 {size} 股（卖出 {self.params.sell_ratio*100:.0f}% 持仓）')
                    self.sell(size=size)
                # 或使用便捷方法
                # self.sell_with_ratio(position_ratio=self.params.sell_ratio)
