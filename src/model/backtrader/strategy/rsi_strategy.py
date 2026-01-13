"""
RSI 策略示例
"""
import backtrader as bt
from model.backtrader.strategy.base import BaseStrategy
from model.backtrader.trigger.signal_trigger import ThresholdSignal


class RSIStrategy(BaseStrategy):
    """
    RSI 策略
    
    策略逻辑：
    - RSI < 30（超卖）→ 买入
    - RSI > 70（超买）→ 卖出
    """
    
    params = (
        ('rsi_period', 14),    # RSI 周期
        ('rsi_low', 30),        # RSI 超卖阈值
        ('rsi_high', 70),       # RSI 超买阈值
        ('printlog', False),
    )
    
    def __init__(self):
        super().__init__()
        
        # 计算 RSI
        self.rsi = bt.indicators.RSI(
            self.data.close,
            period=self.params.rsi_period
        )
        
        # RSI 信号
        self.oversold_signal = ThresholdSignal(
            self.rsi,
            self.params.rsi_low,
            above=False  # 低于阈值触发
        )
        self.overbought_signal = ThresholdSignal(
            self.rsi,
            self.params.rsi_high,
            above=True  # 超过阈值触发
        )
    
    def next(self):
        """策略主逻辑"""
        # 如果有未完成的订单，跳过
        if self.order:
            return
        
        # 检查超卖信号（买入）
        if self.oversold_signal.check():
            if not self.position:
                self.log(f'RSI 超卖 ({self.rsi[0]:.2f})，买入')
                self.buy()
        
        # 检查超买信号（卖出）
        elif self.overbought_signal.check():
            if self.position:
                self.log(f'RSI 超买 ({self.rsi[0]:.2f})，卖出')
                self.sell()
