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
                self.log(f'金叉信号，买入')
                self.buy()
        
        # 检查死叉（卖出信号）
        elif self.crossover.check_death_cross():
            if self.position:
                self.log(f'死叉信号，卖出')
                self.sell()
