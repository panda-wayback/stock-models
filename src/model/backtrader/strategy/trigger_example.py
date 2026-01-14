"""
触发频率选择示例策略
演示如何使用不同的数据频率进行触发判断
"""
from model.backtrader.strategy.base import BaseStrategy
import backtrader as bt


class TriggerExampleStrategy(BaseStrategy):
    """
    触发频率选择示例策略
    
    演示：
    1. 使用日线触发（trigger_frequency='d'）
    2. 使用分时触发（trigger_frequency='5', '15', '30', '60'）
    3. 使用主数据源触发（trigger_frequency=None，默认）
    """
    
    params = (
        ('printlog', True),
        ('trigger_frequency', 'd'),  # 使用日线触发，可选：'d', '5', '15', '30', '60', None
    )
    
    def __init__(self):
        super().__init__()
        
        # 策略逻辑初始化
        # 注意：触发数据源会在第一次调用 get_trigger_data() 时自动初始化
    
    def next(self):
        """
        策略主逻辑
        
        注意：
        - backtrader 的 next() 总是由主数据源触发
        - 如果设置了 trigger_frequency，使用 should_trigger() 判断是否执行策略逻辑
        - 使用 get_trigger_data() 获取指定频率的数据源
        """
        # 1. 判断是否应该触发（基于 trigger_frequency）
        if not self.should_trigger():
            return  # 触发数据源没有更新，跳过
        
        # 2. 获取触发数据源
        trigger_data = self.get_trigger_data()
        
        # 3. 获取触发数据源的价格
        trigger_price = trigger_data.close[0]
        trigger_date = trigger_data.datetime.date(0)
        
        # 4. 获取其他数据源（如果需要）
        try:
            daily_data = self.get_data("000651_d")  # 日线数据
            daily_price = daily_data.close[0]
        except ValueError:
            daily_data = None
            daily_price = None
        
        # 5. 打印触发信息（用于调试）
        if self.params.printlog:
            trigger_name = self._trigger_data_name or 'main'
            self.log(
                f'触发数据源: {trigger_name}, 价格: {trigger_price:.2f}, 日期: {trigger_date}',
                doprint=True
            )
        
        # 6. 执行策略逻辑
        if self.order:
            return  # 有未完成的订单，跳过
        
        # 示例策略：简单的价格判断
        # 这里可以根据触发数据源的价格进行交易判断
        if not self.position:
            # 买入逻辑（基于触发数据源）
            if trigger_price < 10.0:  # 示例条件
                size = self.calculate_position_size(cash_ratio=0.5)
                if size > 0:
                    self.log(f'基于 {trigger_name} 触发买入，价格: {trigger_price:.2f}')
                    self.buy(size=size)
        else:
            # 卖出逻辑（基于触发数据源）
            if trigger_price > 12.0:  # 示例条件
                size = self.calculate_position_size(position_ratio=1.0)
                if size > 0:
                    self.log(f'基于 {trigger_name} 触发卖出，价格: {trigger_price:.2f}')
                    self.sell(size=size)


class DailyTriggerStrategy(BaseStrategy):
    """
    使用日线触发的策略示例
    """
    
    params = (
        ('printlog', False),
        ('trigger_frequency', 'd'),  # 使用日线触发
    )
    
    def next(self):
        """只在日线数据更新时执行策略逻辑"""
        if not self.should_trigger():
            return
        
        trigger_data = self.get_trigger_data()
        price = trigger_data.close[0]
        
        # 策略逻辑...
        if self.order:
            return
        
        # 示例：日线策略
        if not self.position and price < 10.0:
            self.buy_with_ratio(cash_ratio=0.5)


class MinuteTriggerStrategy(BaseStrategy):
    """
    使用分时触发的策略示例（5分钟线）
    """
    
    params = (
        ('printlog', False),
        ('trigger_frequency', '5'),  # 使用5分钟线触发
    )
    
    def next(self):
        """只在5分钟线数据更新时执行策略逻辑"""
        if not self.should_trigger():
            return
        
        trigger_data = self.get_trigger_data()
        price = trigger_data.close[0]
        
        # 策略逻辑...
        if self.order:
            return
        
        # 示例：分时策略
        if not self.position and price < 10.0:
            self.buy_with_ratio(cash_ratio=0.3)
